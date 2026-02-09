"""Tests for the Traefik module: catalog entry, chart value paths, install flow."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.module_catalog import get_catalog_entry
from app.db.models import HelmRelease
from tests.conftest import seed_helm_release


# ---------------------------------------------------------------------------
# Helper: default Traefik install params
# ---------------------------------------------------------------------------

def _traefik_install_params(**overrides):
    """Default params matching a Traefik install from the frontend wizard."""
    params = {
        "release_name": "traefik",
        "chart_name": "traefik/traefik",
        "namespace": "traefik",
        "chart_version": None,
        "repo_name": "traefik",
        "repo_url": "https://traefik.github.io/charts",
        "catalog_id": "traefik",
        "values_yaml": (
            "service:\n  type: LoadBalancer\n"
            "ports:\n  websecure:\n    http:\n      tls:\n        enabled: true\n"
            "ingressRoute:\n  dashboard:\n    enabled: false"
        ),
        "values_json": json.dumps({
            "service.type": "LoadBalancer",
            "ports.websecure.http.tls.enabled": True,
            "ingressRoute.dashboard.enabled": False,
            "deployment.replicas": 1,
            "logs.general.level": "INFO",
        }),
    }
    params.update(overrides)
    return params


# ===========================================================================
# 1. Catalog Entry Validation
# ===========================================================================

class TestTraefikCatalogEntry:
    """Validate the Traefik catalog entry structure."""

    def test_traefik_catalog_entry_exists(self):
        """Traefik catalog entry exists with correct id, name, and scope."""
        entry = get_catalog_entry("traefik")
        assert entry is not None, "Traefik catalog entry not found"
        assert entry["id"] == "traefik"
        assert entry["name"] == "Traefik"
        assert entry["scope"] == "cluster"
        assert entry["category"] == "networking"

    def test_traefik_catalog_repo_chart(self):
        """Traefik uses a standard helm repo (not OCI)."""
        entry = get_catalog_entry("traefik")
        assert entry["chart_name"] == "traefik/traefik"
        assert entry["repo_name"] == "traefik"
        assert entry["repo_url"] == "https://traefik.github.io/charts"

    def test_traefik_catalog_cluster_defaults(self):
        """Cluster-scoped: has default namespace and release name."""
        entry = get_catalog_entry("traefik")
        assert entry["default_namespace"] == "traefik"
        assert entry["default_release_name"] == "traefik"

    def test_traefik_catalog_no_privileged_namespace(self):
        """Traefik does NOT require privileged namespace."""
        entry = get_catalog_entry("traefik")
        assert entry.get("privileged_namespace") is not True, (
            "Traefik runs as non-root with read-only filesystem — "
            "should NOT have privileged_namespace=True"
        )


# ===========================================================================
# 2. Wizard Field Validation — must match actual chart values.yaml schema
# ===========================================================================

class TestTraefikWizardFields:
    """Validate Traefik wizard fields match the actual chart structure.

    CRITICAL: The Traefik chart uses strict JSON schema validation with
    additionalProperties: false on port entries. The TLS setting for the
    websecure entrypoint lives at:
        ports.websecure.http.tls.enabled
    NOT at:
        ports.websecure.tls.enabled  (WRONG — causes install failure)
    """

    @pytest.fixture
    def traefik_fields(self):
        entry = get_catalog_entry("traefik")
        return {f["key"]: f for f in entry["wizard_fields"]}

    def test_traefik_wizard_field_keys(self, traefik_fields):
        """All expected wizard fields are present with correct chart value keys."""
        expected_keys = {
            "service.type",
            "ports.websecure.http.tls.enabled",
            "ingressRoute.dashboard.enabled",
            "deployment.replicas",
            "logs.general.level",
        }
        actual_keys = set(traefik_fields.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"Missing wizard fields: {missing}"
        assert not extra, f"Unexpected wizard fields: {extra}"

    def test_traefik_tls_field_uses_correct_path(self, traefik_fields):
        """TLS field MUST use ports.websecure.http.tls.enabled — NOT ports.websecure.tls.enabled.

        The Traefik helm chart enforces additionalProperties: false on port entries.
        Using 'ports.websecure.tls.enabled' causes:
            Error: INSTALLATION FAILED: values don't meet the specifications
            of the schema(s): at '/ports/websecure': additional properties 'tls' not allowed

        Regression test for: Traefik install failure due to wrong TLS value path.
        """
        assert "ports.websecure.http.tls.enabled" in traefik_fields, (
            "TLS field must use 'ports.websecure.http.tls.enabled' — "
            "the chart rejects 'ports.websecure.tls.enabled' due to strict schema"
        )
        assert "ports.websecure.tls.enabled" not in traefik_fields, (
            "WRONG path 'ports.websecure.tls.enabled' must NOT be used — "
            "causes additionalProperties validation failure"
        )

    def test_traefik_tls_default_enabled(self, traefik_fields):
        """TLS on websecure port is enabled by default (matches chart default)."""
        field = traefik_fields["ports.websecure.http.tls.enabled"]
        assert field["default"] is True

    def test_traefik_service_type_options(self, traefik_fields):
        """Service type has all three valid options."""
        field = traefik_fields["service.type"]
        assert field["type"] == "select"
        assert set(field["options"]) == {"LoadBalancer", "NodePort", "ClusterIP"}
        assert field["default"] == "LoadBalancer"

    def test_traefik_deployment_replicas(self, traefik_fields):
        """Deployment replicas field exists with sensible default."""
        field = traefik_fields["deployment.replicas"]
        assert field["type"] == "number"
        assert field["default"] == 1

    def test_traefik_log_level_options(self, traefik_fields):
        """Log level field has valid Traefik log levels."""
        field = traefik_fields["logs.general.level"]
        assert field["type"] == "select"
        assert "INFO" in field["options"]
        assert "DEBUG" in field["options"]
        assert "ERROR" in field["options"]
        assert field["default"] == "INFO"

    def test_traefik_wizard_sections(self, traefik_fields):
        """Fields span all expected sections."""
        sections = {f["section"] for f in traefik_fields.values()}
        expected_sections = {
            "Networking", "TLS", "Dashboard", "Deployment", "Logging",
        }
        missing = expected_sections - sections
        assert not missing, f"Missing sections: {missing}"


# ===========================================================================
# 3. Install Flow — repo-based (not OCI)
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
async def test_traefik_install_calls_repo_add(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Traefik uses a standard helm repo — repo_add MUST be called before install."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="traefik",
                                chart_name="traefik/traefik",
                                repo_name="traefik",
                                repo_url="https://traefik.github.io/charts")
    params = _traefik_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_awaited_once()
    mock_helm_runner.install.assert_awaited_once()


@pytest.mark.asyncio
async def test_traefik_install_no_privileged_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install, mock_label_ns,
):
    """Traefik does not need privileged namespace labeling."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="traefik",
                                chart_name="traefik/traefik")
    params = _traefik_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_label_ns.assert_not_awaited()

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


