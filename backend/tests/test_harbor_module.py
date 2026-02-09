"""Tests for the Harbor OCI registry module catalog entry and install flow."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.module_catalog import get_catalog_entry
from app.db.models import HelmRelease
from tests.conftest import seed_helm_release


# ---------------------------------------------------------------------------
# Helper: default install params
# ---------------------------------------------------------------------------

def _harbor_install_params(**overrides):
    """Default params for Harbor install."""
    params = {
        "release_name": "harbor",
        "chart_name": "harbor/harbor",
        "namespace": "harbor",
        "chart_version": None,
        "repo_name": "harbor",
        "repo_url": "https://helm.goharbor.io",
        "catalog_id": "harbor",
        "values_yaml": "harborAdminPassword: MySecurePass123",
        "values_json": json.dumps({
            "expose.type": "nodePort",
            "expose.tls.enabled": True,
            "harborAdminPassword": "MySecurePass123",
            "persistence.enabled": True,
        }),
    }
    params.update(overrides)
    return params


# ===========================================================================
# 1. Harbor — Catalog Entry Validation
# ===========================================================================

class TestHarborCatalogEntry:
    """Validate the Harbor catalog entry."""

    def test_harbor_exists(self):
        """Harbor catalog entry exists with correct id, name, scope."""
        entry = get_catalog_entry("harbor")
        assert entry is not None, "Harbor catalog entry not found"
        assert entry["id"] == "harbor"
        assert entry["name"] == "Harbor"
        assert entry["scope"] == "cluster"
        assert entry["category"] == "ci-cd"

    def test_harbor_chart_source(self):
        """Harbor uses standard Helm repo (not OCI)."""
        entry = get_catalog_entry("harbor")
        assert entry["chart_name"] == "harbor/harbor"
        assert entry["repo_name"] == "harbor"
        assert entry["repo_url"] == "https://helm.goharbor.io"

    def test_harbor_cluster_defaults(self):
        """Cluster-scoped: has default namespace and release name."""
        entry = get_catalog_entry("harbor")
        assert entry["default_namespace"] == "harbor"
        assert entry["default_release_name"] == "harbor"

    def test_harbor_no_privileged_namespace(self):
        """Harbor does not require privileged namespace."""
        entry = get_catalog_entry("harbor")
        assert entry.get("privileged_namespace") is not True


# ===========================================================================
# 2. Harbor — Wizard Fields
# ===========================================================================

class TestHarborWizardFields:
    """Validate Harbor wizard fields."""

    @pytest.fixture
    def harbor_fields(self):
        entry = get_catalog_entry("harbor")
        return {f["key"]: f for f in entry["wizard_fields"]}

    def test_harbor_field_keys(self, harbor_fields):
        """All expected wizard fields present."""
        expected_keys = {
            "expose.type",
            "expose.tls.enabled",
            "externalURL",
            "harborAdminPassword",
            "persistence.enabled",
            "persistence.persistentVolumeClaim.registry.size",
            "persistence.persistentVolumeClaim.database.size",
            "trivy.enabled",
            "metrics.enabled",
        }
        actual_keys = set(harbor_fields.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"Missing wizard fields: {missing}"
        assert not extra, f"Unexpected wizard fields: {extra}"

    def test_harbor_expose_type_options(self, harbor_fields):
        """Expose type has all valid options."""
        field = harbor_fields["expose.type"]
        assert field["type"] == "select"
        assert "nodePort" in field["options"]
        assert "loadBalancer" in field["options"]
        assert "ingress" in field["options"]
        assert "clusterIP" in field["options"]
        assert field["default"] == "nodePort"

    def test_harbor_admin_password_required(self, harbor_fields):
        """Admin password field is required."""
        field = harbor_fields["harborAdminPassword"]
        assert field["type"] == "text"
        assert field.get("required") is True
        assert field["default"] == "Harbor12345"

    def test_harbor_persistence_defaults(self, harbor_fields):
        """Persistence enabled by default with reasonable sizes."""
        assert harbor_fields["persistence.enabled"]["default"] is True
        assert harbor_fields["persistence.persistentVolumeClaim.registry.size"]["default"] == "50Gi"
        assert harbor_fields["persistence.persistentVolumeClaim.database.size"]["default"] == "5Gi"

    def test_harbor_trivy_enabled_by_default(self, harbor_fields):
        """Trivy scanner enabled by default for security."""
        field = harbor_fields["trivy.enabled"]
        assert field["type"] == "boolean"
        assert field["default"] is True

    def test_harbor_sections(self, harbor_fields):
        """Fields span expected sections."""
        sections = {f["section"] for f in harbor_fields.values()}
        expected_sections = {"Networking", "Authentication", "Storage", "Security", "Monitoring"}
        missing = expected_sections - sections
        assert not missing, f"Missing sections: {missing}"


# ===========================================================================
# 3. Harbor — Install Flow
# ===========================================================================

@pytest.fixture
def mock_post_install():
    with patch("app.api.ws_handler._run_post_install", new_callable=AsyncMock, return_value="") as m:
        yield m


@pytest.mark.asyncio
async def test_harbor_install_adds_repo(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Harbor uses standard Helm repo, so repo_add IS called."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="harbor",
        chart_name="harbor/harbor", namespace="harbor",
    )
    params = _harbor_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_awaited_once_with("harbor", "https://helm.goharbor.io")
    mock_helm_runner.install.assert_awaited_once()


@pytest.mark.asyncio
async def test_harbor_install_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Full happy-path Harbor install."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="harbor",
        chart_name="harbor/harbor", namespace="harbor",
    )
    params = _harbor_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["chart"] == "harbor/harbor"
    assert call_kwargs[1]["namespace"] == "harbor"


@pytest.mark.asyncio
async def test_harbor_install_broadcasts_status(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Harbor install broadcasts deploying and deployed status events."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="harbor",
        chart_name="harbor/harbor", namespace="harbor",
    )
    params = _harbor_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    statuses = [e["data"]["status"] for e in status_events]
    assert "deploying" in statuses
    assert "deployed" in statuses


@pytest.mark.asyncio
async def test_harbor_install_failure(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Harbor install sets failed status when helm install fails."""
    from app.api.ws_handler import _do_helm_install

    mock_helm_runner.install = AsyncMock(return_value=(False, "timeout waiting for condition"))

    release = seed_helm_release(
        mock_db, status="pending", catalog_id="harbor",
        chart_name="harbor/harbor", namespace="harbor",
    )
    params = _harbor_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "failed"
