"""CI/CD runner monitoring via ARC (Actions Runner Controller) CRDs.

Data is pushed to all connected clients via periodic broadcast events
(cicd_update) rather than polled by the frontend.
"""
import asyncio
import base64
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)

_ARC_CONTROLLER_NS = "arc-systems"
_BROADCAST_INTERVAL = 10  # seconds

# Background task handle
_broadcast_task: asyncio.Task | None = None

# GitHub PAT cache: "namespace/secret_name" -> (token, timestamp)
_github_token_cache: dict[str, tuple[str, float]] = {}
_GITHUB_TOKEN_CACHE_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# kubectl helpers
# ---------------------------------------------------------------------------

async def _kubectl_json(kubectl: str, *args, timeout: int = 15):
    """Run a kubectl command and return parsed JSON or (None, error_str)."""
    kubeconfig = str(Path.home() / ".kube" / "config")
    proc = await asyncio.create_subprocess_exec(
        kubectl, *args, "--kubeconfig", kubeconfig, "-o", "json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    if proc.returncode != 0:
        return None, stderr.decode().strip() or "kubectl command failed"
    try:
        return json.loads(stdout.decode()), None
    except json.JSONDecodeError:
        return None, "Failed to parse kubectl JSON output"


def _parse_pod(pod: dict, now: float) -> dict:
    """Extract common pod fields."""
    meta = pod.get("metadata", {})
    status = pod.get("status", {})
    containers = status.get("containerStatuses", [])
    ready = all(c.get("ready", False) for c in containers) if containers else False
    restarts = sum(c.get("restartCount", 0) for c in containers)

    created = meta.get("creationTimestamp", "")
    age = 0
    if created:
        try:
            from datetime import datetime, timezone
            ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age = int(now - ct.timestamp())
        except Exception:
            pass

    return {
        "name": meta.get("name", ""),
        "namespace": meta.get("namespace", ""),
        "status": status.get("phase", "Unknown"),
        "ready": ready,
        "restarts": restarts,
        "age_seconds": age,
        "created_at": created,
    }


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

async def _get_github_token(kubectl: str, secret_name: str, namespace: str) -> str | None:
    """Read GitHub PAT from a Kubernetes secret. Cached for 5 minutes."""
    cache_key = f"{namespace}/{secret_name}"
    now = time.time()
    cached = _github_token_cache.get(cache_key)
    if cached and now - cached[1] < _GITHUB_TOKEN_CACHE_TTL:
        return cached[0]

    data, err = await _kubectl_json(
        kubectl, "get", "secret", secret_name, "-n", namespace,
    )
    if err or not data:
        return None

    token_b64 = data.get("data", {}).get("github_token", "")
    if not token_b64:
        return None

    try:
        token = base64.b64decode(token_b64).decode().strip()
    except Exception:
        return None

    _github_token_cache[cache_key] = (token, now)
    return token


def _github_runners_api_url(config_url: str) -> str | None:
    """Derive the GitHub API runners endpoint from githubConfigUrl.

    https://github.com/OrgName        -> /orgs/OrgName/actions/runners
    https://github.com/owner/repo     -> /repos/owner/repo/actions/runners
    """
    try:
        parsed = urlparse(config_url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) == 1:
            return f"https://api.github.com/orgs/{parts[0]}/actions/runners?per_page=100"
        elif len(parts) == 2:
            return f"https://api.github.com/repos/{parts[0]}/{parts[1]}/actions/runners?per_page=100"
        return None
    except Exception:
        return None


async def _github_api_get(token: str, url: str, timeout: int = 10):
    """Call GitHub REST API and return parsed JSON."""
    def _do_request():
        req = Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    try:
        return await asyncio.to_thread(_do_request)
    except Exception:
        logger.debug("GitHub API call failed: %s", url, exc_info=True)
        return None


async def _fetch_github_status(runner_sets: list[dict]) -> dict:
    """Fetch runner busy/idle/online status from GitHub API.

    *runner_sets* must include ``github_config_url``, ``github_config_secret``,
    and ``namespace`` keys (as returned by ``_fetch_overview``).

    Returns ``{runner_name: {"busy": bool, "github_status": str}}``.
    """
    kubectl = _ws._find_kubectl()
    if not kubectl:
        return {}

    result: dict[str, dict] = {}
    seen_api_urls: dict[str, bool] = {}

    for rs in runner_sets:
        config_url = rs.get("github_config_url", "")
        secret_name = rs.get("github_config_secret", "")
        namespace = rs.get("namespace", "")
        if not config_url or not secret_name:
            continue

        api_url = _github_runners_api_url(config_url)
        if not api_url or api_url in seen_api_urls:
            continue

        token = await _get_github_token(kubectl, secret_name, namespace)
        if not token:
            continue

        data = await _github_api_get(token, api_url)
        if not data:
            continue

        seen_api_urls[api_url] = True
        for runner in data.get("runners", []):
            result[runner.get("name", "")] = {
                "busy": runner.get("busy", False),
                "github_status": runner.get("status", "unknown"),
            }

    return result


# ---------------------------------------------------------------------------
# Core data-fetching (shared by request handlers and broadcaster)
# ---------------------------------------------------------------------------

async def _fetch_overview() -> dict | None:
    """Fetch ARC controller + runner set data. Returns None on failure."""
    kubectl = _ws._find_kubectl()
    if not kubectl:
        return None

    now = time.time()

    (rs_data, rs_err), (ctrl_data, ctrl_err) = await asyncio.gather(
        _kubectl_json(kubectl, "get", "autoscalingrunnersets", "-A"),
        _kubectl_json(kubectl, "get", "pods", "-n", _ARC_CONTROLLER_NS,
                      "-l", "app.kubernetes.io/part-of=gha-rs-controller"),
    )

    controller = {"healthy": False, "pods": []}
    if ctrl_data:
        for pod in ctrl_data.get("items", []):
            controller["pods"].append(_parse_pod(pod, now))
        controller["healthy"] = any(
            p["status"] == "Running" and p["ready"] for p in controller["pods"]
        )

    runner_sets = []
    if rs_data:
        for item in rs_data.get("items", []):
            meta = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})
            annotations = meta.get("annotations", {})

            runner_sets.append({
                "name": meta.get("name", ""),
                "namespace": meta.get("namespace", ""),
                "github_config_url": spec.get("githubConfigUrl", ""),
                "github_config_secret": spec.get("githubConfigSecret", ""),
                "runner_group": annotations.get("actions.github.com/runner-group-name", ""),
                "min_runners": spec.get("minRunners", 0),
                "max_runners": spec.get("maxRunners", 0),
                "current_runners": status.get("currentRunners", 0),
                "pending_runners": status.get("pendingEphemeralRunners", 0),
                "running_runners": status.get("runningEphemeralRunners", 0),
                "created_at": meta.get("creationTimestamp", ""),
            })

    if rs_err and not rs_data:
        if "NotFound" not in rs_err and "no matching resources" not in rs_err.lower():
            return None

    return {"controller": controller, "runner_sets": runner_sets}