@pytest.mark.asyncio
async def test_traefik_install_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Full happy-path: pending -> deploying -> deployed with correct chart ref."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="traefik",
                                chart_name="traefik/traefik",
                                namespace="traefik")
    params = _traefik_install_params()

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

    # Verify chart ref passed to helm
    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["chart"] == "traefik/traefik"
    assert call_kwargs[1]["namespace"] == "traefik"


# ===========================================================================
# 4. Values Passthrough
# ===========================================================================

@pytest.mark.asyncio
async def test_traefik_install_values_passthrough(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Values YAML with correct TLS path is passed through to helm install."""
    from app.api.ws_handler import _do_helm_install

    values_yaml = (
        "service:\n  type: LoadBalancer\n"
        "ports:\n  websecure:\n    http:\n      tls:\n        enabled: true\n"
        "ingressRoute:\n  dashboard:\n    enabled: true\n"
        "deployment:\n  replicas: 2"
    )
    release = seed_helm_release(mock_db, status="pending", catalog_id="traefik",
                                chart_name="traefik/traefik",
                                namespace="traefik")
    params = _traefik_install_params(values_yaml=values_yaml)

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"

    # Verify values_yaml was passed with correct TLS path
    call_kwargs = mock_helm_runner.install.call_args
    passed_yaml = call_kwargs[1].get("values_yaml") or ""
    assert "websecure" in passed_yaml
    assert "service" in passed_yaml


@pytest.mark.asyncio
async def test_traefik_install_with_all_wizard_defaults(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Install with all default wizard values succeeds."""
    from app.api.ws_handler import _do_helm_install

    entry = get_catalog_entry("traefik")
    wizard_values = {}
    for field in entry["wizard_fields"]:
        wizard_values[field["key"]] = field["default"]

    values_yaml_lines = []
    for key, val in wizard_values.items():
        if not key.startswith("_"):
            values_yaml_lines.append(f"{key}: {val}")
    values_yaml = "\n".join(values_yaml_lines)

    release = seed_helm_release(mock_db, status="pending", catalog_id="traefik",
                                chart_name="traefik/traefik",
                                namespace="traefik")
    params = _traefik_install_params(
        values_yaml=values_yaml,
        values_json=json.dumps(wizard_values),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()
