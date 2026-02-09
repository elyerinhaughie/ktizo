"""Node resource metrics via the Kubernetes Metrics API (metrics.k8s.io/v1beta1).

Requires Metrics Server to be installed in the cluster.  When unavailable the
handler returns ``{"available": false}`` and the broadcast loop silently skips.

Data is pushed to all connected clients via periodic ``metrics_update``
broadcast events (every 15 s) and also available on demand via the
``metrics.get`` WebSocket action.
"""
import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)

_BROADCAST_INTERVAL = 15  # seconds

# Background task handle
_broadcast_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Kubernetes client helpers
# ---------------------------------------------------------------------------

def _get_k8s_clients():
    """Return ``(CoreV1Api, CustomObjectsApi)`` or ``(None, None)``."""
    try:
        from kubernetes import client, config

        kubeconfig = Path.home() / ".kube" / "config"
        if not kubeconfig.exists():
            return None, None
        config.load_kube_config(config_file=str(kubeconfig))
        return client.CoreV1Api(), client.CustomObjectsApi()
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Unit parsing
# ---------------------------------------------------------------------------

def _parse_cpu(value: str) -> int:
    """Parse a Kubernetes CPU string to *millicores*.

    Examples: ``'250m'`` → 250, ``'4'`` → 4000, ``'1500n'`` → 1.
    """
    value = str(value).strip()
    if value.endswith("n"):
        return int(value[:-1]) // 1_000_000
    if value.endswith("u"):
        return int(value[:-1]) // 1_000
    if value.endswith("m"):
        return int(value[:-1])
    return int(value) * 1000


def _parse_memory(value: str) -> int:
    """Parse a Kubernetes memory string to *bytes*.

    Handles binary suffixes (Ki, Mi, Gi, Ti) and SI suffixes (K, M, G, T).
    """
    value = str(value).strip()
    suffixes = {
        "Ti": 1024 ** 4, "Gi": 1024 ** 3, "Mi": 1024 ** 2, "Ki": 1024,
        "T": 10 ** 12, "G": 10 ** 9, "M": 10 ** 6, "K": 10 ** 3,
    }
    for suffix, multiplier in suffixes.items():
        if value.endswith(suffix):
            return int(value[: -len(suffix)]) * multiplier
    return int(value)


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