async def _fetch_runners(scale_set_name: str | None = None) -> list | None:
    """Fetch ephemeral runners. Returns None on failure."""
    kubectl = _ws._find_kubectl()
    if not kubectl:
        return None

    now = time.time()
    args = ["get", "ephemeralrunners", "-A"]
    if scale_set_name:
        args.extend(["-l", f"actions.github.com/scale-set-name={scale_set_name}"])

    data, err = await _kubectl_json(kubectl, *args)
    if err and not data:
        if "NotFound" in err or "no matching resources" in err.lower():
            return []
        return None

    runners = []
    for item in (data or {}).get("items", []):
        meta = item.get("metadata", {})
        status = item.get("status", {})
        labels = meta.get("labels", {})

        created = meta.get("creationTimestamp", "")
        age = 0
        if created:
            try:
                from datetime import datetime, timezone
                ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age = int(now - ct.timestamp())
            except Exception:
                pass

        runners.append({
            "name": meta.get("name", ""),
            "namespace": meta.get("namespace", ""),
            "scale_set_name": labels.get("actions.github.com/scale-set-name", ""),
            "phase": status.get("phase", "Unknown"),
            "ready": status.get("ready", False),
            "runner_id": status.get("runnerId", 0),
            "created_at": created,
            "age_seconds": age,
            # Job info (populated when runner is executing a workflow job)
            "job_repository": status.get("jobRepositoryName", ""),
            "job_display_name": status.get("jobDisplayName", ""),
            "job_workflow_ref": status.get("jobWorkflowRef", ""),
            "job_id": status.get("jobId", ""),
            "workflow_run_id": status.get("workflowRunId", ""),
        })

    return runners


async def _fetch_listeners() -> list | None:
    """Fetch ARC listener pods. Returns None on failure."""
    kubectl = _ws._find_kubectl()
    if not kubectl:
        return None

    now = time.time()
    data, err = await _kubectl_json(
        kubectl, "get", "pods", "-n", _ARC_CONTROLLER_NS,
        "-l", "actions.github.com/scale-set-name",
    )
    if err and not data:
        if "NotFound" in err or "no matching resources" in err.lower():
            return []
        return None

    listeners = []
    for pod in (data or {}).get("items", []):
        meta = pod.get("metadata", {})
        labels = meta.get("labels", {})
        parsed = _parse_pod(pod, now)
        parsed["scale_set_name"] = labels.get("actions.github.com/scale-set-name", "")
        listeners.append(parsed)

    return listeners


