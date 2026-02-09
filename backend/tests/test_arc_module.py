"""Tests for the Actions Runner Controller (ARC) modules: controller + runner scale set."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.module_catalog import get_catalog_entry
from app.db.models import HelmRelease
from tests.conftest import seed_helm_release


# ---------------------------------------------------------------------------
# Helper: default install params
# ---------------------------------------------------------------------------

def _arc_controller_install_params(**overrides):
    """Default params for ARC controller install."""
    params = {
        "release_name": "arc",
        "chart_name": "oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller",
        "namespace": "arc-systems",
        "chart_version": None,
        "repo_name": "",
        "repo_url": "",
        "catalog_id": "arc-controller",
        "values_yaml": "",
        "values_json": json.dumps({}),
    }
    params.update(overrides)
    return params


def _arc_runner_set_install_params(**overrides):
    """Default params for ARC runner scale set install."""
    params = {
        "release_name": "arc-runner-set",
        "chart_name": "oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set",
        "namespace": "arc-runners",
        "chart_version": None,
        "repo_name": "",
        "repo_url": "",
        "catalog_id": "arc-runner-set",
        "values_yaml": (
            "githubConfigUrl: https://github.com/myorg/myrepo\n"
            "githubConfigSecret:\n  github_token: ghp_example"
        ),
        "values_json": json.dumps({
            "githubConfigUrl": "https://github.com/myorg/myrepo",
            "maxRunners": 10,
            "minRunners": 0,
            "containerMode.type": "dind",
        }),
    }
    params.update(overrides)
    return params


# ===========================================================================
# 1. ARC Controller — Catalog Entry Validation
# ===========================================================================

class TestArcControllerCatalogEntry:
    """Validate the ARC controller catalog entry."""

    def test_arc_controller_exists(self):
        """ARC controller catalog entry exists with correct id, name, scope."""
        entry = get_catalog_entry("arc-controller")
        assert entry is not None, "ARC controller catalog entry not found"
        assert entry["id"] == "arc-controller"
        assert entry["name"] == "Actions Runner Controller"
        assert entry["scope"] == "cluster"
        assert entry["category"] == "ci-cd"

    def test_arc_controller_oci_chart(self):
        """ARC controller uses OCI chart from ghcr.io."""
        entry = get_catalog_entry("arc-controller")
        assert entry["chart_name"].startswith("oci://ghcr.io/"), (
            f"Expected ghcr.io OCI ref, got: {entry['chart_name']}"
        )
        assert "gha-runner-scale-set-controller" in entry["chart_name"]
        assert entry["repo_name"] == "", "OCI charts must have empty repo_name"
        assert entry["repo_url"] == "", "OCI charts must have empty repo_url"

    def test_arc_controller_cluster_defaults(self):
        """Cluster-scoped: has default namespace and release name."""
        entry = get_catalog_entry("arc-controller")
        assert entry["default_namespace"] == "arc-systems"
        assert entry["default_release_name"] == "arc"

    def test_arc_controller_privileged_namespace(self):
        """ARC controller requires privileged namespace for listener pods."""
        entry = get_catalog_entry("arc-controller")
        assert entry.get("privileged_namespace") is True


# ===========================================================================
# 2. ARC Controller — Wizard Fields
# ===========================================================================

class TestArcControllerWizardFields:
    """Validate ARC controller wizard fields."""

    @pytest.fixture
    def controller_fields(self):
        entry = get_catalog_entry("arc-controller")
        return {f["key"]: f for f in entry["wizard_fields"]}

    def test_arc_controller_field_keys(self, controller_fields):
        """Controller has minimal wizard fields — most config is in runner sets."""
        expected_keys = {
            "replicaCount",
            "flags.logLevel",
            "flags.updateStrategy",
        }
        actual_keys = set(controller_fields.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"Missing wizard fields: {missing}"
        assert not extra, f"Unexpected wizard fields: {extra}"

    def test_arc_controller_log_level_options(self, controller_fields):
        """Log level has valid options."""
        field = controller_fields["flags.logLevel"]
        assert field["type"] == "select"
        assert "debug" in field["options"]
        assert "info" in field["options"]
        assert field["default"] == "info"

    def test_arc_controller_update_strategy_options(self, controller_fields):
        """Update strategy has valid options."""
        field = controller_fields["flags.updateStrategy"]
        assert field["type"] == "select"
        assert "immediate" in field["options"]
        assert "eventual" in field["options"]

    def test_arc_controller_sections(self, controller_fields):
        """Fields span expected sections."""
        sections = {f["section"] for f in controller_fields.values()}
        expected_sections = {"Deployment", "Logging"}
        missing = expected_sections - sections
        assert not missing, f"Missing sections: {missing}"


# ===========================================================================
# 3. ARC Runner Scale Set — Catalog Entry Validation
# ===========================================================================

class TestArcRunnerSetCatalogEntry:
    """Validate the ARC runner scale set catalog entry."""

    def test_arc_runner_set_exists(self):
        """ARC runner scale set catalog entry exists."""
        entry = get_catalog_entry("arc-runner-set")
        assert entry is not None, "ARC runner scale set catalog entry not found"
        assert entry["id"] == "arc-runner-set"
        assert entry["name"] == "GitHub Actions Runner Set"
        assert entry["scope"] == "application"
        assert entry["category"] == "ci-cd"

    def test_arc_runner_set_oci_chart(self):
        """Runner scale set uses OCI chart from ghcr.io."""
        entry = get_catalog_entry("arc-runner-set")
        assert entry["chart_name"].startswith("oci://ghcr.io/"), (
            f"Expected ghcr.io OCI ref, got: {entry['chart_name']}"
        )
        assert entry["chart_name"].endswith("/gha-runner-scale-set"), (
            "Runner set chart must end with /gha-runner-scale-set (not the controller chart)"
        )
        assert entry["repo_name"] == ""
        assert entry["repo_url"] == ""

    def test_arc_runner_set_application_defaults(self):
        """Application-scoped: user provides namespace and release name."""
        entry = get_catalog_entry("arc-runner-set")
        assert entry["default_namespace"] == "", (
            "Application-scoped: user must provide namespace"
        )
        assert entry["default_release_name"] == "", (
            "Application-scoped: user provides release name (becomes runs-on label)"
        )

    def test_arc_runner_set_privileged_namespace(self):
        """Runner set requires privileged namespace (DinD needs it)."""
        entry = get_catalog_entry("arc-runner-set")
        assert entry.get("privileged_namespace") is True


# ===========================================================================
# 4. ARC Runner Scale Set — Wizard Fields
# ===========================================================================

class TestArcRunnerSetWizardFields:
    """Validate ARC runner scale set wizard fields match the actual chart."""

    @pytest.fixture
    def runner_fields(self):
        entry = get_catalog_entry("arc-runner-set")
        return {f["key"]: f for f in entry["wizard_fields"]}

    def test_arc_runner_set_field_keys(self, runner_fields):
        """All expected wizard fields present."""
        expected_keys = {
            "githubConfigUrl",
            "githubConfigSecret.github_token",
            "maxRunners",
            "minRunners",
            "containerMode.type",
            "runnerGroup",
            "containerMode.kubernetesModeWorkVolumeClaim.storageClassName",
            "containerMode.kubernetesModeWorkVolumeClaim.resources.requests.storage",
        }
        actual_keys = set(runner_fields.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"Missing wizard fields: {missing}"
        assert not extra, f"Unexpected wizard fields: {extra}"

    def test_arc_runner_set_github_config_url(self, runner_fields):
        """GitHub config URL field is required text input."""
        field = runner_fields["githubConfigUrl"]
        assert field["type"] == "text"
        assert field["default"] == ""
        assert field["section"] == "GitHub"

    def test_arc_runner_set_github_token(self, runner_fields):
        """GitHub token field warns about classic PAT requirement."""
        field = runner_fields["githubConfigSecret.github_token"]
        assert field["type"] == "text"
        assert field["default"] == ""
        assert field["section"] == "GitHub"
        # Must warn users that fine-grained PATs don't work for org-level
        desc = field["description"].lower()
        assert "classic" in desc, "Description must mention classic PAT"
        assert "fine-grained" in desc or "github_pat" in desc, (
            "Description must warn about fine-grained PAT limitation"
        )

    def test_arc_runner_set_scaling_fields(self, runner_fields):
        """Scaling fields have sensible defaults."""
        assert runner_fields["maxRunners"]["type"] == "number"
        assert runner_fields["maxRunners"]["default"] == 10
        assert runner_fields["minRunners"]["type"] == "number"
        assert runner_fields["minRunners"]["default"] == 0

    def test_arc_runner_set_runner_group_default_empty(self, runner_fields):
        """Runner group defaults to empty string for broad compatibility.

        An explicit 'default' value only works on GitHub Team/Enterprise plans.
        Empty string lets ARC auto-detect the org's default runner group, which
        works on all plan tiers including free.
        """
        field = runner_fields["runnerGroup"]
        assert field["type"] == "text"
        assert field["default"] == "", (
            "runnerGroup must default to empty string — explicit 'default' "
            "fails on GitHub Free orgs"
        )

    def test_arc_runner_set_container_mode(self, runner_fields):
        """Container mode has valid options."""
        field = runner_fields["containerMode.type"]
        assert field["type"] == "select"
        assert "dind" in field["options"]
        assert "kubernetes" in field["options"]

    def test_arc_runner_set_volume_claim_show_when(self, runner_fields):
        """Volume claim fields only shown when containerMode.type is kubernetes.

        Without these fields, kubernetes mode fails with:
            spec.template.spec.volumes[0].ephemeral.volumeClaimTemplate.spec: Required value

        Regression test for: ARC runner set kubernetes mode install failure.
        """
        sc_field = runner_fields["containerMode.kubernetesModeWorkVolumeClaim.storageClassName"]
        assert sc_field.get("show_when") == {"key": "containerMode.type", "value": "kubernetes"}, (
            "storageClassName must be conditional on kubernetes mode"
        )

        storage_field = runner_fields["containerMode.kubernetesModeWorkVolumeClaim.resources.requests.storage"]
        assert storage_field.get("show_when") == {"key": "containerMode.type", "value": "kubernetes"}, (
            "storage size must be conditional on kubernetes mode"
        )

    def test_arc_runner_set_volume_claim_defaults(self, runner_fields):
        """Volume claim fields have sensible defaults."""
        sc_field = runner_fields["containerMode.kubernetesModeWorkVolumeClaim.storageClassName"]
        assert sc_field["type"] == "text"
        assert sc_field["default"] == "longhorn"

        storage_field = runner_fields["containerMode.kubernetesModeWorkVolumeClaim.resources.requests.storage"]
        assert storage_field["type"] == "text"
        assert storage_field["default"] == "1Gi"

    def test_arc_runner_set_default_values_access_modes(self):
        """default_values must include accessModes for kubernetesModeWorkVolumeClaim.

        The PVC spec requires accessModes: ["ReadWriteOnce"]. This is not user-configurable
        and must be injected automatically via default_values.
        """
        entry = get_catalog_entry("arc-runner-set")
        dv = entry.get("default_values", {})
        access_modes = (
            dv.get("containerMode", {})
              .get("kubernetesModeWorkVolumeClaim", {})
              .get("accessModes")
        )
        assert access_modes == ["ReadWriteOnce"], (
            f"default_values must include accessModes: ['ReadWriteOnce'], got: {access_modes}"
        )

    def test_arc_runner_set_sections(self, runner_fields):
        """Fields span expected sections."""
        sections = {f["section"] for f in runner_fields.values()}
        expected_sections = {"GitHub", "Scaling", "Runner"}
        missing = expected_sections - sections
        assert not missing, f"Missing sections: {missing}"


# ===========================================================================
# 5. OCI Install Flow — Controller
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
async def test_arc_controller_install_skips_repo_add(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """OCI chart: repo_add NOT called."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="arc-controller",
                                chart_name="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller")
    params = _arc_controller_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_not_awaited()
    mock_helm_runner.install.assert_awaited_once()