def _fetch_metrics_sync() -> dict | None:
    """Synchronous fetch — called via ``asyncio.to_thread()``.

    Returns the full metrics payload dict, or ``None`` on hard failure
    (e.g. no kubeconfig / library missing).
    """
    core_api, custom_api = _get_k8s_clients()
    if core_api is None:
        return None

    # 1. Get node capacity / allocatable
    try:
        node_list = core_api.list_node()
    except Exception as exc:
        logger.warning("Failed to list nodes: %s", exc)
        return None

    capacity_map: dict[str, dict] = {}
    for node in node_list.items:
        name = node.metadata.name
        alloc = node.status.allocatable or {}
        addrs = [
            a.address
            for a in (node.status.addresses or [])
            if a.type == "InternalIP"
        ]
        capacity_map[name] = {
            "cpu_allocatable_millicores": _parse_cpu(alloc.get("cpu", "0")),
            "memory_allocatable_bytes": _parse_memory(alloc.get("memory", "0")),
            "addresses": addrs,
        }

    # 2. Get live usage from Metrics API
    try:
        metrics_resp = custom_api.list_cluster_custom_object(
            "metrics.k8s.io", "v1beta1", "nodes",
        )
    except Exception as exc:
        err_str = str(exc)
        if "404" in err_str or "not found" in err_str.lower():
            return {"available": False, "cluster": None, "nodes": {}}
        logger.warning("Metrics API query failed: %s", exc)
        return {"available": False, "cluster": None, "nodes": {}}

    # 3. Combine per-node data
    nodes: dict[str, dict] = {}
    total_cpu_usage = 0
    total_cpu_alloc = 0
    total_mem_usage = 0
    total_mem_alloc = 0

    for item in metrics_resp.get("items", []):
        name = item.get("metadata", {}).get("name", "")
        usage = item.get("usage", {})
        cpu_usage = _parse_cpu(usage.get("cpu", "0"))
        mem_usage = _parse_memory(usage.get("memory", "0"))

        cap = capacity_map.get(name, {})
        cpu_alloc = cap.get("cpu_allocatable_millicores", 0)
        mem_alloc = cap.get("memory_allocatable_bytes", 0)

        cpu_pct = round(cpu_usage / cpu_alloc * 100, 1) if cpu_alloc else 0.0
        mem_pct = round(mem_usage / mem_alloc * 100, 1) if mem_alloc else 0.0

        nodes[name] = {
            "cpu_usage_millicores": cpu_usage,
            "cpu_allocatable_millicores": cpu_alloc,
            "cpu_percent": cpu_pct,
            "memory_usage_bytes": mem_usage,
            "memory_allocatable_bytes": mem_alloc,
            "memory_percent": mem_pct,
            "addresses": cap.get("addresses", []),
        }

        total_cpu_usage += cpu_usage
        total_cpu_alloc += cpu_alloc
        total_mem_usage += mem_usage
        total_mem_alloc += mem_alloc

    cluster_cpu_pct = round(total_cpu_usage / total_cpu_alloc * 100, 1) if total_cpu_alloc else 0.0
    cluster_mem_pct = round(total_mem_usage / total_mem_alloc * 100, 1) if total_mem_alloc else 0.0

    return {
        "available": True,
        "cluster": {
            "cpu_usage_millicores": total_cpu_usage,
            "cpu_allocatable_millicores": total_cpu_alloc,
            "cpu_percent": cluster_cpu_pct,
            "memory_usage_bytes": total_mem_usage,
            "memory_allocatable_bytes": total_mem_alloc,
            "memory_percent": cluster_mem_pct,
        },
        "nodes": nodes,
    }


async def _fetch_metrics() -> dict | None:
    """Async wrapper — runs the blocking K8s calls in a thread pool."""
    return await asyncio.to_thread(_fetch_metrics_sync)


# ---------------------------------------------------------------------------
# Background broadcaster
# ---------------------------------------------------------------------------

async def _metrics_broadcast_loop():
    """Periodically fetch node metrics and broadcast to all connected clients."""
    while True:
        try:
            await asyncio.sleep(_BROADCAST_INTERVAL)
            data = await _fetch_metrics()
            if data is None:
                continue
            if not data.get("available"):
                continue
            await _ws._broadcast("metrics_update", data)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("metrics broadcast loop error")
            await asyncio.sleep(_BROADCAST_INTERVAL)


def start_metrics_broadcaster():
    """Start the background broadcast loop (called once at app startup)."""
    global _broadcast_task
    if _broadcast_task is None or _broadcast_task.done():
        _broadcast_task = asyncio.create_task(_metrics_broadcast_loop())
        logger.info("Metrics broadcast loop started (interval=%ds)", _BROADCAST_INTERVAL)


def stop_metrics_broadcaster():
    """Stop the background broadcast loop."""
    global _broadcast_task
    if _broadcast_task and not _broadcast_task.done():
        _broadcast_task.cancel()
        _broadcast_task = None


# ---------------------------------------------------------------------------
# Request handlers
# ---------------------------------------------------------------------------

async def _metrics_get(params: dict, ws: WebSocket, req_id: str):
    """On-demand fetch of current node metrics."""
    data = await _fetch_metrics()
    if data is None:
        return await _ws._respond(ws, req_id, {"available": False, "cluster": None, "nodes": {}})
    await _ws._respond(ws, req_id, data)


# ---------------------------------------------------------------------------
# Action map
# ---------------------------------------------------------------------------

METRICS_ACTIONS = {
    "metrics.get": _metrics_get,
}
