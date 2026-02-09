"""Handler package — assembles the WebSocket ACTION_MAP from all sub-modules."""

from app.api.handlers.devices import DEVICE_ACTIONS
from app.api.handlers.network import NETWORK_ACTIONS
from app.api.handlers.cluster import CLUSTER_ACTIONS
from app.api.handlers.volumes import VOLUME_ACTIONS
from app.api.handlers.audit import AUDIT_ACTIONS
from app.api.handlers.talos import TALOS_ACTIONS
from app.api.handlers.modules import MODULE_ACTIONS
from app.api.handlers.longhorn import LONGHORN_ACTIONS
from app.api.handlers.troubleshoot import TROUBLESHOOT_ACTIONS


def build_action_map() -> dict:
    """Merge all per-domain action dicts into one map."""
    action_map: dict = {}
    for actions in [
        DEVICE_ACTIONS,
        NETWORK_ACTIONS,
        CLUSTER_ACTIONS,
        VOLUME_ACTIONS,
        AUDIT_ACTIONS,
        TALOS_ACTIONS,
        MODULE_ACTIONS,
        LONGHORN_ACTIONS,
        TROUBLESHOOT_ACTIONS,
    ]:
        action_map.update(actions)
    return action_map
