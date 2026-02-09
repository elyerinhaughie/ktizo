"""Tests for the MariaDB module: catalog entry, OCI install flow, Galera clustering."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.module_catalog import get_catalog_entry
from app.db.models import HelmRelease
from tests.conftest import seed_helm_release


# ---------------------------------------------------------------------------
# Helper: default MariaDB install params
# ---------------------------------------------------------------------------

def _mariadb_install_params(**overrides):
    """Default params matching a MariaDB standalone install from the frontend wizard."""
    params = {
        "release_name": "my-mariadb",
        "chart_name": "oci://registry-1.docker.io/cloudpirates/mariadb",
        "namespace": "mariadb-ns",
        "chart_version": None,
        "repo_name": "",
        "repo_url": "",
        "catalog_id": "mariadb",
        "values_yaml": "auth:\n  rootPassword: \"\"\n  database: my_database\npersistence:\n  enabled: true\n  size: 8Gi",
        "values_json": json.dumps({
            "auth.rootPassword": "",
            "auth.database": "my_database",
            "auth.username": "",
            "auth.password": "",
            "persistence.enabled": True,
            "persistence.size": "8Gi",
            "galera.enabled": False,
        }),
    }
    params.update(overrides)
    return params


# ===========================================================================
# 1. Catalog Entry Validation
# ===========================================================================

class TestMariaDBCatalogEntry:
    """Validate the MariaDB catalog entry structure."""

    def test_mariadb_catalog_entry_exists(self):
        """MariaDB catalog entry exists with correct id, name, and scope."""
        entry = get_catalog_entry("mariadb")
        assert entry is not None, "MariaDB catalog entry not found"
        assert entry["id"] == "mariadb"
        assert entry["name"] == "MariaDB"
        assert entry["scope"] == "application"
        assert entry["category"] == "databases"

    def test_mariadb_catalog_oci_chart(self):
        """MariaDB uses OCI chart reference from CloudPirates."""
        entry = get_catalog_entry("mariadb")
        assert entry["chart_name"].startswith("oci://"), (
            f"Expected OCI chart ref, got: {entry['chart_name']}"
        )
        assert "cloudpirates/mariadb" in entry["chart_name"]
        assert entry["repo_name"] == "", "OCI charts must have empty repo_name"
        assert entry["repo_url"] == "", "OCI charts must have empty repo_url"

    def test_mariadb_catalog_empty_defaults(self):
        """Application-scoped: user must provide namespace and release name."""
        entry = get_catalog_entry("mariadb")
        assert entry["default_namespace"] == "", (
            "Application-scoped MariaDB must have empty default_namespace"
        )
        assert entry["default_release_name"] == "", (
            "Application-scoped MariaDB must have empty default_release_name"
        )

    def test_mariadb_catalog_no_privileged_namespace(self):
        """MariaDB does NOT require privileged namespace."""
        entry = get_catalog_entry("mariadb")
        assert entry.get("privileged_namespace") is not True, (
            "MariaDB should NOT have privileged_namespace=True"
        )


# ===========================================================================
# 2. Wizard Field Validation — matches actual CloudPirates chart values.yaml
# ===========================================================================

class TestMariaDBWizardFields:
    """Validate MariaDB wizard fields match the actual CloudPirates chart structure.

    The CloudPirates MariaDB chart uses:
    - Top-level persistence.* (NOT primary.persistence.*)
    - Top-level resources.* (NOT primary.resources.*)
    - galera.enabled + galera.replicaCount for clustering (NOT architecture/secondary)
    """

    @pytest.fixture
    def mariadb_fields(self):
        entry = get_catalog_entry("mariadb")
        return {f["key"]: f for f in entry["wizard_fields"]}

    def test_mariadb_wizard_field_keys(self, mariadb_fields):
        """All expected wizard fields are present with correct chart value keys."""
        expected_keys = {
            "auth.rootPassword", "auth.database", "auth.username", "auth.password",
            "persistence.enabled", "persistence.size",
            "galera.enabled", "galera.replicaCount",
            "resources.requests.memory", "resources.requests.cpu",
            "metrics.enabled",
        }
        actual_keys = set(mariadb_fields.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"Missing wizard fields: {missing}"
        assert not extra, f"Unexpected wizard fields: {extra}"

    def test_mariadb_wizard_galera_conditional(self, mariadb_fields):
        """galera.replicaCount only shows when galera.enabled is true."""
        field = mariadb_fields["galera.replicaCount"]
        assert "show_when" in field, "galera.replicaCount missing show_when"
        assert field["show_when"]["key"] == "galera.enabled"
        assert field["show_when"]["value"] is True

    def test_mariadb_wizard_galera_defaults(self, mariadb_fields):
        """Galera defaults: disabled, 3 nodes when enabled."""
        assert mariadb_fields["galera.enabled"]["default"] is False
        assert mariadb_fields["galera.replicaCount"]["default"] == 3

    def test_mariadb_wizard_persistence_is_top_level(self, mariadb_fields):
        """Persistence uses top-level keys (not primary.persistence.*)
        matching the actual CloudPirates chart structure."""
        assert "persistence.enabled" in mariadb_fields
        assert "persistence.size" in mariadb_fields
        assert "primary.persistence.enabled" not in mariadb_fields, (
            "Chart uses top-level persistence.*, not primary.persistence.*"
        )

    def test_mariadb_wizard_resources_are_top_level(self, mariadb_fields):
        """Resources use top-level keys (not primary.resources.*)."""
        assert "resources.requests.memory" in mariadb_fields
        assert "resources.requests.cpu" in mariadb_fields
        assert "primary.resources.requests.memory" not in mariadb_fields, (
            "Chart uses top-level resources.*, not primary.resources.*"
        )

    def test_mariadb_wizard_sections(self, mariadb_fields):
        """Fields span all expected sections."""
        sections = {f["section"] for f in mariadb_fields.values()}
        expected_sections = {
            "Authentication", "Storage", "Clustering",
            "Resources", "Monitoring",
        }
        missing = expected_sections - sections
        assert not missing, f"Missing sections: {missing}"


# ===========================================================================
# 3. OCI Install Flow
# ===========================================================================

@pytest.fixture
def mock_post_install():
    with patch("app.api.ws_handler._run_post_install", new_callable=AsyncMock, return_value="") as m:
        yield m


@pytest.fixture
def mock_label_ns():
    with patch("app.api.ws_handler._label_namespace_privileged", new_callable=AsyncMock) as m:
        yield m


@pytest.mark.asyncio
async def test_mariadb_install_skips_repo_add(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """OCI chart: repo_add NOT called when repo_name/repo_url are empty."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="mariadb",
                                chart_name="oci://registry-1.docker.io/cloudpirates/mariadb")
    params = _mariadb_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_not_awaited()
    mock_helm_runner.install.assert_awaited_once()