@pytest.mark.asyncio
async def test_arc_controller_install_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Full happy-path controller install."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="arc-controller",
                                chart_name="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller",
                                namespace="arc-systems")
    params = _arc_controller_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    call_kwargs = mock_helm_runner.install.call_args
    assert "gha-runner-scale-set-controller" in call_kwargs[1]["chart"]
    assert call_kwargs[1]["namespace"] == "arc-systems"


# ===========================================================================
# 6. OCI Install Flow — Runner Scale Set
# ===========================================================================

@pytest.mark.asyncio
async def test_arc_runner_set_install_skips_repo_add(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """OCI chart: repo_add NOT called."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="arc-runner-set",
                                chart_name="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set")
    params = _arc_runner_set_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_not_awaited()
    mock_helm_runner.install.assert_awaited_once()


@pytest.mark.asyncio
async def test_arc_runner_set_install_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Full happy-path runner scale set install."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="arc-runner-set",
                                chart_name="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set",
                                namespace="arc-runners")
    params = _arc_runner_set_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    statuses = [e["data"]["status"] for e in status_events]
    assert "deploying" in statuses
    assert "deployed" in statuses

    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["chart"].endswith("/gha-runner-scale-set")
    assert call_kwargs[1]["namespace"] == "arc-runners"


@pytest.mark.asyncio
async def test_arc_runner_set_custom_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Application scope: user-provided namespace is passed through."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="arc-runner-set",
                                chart_name="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set",
                                namespace="my-ci-runners")
    params = _arc_runner_set_install_params(namespace="my-ci-runners")

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"

    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["namespace"] == "my-ci-runners"


@pytest.mark.asyncio
async def test_arc_runner_set_privileged_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install, mock_label_ns,
):
    """Runner set requires privileged namespace labeling (DinD needs it)."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="arc-runner-set",
                                chart_name="oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set")
    params = _arc_runner_set_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_label_ns.assert_awaited_once()
