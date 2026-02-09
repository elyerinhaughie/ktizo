"""Cluster-related WebSocket action handlers."""
import json
import logging
from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


async def _cluster_get(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import cluster as crud
        settings = crud.get_cluster_settings(db)
        if not settings:
            return await _ws._respond(ws, req_id, error="Cluster settings not found")
        await _ws._respond(ws, req_id, settings)
    finally:
        db.close()


async def _cluster_create(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import cluster as crud
        from app.schemas.cluster import ClusterSettingsCreate
        if not params.get("cluster_name", "").strip():
            return await _ws._respond(ws, req_id, error="Cluster name is required")
        existing = crud.get_cluster_settings(db)
        if existing:
            return await _ws._respond(ws, req_id, error="Cluster settings already exist. Use cluster.update.")
        created = crud.create_cluster_settings(db, ClusterSettingsCreate(**params))
        await _ws._respond(ws, req_id, created)
        await _ws._broadcast("cluster_updated", created)
    finally:
        db.close()


async def _cluster_update(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import cluster as cluster_crud, device as device_crud
        from app.schemas.cluster import ClusterSettingsUpdate
        from app.db.models import DeviceStatus

        if "cluster_name" in params and not params["cluster_name"].strip():
            return await _ws._respond(ws, req_id, error="Cluster name is required")

        settings_id = params.pop("settings_id")
        update_schema = ClusterSettingsUpdate(**params)
        updated = cluster_crud.update_cluster_settings(db, settings_id, update_schema)
        if not updated:
            return await _ws._respond(ws, req_id, error="Cluster settings not found")

        # kubectl version
        if update_schema.kubectl_version is not None:
            try:
                from app.services.kubectl_downloader import KubectlDownloader
                KubectlDownloader().set_kubectl_version(updated.kubectl_version)
            except Exception as e:
                logger.warning(f"kubectl version: {e}")

        # talosctl version
        if update_schema.talos_version is not None:
            try:
                from app.services.talosctl_downloader import TalosctlDownloader
                TalosctlDownloader().set_talosctl_version(updated.talos_version)
            except Exception as e:
                logger.warning(f"talosctl version: {e}")

        # Auto-regen configs
        try:
            from app.api.cluster_router import generate_cluster_config
            await generate_cluster_config(db)
            from app.services.config_generator import ConfigGenerator
            cg = ConfigGenerator()
            for d in device_crud.get_devices_by_status(db, DeviceStatus.APPROVED, 0, 1000):
                cg.generate_device_config(d)
        except Exception as e:
            logger.warning(f"Auto-regen after cluster update: {e}")

        await _ws.log_action(db, "updated_cluster_settings", "Cluster Settings",
            json.dumps({"cluster_name": updated.cluster_name, "kubernetes_version": updated.kubernetes_version}),
            "cluster_settings", str(settings_id))

        await _ws._respond(ws, req_id, updated)
        await _ws._broadcast("cluster_updated", updated)
    finally:
        db.close()


async def _cluster_generate_config(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.api.cluster_router import generate_cluster_config
        result = await generate_cluster_config(db)
        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("cluster_config_generated", {})
    finally:
        db.close()


async def _cluster_generate_secrets(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.api.cluster_router import generate_secrets
        from app.schemas.cluster import GenerateSecretsRequest
        result = await generate_secrets(GenerateSecretsRequest(**params), db)
        await _ws._respond(ws, req_id, _ws._serialize(result))
        await _ws._broadcast("cluster_secrets_generated", {})
    finally:
        db.close()


async def _cluster_bootstrap(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.api.cluster_router import bootstrap_cluster
        result = await bootstrap_cluster(db)
        await _ws._respond(ws, req_id, result)
        await _ws._broadcast("cluster_bootstrapped", {})
    finally:
        db.close()


async def _cluster_kubeconfig(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.api.cluster_router import download_kubeconfig
        result = await download_kubeconfig(db)
        # result is a Response object with kubeconfig content
        content = result.body.decode() if hasattr(result, 'body') else str(result)
        await _ws._respond(ws, req_id, {"kubeconfig": content})
    finally:
        db.close()


CLUSTER_ACTIONS = {
    "cluster.get": _cluster_get,
    "cluster.create": _cluster_create,
    "cluster.update": _cluster_update,
    "cluster.generate_config": _cluster_generate_config,
    "cluster.generate_secrets": _cluster_generate_secrets,
    "cluster.bootstrap": _cluster_bootstrap,
    "cluster.kubeconfig": _cluster_kubeconfig,
}
