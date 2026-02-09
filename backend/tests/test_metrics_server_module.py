"""Tests for the Metrics Server module catalog entry and install flow."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.module_catalog import get_catalog_entry
from app.db.models import HelmRelease
from tests.conftest import seed_helm_release


# ---------------------------------------------------------------------------
# Helper: default install params
# ---------------------------------------------------------------------------

def _metrics_server_install_params(**overrides):
    """Default params for Metrics Server install."""
    params = {
        "release_name": "metrics-server",
        "chart_name": "metrics-server/metrics-server",
        "namespace": "kube-system",
        "chart_version": None,
        "repo_name": "metrics-server",
        "repo_url": "https://kubernetes-sigs.github.io/metrics-server/",
        "catalog_id": "metrics-server",
        "values_yaml": "",
        "values_json": json.dumps({
            "_kubeletInsecureTls": True,
            "replicas": 1,
        }),
    }
    params.update(overrides)
    return params


# ===========================================================================
# 1. Metrics Server — Catalog Entry Validation
# ===========================================================================

class TestMetricsServerCatalogEntry:
    """Validate the Metrics Server catalog entry."""

    def test_metrics_server_exists(self):
        """Metrics Server catalog entry exists with correct id, name, scope."""
        entry = get_catalog_entry("metrics-server")
        assert entry is not None, "Metrics Server catalog entry not found"
        assert entry["id"] == "metrics-server"
        assert entry["name"] == "Metrics Server"
        assert entry["scope"] == "cluster"
        assert entry["category"] == "monitoring"

    def test_metrics_server_chart_source(self):
        """Metrics Server uses standard Helm repo."""
        entry = get_catalog_entry("metrics-server")
        assert entry["chart_name"] == "metrics-server/metrics-server"
        assert entry["repo_name"] == "metrics-server"
        assert entry["repo_url"] == "https://kubernetes-sigs.github.io/metrics-server/"

    def test_metrics_server_cluster_defaults(self):
        """Cluster-scoped: has default namespace and release name."""
        entry = get_catalog_entry("metrics-server")
        assert entry["default_namespace"] == "kube-system"
        assert entry["default_release_name"] == "metrics-server"

    def test_metrics_server_no_privileged_namespace(self):
        """Metrics Server does not require privileged namespace."""
        entry = get_catalog_entry("metrics-server")
        assert entry.get("privileged_namespace") is not True


# ===========================================================================
# 2. Metrics Server — Wizard Fields
# ===========================================================================

class TestMetricsServerWizardFields:
    """Validate Metrics Server wizard fields."""

    @pytest.fixture
    def ms_fields(self):
        entry = get_catalog_entry("metrics-server")
        return {f["key"]: f for f in entry["wizard_fields"]}

    def test_metrics_server_field_keys(self, ms_fields):
        """All expected wizard fields present."""
        expected_keys = {
            "_kubeletInsecureTls",
            "replicas",
            "_metricResolution",
        }
        actual_keys = set(ms_fields.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"Missing wizard fields: {missing}"
        assert not extra, f"Unexpected wizard fields: {extra}"

    def test_metrics_server_kubelet_insecure_tls_default(self, ms_fields):
        """Kubelet insecure TLS defaults to True for Talos Linux."""
        field = ms_fields["_kubeletInsecureTls"]
        assert field["type"] == "boolean"
        assert field["default"] is True
        # Description must mention Talos
        desc = field["description"].lower()
        assert "talos" in desc, "Description must mention Talos Linux"

    def test_metrics_server_replicas(self, ms_fields):
        """Replicas field has sensible default."""
        field = ms_fields["replicas"]
        assert field["type"] == "number"
        assert field["default"] == 1

    def test_metrics_server_resolution_options(self, ms_fields):
        """Metric resolution has valid options."""
        field = ms_fields["_metricResolution"]
        assert field["type"] == "select"
        assert "15s" in field["options"]
        assert "30s" in field["options"]
        assert field["default"] == "15s"

    def test_metrics_server_sections(self, ms_fields):
        """Fields span expected sections."""
        sections = {f["section"] for f in ms_fields.values()}
        expected_sections = {"TLS", "Deployment", "Collection"}
        missing = expected_sections - sections
        assert not missing, f"Missing sections: {missing}"


# ===========================================================================
# 3. Metrics Server — Install Flow
# ===========================================================================

@pytest.fixture
def mock_post_install():
    with patch("app.api.ws_handler._run_post_install", new_callable=AsyncMock, return_value="") as m:
        yield m


@pytest.mark.asyncio
async def test_metrics_server_install_adds_repo(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Metrics Server uses standard Helm repo, so repo_add IS called."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="metrics-server",
        chart_name="metrics-server/metrics-server", namespace="kube-system",
    )
    params = _metrics_server_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_awaited_once_with(
        "metrics-server", "https://kubernetes-sigs.github.io/metrics-server/"
    )
    mock_helm_runner.install.assert_awaited_once()


@pytest.mark.asyncio
async def test_metrics_server_install_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Full happy-path Metrics Server install."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="metrics-server",
        chart_name="metrics-server/metrics-server", namespace="kube-system",
    )
    params = _metrics_server_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["chart"] == "metrics-server/metrics-server"
    assert call_kwargs[1]["namespace"] == "kube-system"


@pytest.mark.asyncio
async def test_metrics_server_install_broadcasts_status(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Metrics Server install broadcasts deploying and deployed status events."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="metrics-server",
        chart_name="metrics-server/metrics-server", namespace="kube-system",
    )
    params = _metrics_server_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    statuses = [e["data"]["status"] for e in status_events]
    assert "deploying" in statuses
    assert "deployed" in statuses


@pytest.mark.asyncio
async def test_metrics_server_install_failure(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Metrics Server install sets failed status when helm install fails."""
    from app.api.ws_handler import _do_helm_install

    mock_helm_runner.install = AsyncMock(return_value=(False, "connection refused"))

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="metrics-server",
        chart_name="metrics-server/metrics-server", namespace="kube-system",
    )
    params = _metrics_server_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "failed"
