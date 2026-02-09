"""Tests for background task functions: _do_helm_install, _do_helm_upgrade, _do_helm_uninstall."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models import HelmRelease
from tests.conftest import seed_helm_release


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_save_disk_partition():
    with patch("app.api.ws_handler._save_disk_partition") as m:
        yield m


@pytest.fixture
def mock_remove_disk_partition():
    with patch("app.api.ws_handler._remove_disk_partition") as m:
        yield m


@pytest.fixture
def mock_regen_configs():
    with patch("app.api.ws_handler._regenerate_all_device_configs") as m:
        yield m


@pytest.fixture
def mock_label_ns():
    with patch("app.api.ws_handler._label_namespace_privileged", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_post_install():
    with patch("app.api.ws_handler._run_post_install", new_callable=AsyncMock, return_value="") as m:
        yield m


@pytest.fixture
def mock_find_kubectl():
    with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"):
        yield


@pytest.fixture
def mock_delete_ns():
    with patch("app.api.ws_handler._delete_namespace_resources", new_callable=AsyncMock) as m:
        yield m


# ---------------------------------------------------------------------------
# Default install params
# ---------------------------------------------------------------------------

def _default_install_params(**overrides):
    params = {
        "release_name": "test-release",
        "chart_name": "test-repo/test-chart",
        "namespace": "test-ns",
        "chart_version": "1.0.0",
        "repo_name": "test-repo",
        "repo_url": "https://charts.example.com",
        "values_yaml": "",
    }
    params.update(overrides)
    return params


# ===========================================================================
# _do_helm_install
# ===========================================================================

@pytest.mark.asyncio
async def test_do_helm_install_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """Happy-path: repo add, install, post-install all succeed -> status='deployed'."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending")
    params = _default_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    # Verify DB status
    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "successfully" in (updated.status_message or "").lower()

    # Verify broadcast events include deploying and deployed
    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    statuses = [e["data"]["status"] for e in status_events]
    assert "deploying" in statuses
    assert "deployed" in statuses

    # Verify helm calls
    mock_helm_runner.repo_add.assert_awaited_once()
    mock_helm_runner.install.assert_awaited_once()
    mock_post_install.assert_awaited_once()


