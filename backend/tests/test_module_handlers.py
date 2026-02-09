"""Tests for modules.* WebSocket handlers in app.api.ws_handler."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.ws_handler import (
    _modules_catalog,
    _modules_list,
    _modules_get,
    _modules_install,
    _modules_upgrade,
    _modules_cancel,
    _modules_force_delete,
    _modules_uninstall,
    _modules_log,
    _modules_repos_list,
    _modules_repos_add,
    _modules_repos_delete,
)
from tests.conftest import (
    seed_helm_release,
    seed_helm_repository,
    get_ws_response,
)


# ---------------------------------------------------------------------------
# modules.catalog
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_catalog_returns_list(mock_ws):
    """_modules_catalog responds with the full catalog list."""
    fake_catalog = [{"id": "longhorn", "name": "Longhorn"}]
    with patch("app.api.ws_handler.get_catalog", return_value=fake_catalog, create=True), \
         patch("app.services.module_catalog.get_catalog", return_value=fake_catalog):
        await _modules_catalog({}, mock_ws, "req-1")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert isinstance(data, list)
    assert len(data) >= 1


# ---------------------------------------------------------------------------
# modules.list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_list_empty(mock_db, mock_ws):
    """_modules_list returns empty list when no releases exist."""
    await _modules_list({}, mock_ws, "req-2")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data == []


@pytest.mark.asyncio
async def test_modules_list_with_releases(mock_db, mock_ws):
    """_modules_list returns all seeded releases."""
    seed_helm_release(mock_db, release_name="rel-a", chart_name="chart/a")
    seed_helm_release(mock_db, release_name="rel-b", chart_name="chart/b")

    await _modules_list({}, mock_ws, "req-3")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert len(data) == 2


# ---------------------------------------------------------------------------
# modules.get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_get_found(mock_db, mock_ws):
    """_modules_get returns the release when it exists."""
    release = seed_helm_release(mock_db, release_name="my-release")

    await _modules_get({"release_id": release.id}, mock_ws, "req-4")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data["release_name"] == "my-release"


@pytest.mark.asyncio
async def test_modules_get_not_found(mock_db, mock_ws):
    """_modules_get returns error when release does not exist."""
    await _modules_get({"release_id": 9999}, mock_ws, "req-5")

    data, error = get_ws_response(mock_ws)
    assert error == "Release not found"


# ---------------------------------------------------------------------------
# modules.install
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_install_creates_release(mock_db, mock_ws, mock_broadcast, mock_log_action):
    """_modules_install creates a DB record, responds with it, and broadcasts."""
    params = {
        "release_name": "new-release",
        "namespace": "default",
        "chart_name": "bitnami/nginx",
        "chart_version": "1.0.0",
    }

    with patch("asyncio.create_task") as mock_task:
        await _modules_install(params, mock_ws, "req-6")

    # Response contains the created release
    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data["release_name"] == "new-release"
    assert data["chart_name"] == "bitnami/nginx"
    assert data["status"] == "pending"

    # Broadcast event was emitted
    assert len(mock_broadcast) == 1
    assert mock_broadcast[0]["type"] == "module_installing"
    assert mock_broadcast[0]["data"]["release_name"] == "new-release"

    # Background task was created (but not actually run)
    mock_task.assert_called_once()

    # DB record exists
    from app.db.models import HelmRelease
    record = mock_db.query(HelmRelease).filter_by(release_name="new-release").first()
    assert record is not None
    assert record.namespace == "default"


@pytest.mark.asyncio
async def test_modules_install_duplicate_error(mock_db, mock_ws, mock_broadcast, mock_log_action):
    """_modules_install returns error when release name already exists."""
    seed_helm_release(mock_db, release_name="dup-release")

    params = {
        "release_name": "dup-release",
        "namespace": "default",
        "chart_name": "bitnami/nginx",
    }

    with patch("asyncio.create_task"):
        await _modules_install(params, mock_ws, "req-7")

    data, error = get_ws_response(mock_ws)
    assert error is not None
    assert "already exists" in error


# ---------------------------------------------------------------------------
# modules.upgrade
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_upgrade_success(mock_db, mock_ws, mock_log_action):
    """_modules_upgrade updates values and launches background task."""
    release = seed_helm_release(mock_db, release_name="upgrade-me")

    params = {
        "release_id": release.id,
        "values_yaml": "replicas: 3",
        "chart_version": "2.0.0",
    }

    with patch("asyncio.create_task") as mock_task:
        await _modules_upgrade(params, mock_ws, "req-8")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data["release_name"] == "upgrade-me"

    # Values were persisted (re-query since handler closes its session reference)
    from app.db.models import HelmRelease
    updated = mock_db.query(HelmRelease).filter_by(id=release.id).first()
    assert updated.values_yaml == "replicas: 3"
    assert updated.chart_version == "2.0.0"

    mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_modules_upgrade_not_found(mock_db, mock_ws, mock_log_action):
    """_modules_upgrade returns error when release does not exist."""
    await _modules_upgrade({"release_id": 9999}, mock_ws, "req-9")

    data, error = get_ws_response(mock_ws)
    assert error == "Release not found"


# ---------------------------------------------------------------------------
# modules.cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_cancel_sets_failed(mock_db, mock_ws, mock_broadcast):
    """_modules_cancel sets status to 'failed' with 'Cancelled by user'."""
    release = seed_helm_release(mock_db, release_name="cancel-me", status="deploying")

    await _modules_cancel({"release_id": release.id}, mock_ws, "req-10")

    data, error = get_ws_response(mock_ws)
    assert error is None

    # Verify DB state (re-query since handler closes its session reference)
    from app.db.models import HelmRelease
    updated = mock_db.query(HelmRelease).filter_by(id=release.id).first()
    assert updated.status == "failed"
    assert updated.status_message == "Cancelled by user"

    # Verify broadcast
    assert any(e["type"] == "module_status_changed" for e in mock_broadcast)
    bc = next(e for e in mock_broadcast if e["type"] == "module_status_changed")
    assert bc["data"]["status"] == "failed"


@pytest.mark.asyncio
async def test_modules_cancel_not_found(mock_db, mock_ws, mock_broadcast):
    """_modules_cancel returns error when release does not exist."""
    await _modules_cancel({"release_id": 9999}, mock_ws, "req-11")

    data, error = get_ws_response(mock_ws)
    assert error == "Release not found"


# ---------------------------------------------------------------------------
# modules.force_delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_force_delete_success(
    mock_db, mock_ws, mock_broadcast, mock_helm_runner, mock_log_action,
):
    """_modules_force_delete removes DB record and attempts helm uninstall."""
    release = seed_helm_release(
        mock_db,
        release_name="force-del",
        namespace="test-ns",
        status="failed",
    )

    with patch("app.api.ws_handler.helm_runner", mock_helm_runner, create=True), \
         patch("app.services.helm_runner.helm_runner", mock_helm_runner), \
         patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
         patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_sub, \
         patch("app.api.ws_handler._delete_namespace_resources", new_callable=AsyncMock):
        mock_sub.return_value = AsyncMock(
            returncode=0,
            communicate=AsyncMock(return_value=(b"{}", b"")),
        )
        await _modules_force_delete({"release_id": release.id}, mock_ws, "req-12")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert "Force-deleted" in data["message"]

    # Verify DB record was removed
    from app.db.models import HelmRelease
    assert mock_db.query(HelmRelease).filter_by(id=release.id).first() is None

    # Verify broadcast
    assert any(e["type"] == "module_status_changed" for e in mock_broadcast)


@pytest.mark.asyncio
async def test_modules_force_delete_not_found(mock_db, mock_ws, mock_broadcast, mock_log_action):
    """_modules_force_delete returns error when release does not exist."""
    with patch("app.services.helm_runner.helm_runner", MagicMock()):
        await _modules_force_delete({"release_id": 9999}, mock_ws, "req-13")

    data, error = get_ws_response(mock_ws)
    assert error == "Release not found"


# ---------------------------------------------------------------------------
# modules.uninstall
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_uninstall_success(mock_db, mock_ws, mock_broadcast, mock_log_action):
    """_modules_uninstall sets status to 'uninstalling' and launches background task."""
    release = seed_helm_release(mock_db, release_name="uninstall-me", status="deployed")

    with patch("asyncio.create_task") as mock_task:
        await _modules_uninstall({"release_id": release.id}, mock_ws, "req-14")

    data, error = get_ws_response(mock_ws)
    assert error is None

    # Verify DB state changed (re-query since handler closes its session reference)
    from app.db.models import HelmRelease
    updated = mock_db.query(HelmRelease).filter_by(id=release.id).first()
    assert updated.status == "uninstalling"

    # Verify broadcast
    assert any(e["type"] == "module_status_changed" for e in mock_broadcast)
    bc = next(e for e in mock_broadcast if e["type"] == "module_status_changed")
    assert bc["data"]["status"] == "uninstalling"

    mock_task.assert_called_once()


@pytest.mark.asyncio
async def test_modules_uninstall_not_found(mock_db, mock_ws, mock_broadcast, mock_log_action):
    """_modules_uninstall returns error when release does not exist."""
    await _modules_uninstall({"release_id": 9999}, mock_ws, "req-15")

    data, error = get_ws_response(mock_ws)
    assert error == "Release not found"


# ---------------------------------------------------------------------------
# modules.log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_log_returns_output(mock_db, mock_ws):
    """_modules_log returns stored log output for a release."""
    release = seed_helm_release(mock_db, release_name="log-test")
    release.log_output = "line1\nline2\nline3"
    mock_db.commit()

    await _modules_log({"release_id": release.id}, mock_ws, "req-16")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data["log"] == "line1\nline2\nline3"
    assert data["release_name"] == "log-test"


@pytest.mark.asyncio
async def test_modules_log_empty_output(mock_db, mock_ws):
    """_modules_log returns empty string when no log output is stored."""
    release = seed_helm_release(mock_db, release_name="no-log")

    await _modules_log({"release_id": release.id}, mock_ws, "req-17")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data["log"] == ""


@pytest.mark.asyncio
async def test_modules_log_not_found(mock_db, mock_ws):
    """_modules_log returns error when release does not exist."""
    await _modules_log({"release_id": 9999}, mock_ws, "req-18")

    data, error = get_ws_response(mock_ws)
    assert error == "Release not found"


# ---------------------------------------------------------------------------
# modules.repos.list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_repos_list_empty(mock_db, mock_ws):
    """_modules_repos_list returns empty list when no repos exist."""
    await _modules_repos_list({}, mock_ws, "req-19")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data == []


@pytest.mark.asyncio
async def test_modules_repos_list_with_repos(mock_db, mock_ws):
    """_modules_repos_list returns all seeded repositories."""
    seed_helm_repository(mock_db, name="bitnami", url="https://charts.bitnami.com/bitnami")
    seed_helm_repository(mock_db, name="jetstack", url="https://charts.jetstack.io")

    await _modules_repos_list({}, mock_ws, "req-20")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert len(data) == 2


# ---------------------------------------------------------------------------
# modules.repos.add
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_repos_add_success(mock_db, mock_ws, mock_helm_runner):
    """_modules_repos_add adds repo to DB and calls helm repo add."""
    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _modules_repos_add(
            {"name": "my-repo", "url": "https://example.com/charts"},
            mock_ws,
            "req-21",
        )

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data["name"] == "my-repo"
    assert data["url"] == "https://example.com/charts"

    # Verify helm_runner.repo_add was called
    mock_helm_runner.repo_add.assert_awaited_once_with("my-repo", "https://example.com/charts")

    # Verify DB record
    from app.db.models import HelmRepository
    record = mock_db.query(HelmRepository).filter_by(name="my-repo").first()
    assert record is not None


@pytest.mark.asyncio
async def test_modules_repos_add_duplicate(mock_db, mock_ws, mock_helm_runner):
    """_modules_repos_add returns error when repo name already exists."""
    seed_helm_repository(mock_db, name="existing-repo", url="https://example.com")

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _modules_repos_add(
            {"name": "existing-repo", "url": "https://other.com"},
            mock_ws,
            "req-22",
        )

    data, error = get_ws_response(mock_ws)
    assert error is not None
    assert "already exists" in error

    # helm_runner.repo_add should NOT have been called
    mock_helm_runner.repo_add.assert_not_awaited()


@pytest.mark.asyncio
async def test_modules_repos_add_helm_failure(mock_db, mock_ws, mock_helm_runner):
    """_modules_repos_add returns error when helm repo add fails."""
    mock_helm_runner.repo_add = AsyncMock(return_value=(False, "connection refused"))

    with patch("app.services.helm_runner.helm_runner", mock_helm_runner):
        await _modules_repos_add(
            {"name": "bad-repo", "url": "https://bad.example.com"},
            mock_ws,
            "req-23",
        )

    data, error = get_ws_response(mock_ws)
    assert error is not None
    assert "Failed to add repo" in error

    # Verify DB record was NOT created
    from app.db.models import HelmRepository
    assert mock_db.query(HelmRepository).filter_by(name="bad-repo").first() is None


# ---------------------------------------------------------------------------
# modules.repos.delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_repos_delete_success(mock_db, mock_ws):
    """_modules_repos_delete removes repo from DB."""
    repo = seed_helm_repository(mock_db, name="delete-me", url="https://example.com")

    await _modules_repos_delete({"repo_id": repo.id}, mock_ws, "req-24")

    data, error = get_ws_response(mock_ws)
    assert error is None
    assert data["message"] == "Repository deleted"

    # Verify DB record removed
    from app.db.models import HelmRepository
    assert mock_db.query(HelmRepository).filter_by(id=repo.id).first() is None


@pytest.mark.asyncio
async def test_modules_repos_delete_not_found(mock_db, mock_ws):
    """_modules_repos_delete returns error when repo does not exist."""
    await _modules_repos_delete({"repo_id": 9999}, mock_ws, "req-25")

    data, error = get_ws_response(mock_ws)
    assert error == "Repository not found"
