"""Tests for the WebSocket dispatcher (handle_ws_message + ACTION_MAP)."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.api.ws_handler import handle_ws_message, ACTION_MAP


EXPECTED_ACTIONS = [
    "devices.list", "devices.get", "devices.create", "devices.update",
    "devices.approval_suggestions", "devices.approve", "devices.reject",
    "devices.delete", "devices.regenerate", "devices.health",
    "devices.shutdown", "devices.reboot", "devices.wake",
    "devices.rolling_refresh", "devices.rolling_refresh_cancel",
    "devices.rolling_refresh_status",
    "network.detect", "network.interfaces", "network.get",
    "network.create", "network.update", "network.apply",
    "cluster.get", "cluster.create", "cluster.update",
    "cluster.generate_config", "cluster.generate_secrets",
    "cluster.bootstrap", "cluster.kubeconfig",
    "volumes.list", "volumes.get", "volumes.get_by_name",
    "volumes.create", "volumes.update", "volumes.delete",
    "audit.list", "audit.clear",
    "talos.get", "talos.update", "versions.talos", "versions.kubernetes",
    "modules.catalog", "modules.list", "modules.get", "modules.install",
    "modules.upgrade", "modules.cancel", "modules.force_delete",
    "modules.uninstall", "modules.log",
    "modules.repos.list", "modules.repos.add", "modules.repos.delete",
    "longhorn.nodes", "longhorn.discover_disks", "longhorn.add_disk",
    "longhorn.remove_disk", "longhorn.use_all_disks", "longhorn.auto_config",
    "troubleshoot.status", "troubleshoot.fix_kubeconfig",
    "troubleshoot.fix_talosconfig", "troubleshoot.regen_configs",
    "troubleshoot.regen_dnsmasq", "troubleshoot.restart_dnsmasq",
    "troubleshoot.download_talosctl", "troubleshoot.download_kubectl",
    "troubleshoot.download_talos_files", "troubleshoot.reinstall_cni",
]


@pytest.mark.asyncio
async def test_invalid_json_returns_error(mock_ws):
    """Sending non-JSON text should return an 'Invalid JSON' error."""
    await handle_ws_message(mock_ws, "not json")

    assert len(mock_ws.sent_messages) == 1
    resp = mock_ws.sent_messages[0]
    assert resp["id"] is None
    assert resp["data"] is None
    assert resp["error"] == "Invalid JSON"


@pytest.mark.asyncio
async def test_unknown_action_returns_error(mock_ws):
    """An unrecognised action should return an 'Unknown action' error."""
    raw = json.dumps({"id": "1", "action": "fake.action"})
    await handle_ws_message(mock_ws, raw)

    assert len(mock_ws.sent_messages) == 1
    resp = mock_ws.sent_messages[0]
    assert resp["id"] == "1"
    assert resp["error"] == "Unknown action: fake.action"


@pytest.mark.asyncio
async def test_missing_params_defaults_to_empty(mock_ws):
    """When 'params' is omitted the handler should receive an empty dict."""
    spy = AsyncMock()
    with patch.dict(ACTION_MAP, {"modules.catalog": spy}):
        raw = json.dumps({"id": "2", "action": "modules.catalog"})
        await handle_ws_message(mock_ws, raw)

    spy.assert_awaited_once_with({}, mock_ws, "2")


@pytest.mark.asyncio
async def test_handler_exception_returns_error(mock_ws):
    """If a handler raises, the error detail should be sent back."""
    failing = AsyncMock(side_effect=ValueError("test error"))
    with patch.dict(ACTION_MAP, {"modules.catalog": failing}):
        raw = json.dumps({"id": "3", "action": "modules.catalog", "params": {}})
        await handle_ws_message(mock_ws, raw)

    assert len(mock_ws.sent_messages) == 1
    resp = mock_ws.sent_messages[0]
    assert resp["id"] == "3"
    assert resp["error"] == "test error"


def test_action_map_has_all_expected_keys():
    """ACTION_MAP must contain every expected action key."""
    missing = [k for k in EXPECTED_ACTIONS if k not in ACTION_MAP]
    assert missing == [], f"Missing actions in ACTION_MAP: {missing}"
    assert len(EXPECTED_ACTIONS) == 69


def test_all_action_map_values_are_callable():
    """Every value in ACTION_MAP must be a callable (async function)."""
    for action, handler in ACTION_MAP.items():
        assert callable(handler), f"ACTION_MAP[{action!r}] is not callable: {handler!r}"
