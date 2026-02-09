"""Bidirectional WebSocket CRUD handler.

Protocol
--------
Client → Server:  {"id": "uuid", "action": "devices.list", "params": {...}}
Server → Client:  {"id": "uuid", "data": ..., "error": null}   (response)
Server → ALL:     {"type": "device_approved", "data": {...}}     (broadcast)
"""
import json
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import WebSocket

# ---------------------------------------------------------------------------
# Shared helpers — defined here so every handler module can
#   import app.api.ws_handler as _ws
# and call _ws._db(), _ws._respond(), etc.
# Patching these at "app.api.ws_handler.<name>" works for ALL handlers.
# ---------------------------------------------------------------------------

from app.api.handlers._base import (          # noqa: F401
    _db,
    _serialize,
    _respond,
    _broadcast,
    log_action,
)

from app.api.handlers._infra import (         # noqa: F401
    _save_disk_partition,
    _remove_disk_partition,
    _regenerate_all_device_configs,
    _label_namespace_privileged,
    _run_post_install,
    _post_install_metallb,
    _find_kubectl,
    _delete_namespace_resources,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Handler imports — MUST come AFTER the helpers above, because handler
# modules do `import app.api.ws_handler as _ws` and expect _ws._db etc.
# to already be defined in this (partially-loaded) module.
# ---------------------------------------------------------------------------

from app.api.handlers.audit import (          # noqa: F401
    AUDIT_ACTIONS,
    _audit_list,
    _audit_clear,
)

from app.api.handlers.volumes import (        # noqa: F401
    VOLUME_ACTIONS,
    _volumes_list,
    _volumes_get,
    _volumes_get_by_name,
    _volumes_create,
    _volumes_update,
    _volumes_delete,
)

from app.api.handlers.talos import (          # noqa: F401
    TALOS_ACTIONS,
    _talos_get,
    _talos_update,
    _versions_talos,
    _versions_kubernetes,
)

from app.api.handlers.network import (        # noqa: F401
    NETWORK_ACTIONS,
    _network_detect,
    _network_interfaces,
    _network_get,
    _network_create,
    _network_update,
    _network_apply,
)

from app.api.handlers.cluster import (        # noqa: F401
    CLUSTER_ACTIONS,
    _cluster_get,
    _cluster_create,
    _cluster_update,
    _cluster_generate_config,
    _cluster_generate_secrets,
    _cluster_bootstrap,
    _cluster_kubeconfig,
)

from app.api.handlers.longhorn import (       # noqa: F401
    LONGHORN_ACTIONS,
    _LONGHORN_NS,
    _LONGHORN_AUTO_CONFIG_FILE,
    _resolve_node_ip,
    _load_longhorn_auto_config,
    _save_longhorn_auto_config,
    _disk_name_from_path,
    _longhorn_reset_disks_after_wipe,
    _longhorn_nodes,
    _longhorn_discover_disks,
    _longhorn_add_disk,
    _longhorn_remove_disk,
    _longhorn_use_all_disks,
    _longhorn_use_all_disks_for_node,
    _longhorn_auto_config,
)

from app.api.handlers.modules import (        # noqa: F401
    MODULE_ACTIONS,
    _modules_catalog,
    _modules_list,
    _modules_get,
    _modules_install,
    _modules_upgrade,
    _modules_cancel,
    _modules_force_delete,
    _modules_uninstall,
    _modules_log,
    _modules_repos_list,
    _modules_repos_add,
    _modules_repos_delete,
    _do_helm_install,
    _do_helm_upgrade,
    _do_helm_uninstall,
)

from app.api.handlers.troubleshoot import (   # noqa: F401
    TROUBLESHOOT_ACTIONS,
    _troubleshoot_check_status,
    _troubleshoot_fix_kubeconfig,
    _troubleshoot_fix_talosconfig,
    _troubleshoot_regen_configs,
    _troubleshoot_regen_dnsmasq,
    _troubleshoot_restart_dnsmasq,
    _troubleshoot_download_talosctl,
    _troubleshoot_download_kubectl,
    _troubleshoot_download_talos_files,
    _troubleshoot_reinstall_cni,
)

from app.api.handlers.cicd import (           # noqa: F401
    CICD_ACTIONS,
    _cicd_overview,
    _cicd_runners,
    _cicd_listeners,
    start_cicd_broadcaster,
    stop_cicd_broadcaster,
)

from app.api.handlers.devices import (        # noqa: F401
    DEVICE_ACTIONS,
    _devices_list,
    _devices_get,
    _devices_create,
    _devices_update,
    _devices_approval_suggestions,
    _devices_approve,
    _devices_reject,
    _devices_delete,
    _devices_regenerate,
    _devices_health,
    _devices_shutdown,
    _devices_reboot,
    _devices_wake,
    _devices_rolling_refresh,
    _devices_rolling_refresh_cancel,
    _devices_rolling_refresh_status,
)

# ---------------------------------------------------------------------------
# ACTION_MAP + dispatcher
# ---------------------------------------------------------------------------

ACTION_MAP: Dict[str, Any] = {}
ACTION_MAP.update(DEVICE_ACTIONS)
ACTION_MAP.update(NETWORK_ACTIONS)
ACTION_MAP.update(CLUSTER_ACTIONS)
ACTION_MAP.update(VOLUME_ACTIONS)
ACTION_MAP.update(AUDIT_ACTIONS)
ACTION_MAP.update(TALOS_ACTIONS)
ACTION_MAP.update(MODULE_ACTIONS)
ACTION_MAP.update(LONGHORN_ACTIONS)
ACTION_MAP.update(TROUBLESHOOT_ACTIONS)
ACTION_MAP.update(CICD_ACTIONS)


async def handle_ws_message(ws: WebSocket, raw: str):
    """Parse and dispatch a single WebSocket message."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await ws.send_json({"id": None, "data": None, "error": "Invalid JSON"})
        return

    req_id = msg.get("id")
    action = msg.get("action", "")
    params = dict(msg.get("params") or {})

    handler = ACTION_MAP.get(action)
    if not handler:
        await _respond(ws, req_id, error=f"Unknown action: {action}")
        return

    try:
        await handler(params, ws, req_id)
    except Exception as e:
        # HTTPException.detail has the real message; str(HTTPException) is empty
        detail = getattr(e, "detail", None) or str(e) or type(e).__name__
        logger.error(f"WS action {action} error: {detail}\n{traceback.format_exc()}")
        await _respond(ws, req_id, error=detail)
