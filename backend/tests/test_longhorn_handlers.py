"""Tests for Longhorn-related functions in app.api.ws_handler."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.ws_handler import (
    _resolve_node_ip,
    _load_longhorn_auto_config,
    _save_longhorn_auto_config,
    _longhorn_nodes,
    _longhorn_add_disk,
    _longhorn_auto_config,
    _longhorn_reset_disks_after_wipe,
)

from tests.conftest import seed_device, get_ws_response


# ---------------------------------------------------------------------------
# _resolve_node_ip
# ---------------------------------------------------------------------------

class TestResolveNodeIp:
    """Tests for resolving a Kubernetes node name to its IP via the devices DB."""

    def test_resolve_node_ip_found(self, mock_db):
        seed_device(mock_db, hostname="node-01", ip_address="10.0.128.5")
        result = _resolve_node_ip("node-01")
        assert result == "10.0.128.5"

    def test_resolve_node_ip_not_found(self, mock_db):
        result = _resolve_node_ip("nonexistent-node")
        assert result is None

    def test_resolve_node_ip_strips_cidr(self, mock_db):
        seed_device(mock_db, hostname="node-cidr", ip_address="10.0.1.5/24")
        result = _resolve_node_ip("node-cidr")
        assert result == "10.0.1.5"

    def test_resolve_node_ip_ignores_pending_devices(self, mock_db):
        from app.db.models import DeviceStatus
        seed_device(mock_db, hostname="pending-node", ip_address="10.0.1.10",
                    status=DeviceStatus.PENDING, mac_address="AA:BB:CC:DD:EE:99")
        result = _resolve_node_ip("pending-node")
        assert result is None


# ---------------------------------------------------------------------------
# _load_longhorn_auto_config / _save_longhorn_auto_config
# ---------------------------------------------------------------------------

class TestLonghornAutoConfigPersistence:
    """Tests for loading and saving the Longhorn auto-disk JSON config file."""

    @pytest.fixture
    def fake_home(self, tmp_path):
        """Redirect _LONGHORN_AUTO_CONFIG_FILE to a temporary directory."""
        fake_file = tmp_path / ".ktizo" / "data" / "longhorn_auto_disks.json"
        with patch("app.api.handlers.longhorn._LONGHORN_AUTO_CONFIG_FILE", fake_file):
            yield tmp_path, fake_file

    def test_load_auto_config_missing_file(self, fake_home):
        """Returns empty dict when the config file does not exist."""
        result = _load_longhorn_auto_config()
        assert result == {}

    def test_save_and_load_auto_config(self, fake_home):
        """Round-trip: save then load should return the same config."""
        config = {"node-01": {"auto_add_disks": True}}
        _save_longhorn_auto_config(config)
        result = _load_longhorn_auto_config()
        assert result == config

    def test_load_auto_config_corrupt_file(self, fake_home):
        """Returns empty dict if the file contains invalid JSON."""
        _, fake_file = fake_home
        fake_file.parent.mkdir(parents=True, exist_ok=True)
        fake_file.write_text("NOT VALID JSON {{{")
        result = _load_longhorn_auto_config()
        assert result == {}


# ---------------------------------------------------------------------------
# _longhorn_nodes handler
# ---------------------------------------------------------------------------

class TestLonghornNodes:
    """Tests for the longhorn.nodes WebSocket handler."""

    @pytest.mark.asyncio
    async def test_longhorn_nodes_kubectl_not_found(self, mock_ws):
        """When kubectl is not found, an error is returned."""
        with patch("app.api.ws_handler._find_kubectl", return_value=None):
            await _longhorn_nodes({}, mock_ws, "req-1")

        data, error = get_ws_response(mock_ws)
        assert error == "kubectl not found"
        assert data is None

    @pytest.mark.asyncio
    async def test_longhorn_nodes_success(self, mock_ws, mock_kubectl, mock_subprocess):
        """Parses kubectl JSON output into structured node list."""
        mock_create, mock_proc = mock_subprocess
        longhorn_response = json.dumps({
            "items": [{
                "metadata": {"name": "node-01"},
                "spec": {
                    "allowScheduling": True,
                    "disks": {
                        "disk-var-mnt-longhorn": {
                            "path": "/var/mnt/longhorn",
                            "allowScheduling": True,
                            "diskType": "filesystem",
                            "storageReserved": 0,
                            "evictionRequested": False,
                            "tags": [],
                        }
                    },
                },
                "status": {
                    "diskStatus": {
                        "disk-var-mnt-longhorn": {
                            "storageMaximum": 100000000000,
                            "storageAvailable": 80000000000,
                            "storageScheduled": 20000000000,
                            "scheduledReplica": {"replica-1": True},
                        }
                    },
                    "conditions": {},
                },
            }]
        }).encode()
        mock_proc.communicate = AsyncMock(return_value=(longhorn_response, b""))

        with patch("app.api.handlers.longhorn._load_longhorn_auto_config", return_value={}):
            await _longhorn_nodes({}, mock_ws, "req-2")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert len(data) == 1
        node = data[0]
        assert node["name"] == "node-01"
        assert node["allowScheduling"] is True
        assert len(node["disks"]) == 1
        disk = node["disks"][0]
        assert disk["name"] == "disk-var-mnt-longhorn"
        assert disk["path"] == "/var/mnt/longhorn"
        assert disk["replicaCount"] == 1
        assert disk["storageMaximum"] == 100000000000
        assert node["autoAddDisks"] is False

    @pytest.mark.asyncio
    async def test_longhorn_nodes_subprocess_failure(self, mock_ws, mock_kubectl, mock_subprocess):
        """Returns error message when kubectl subprocess fails."""
        mock_create, mock_proc = mock_subprocess
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"connection refused"))

        await _longhorn_nodes({}, mock_ws, "req-3")

        data, error = get_ws_response(mock_ws)
        assert "Failed to get Longhorn nodes" in error
        assert "connection refused" in error


# ---------------------------------------------------------------------------
# _longhorn_add_disk handler
# ---------------------------------------------------------------------------

class TestLonghornAddDisk:
    """Tests for the longhorn.add_disk WebSocket handler."""

    @pytest.mark.asyncio
    async def test_longhorn_add_disk_missing_params(self, mock_ws):
        """Returns error when node_name or disk_path is missing."""
        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"):
            await _longhorn_add_disk({}, mock_ws, "req-1")

        data, error = get_ws_response(mock_ws)
        assert error == "node_name and disk_path required"

    @pytest.mark.asyncio
    async def test_longhorn_add_disk_missing_disk_path(self, mock_ws):
        """Returns error when only node_name is provided but disk_path is missing."""
        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"):
            await _longhorn_add_disk({"node_name": "node-01"}, mock_ws, "req-2")

        data, error = get_ws_response(mock_ws)
        assert error == "node_name and disk_path required"

    @pytest.mark.asyncio
    async def test_longhorn_add_disk_success(self, mock_ws, mock_kubectl, mock_subprocess, mock_broadcast):
        """Verifies subprocess is called with correct kubectl patch JSON."""
        mock_create, mock_proc = mock_subprocess
        mock_proc.communicate = AsyncMock(return_value=(b"patched", b""))

        await _longhorn_add_disk(
            {"node_name": "node-01", "disk_path": "/var/mnt/longhorn"},
            mock_ws, "req-3",
        )

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert "added" in data["message"].lower()
        assert "disk-var-mnt-longhorn" in data["message"]

        # Verify the kubectl patch call
        call_args = mock_create.call_args
        args = call_args[0]
        assert "patch" in args
        assert "nodes.longhorn.io" in args
        assert "node-01" in args
        # The patch JSON should include the disk path
        patch_json_str = args[args.index("--patch") + 1]
        patch_data = json.loads(patch_json_str)
        assert patch_data["spec"]["disks"]["disk-var-mnt-longhorn"]["path"] == "/var/mnt/longhorn"
        assert patch_data["spec"]["disks"]["disk-var-mnt-longhorn"]["allowScheduling"] is True

    @pytest.mark.asyncio
    async def test_longhorn_add_disk_custom_name(self, mock_ws, mock_kubectl, mock_subprocess, mock_broadcast):
        """Uses the provided custom disk_name instead of auto-generating one."""
        mock_create, mock_proc = mock_subprocess
        mock_proc.communicate = AsyncMock(return_value=(b"patched", b""))

        await _longhorn_add_disk(
            {"node_name": "node-01", "disk_path": "/var/mnt/longhorn", "disk_name": "my-custom-disk"},
            mock_ws, "req-4",
        )

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert "my-custom-disk" in data["message"]

    @pytest.mark.asyncio
    async def test_longhorn_add_disk_kubectl_not_found(self, mock_ws):
        """Returns error when kubectl binary cannot be found."""
        with patch("app.api.ws_handler._find_kubectl", return_value=None):
            await _longhorn_add_disk(
                {"node_name": "node-01", "disk_path": "/var/mnt/longhorn"},
                mock_ws, "req-5",
            )

        data, error = get_ws_response(mock_ws)
        assert error == "kubectl not found"


# ---------------------------------------------------------------------------
# _longhorn_auto_config handler
# ---------------------------------------------------------------------------

class TestLonghornAutoConfig:
    """Tests for the longhorn.auto_config WebSocket handler."""

    @pytest.fixture
    def fake_home(self, tmp_path):
        """Redirect _LONGHORN_AUTO_CONFIG_FILE to a temporary directory."""
        fake_file = tmp_path / ".ktizo" / "data" / "longhorn_auto_disks.json"
        with patch("app.api.handlers.longhorn._LONGHORN_AUTO_CONFIG_FILE", fake_file):
            yield tmp_path, fake_file

    @pytest.mark.asyncio
    async def test_longhorn_auto_config_set(self, mock_ws, fake_home):
        """SET mode: enables auto_add_disks for a node and persists it."""
        await _longhorn_auto_config(
            {"node_name": "node-01", "auto_add_disks": True},
            mock_ws, "req-1",
        )

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert "enabled" in data["message"].lower()

        # Verify the file was written
        _, fake_file = fake_home
        assert fake_file.exists()
        saved = json.loads(fake_file.read_text())
        assert saved["node-01"]["auto_add_disks"] is True

    @pytest.mark.asyncio
    async def test_longhorn_auto_config_get(self, mock_ws, fake_home):
        """GET mode: returns previously saved config for a node."""
        # First set
        await _longhorn_auto_config(
            {"node_name": "node-01", "auto_add_disks": True},
            mock_ws, "req-set",
        )

        # Then get
        await _longhorn_auto_config(
            {"node_name": "node-01"},
            mock_ws, "req-get",
        )

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data["node_name"] == "node-01"
        assert data["auto_add_disks"] is True

    @pytest.mark.asyncio
    async def test_longhorn_auto_config_get_all(self, mock_ws, fake_home):
        """GET mode without node_name: returns entire config dict."""
        await _longhorn_auto_config(
            {"node_name": "node-01", "auto_add_disks": True},
            mock_ws, "req-set",
        )

        await _longhorn_auto_config({}, mock_ws, "req-all")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert "node-01" in data

    @pytest.mark.asyncio
    async def test_longhorn_auto_config_set_requires_node_name(self, mock_ws, fake_home):
        """SET mode without node_name returns an error."""
        await _longhorn_auto_config(
            {"auto_add_disks": True},
            mock_ws, "req-err",
        )

        data, error = get_ws_response(mock_ws)
        assert error == "node_name required for set"

    @pytest.mark.asyncio
    async def test_longhorn_auto_config_disable(self, mock_ws, fake_home):
        """SET mode with auto_add_disks=False removes the node entry."""
        # Enable first
        await _longhorn_auto_config(
            {"node_name": "node-01", "auto_add_disks": True},
            mock_ws, "req-en",
        )
        # Disable
        await _longhorn_auto_config(
            {"node_name": "node-01", "auto_add_disks": False},
            mock_ws, "req-dis",
        )

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert "disabled" in data["message"].lower()

        # Verify the file no longer has the node
        _, fake_file = fake_home
        saved = json.loads(fake_file.read_text())
        assert "node-01" not in saved


# ---------------------------------------------------------------------------
# _longhorn_reset_disks_after_wipe
# ---------------------------------------------------------------------------

class TestResetDisksAfterWipe:
    """Tests for the internal _longhorn_reset_disks_after_wipe function."""

    @pytest.mark.asyncio
    async def test_reset_disks_after_wipe(self, mock_kubectl, mock_subprocess):
        """Mock kubectl to return node with one disk, verify old disk removed and new one added."""
        mock_create, mock_proc = mock_subprocess

        node_data = json.dumps({
            "spec": {
                "disks": {
                    "disk-var-mnt-longhorn": {
                        "path": "/var/mnt/longhorn",
                        "allowScheduling": True,
                        "storageReserved": 0,
                        "tags": [],
                    }
                }
            }
        }).encode()

        # First call: get node → returns node_data
        # Second call: patch to remove old disks → success
        # Third call: patch to add new disks → success
        call_count = 0
        original_proc = AsyncMock()
        original_proc.returncode = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            proc = AsyncMock()
            proc.returncode = 0
            if call_count == 0:
                proc.communicate = AsyncMock(return_value=(node_data, b""))
            else:
                proc.communicate = AsyncMock(return_value=(b"patched", b""))
            call_count += 1
            return proc

        mock_create.side_effect = side_effect

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("time.time", return_value=1700000000.0):
                await _longhorn_reset_disks_after_wipe("node-01")

        # We expect 3 subprocess calls: get, remove patch, add patch
        assert mock_create.call_count == 3

        # Verify the remove patch (second call)
        remove_call_args = mock_create.call_args_list[1][0]
        remove_patch_idx = list(remove_call_args).index("--patch") + 1
        remove_patch = json.loads(remove_call_args[remove_patch_idx])
        assert "disk-var-mnt-longhorn" in remove_patch["spec"]["disks"]
        assert remove_patch["spec"]["disks"]["disk-var-mnt-longhorn"] is None

        # Verify the add patch (third call)
        add_call_args = mock_create.call_args_list[2][0]
        add_patch_idx = list(add_call_args).index("--patch") + 1
        add_patch = json.loads(add_call_args[add_patch_idx])
        new_disk_names = list(add_patch["spec"]["disks"].keys())
        assert len(new_disk_names) == 1
        # New name should have a timestamp suffix and start with disk-var-mnt-longhorn
        assert new_disk_names[0].startswith("disk-var-mnt-longhorn-")
        new_disk = add_patch["spec"]["disks"][new_disk_names[0]]
        assert new_disk["path"] == "/var/mnt/longhorn"
        assert new_disk["allowScheduling"] is True

    @pytest.mark.asyncio
    async def test_reset_disks_after_wipe_no_kubectl(self):
        """Does nothing when kubectl is not found."""
        with patch("app.api.ws_handler._find_kubectl", return_value=None):
            # Should not raise
            await _longhorn_reset_disks_after_wipe("node-01")

    @pytest.mark.asyncio
    async def test_reset_disks_after_wipe_no_disks(self, mock_kubectl, mock_subprocess):
        """Does nothing when the node has no disks."""
        mock_create, mock_proc = mock_subprocess
        mock_proc.communicate = AsyncMock(
            return_value=(json.dumps({"spec": {"disks": {}}}).encode(), b"")
        )

        await _longhorn_reset_disks_after_wipe("node-01")

        # Only the initial get call should happen
        assert mock_create.call_count == 1