def _merge_github_status(runners: list, github_status: dict) -> list:
    """Enrich runner dicts with GitHub API busy/online data."""
    for runner in runners:
        gh = github_status.get(runner["name"])
        if gh:
            runner["busy"] = gh["busy"]
            runner["github_status"] = gh["github_status"]
        else:
            # Not yet registered with GitHub or API unavailable
            runner["busy"] = None
            runner["github_status"] = "unknown"
    return runners


# ---------------------------------------------------------------------------
# Background broadcaster — pushes cicd_update to all clients every N seconds
# ---------------------------------------------------------------------------

async def _cicd_broadcast_loop():
    """Periodically fetch ARC status and broadcast to all connected clients."""
    while True:
        try:
            await asyncio.sleep(_BROADCAST_INTERVAL)

            overview = await _fetch_overview()
            if overview is None:
                continue  # kubectl not available or query failed

            # Fetch K8s runners, listeners, and GitHub status in parallel
            runners_coro = _fetch_runners()
            listeners_coro = _fetch_listeners()
            github_coro = _fetch_github_status(overview["runner_sets"])

            runners, listeners, github_status = await asyncio.gather(
                runners_coro, listeners_coro, github_coro,
            )

            if runners:
                _merge_github_status(runners, github_status)

            await _ws._broadcast("cicd_update", {
                "overview": overview,
                "runners": runners or [],
                "listeners": listeners or [],
            })
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("cicd broadcast loop error")
            await asyncio.sleep(_BROADCAST_INTERVAL)


def start_cicd_broadcaster():
    """Start the background broadcast loop (called once at app startup)."""
    global _broadcast_task
    if _broadcast_task is None or _broadcast_task.done():
        _broadcast_task = asyncio.create_task(_cicd_broadcast_loop())
        logger.info("CI/CD broadcast loop started (interval=%ds)", _BROADCAST_INTERVAL)


def stop_cicd_broadcaster():
    """Stop the background broadcast loop."""
    global _broadcast_task
    if _broadcast_task and not _broadcast_task.done():
        _broadcast_task.cancel()
        _broadcast_task = None


# ---------------------------------------------------------------------------
# Request handlers (initial load + on-demand refresh)
# ---------------------------------------------------------------------------

async def _cicd_full(params: dict, ws: WebSocket, req_id: str):
    """Full snapshot: overview + runners (with GitHub status) + listeners.

    Returns the same shape as cicd_update broadcasts so the frontend can
    use a single code path.
    """
    overview = await _fetch_overview()
    if overview is None:
        return await _ws._respond(ws, req_id, error="kubectl not found or query failed")

    runners, listeners, github_status = await asyncio.gather(
        _fetch_runners(),
        _fetch_listeners(),
        _fetch_github_status(overview["runner_sets"]),
    )

    if runners:
        _merge_github_status(runners, github_status)

    await _ws._respond(ws, req_id, {
        "overview": overview,
        "runners": runners or [],
        "listeners": listeners or [],
    })


async def _cicd_overview(params: dict, ws: WebSocket, req_id: str):
    """Get ARC controller health and all runner scale sets."""
    result = await _fetch_overview()
    if result is None:
        return await _ws._respond(ws, req_id, error="kubectl not found or query failed")
    await _ws._respond(ws, req_id, result)


async def _cicd_runners(params: dict, ws: WebSocket, req_id: str):
    """List ephemeral runners, optionally filtered by scale set name."""
    result = await _fetch_runners(params.get("scale_set_name"))
    if result is None:
        return await _ws._respond(ws, req_id, error="kubectl not found or query failed")
    await _ws._respond(ws, req_id, result)


async def _cicd_listeners(params: dict, ws: WebSocket, req_id: str):
    """List ARC listener pods in the controller namespace."""
    result = await _fetch_listeners()
    if result is None:
        return await _ws._respond(ws, req_id, error="kubectl not found or query failed")
    await _ws._respond(ws, req_id, result)


# ---------------------------------------------------------------------------
# Action map
# ---------------------------------------------------------------------------

CICD_ACTIONS = {
    "cicd.full": _cicd_full,
    "cicd.overview": _cicd_overview,
    "cicd.runners": _cicd_runners,
    "cicd.listeners": _cicd_listeners,
}
