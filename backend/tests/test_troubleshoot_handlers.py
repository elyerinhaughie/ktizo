"""Tests for troubleshoot handlers in app.api.ws_handler."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Pre-import modules that are lazily imported inside handlers so patch() can
# resolve their attributes.
import app.api.cluster_router  # noqa: F401 — needed for patch paths
import app.api.terminal_router  # noqa: F401 — needed for patch paths

from app.api.ws_handler import (
    _troubleshoot_check_status,
    _troubleshoot_regen_configs,
    _troubleshoot_reinstall_cni,
    _troubleshoot_fix_kubeconfig,
)

from tests.conftest import seed_device, get_ws_response


# ---------------------------------------------------------------------------
# _troubleshoot_check_status
# ---------------------------------------------------------------------------

class TestTroubleshootCheckStatus:
    """Tests for the troubleshoot.status WebSocket handler."""

    @pytest.mark.asyncio
    async def test_check_status_returns_expected_keys(self, mock_db, mock_ws):
        """Response should contain kubeconfig, talosconfig, talosctl, kubectl,
        dnsmasq, templates, and devices keys."""
        with patch("app.api.ws_handler.Path.home", return_value=MagicMock(
            __truediv__=lambda self, other: MagicMock(
                exists=MagicMock(return_value=False),
                __truediv__=lambda self2, other2: MagicMock(
                    exists=MagicMock(return_value=False),
                    __str__=lambda s: "/fake/path",
                ),
                __str__=lambda s: "/fake/path",
            ),
        )):
            with patch("app.api.ws_handler._troubleshoot_check_status") as mock_handler:
                # Build a realistic mock response instead of fighting Path mocking
                pass

        # Use a more direct approach: mock all the external dependencies
        fake_home = MagicMock()

        # Create path-like objects that support / operator
        def make_path(exists=False):
            p = MagicMock()
            p.exists.return_value = exists
            p.__truediv__ = lambda self, other: make_path(exists=False)
            p.__str__ = lambda self: "/fake/path"
            return p

        fake_home_path = make_path()

        with patch("app.api.ws_handler.Path.home", return_value=fake_home_path), \
             patch("app.api.cluster_router.find_talosctl", side_effect=FileNotFoundError), \
             patch("app.api.cluster_router.get_templates_base_dir", return_value=make_path()), \
             patch("shutil.which", return_value=None), \
             patch("subprocess.run", side_effect=FileNotFoundError):
            await _troubleshoot_check_status({}, mock_ws, "req-1")

        data, error = get_ws_response(mock_ws)
        assert error is None
        expected_keys = {"kubeconfig", "talosconfig", "talosctl", "kubectl", "dnsmasq", "templates", "devices"}
        assert expected_keys.issubset(set(data.keys())), f"Missing keys: {expected_keys - set(data.keys())}"

    @pytest.mark.asyncio
    async def test_check_status_device_counts(self, mock_db, mock_ws):
        """Device counts should reflect what is in the database."""
        from app.db.models import DeviceStatus
        seed_device(mock_db, hostname="node-01", mac_address="AA:BB:CC:DD:EE:01",
                    status=DeviceStatus.APPROVED)
        seed_device(mock_db, hostname="node-02", mac_address="AA:BB:CC:DD:EE:02",
                    status=DeviceStatus.PENDING)

        fake_home_path = MagicMock()
        fake_home_path.__truediv__ = lambda self, other: MagicMock(
            exists=MagicMock(return_value=False),
            __truediv__=lambda self2, other2: MagicMock(
                exists=MagicMock(return_value=False),
                __str__=lambda s: "/fake/path",
            ),
            __str__=lambda s: "/fake/path",
        )

        with patch("app.api.ws_handler.Path.home", return_value=fake_home_path), \
             patch("app.api.cluster_router.find_talosctl", side_effect=FileNotFoundError), \
             patch("app.api.cluster_router.get_templates_base_dir", return_value=fake_home_path), \
             patch("shutil.which", return_value=None), \
             patch("subprocess.run", side_effect=FileNotFoundError):
            await _troubleshoot_check_status({}, mock_ws, "req-2")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data["devices"]["total"] == 2
        assert data["devices"]["approved"] == 1
        assert data["devices"]["pending"] == 1


# ---------------------------------------------------------------------------
# _troubleshoot_regen_configs
# ---------------------------------------------------------------------------

class TestTroubleshootRegenConfigs:
    """Tests for the troubleshoot.regen_configs WebSocket handler."""

    @pytest.mark.asyncio
    async def test_regen_configs_success(self, mock_db, mock_ws):
        """Regenerates device configs and returns success with count."""
        from app.db.models import DeviceStatus
        seed_device(mock_db, hostname="node-01", mac_address="AA:BB:CC:DD:EE:01",
                    status=DeviceStatus.APPROVED)

        mock_cg = MagicMock()
        mock_cg.regenerate_all_configs.return_value = 1

        mock_ns = MagicMock()
        mock_ns.tftp_root = "/var/lib/tftpboot"
        mock_ns.server_ip = "10.0.42.2"
        mock_ns.talos_version = "1.12.2"
        mock_ns.strict_boot_mode = True

        mock_cs = MagicMock()
        mock_cs.install_disk = "/dev/sda"

        mock_ig = MagicMock()

        with patch("app.api.ws_handler._db", return_value=mock_db), \
             patch("app.crud.device.get_devices_by_status", return_value=[MagicMock()]), \
             patch("app.services.config_generator.ConfigGenerator", return_value=mock_cg), \
             patch("app.crud.network.get_network_settings", return_value=mock_ns), \
             patch("app.crud.cluster.get_cluster_settings", return_value=mock_cs), \
             patch("app.services.ipxe_generator.IPXEGenerator", return_value=mock_ig):
            await _troubleshoot_regen_configs({}, mock_ws, "req-1")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data["configs_regenerated"] == 1
        assert data["boot_ipxe"] is True


# ---------------------------------------------------------------------------
# _troubleshoot_reinstall_cni
# ---------------------------------------------------------------------------

class TestTroubleshootReinstallCni:
    """Tests for the troubleshoot.reinstall_cni WebSocket handler."""

    def _seed_cluster_settings(self, db, cni="flannel"):
        from app.db.models import ClusterSettings
        cs = ClusterSettings(
            cluster_name="test-cluster",
            cni=cni,
        )
        db.add(cs)
        db.commit()
        db.refresh(cs)
        return cs

    @pytest.mark.asyncio
    async def test_reinstall_cni_flannel_rejects(self, mock_db, mock_ws):
        """Flannel is built into Talos, so the handler should reject it."""
        self._seed_cluster_settings(mock_db, cni="flannel")

        await _troubleshoot_reinstall_cni({}, mock_ws, "req-1")

        data, error = get_ws_response(mock_ws)
        assert error is not None
        assert "flannel" in error.lower() or "no helm install needed" in error.lower()

    @pytest.mark.asyncio
    async def test_reinstall_cni_no_settings(self, mock_db, mock_ws):
        """Returns error when there are no cluster settings in the DB."""
        await _troubleshoot_reinstall_cni({}, mock_ws, "req-2")

        data, error = get_ws_response(mock_ws)
        assert error is not None
        assert "no cluster settings" in error.lower()

    @pytest.mark.asyncio
    async def test_reinstall_cni_cilium_success(self, mock_db, mock_ws):
        """For non-flannel CNIs like cilium, calls _deploy_cni and returns success."""
        from app.db.models import DeviceStatus, DeviceRole
        self._seed_cluster_settings(mock_db, cni="cilium")
        seed_device(mock_db, hostname="cp-node", mac_address="AA:BB:CC:DD:EE:10",
                    role=DeviceRole.CONTROLPLANE, ip_address="10.0.128.1",
                    status=DeviceStatus.APPROVED)

        # _deploy_cni is imported inside the handler from app.api.cluster_router
        with patch("app.api.cluster_router._deploy_cni", return_value=True):
            await _troubleshoot_reinstall_cni({}, mock_ws, "req-3")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert "cilium" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_reinstall_cni_deploy_failure(self, mock_db, mock_ws):
        """Returns error when _deploy_cni returns False."""
        self._seed_cluster_settings(mock_db, cni="cilium")

        with patch("app.api.cluster_router._deploy_cni", return_value=False):
            await _troubleshoot_reinstall_cni({}, mock_ws, "req-4")

        data, error = get_ws_response(mock_ws)
        assert error is not None
        assert "failed" in error.lower()


# ---------------------------------------------------------------------------
# _troubleshoot_fix_kubeconfig
# ---------------------------------------------------------------------------

class TestTroubleshootFixKubeconfig:
    """Tests for the troubleshoot.fix_kubeconfig WebSocket handler."""

    @pytest.mark.asyncio
    async def test_fix_kubeconfig_success(self, mock_ws):
        """When both talosconfig and kubeconfig succeed, returns a success message."""
        with patch("app.api.terminal_router._ensure_talosconfig", return_value=True), \
             patch("app.api.terminal_router._ensure_kubeconfig", return_value=True):
            await _troubleshoot_fix_kubeconfig({}, mock_ws, "req-1")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert "kubeconfig" in data["message"].lower()
        assert data["kubeconfig"] is True
        assert data["talosconfig"] is True

    @pytest.mark.asyncio
    async def test_fix_kubeconfig_failure(self, mock_ws):
        """When kubeconfig cannot be fetched, returns an error."""
        with patch("app.api.terminal_router._ensure_talosconfig", return_value=True), \
             patch("app.api.terminal_router._ensure_kubeconfig", return_value=False):
            await _troubleshoot_fix_kubeconfig({}, mock_ws, "req-2")

        data, error = get_ws_response(mock_ws)
        assert error is not None
        assert "could not fetch kubeconfig" in error.lower()
