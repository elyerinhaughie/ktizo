"""
Module (Helm) management handlers for WebSocket API.

Handles:
- Module catalog browsing
- Helm release installation/upgrade/uninstallation
- Repository management
- Installation logging and status tracking
"""

import json
import asyncio
import logging
import traceback
from typing import Optional
from pathlib import Path
from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# modules.* — Helm chart management
# ---------------------------------------------------------------------------

async def _modules_catalog(params: dict, ws: WebSocket, req_id: str):
    from app.services.module_catalog import get_catalog
    await _ws._respond(ws, req_id, get_catalog())


async def _modules_list(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import helm as crud
        releases = crud.get_helm_releases(db)
        await _ws._respond(ws, req_id, releases)
    finally:
        db.close()


async def _modules_get(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import helm as crud
        release = crud.get_helm_release(db, params["release_id"])
        if not release:
            return await _ws._respond(ws, req_id, error="Release not found")
        await _ws._respond(ws, req_id, release)
    finally:
        db.close()


async def _modules_install(params: dict, ws: WebSocket, req_id: str):
    """Install a helm chart. Creates DB record, responds immediately, runs helm in background."""
    import asyncio as _asyncio
    db = _ws._db()
    try:
        from app.crud import helm as crud
        from app.schemas.helm import HelmReleaseCreate

        from app.services.helm_runner import helm_runner
        namespace = params.get("namespace", "default")

        # Validate Redis topology and replica limits before install
        if params.get("catalog_id") == "redis" and params.get("values_json"):
            try:
                vals = json.loads(params["values_json"]) if isinstance(params["values_json"], str) else params["values_json"]
                replica_count = int(vals.get("replicaCount", 3))
                if replica_count > 12:
                    return await _ws._respond(ws, req_id,
                        error=f"Redis supports a maximum of 12 nodes through the wizard (got {replica_count}). "
                              f"Each node creates a PVC; with Longhorn replication this can quickly exhaust cluster storage.")
                if vals.get("architecture") == "cluster":
                    cluster_replica_count = int(vals.get("clusterReplicaCount", 0))
                    if replica_count < 3:
                        return await _ws._respond(ws, req_id,
                            error=f"Redis cluster requires at least 3 nodes (got {replica_count})")
                    divisor = cluster_replica_count + 1
                    if replica_count % divisor != 0:
                        masters = replica_count // divisor
                        return await _ws._respond(ws, req_id,
                            error=f"Invalid cluster topology: {replica_count} nodes with {cluster_replica_count} replicas per master "
                                  f"is not evenly divisible. Node count must be a multiple of {divisor} "
                                  f"(e.g., {divisor * max(3, masters)}, {divisor * (max(3, masters) + 1)}, {divisor * (max(3, masters) + 2)})")
            except (ValueError, TypeError):
                pass

        # Check for duplicate in our DB
        existing = crud.get_helm_release_by_name(db, params["release_name"])
        if existing:
            # If it's already deployed and tracked, don't allow re-install
            if existing.status == "deployed":
                return await _ws._respond(ws, req_id, error=f"Release '{params['release_name']}' is already deployed and tracked")
            # Stale/failed entry — clean it up so we can re-install or import
            crud.delete_helm_release(db, existing.id)

        # Check if release already exists in the cluster (installed outside Ktizo)
        helm_status = await helm_runner.get_status(params["release_name"], namespace)
        if helm_status:
            info = helm_status.get("info", {})
            return await _ws._respond(ws, req_id, {
                "conflict": "exists_in_cluster",
                "release_name": params["release_name"],
                "namespace": namespace,
                "chart": helm_status.get("chart", ""),
                "status": info.get("status", "unknown"),
                "revision": helm_status.get("version", 0),
                "app_version": info.get("app_version", ""),
            })

        release = crud.create_helm_release(db, HelmReleaseCreate(**params))
        await _ws._respond(ws, req_id, release)
        await _ws._broadcast("module_installing", {
            "id": release.id,
            "release_name": release.release_name,
            "chart_name": release.chart_name,
        })

        # Launch background task
        _asyncio.create_task(_do_helm_install(release.id, params))
    finally:
        db.close()


async def _do_helm_install(release_id: int, params: dict):
    """Background: repo add + helm install, update DB + broadcast with full log output."""
    from app.crud import helm as crud
    from app.services.helm_runner import helm_runner
    from datetime import datetime, timezone

    log_lines = []

    def _log(line: str):
        log_lines.append(line)
        logger.info(f"[module:{release_id}] {line}")

    async def _broadcast_log():
        await _ws._broadcast("module_log", {
            "id": release_id,
            "log": "\n".join(log_lines),
        })

    db = _ws._db()
    try:
        release = crud.get_helm_release(db, release_id)
        if not release:
            return

        release_name = release.release_name
        _log(f"Starting installation of {release_name}")
        _log(f"  Chart: {params.get('chart_name')}")
        _log(f"  Namespace: {params.get('namespace', 'default')}")
        _log(f"  Version: {params.get('chart_version') or 'latest'}")

        crud.update_helm_release_status(db, release_id, "deploying", "Installing...")
        await _ws._broadcast("module_status_changed", {
            "id": release_id, "release_name": release_name,
            "status": "deploying", "status_message": "Installing...",
        })
        await _broadcast_log()

        # Add repo if specified
        if params.get("repo_url") and params.get("repo_name"):
            _log(f"\n--- Adding helm repo: {params['repo_name']} ({params['repo_url']})")
            await _broadcast_log()
            ok, msg = await helm_runner.repo_add(params["repo_name"], params["repo_url"])
            _log(msg)
            if not ok:
                _log(f"\nFAILED: Repo add failed")
                full_log = "\n".join(log_lines)
                crud.update_helm_release_status(db, release_id, "failed", f"Repo add failed: {msg}", log_output=full_log)
                await _ws._broadcast("module_status_changed", {
                    "id": release_id, "release_name": release_name,
                    "status": "failed", "status_message": f"Repo add failed: {msg}",
                })
                await _broadcast_log()
                return

            _log("\n--- Updating helm repos")
            await _broadcast_log()
            ok_update, msg_update = await helm_runner.repo_update()
            _log(msg_update)
            await _broadcast_log()

        # Handle Talos disk partitions for modules that need them (e.g., Longhorn)
        if params.get("catalog_id") and params.get("values_json"):
            try:
                wizard_vals = json.loads(params["values_json"]) if isinstance(params["values_json"], str) else params["values_json"]

                # Determine if EPHEMERAL is capped (separate partition possible)
                ephemeral_capped = False
                try:
                    from app.crud import volume as volume_crud
                    volumes = volume_crud.get_volume_configs(db)
                    for v in volumes:
                        if v.name.value == "EPHEMERAL" and v.max_size:
                            ephemeral_capped = True
                            break
                except Exception:
                    pass

                if ephemeral_capped and wizard_vals.get("_partition.enabled"):
                    # EPHEMERAL is capped — create a separate partition for storage
                    mountpoint = wizard_vals.get("_partition.mountpoint", "/var/mnt/longhorn")
                    _ws._save_disk_partition(mountpoint)
                    await asyncio.to_thread(_ws._regenerate_all_device_configs, db)
                    _log(f"\n--- Created disk partition config: mountpoint={mountpoint}")
                    _log(f"    EPHEMERAL is capped — using dedicated partition")
                    await _broadcast_log()
                elif not ephemeral_capped and wizard_vals.get("_partition.enabled"):
                    # EPHEMERAL fills the disk — no room for a separate partition
                    # Override data path to use /var/lib/longhorn inside EPHEMERAL
                    data_path = "/var/lib/longhorn"
                    _log(f"\n--- EPHEMERAL fills disk — skipping partition, using {data_path}")
                    await _broadcast_log()

                    # Override defaultDataPath in values_yaml
                    existing_yaml = params.get("values_yaml") or ""
                    override_yaml = f"defaultSettings:\n  defaultDataPath: {data_path}"
                    if existing_yaml:
                        params["values_yaml"] = f"{existing_yaml}\n{override_yaml}"
                    else:
                        params["values_yaml"] = override_yaml

                    # Save partition entry for tracking (used by uninstall cleanup)
                    _ws._save_disk_partition(data_path)
            except Exception as e:
                _log(f"\nWARNING: Failed to apply disk partition config: {e}")
                await _broadcast_log()

        # Set privileged PodSecurity on namespace if required by catalog entry
        if params.get("catalog_id"):
            from app.services.module_catalog import get_catalog_entry
            catalog = get_catalog_entry(params["catalog_id"])
            if catalog and catalog.get("privileged_namespace"):
                _log(f"\n--- Labeling namespace as privileged: {params.get('namespace', 'default')}")
                await _broadcast_log()
                await _ws._label_namespace_privileged(params.get("namespace", "default"))

        # Run helm install
        _log(f"\n--- Running: helm install {params['release_name']} {params['chart_name']}")
        _log(f"    This may take several minutes...")
        await _broadcast_log()

        ok, msg = await helm_runner.install(
            release_name=params["release_name"],
            chart=params["chart_name"],
            namespace=params.get("namespace", "default"),
            version=params.get("chart_version"),
            values_yaml=params.get("values_yaml"),
        )

        _log(f"\n--- Helm output:")
        _log(msg)

        if ok:
            # Run post-install hooks for catalog modules
            post_install_msg = await _ws._run_post_install(params)
            deploy_msg = "Deployed successfully"
            if post_install_msg:
                deploy_msg += f". {post_install_msg}"
                _log(f"\n--- Post-install: {post_install_msg}")

            status_info = await helm_runner.get_status(params["release_name"], params.get("namespace", "default"))
            revision = None
            app_version = None
            if status_info and isinstance(status_info, dict):
                revision = status_info.get("version")
                info = status_info.get("info", {})
                if isinstance(info, dict):
                    app_version = info.get("app_version")

            _log(f"\nSUCCESS: {deploy_msg}")
            full_log = "\n".join(log_lines)
            crud.update_helm_release_status(
                db, release_id, "deployed", deploy_msg,
                revision=revision, app_version=app_version,
                deployed_at=datetime.now(timezone.utc),
                log_output=full_log,
            )
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "release_name": release_name,
                "status": "deployed", "status_message": deploy_msg,
            })
            await _broadcast_log()
            await _ws.log_action(db, "installed_module", "Modules",
                json.dumps({"release": params["release_name"], "chart": params["chart_name"],
                             "namespace": params.get("namespace", "default")}),
                "helm_release", str(release_id))
        else:
            _log(f"\nFAILED: {msg}")

            # Attempt cleanup of partial resources left by the failed install
            _log("\n--- Cleaning up failed installation...")
            await _broadcast_log()
            try:
                await helm_runner.force_uninstall(params["release_name"], params.get("namespace", "default"))
                _log("Cleanup completed (helm uninstall)")
            except Exception as cleanup_err:
                _log(f"Cleanup warning: {cleanup_err}")
            await _broadcast_log()

            full_log = "\n".join(log_lines)
            crud.update_helm_release_status(db, release_id, "failed", msg, log_output=full_log)
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "release_name": release_name,
                "status": "failed", "status_message": msg,
            })
            await _broadcast_log()
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Helm install error: {e}\n{tb}")
        _log(f"\nEXCEPTION: {e}\n{tb}")
        full_log = "\n".join(log_lines)
        try:
            crud.update_helm_release_status(db, release_id, "failed", str(e), log_output=full_log)
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "status": "failed", "status_message": str(e),
            })
            await _broadcast_log()
        except Exception:
            pass
    finally:
        db.close()


