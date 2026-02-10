"""Tests for the Redis module: catalog entry, OCI install flow, application scope, dependencies, validation."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.module_catalog import get_catalog_entry
from app.services.helm_runner import wizard_to_values
from app.db.models import HelmRelease
from tests.conftest import seed_helm_release, get_ws_response


# ---------------------------------------------------------------------------
# Helper: default Redis install params
# ---------------------------------------------------------------------------

def _redis_install_params(**overrides):
    """Default params matching a Redis install from the frontend wizard."""
    params = {
        "release_name": "my-redis",
        "chart_name": "oci://registry-1.docker.io/cloudpirates/redis",
        "namespace": "redis-ns",
        "chart_version": None,
        "repo_name": "",
        "repo_url": "",
        "catalog_id": "redis",
        "values_yaml": "architecture: replication\nreplicaCount: 3",
        "values_json": json.dumps({
            "architecture": "replication",
            "replicaCount": 3,
            "persistence.enabled": True,
            "persistence.size": "8Gi",
            "auth.enabled": True,
            "auth.password": "",
        }),
    }
    params.update(overrides)
    return params


# ===========================================================================
# 1. Catalog Entry Validation
# ===========================================================================

class TestRedisCatalogEntry:
    """Validate the Redis catalog entry structure."""

    def test_redis_catalog_entry_exists(self):
        """Redis catalog entry exists with correct id, name, and scope."""
        entry = get_catalog_entry("redis")
        assert entry is not None, "Redis catalog entry not found"
        assert entry["id"] == "redis"
        assert entry["name"] == "Redis"
        assert entry["scope"] == "application"
        assert entry["category"] == "databases"

    def test_redis_catalog_oci_chart(self):
        """Redis uses OCI chart reference — no helm repo add needed."""
        entry = get_catalog_entry("redis")
        assert entry["chart_name"].startswith("oci://"), (
            f"Expected OCI chart ref, got: {entry['chart_name']}"
        )
        assert entry["repo_name"] == "", "OCI charts must have empty repo_name"
        assert entry["repo_url"] == "", "OCI charts must have empty repo_url"

    def test_redis_catalog_empty_defaults(self):
        """Application-scoped modules must have empty default_namespace and default_release_name."""
        entry = get_catalog_entry("redis")
        assert entry["default_namespace"] == "", (
            "Application-scoped Redis must have empty default_namespace (user provides)"
        )
        assert entry["default_release_name"] == "", (
            "Application-scoped Redis must have empty default_release_name (user provides)"
        )

    def test_redis_catalog_no_privileged_namespace(self):
        """Redis does NOT require privileged namespace (no hostNetwork or privileged containers)."""
        entry = get_catalog_entry("redis")
        assert entry.get("privileged_namespace") is not True, (
            "Redis should NOT have privileged_namespace=True — "
            "it runs as non-root with read-only filesystem"
        )


# ===========================================================================
# 2. Wizard Field Validation
# ===========================================================================

class TestRedisWizardFields:
    """Validate Redis wizard field definitions."""

    @pytest.fixture
    def redis_fields(self):
        entry = get_catalog_entry("redis")
        return {f["key"]: f for f in entry["wizard_fields"]}

    def test_redis_wizard_field_keys(self, redis_fields):
        """All 15 expected wizard fields are present."""
        expected_keys = {
            "architecture", "replicaCount",
            "clusterReplicaCount", "cluster.config.nodeTimeout", "cluster.config.requireFullCoverage",
            "sentinel.enabled", "sentinel.quorum",
            "auth.enabled", "auth.password",
            "persistence.enabled", "persistence.size",
            "resources.requests.memory", "resources.limits.memory",
            "metrics.enabled", "pdb.enabled",
        }
        actual_keys = set(redis_fields.keys())
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys
        assert not missing, f"Missing wizard fields: {missing}"
        assert not extra, f"Unexpected wizard fields: {extra}"

    def test_redis_wizard_show_when_cluster_fields(self, redis_fields):
        """Cluster-specific fields only show when architecture=cluster."""
        cluster_keys = ["clusterReplicaCount", "cluster.config.nodeTimeout", "cluster.config.requireFullCoverage"]
        for key in cluster_keys:
            field = redis_fields[key]
            assert "show_when" in field, f"Field '{key}' missing show_when"
            assert field["show_when"]["key"] == "architecture", (
                f"Field '{key}' show_when.key should be 'architecture'"
            )
            assert field["show_when"]["value"] == "cluster", (
                f"Field '{key}' show_when.value should be 'cluster'"
            )

    def test_redis_wizard_show_when_sentinel_fields(self, redis_fields):
        """Sentinel fields only show when architecture=replication."""
        sentinel_keys = ["sentinel.enabled", "sentinel.quorum"]
        for key in sentinel_keys:
            field = redis_fields[key]
            assert "show_when" in field, f"Field '{key}' missing show_when"
            assert field["show_when"]["key"] == "architecture", (
                f"Field '{key}' show_when.key should be 'architecture'"
            )
            assert field["show_when"]["value"] == "replication", (
                f"Field '{key}' show_when.value should be 'replication'"
            )

    def test_redis_wizard_sections(self, redis_fields):
        """Fields span all expected sections."""
        sections = {f["section"] for f in redis_fields.values()}
        expected_sections = {
            "Topology", "Cluster", "High Availability", "Security",
            "Storage", "Resources", "Monitoring", "Availability",
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
async def test_redis_install_skips_repo_add(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """OCI chart install: repo_add is NOT called when repo_name/repo_url are empty."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis")
    params = _redis_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_not_awaited()
    mock_helm_runner.install.assert_awaited_once()