@pytest.mark.asyncio
async def test_do_helm_install_repo_failure(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """repo_add returns (False, 'error') -> status='failed', install never called."""
    from app.api.ws_handler import _do_helm_install

    mock_helm_runner.repo_add = AsyncMock(return_value=(False, "repo add error"))
    release = seed_helm_release(mock_db, status="pending")
    params = _default_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "failed"
    assert "repo add" in (updated.status_message or "").lower()

    mock_helm_runner.install.assert_not_awaited()


@pytest.mark.asyncio
async def test_do_helm_install_helm_failure(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """install returns (False, 'timeout') -> status='failed'."""
    from app.api.ws_handler import _do_helm_install

    mock_helm_runner.install = AsyncMock(return_value=(False, "timeout"))
    release = seed_helm_release(mock_db, status="pending")
    params = _default_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "failed"
    assert "timeout" in (updated.status_message or "").lower()

    # Broadcast should include the failure
    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    final = status_events[-1]
    assert final["data"]["status"] == "failed"


@pytest.mark.asyncio
async def test_do_helm_install_privileged_namespace(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install, mock_label_ns,
):
    """catalog entry with privileged_namespace=True -> _label_namespace_privileged called."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending", catalog_id="longhorn")
    params = _default_install_params(catalog_id="longhorn")

    fake_catalog = {"privileged_namespace": True}

    with (
        patch("app.services.helm_runner.helm_runner", mock_helm_runner),
        patch("app.services.module_catalog.get_catalog_entry", return_value=fake_catalog),
    ):
        await _do_helm_install(release.id, params)

    mock_label_ns.assert_awaited_once_with("test-ns")

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


@pytest.mark.asyncio
async def test_do_helm_install_metallb_labels_namespace_privileged(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_label_ns,
):
    """MetalLB fresh install must label namespace as privileged BEFORE helm install.

    Without this, MetalLB speaker pods (hostNetwork, NET_ADMIN, SYS_ADMIN)
    are rejected by Kubernetes PodSecurity admission and helm times out.
    Regression test for: privileged_namespace flag missing from MetalLB catalog.
    """
    from app.api.ws_handler import _do_helm_install
    from app.services.module_catalog import get_catalog_entry

    # Use the REAL catalog entry — not a mock
    real_catalog = get_catalog_entry("metallb")
    assert real_catalog is not None, "metallb catalog entry must exist"
    assert real_catalog.get("privileged_namespace") is True, (
        "metallb catalog entry must have privileged_namespace=True"
    )

    release = seed_helm_release(
        mock_db,
        release_name="metallb",
        namespace="metallb-system",
        chart_name="metallb/metallb",
        catalog_id="metallb",
        status="pending",
    )
    params = {
        "release_name": "metallb",
        "chart_name": "metallb/metallb",
        "namespace": "metallb-system",
        "repo_name": "metallb",
        "repo_url": "https://metallb.github.io/metallb",
        "catalog_id": "metallb",
        "values_yaml": None,
        "values_json": json.dumps({"_addressPool": "10.0.200.1-10.0.200.50"}),
    }

    # Mock post-install (MetalLB creates IPAddressPool CR after helm install)
    with (
        patch("app.services.helm_runner.helm_runner", mock_helm_runner),
        patch("app.api.ws_handler._run_post_install", new_callable=AsyncMock, return_value="IPAddressPool created"),
    ):
        await _do_helm_install(release.id, params)

    # CRITICAL: namespace must be labeled BEFORE helm install
    mock_label_ns.assert_awaited_once_with("metallb-system")

    # Verify the install succeeded
    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed", (
        f"Expected 'deployed' but got '{updated.status}': {updated.status_message}"
    )

    # Verify helm install was called
    mock_helm_runner.install.assert_awaited_once()
    call_kwargs = mock_helm_runner.install.call_args
    assert call_kwargs[1]["namespace"] == "metallb-system" or call_kwargs[0][0] == "metallb"


@pytest.mark.asyncio
async def test_do_helm_install_exception(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """install raises Exception -> status='failed'."""
    from app.api.ws_handler import _do_helm_install

    mock_helm_runner.install = AsyncMock(side_effect=Exception("unexpected boom"))
    release = seed_helm_release(mock_db, status="pending")
    params = _default_install_params()

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "failed"
    assert "unexpected boom" in (updated.status_message or "")

    # Broadcast should include the failure
    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    assert any(e["data"]["status"] == "failed" for e in status_events)


@pytest.mark.asyncio
async def test_do_helm_install_no_repo(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_post_install,
):
    """No repo_name/repo_url in params -> repo_add NOT called, install still runs."""
    from app.api.ws_handler import _do_helm_install

    release = seed_helm_release(mock_db, status="pending")
    params = _default_install_params(repo_name=None, repo_url=None)

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_install(release.id, params)

    mock_helm_runner.repo_add.assert_not_awaited()
    mock_helm_runner.install.assert_awaited_once()

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"


# ===========================================================================
# _do_helm_upgrade
# ===========================================================================

@pytest.mark.asyncio
async def test_do_helm_upgrade_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner,
):
    """Happy-path upgrade: status transitions to 'deployed'."""
    from app.api.ws_handler import _do_helm_upgrade

    release = seed_helm_release(
        mock_db,
        status="deployed",
        values_yaml="key: value",
        repo_name="test-repo",
        repo_url="https://charts.example.com",
    )

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_upgrade(release.id)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "deployed"
    assert "upgraded" in (updated.status_message or "").lower()

    # Verify broadcast events
    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    statuses = [e["data"]["status"] for e in status_events]
    assert "deploying" in statuses
    assert "deployed" in statuses

    mock_helm_runner.upgrade.assert_awaited_once()
    mock_helm_runner.repo_add.assert_awaited_once()


@pytest.mark.asyncio
async def test_do_helm_upgrade_failure(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner,
):
    """upgrade returns (False, 'error') -> status='failed'."""
    from app.api.ws_handler import _do_helm_upgrade

    mock_helm_runner.upgrade = AsyncMock(return_value=(False, "values validation error"))
    release = seed_helm_release(mock_db, status="deployed")

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_upgrade(release.id)

    mock_db.expire_all()
    updated = mock_db.query(HelmRelease).filter(HelmRelease.id == release.id).first()
    assert updated.status == "failed"
    assert "values validation error" in (updated.status_message or "")

    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    final = status_events[-1]
    assert final["data"]["status"] == "failed"


# ===========================================================================
# _do_helm_uninstall
# ===========================================================================

@pytest.mark.asyncio
async def test_do_helm_uninstall_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_find_kubectl, mock_delete_ns,
):
    """Happy-path uninstall: record deleted, broadcast 'uninstalled'."""
    from app.api.ws_handler import _do_helm_uninstall

    release = seed_helm_release(mock_db, status="deployed", namespace="longhorn-system")
    release_id = release.id

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_uninstall(release_id)

    mock_db.expire_all()
    deleted = mock_db.query(HelmRelease).filter(HelmRelease.id == release_id).first()
    assert deleted is None, "DB record should be deleted after successful uninstall"

    # Broadcast should include uninstalled
    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    assert any(e["data"]["status"] == "uninstalled" for e in status_events)

    mock_helm_runner.uninstall.assert_awaited_once()
    mock_delete_ns.assert_awaited_once_with("longhorn-system")


@pytest.mark.asyncio
async def test_do_helm_uninstall_helm_failure(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_find_kubectl, mock_delete_ns,
):
    """uninstall returns (False, 'permission denied') -> status='failed', record NOT deleted."""
    from app.api.ws_handler import _do_helm_uninstall

    mock_helm_runner.uninstall = AsyncMock(return_value=(False, "permission denied"))
    release = seed_helm_release(mock_db, status="deployed", namespace="test-ns")
    release_id = release.id

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_uninstall(release_id)

    mock_db.expire_all()
    still_exists = mock_db.query(HelmRelease).filter(HelmRelease.id == release_id).first()
    assert still_exists is not None, "DB record should NOT be deleted on failure"
    assert still_exists.status == "failed"

    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    final = status_events[-1]
    assert final["data"]["status"] == "failed"

    # Namespace cleanup should NOT run on failure
    mock_delete_ns.assert_not_awaited()


@pytest.mark.asyncio
async def test_do_helm_uninstall_not_found_is_success(
    mock_db, mock_broadcast, mock_log_action,
    mock_helm_runner, mock_find_kubectl, mock_delete_ns,
):
    """uninstall returns (False, 'release: not found') -> treated as success, record deleted."""
    from app.api.ws_handler import _do_helm_uninstall

    mock_helm_runner.uninstall = AsyncMock(return_value=(False, "release: not found"))
    release = seed_helm_release(mock_db, status="deployed", namespace="gone-ns")
    release_id = release.id

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _do_helm_uninstall(release_id)

    mock_db.expire_all()
    deleted = mock_db.query(HelmRelease).filter(HelmRelease.id == release_id).first()
    assert deleted is None, "DB record should be deleted when release is 'not found'"

    status_events = [e for e in mock_broadcast if e["type"] == "module_status_changed"]
    assert any(e["data"]["status"] == "uninstalled" for e in status_events)

    # Namespace cleanup should still run for non-default namespaces
    mock_delete_ns.assert_awaited_once_with("gone-ns")