async def _modules_upgrade(params: dict, ws: WebSocket, req_id: str):
    """Upgrade a helm release. Similar async pattern."""
    import asyncio as _asyncio
    db = _ws._db()
    try:
        from app.crud import helm as crud
        release = crud.get_helm_release(db, params["release_id"])
        if not release:
            return await _ws._respond(ws, req_id, error="Release not found")

        # Update values in DB if provided
        if params.get("values_yaml") is not None:
            release.values_yaml = params["values_yaml"]
        if params.get("values_json") is not None:
            release.values_json = params["values_json"]
        if params.get("chart_version") is not None:
            release.chart_version = params["chart_version"]
        db.commit()

        await _ws._respond(ws, req_id, release)
        _asyncio.create_task(_do_helm_upgrade(release.id))
    finally:
        db.close()


async def _do_helm_upgrade(release_id: int):
    """Background: helm upgrade, update DB + broadcast with full log output."""
    from app.crud import helm as crud
    from app.services.helm_runner import helm_runner
    from datetime import datetime, timezone

    log_lines = []

    def _log(line: str):
        log_lines.append(line)
        logger.info(f"[module:{release_id}] {line}")

    async def _broadcast_log():
        await _ws._broadcast("module_log", {
            "id": release_id,
            "log": "\n".join(log_lines),
        })

    db = _ws._db()
    try:
        release = crud.get_helm_release(db, release_id)
        if not release:
            return

        release_name = release.release_name
        _log(f"Starting upgrade of {release_name}")
        _log(f"  Chart: {release.chart_name}")
        _log(f"  Namespace: {release.namespace}")
        _log(f"  Version: {release.chart_version or 'latest'}")

        crud.update_helm_release_status(db, release_id, "deploying", "Upgrading...")
        await _ws._broadcast("module_status_changed", {
            "id": release_id, "release_name": release_name,
            "status": "deploying", "status_message": "Upgrading...",
        })
        await _broadcast_log()

        # Re-add repo if needed
        if release.repo_url and release.repo_name:
            _log(f"\n--- Adding helm repo: {release.repo_name} ({release.repo_url})")
            await _broadcast_log()
            ok_repo, msg_repo = await helm_runner.repo_add(release.repo_name, release.repo_url)
            _log(msg_repo)
            await _broadcast_log()

            _log("\n--- Updating helm repos")
            await _broadcast_log()
            ok_update, msg_update = await helm_runner.repo_update()
            _log(msg_update)
            await _broadcast_log()

        _log(f"\n--- Running: helm upgrade {release_name} {release.chart_name}")
        _log(f"    This may take several minutes...")
        await _broadcast_log()

        ok, msg = await helm_runner.upgrade(
            release_name=release.release_name,
            chart=release.chart_name,
            namespace=release.namespace,
            version=release.chart_version,
            values_yaml=release.values_yaml,
        )

        _log(f"\n--- Helm output:")
        _log(msg)

        if ok:
            status_info = await helm_runner.get_status(release.release_name, release.namespace)
            revision = None
            app_version = None
            if status_info and isinstance(status_info, dict):
                revision = status_info.get("version")
                info = status_info.get("info", {})
                if isinstance(info, dict):
                    app_version = info.get("app_version")

            _log(f"\nSUCCESS: Upgraded successfully")
            full_log = "\n".join(log_lines)
            crud.update_helm_release_status(
                db, release_id, "deployed", "Upgraded successfully",
                revision=revision, app_version=app_version,
                deployed_at=datetime.now(timezone.utc),
                log_output=full_log,
            )
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "release_name": release_name,
                "status": "deployed", "status_message": "Upgraded successfully",
            })
            await _broadcast_log()
            await _ws.log_action(db, "upgraded_module", "Modules",
                json.dumps({"release": release_name, "chart": release.chart_name}),
                "helm_release", str(release_id))
        else:
            _log(f"\nFAILED: {msg}")
            full_log = "\n".join(log_lines)
            crud.update_helm_release_status(db, release_id, "failed", msg, log_output=full_log)
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "release_name": release_name,
                "status": "failed", "status_message": msg,
            })
            await _broadcast_log()
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Helm upgrade error: {e}\n{tb}")
        _log(f"\nEXCEPTION: {e}\n{tb}")
        full_log = "\n".join(log_lines)
        try:
            crud.update_helm_release_status(db, release_id, "failed", str(e), log_output=full_log)
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "status": "failed", "status_message": str(e),
            })
            await _broadcast_log()
        except Exception:
            pass
    finally:
        db.close()