@pytest.mark.asyncio
async def test_redis_install_no_privileged_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install, mock_label_ns,
):
    """Redis catalog has no privileged_namespace — namespace labeling must NOT happen."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis")
    params = _redis_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_label_ns.assert_not_awaited()

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


@pytest.mark.asyncio
async def test_redis_install_success_oci(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Full happy-path Redis OCI install: pending → deploying → deployed."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                namespace="redis-ns")
    params = _redis_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    # Verify DB status transitions
    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    # Verify broadcast events include deploying and deployed
    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    statuses = [e["data"]["status"] for e in status_events]
    assert "deploying" in statuses
    assert "deployed" in statuses

    # Verify the OCI chart ref was passed to helm install
    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["chart"] == "oci://registry-1.docker.io/cloudpirates/redis"
    assert call_kwargs[1]["namespace"] == "redis-ns"


# ===========================================================================
# 4. Application Scope Behavior
# ===========================================================================

@pytest.mark.asyncio
async def test_redis_install_custom_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """User-provided namespace is passed through to helm install."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                namespace="my-custom-redis-ns")
    params = _redis_install_params(namespace="my-custom-redis-ns")

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"

    # Verify namespace passed to helm
    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["namespace"] == "my-custom-redis-ns"


@pytest.mark.asyncio
async def test_redis_multiple_instances(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Application scope allows multiple Redis instances in different namespaces."""
    from app.api.ws_handler import _do_helm_install

    # First instance
    release1 = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                 release_name="redis-cache",
                                 chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                 namespace="cache-ns")
    params1 = _redis_install_params(release_name="redis-cache", namespace="cache-ns")

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release1.id, params1)

    # Second instance
    release2 = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                 release_name="redis-sessions",
                                 chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                 namespace="sessions-ns")
    params2 = _redis_install_params(release_name="redis-sessions", namespace="sessions-ns")

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release2.id, params2)

    # Both should be deployed
    mock_db.expire_all()
    updated1 = mock_db.query(HelmRelease).filter(HelmRelease.id == release1.id).first()
    updated2 = mock_db.query(HelmRelease).filter(HelmRelease.id == release2.id).first()
    assert updated1.status == "deployed"
    assert updated2.status == "deployed"

    # Verify helm install called twice with different namespaces
    assert mock_helm_runner.install.await_count == 2


# ===========================================================================
# 5. Dependency Scenarios
# ===========================================================================

@pytest.mark.asyncio
async def test_redis_install_with_persistence_values(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Persistence values (requires Longhorn StorageClass) are passed through to helm."""
    from app.api.ws_handler import _do_helm_install

    values_yaml = "persistence:\n  enabled: true\n  size: 8Gi"
    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                namespace="redis-ns")
    params = _redis_install_params(values_yaml=values_yaml)

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"

    # Verify values_yaml was passed to helm install
    call_kwargs = mock_helm_runner.install.call_args
    assert "persistence" in (call_kwargs[1].get("values_yaml") or "")