@pytest.mark.asyncio
async def test_mariadb_install_no_privileged_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install, mock_label_ns,
):
    """MariaDB does not need privileged namespace labeling."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="mariadb",
                                chart_name="oci://registry-1.docker.io/cloudpirates/mariadb")
    params = _mariadb_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_label_ns.assert_not_awaited()

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


@pytest.mark.asyncio
async def test_mariadb_install_success_oci(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Full happy-path: pending -> deploying -> deployed with OCI chart ref."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="mariadb",
                                chart_name="oci://registry-1.docker.io/cloudpirates/mariadb",
                                namespace="mariadb-ns")
    params = _mariadb_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    # Verify broadcast events
    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    statuses = [e["data"]["status"] for e in status_events]
    assert "deploying" in statuses
    assert "deployed" in statuses

    # Verify OCI chart ref passed to helm
    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["chart"] == "oci://registry-1.docker.io/cloudpirates/mariadb"
    assert call_kwargs[1]["namespace"] == "mariadb-ns"


# ===========================================================================
# 4. Application Scope + Values
# ===========================================================================

@pytest.mark.asyncio
async def test_mariadb_install_custom_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """User-provided namespace is passed through to helm install."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="mariadb",
                                chart_name="oci://registry-1.docker.io/cloudpirates/mariadb",
                                namespace="my-app-db")
    params = _mariadb_install_params(namespace="my-app-db")

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"

    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["namespace"] == "my-app-db"


@pytest.mark.asyncio
async def test_mariadb_install_standalone_default(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Default standalone (galera disabled) installs single-node MariaDB."""
    from app.api.ws_handler import _do_helm_install

    values_yaml = "persistence:\n  enabled: true\n  size: 8Gi"
    release = seed_helm_release(mock_db, status="pending", catalog_id="mariadb",
                                chart_name="oci://registry-1.docker.io/cloudpirates/mariadb",
                                namespace="standalone-db")
    params = _mariadb_install_params(
        namespace="standalone-db",
        values_yaml=values_yaml,
        values_json=json.dumps({"persistence.enabled": True, "galera.enabled": False}),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


@pytest.mark.asyncio
async def test_mariadb_install_galera_cluster(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Galera cluster mode passes galera.enabled=true and galera.replicaCount to helm."""
    from app.api.ws_handler import _do_helm_install

    values_yaml = "galera:\n  enabled: true\n  replicaCount: 3\npersistence:\n  enabled: true\n  size: 8Gi"
    release = seed_helm_release(mock_db, status="pending", catalog_id="mariadb",
                                chart_name="oci://registry-1.docker.io/cloudpirates/mariadb",
                                namespace="galera-db")
    params = _mariadb_install_params(
        namespace="galera-db",
        values_yaml=values_yaml,
        values_json=json.dumps({
            "galera.enabled": True,
            "galera.replicaCount": 3,
            "persistence.enabled": True,
            "persistence.size": "8Gi",
        }),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"

    # Verify galera values were passed through
    call_kwargs = mock_helm_runner.install.call_args
    passed_yaml = call_kwargs[1].get("values_yaml") or ""
    assert "galera" in passed_yaml
    assert "replicaCount" in passed_yaml


@pytest.mark.asyncio
async def test_mariadb_install_with_all_wizard_defaults(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Install with all default wizard values succeeds."""
    from app.api.ws_handler import _do_helm_install

    entry = get_catalog_entry("mariadb")
    wizard_values = {}
    for field in entry["wizard_fields"]:
        wizard_values[field["key"]] = field["default"]

    values_yaml_lines = []
    for key, val in wizard_values.items():
        if not key.startswith("_"):
            values_yaml_lines.append(f"{key}: {val}")
    values_yaml = "\n".join(values_yaml_lines)

    release = seed_helm_release(mock_db, status="pending", catalog_id="mariadb",
                                chart_name="oci://registry-1.docker.io/cloudpirates/mariadb",
                                namespace="mariadb-defaults")
    params = _mariadb_install_params(
        namespace="mariadb-defaults",
        values_yaml=values_yaml,
        values_json=json.dumps(wizard_values),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["values_yaml"] is not None