async def _modules_cancel(params: dict, ws: WebSocket, req_id: str):
    """Force-fail a stuck deployment."""
    db = _ws._db()
    try:
        from app.crud import helm as crud
        release = crud.get_helm_release(db, params["release_id"])
        if not release:
            return await _ws._respond(ws, req_id, error="Release not found")

        crud.update_helm_release_status(db, release.id, "failed", "Cancelled by user")
        await _ws._respond(ws, req_id, release)
        await _ws._broadcast("module_status_changed", {
            "id": release.id, "release_name": release.release_name,
            "status": "failed", "status_message": "Cancelled by user",
        })
    finally:
        db.close()


async def _modules_force_delete(params: dict, ws: WebSocket, req_id: str):
    """Force-delete a release: quick helm uninstall attempt, then remove DB record immediately."""
    db = _ws._db()
    try:
        from app.crud import helm as crud
        from app.services.helm_runner import helm_runner

        release = crud.get_helm_release(db, params["release_id"])
        if not release:
            return await _ws._respond(ws, req_id, error="Release not found")

        release_name = release.release_name
        namespace = release.namespace

        # Best-effort quick helm uninstall (15s timeout, no --wait, no hooks)
        try:
            await helm_runner.force_uninstall(release_name, namespace)
        except Exception:
            pass

        # Clean up disk partition config if applicable
        if release.catalog_id and release.values_json:
            try:
                wizard_vals = json.loads(release.values_json)
                if wizard_vals.get("_partition.enabled"):
                    mountpoint = wizard_vals.get("_partition.mountpoint", "/var/mnt/longhorn")
                    _ws._remove_disk_partition(mountpoint)
                    await asyncio.to_thread(_ws._regenerate_all_device_configs, db)
            except Exception:
                pass

        crud.delete_helm_release(db, release.id)
        await _ws._respond(ws, req_id, {"message": f"Force-deleted {release_name}"})
        await _ws._broadcast("module_status_changed", {
            "id": release.id, "release_name": release_name,
            "status": "uninstalled", "status_message": "Force-deleted",
        })
        await _ws.log_action(db, "force_deleted_module", "Modules",
            json.dumps({"release": release_name}),
            "helm_release", str(release.id))
    finally:
        db.close()