@pytest.mark.asyncio
async def test_redis_install_without_persistence(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Redis install with persistence disabled succeeds (no Longhorn dependency)."""
    from app.api.ws_handler import _do_helm_install

    values_yaml = "persistence:\n  enabled: false\narchitecture: standalone"
    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                namespace="redis-standalone")
    params = _redis_install_params(
        namespace="redis-standalone",
        values_yaml=values_yaml,
        values_json=json.dumps({"persistence.enabled": False, "architecture": "standalone"}),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


@pytest.mark.asyncio
async def test_redis_install_with_all_wizard_defaults(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Install with all default wizard values succeeds and passes valid YAML."""
    from app.api.ws_handler import _do_helm_install

    # Build values from all wizard field defaults
    entry = get_catalog_entry("redis")
    wizard_values = {}
    for field in entry["wizard_fields"]:
        wizard_values[field["key"]] = field["default"]

    # Build values_yaml like the frontend does (dot-notation → nested YAML)
    values_yaml_lines = []
    for key, val in wizard_values.items():
        if not key.startswith("_"):
            values_yaml_lines.append(f"{key}: {val}")
    values_yaml = "\n".join(values_yaml_lines)

    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                namespace="redis-defaults")
    params = _redis_install_params(
        namespace="redis-defaults",
        values_yaml=values_yaml,
        values_json=json.dumps(wizard_values),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    # Verify helm install was called with the values
    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["values_yaml"] is not None
    assert "architecture" in call_kwargs[1]["values_yaml"]


# ===========================================================================
# 6. Catalog Default Alignment
# ===========================================================================

class TestRedisCatalogDefaults:
    """Verify catalog defaults match the actual chart defaults."""

    def test_cluster_replica_count_default_zero(self):
        """clusterReplicaCount default should be 0 (matches chart default)."""
        entry = get_catalog_entry("redis")
        fields = {f["key"]: f for f in entry["wizard_fields"]}
        assert fields["clusterReplicaCount"]["default"] == 0, (
            "clusterReplicaCount default should be 0 (chart default), not 1"
        )

    def test_sentinel_default_disabled(self):
        """sentinel.enabled default should be False (matches chart default)."""
        entry = get_catalog_entry("redis")
        fields = {f["key"]: f for f in entry["wizard_fields"]}
        assert fields["sentinel.enabled"]["default"] is False, (
            "sentinel.enabled default should be False (chart default), not True"
        )


# ===========================================================================
# 7. Cluster Topology Validation
# ===========================================================================

@pytest.mark.asyncio
async def test_redis_cluster_rejects_invalid_topology(mock_db, mock_ws, mock_helm_runner):
    """Cluster install with non-divisible node count is rejected before install starts."""
    from app.api.ws_handler import _modules_install

    params = _redis_install_params(
        values_json=json.dumps({
            "architecture": "cluster",
            "replicaCount": 5,
            "clusterReplicaCount": 1,
        }),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _modules_install(params, mock_ws, "req-validate")

    data, error = get_ws_response(mock_ws)
    assert error is not None, "Should reject invalid cluster topology"
    assert "not evenly divisible" in error.lower() or "multiple of" in error.lower()
    # Helm install should NOT have been called
    mock_helm_runner.install.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_cluster_rejects_too_few_nodes(mock_db, mock_ws, mock_helm_runner):
    """Cluster install with fewer than 3 nodes is rejected."""
    from app.api.ws_handler import _modules_install

    params = _redis_install_params(
        values_json=json.dumps({
            "architecture": "cluster",
            "replicaCount": 2,
            "clusterReplicaCount": 0,
        }),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _modules_install(params, mock_ws, "req-validate-min")

    data, error = get_ws_response(mock_ws)
    assert error is not None, "Should reject cluster with < 3 nodes"
    assert "at least 3" in error.lower()


@pytest.mark.asyncio
async def test_redis_cluster_accepts_valid_topology(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Cluster install with valid topology (6 nodes, 1 replica per master) succeeds."""
    from app.api.ws_handler import _do_helm_install

    values_json = json.dumps({
        "architecture": "cluster",
        "replicaCount": 6,
        "clusterReplicaCount": 1,
    })
    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                namespace="redis-cluster")
    params = _redis_install_params(
        namespace="redis-cluster",
        values_yaml="architecture: cluster\nreplicaCount: 6\nclusterReplicaCount: 1",
        values_json=values_json,
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


@pytest.mark.asyncio
async def test_redis_replication_skips_cluster_validation(mock_db, mock_ws, mock_helm_runner):
    """Replication architecture skips cluster topology validation entirely."""
    from app.api.ws_handler import _modules_install

    params = _redis_install_params(
        values_json=json.dumps({
            "architecture": "replication",
            "replicaCount": 3,
        }),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        mock_helm_runner.get_status = AsyncMock(return_value=None)
        await _modules_install(params, mock_ws, "req-repl")

    data, error = get_ws_response(mock_ws)
    assert error is None, f"Replication mode should not be rejected, got: {error}"


# ===========================================================================
# 8. wizard_to_values Dot-Notation Conversion
# ===========================================================================

class TestWizardToValues:
    """Verify dot-notation → nested dict conversion for Redis cluster config."""

    def test_cluster_config_nesting(self):
        """cluster.config.nodeTimeout becomes {cluster: {config: {nodeTimeout: ...}}}."""
        flat = {
            "architecture": "cluster",
            "cluster.config.nodeTimeout": 15000,
            "cluster.config.requireFullCoverage": True,
        }
        nested = wizard_to_values(flat)
        assert nested["architecture"] == "cluster"
        assert nested["cluster"]["config"]["nodeTimeout"] == 15000
        assert nested["cluster"]["config"]["requireFullCoverage"] is True

    def test_auth_nesting(self):
        """auth.enabled and auth.password nest under auth."""
        flat = {"auth.enabled": True, "auth.password": "secret"}
        nested = wizard_to_values(flat)
        assert nested["auth"]["enabled"] is True
        assert nested["auth"]["password"] == "secret"

    def test_persistence_nesting(self):
        """persistence.enabled and persistence.size nest under persistence."""
        flat = {"persistence.enabled": True, "persistence.size": "8Gi"}
        nested = wizard_to_values(flat)
        assert nested["persistence"]["enabled"] is True
        assert nested["persistence"]["size"] == "8Gi"

    def test_resources_deep_nesting(self):
        """resources.requests.memory becomes {resources: {requests: {memory: ...}}}."""
        flat = {"resources.requests.memory": "128Mi", "resources.limits.memory": "256Mi"}
        nested = wizard_to_values(flat)
        assert nested["resources"]["requests"]["memory"] == "128Mi"
        assert nested["resources"]["limits"]["memory"] == "256Mi"

    def test_sentinel_nesting(self):
        """sentinel.enabled and sentinel.quorum nest under sentinel."""
        flat = {"sentinel.enabled": True, "sentinel.quorum": 2}
        nested = wizard_to_values(flat)
        assert nested["sentinel"]["enabled"] is True
        assert nested["sentinel"]["quorum"] == 2


# ===========================================================================
# 9. Replica Count Maximum Validation
# ===========================================================================

class TestRedisReplicaCountMax:
    """Validate the replicaCount max field and backend enforcement."""

    def test_redis_replica_count_has_max(self):
        """replicaCount wizard field has a max of 12."""
        entry = get_catalog_entry("redis")
        fields = {f["key"]: f for f in entry["wizard_fields"]}
        assert "max" in fields["replicaCount"], "replicaCount field must have a 'max' key"
        assert fields["replicaCount"]["max"] == 12


@pytest.mark.asyncio
async def test_redis_cluster_rejects_excessive_nodes(mock_db, mock_ws, mock_helm_runner):
    """Cluster install with replicaCount > 12 is rejected before install starts."""
    from app.api.handlers.modules import _modules_install

    params = _redis_install_params(
        values_json=json.dumps({
            "architecture": "cluster",
            "replicaCount": 15,
            "clusterReplicaCount": 0,
        }),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _modules_install(params, mock_ws, "req-max-cluster")

    data, error = get_ws_response(mock_ws)
    assert error is not None, "Should reject replicaCount > 12"
    assert "maximum of 12" in error.lower()
    mock_helm_runner.install.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_replication_rejects_excessive_nodes(mock_db, mock_ws, mock_helm_runner):
    """Replication install with replicaCount > 12 is also rejected."""
    from app.api.handlers.modules import _modules_install

    params = _redis_install_params(
        values_json=json.dumps({
            "architecture": "replication",
            "replicaCount": 21,
        }),
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _modules_install(params, mock_ws, "req-max-repl")

    data, error = get_ws_response(mock_ws)
    assert error is not None, "Should reject replicaCount > 12 for replication"
    assert "maximum of 12" in error.lower()
    mock_helm_runner.install.assert_not_awaited()


# ===========================================================================
# 10. Failed Install Triggers Cleanup
# ===========================================================================

@pytest.mark.asyncio
async def test_redis_install_failure_triggers_cleanup(
    mock_db, mock_broadcast, mock_log_action,
    mock_post_install,
):
    """Failed helm install triggers force_uninstall to clean up orphaned resources."""
    from app.api.handlers.modules import _do_helm_install
    from unittest.mock import AsyncMock, MagicMock

    # Create a helm runner that fails on install
    runner = MagicMock()
    runner.repo_add = AsyncMock(return_value=(True, "repo added"))
    runner.repo_update = AsyncMock(return_value=(True, "updated"))
    runner.install = AsyncMock(return_value=(False, "context deadline exceeded"))
    runner.force_uninstall = AsyncMock(return_value=(True, "uninstalled"))
    runner.get_status = AsyncMock(return_value=None)

    release = seed_helm_release(mock_db, status="pending", catalog_id="redis",
                                chart_name="oci://registry-1.docker.io/cloudpirates/redis",
                                namespace="redis-fail")
    params = _redis_install_params(namespace="redis-fail")

    with patch("app.services.helm_runner.helm_runner", runner):
        await _do_helm_install(release.id, params)

    # Verify force_uninstall was called for cleanup
    runner.force_uninstall.assert_awaited_once_with("my-redis", "redis-fail")

    # Verify DB status is "failed"
    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "failed"
    assert "context deadline exceeded" in (updated.status_message or "")