async def _modules_uninstall(params: dict, ws: WebSocket, req_id: str):
    """Uninstall a helm release."""
    import asyncio as _asyncio
    db = _ws._db()
    try:
        from app.crud import helm as crud
        release = crud.get_helm_release(db, params["release_id"])
        if not release:
            return await _ws._respond(ws, req_id, error="Release not found")

        crud.update_helm_release_status(db, release.id, "uninstalling", "Uninstalling...")
        await _ws._respond(ws, req_id, release)
        await _ws._broadcast("module_status_changed", {
            "id": release.id, "release_name": release.release_name,
            "status": "uninstalling", "status_message": "Uninstalling...",
        })

        _asyncio.create_task(_do_helm_uninstall(release.id))
    finally:
        db.close()


async def _do_helm_uninstall(release_id: int):
    """Background: helm uninstall, clean up namespace, delete DB record + broadcast with full log output."""
    from app.crud import helm as crud
    from app.services.helm_runner import helm_runner

    log_lines = []

    def _log(line: str):
        log_lines.append(line)
        logger.info(f"[module:{release_id}] {line}")

    async def _broadcast_log():
        await _ws._broadcast("module_log", {
            "id": release_id,
            "log": "\n".join(log_lines),
        })

    db = _ws._db()
    try:
        release = crud.get_helm_release(db, release_id)
        if not release:
            return

        release_name = release.release_name
        chart_name = release.chart_name
        catalog_id = release.catalog_id
        namespace = release.namespace

        _log(f"Starting uninstall of {release_name}")
        _log(f"  Namespace: {namespace}")
        await _broadcast_log()

        _log(f"\n--- Running: helm uninstall {release_name} --namespace {namespace}")
        await _broadcast_log()
        ok, msg = await helm_runner.uninstall(release_name, namespace)
        _log(msg)
        await _broadcast_log()

        # Treat "not found" as success — release was already removed
        release_gone = ok or "not found" in (msg or "").lower()

        if release_gone:
            if not ok:
                _log("\nRelease already removed from helm, cleaning up remaining resources...")
                await _broadcast_log()

            # Clean up remaining resources in the namespace
            if namespace and namespace != "default" and namespace != "kube-system":
                try:
                    _log(f"\n--- Cleaning up namespace resources: {namespace}")
                    await _broadcast_log()
                    await _ws._delete_namespace_resources(namespace)
                    _log("Namespace cleanup completed")
                    await _broadcast_log()
                except Exception as e:
                    _log(f"WARNING: Namespace cleanup error: {e}")
                    await _broadcast_log()

            # Clean up Talos disk partition config if applicable
            if catalog_id and release.values_json:
                try:
                    wizard_vals = json.loads(release.values_json)
                    if wizard_vals.get("_partition.enabled"):
                        mountpoint = wizard_vals.get("_partition.mountpoint", "/var/mnt/longhorn")
                        _ws._remove_disk_partition(mountpoint)
                        await asyncio.to_thread(_ws._regenerate_all_device_configs, db)
                        _log(f"\n--- Removed disk partition config: mountpoint={mountpoint}")
                        await _broadcast_log()
                except Exception as e:
                    _log(f"WARNING: Failed to clean up disk partition config: {e}")
                    await _broadcast_log()

            status_msg = "Uninstalled successfully" if ok else "Release already removed, cleaned up"
            _log(f"\nSUCCESS: {status_msg}")
            full_log = "\n".join(log_lines)
            # Store log before deleting the release
            crud.update_helm_release_status(db, release_id, "uninstalling", status_msg, log_output=full_log)
            crud.delete_helm_release(db, release_id)
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "release_name": release_name,
                "status": "uninstalled", "status_message": status_msg,
            })
            await _broadcast_log()
            await _ws.log_action(db, "uninstalled_module", "Modules",
                json.dumps({"release": release_name, "chart": chart_name}),
                "helm_release", str(release_id))
        else:
            _log(f"\nFAILED: Uninstall failed: {msg}")
            full_log = "\n".join(log_lines)
            crud.update_helm_release_status(db, release_id, "failed", f"Uninstall failed: {msg}", log_output=full_log)
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "release_name": release_name,
                "status": "failed", "status_message": f"Uninstall failed: {msg}",
            })
            await _broadcast_log()
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Helm uninstall error: {e}\n{tb}")
        _log(f"\nEXCEPTION: {e}\n{tb}")
        full_log = "\n".join(log_lines)
        try:
            crud.update_helm_release_status(db, release_id, "failed", str(e), log_output=full_log)
            await _ws._broadcast("module_status_changed", {
                "id": release_id, "status": "failed", "status_message": str(e),
            })
            await _broadcast_log()
        except Exception:
            pass
    finally:
        db.close()


async def _modules_log(params: dict, ws: WebSocket, req_id: str):
    """Fetch stored log output for a helm release."""
    db = _ws._db()
    try:
        from app.crud import helm as crud
        release = crud.get_helm_release(db, params["release_id"])
        if not release:
            return await _ws._respond(ws, req_id, error="Release not found")
        await _ws._respond(ws, req_id, {"id": release.id, "release_name": release.release_name, "log": release.log_output or ""})
    finally:
        db.close()


async def _modules_repos_list(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import helm as crud
        repos = crud.get_helm_repositories(db)
        await _ws._respond(ws, req_id, repos)
    finally:
        db.close()


async def _modules_repos_add(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import helm as crud
        from app.services.helm_runner import helm_runner

        name = params["name"]
        url = params["url"]

        existing = crud.get_helm_repository_by_name(db, name)
        if existing:
            return await _ws._respond(ws, req_id, error=f"Repository '{name}' already exists")

        ok, msg = await helm_runner.repo_add(name, url)
        if not ok:
            return await _ws._respond(ws, req_id, error=f"Failed to add repo: {msg}")

        repo = crud.add_helm_repository(db, name, url)
        await _ws._respond(ws, req_id, repo)
    finally:
        db.close()


async def _modules_repos_delete(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import helm as crud
        deleted = crud.delete_helm_repository(db, params["repo_id"])
        if not deleted:
            return await _ws._respond(ws, req_id, error="Repository not found")
        await _ws._respond(ws, req_id, {"message": "Repository deleted"})
    finally:
        db.close()


async def _modules_import(params: dict, ws: WebSocket, req_id: str):
    """Import an existing cluster release into Ktizo's tracking DB."""
    from datetime import datetime, timezone
    db = _ws._db()
    try:
        from app.crud import helm as crud
        from app.db.models import HelmRelease
        from app.services.helm_runner import helm_runner

        release_name = params.get("release_name")
        namespace = params.get("namespace", "default")
        if not release_name:
            return await _ws._respond(ws, req_id, error="release_name is required")

        # Already tracked?
        existing = crud.get_helm_release_by_name(db, release_name)
        if existing:
            return await _ws._respond(ws, req_id, error=f"Release '{release_name}' is already tracked")

        # Verify it actually exists in the cluster
        helm_status = await helm_runner.get_status(release_name, namespace)
        if not helm_status:
            return await _ws._respond(ws, req_id, error=f"Release '{release_name}' not found in namespace '{namespace}'")

        info = helm_status.get("info", {})

        db_release = HelmRelease(
            release_name=release_name,
            namespace=namespace,
            chart_name=params.get("chart_name", helm_status.get("chart", "")),
            chart_version=params.get("chart_version"),
            catalog_id=params.get("catalog_id"),
            repo_name=params.get("repo_name"),
            repo_url=params.get("repo_url"),
            values_yaml=params.get("values_yaml"),
            values_json=params.get("values_json"),
            status="deployed" if info.get("status") == "deployed" else info.get("status", "deployed"),
            status_message="Imported from existing cluster release",
            revision=helm_status.get("version"),
            app_version=info.get("app_version"),
            deployed_at=datetime.now(timezone.utc),
        )
        db.add(db_release)
        db.commit()
        db.refresh(db_release)

        await _ws._respond(ws, req_id, db_release)
        await _ws._broadcast("module_status_changed", {
            "id": db_release.id,
            "release_name": db_release.release_name,
            "status": db_release.status,
        })
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Export action mapping
# ---------------------------------------------------------------------------

MODULE_ACTIONS = {
    "modules.catalog": _modules_catalog,
    "modules.list": _modules_list,
    "modules.get": _modules_get,
    "modules.install": _modules_install,
    "modules.import": _modules_import,
    "modules.upgrade": _modules_upgrade,
    "modules.cancel": _modules_cancel,
    "modules.force_delete": _modules_force_delete,
    "modules.uninstall": _modules_uninstall,
    "modules.log": _modules_log,
    "modules.repos.list": _modules_repos_list,
    "modules.repos.add": _modules_repos_add,
    "modules.repos.delete": _modules_repos_delete,
}
