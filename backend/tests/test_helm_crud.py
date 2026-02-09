"""Tests for app.crud.helm CRUD operations."""
import pytest

from app.crud.helm import (
    create_helm_release,
    get_helm_release,
    get_helm_release_by_name,
    get_helm_releases,
    update_helm_release,
    update_helm_release_status,
    delete_helm_release,
    get_helm_repositories,
    get_helm_repository_by_name,
    add_helm_repository,
    delete_helm_repository,
)
from app.schemas.helm import HelmReleaseCreate, HelmReleaseUpdate
from tests.conftest import seed_helm_release, seed_helm_repository


def test_create_helm_release(db_session):
    schema = HelmReleaseCreate(
        release_name="my-release",
        namespace="kube-system",
        chart_name="bitnami/nginx",
        chart_version="1.2.3",
        repo_name="bitnami",
        repo_url="https://charts.bitnami.com/bitnami",
        catalog_id="cat-001",
        values_yaml="replicaCount: 2",
        values_json='{"replicaCount": 2}',
    )
    release = create_helm_release(db_session, schema)

    assert release.id is not None
    assert release.release_name == "my-release"
    assert release.namespace == "kube-system"
    assert release.chart_name == "bitnami/nginx"
    assert release.chart_version == "1.2.3"
    assert release.repo_name == "bitnami"
    assert release.repo_url == "https://charts.bitnami.com/bitnami"
    assert release.catalog_id == "cat-001"
    assert release.values_yaml == "replicaCount: 2"
    assert release.values_json == '{"replicaCount": 2}'
    assert release.status == "pending"


def test_get_helm_release(db_session):
    seeded = seed_helm_release(db_session, release_name="get-by-id")
    fetched = get_helm_release(db_session, seeded.id)

    assert fetched is not None
    assert fetched.id == seeded.id
    assert fetched.release_name == "get-by-id"


def test_get_helm_release_by_name(db_session):
    seed_helm_release(db_session, release_name="unique-name")
    fetched = get_helm_release_by_name(db_session, "unique-name")

    assert fetched is not None
    assert fetched.release_name == "unique-name"


def test_get_helm_releases_list(db_session):
    seed_helm_release(db_session, release_name="release-a")
    seed_helm_release(db_session, release_name="release-b")
    seed_helm_release(db_session, release_name="release-c")

    releases = get_helm_releases(db_session)
    assert len(releases) == 3
    names = {r.release_name for r in releases}
    assert names == {"release-a", "release-b", "release-c"}


def test_update_helm_release(db_session):
    seeded = seed_helm_release(db_session, release_name="to-update", chart_name="old/chart")
    update = HelmReleaseUpdate(chart_version="9.9.9")
    updated = update_helm_release(db_session, seeded.id, update)

    assert updated is not None
    assert updated.chart_version == "9.9.9"
    assert updated.release_name == "to-update"


def test_update_helm_release_status(db_session):
    seeded = seed_helm_release(db_session, release_name="status-update")
    updated = update_helm_release_status(
        db_session,
        seeded.id,
        status="deployed",
        message="Install complete",
        revision=3,
    )

    assert updated is not None
    assert updated.status == "deployed"
    assert updated.status_message == "Install complete"
    assert updated.revision == 3


def test_delete_helm_release(db_session):
    seeded = seed_helm_release(db_session, release_name="to-delete")
    result = delete_helm_release(db_session, seeded.id)
    assert result is True

    fetched = get_helm_release(db_session, seeded.id)
    assert fetched is None


def test_add_helm_repository(db_session):
    repo = add_helm_repository(db_session, "my-repo", "https://my-repo.example.com/charts")

    assert repo.id is not None
    assert repo.name == "my-repo"
    assert repo.url == "https://my-repo.example.com/charts"


def test_get_helm_repository_by_name(db_session):
    seed_helm_repository(db_session, name="find-me", url="https://find.me/charts")
    fetched = get_helm_repository_by_name(db_session, "find-me")

    assert fetched is not None
    assert fetched.name == "find-me"
    assert fetched.url == "https://find.me/charts"


def test_delete_helm_repository(db_session):
    repo = seed_helm_repository(db_session, name="delete-me", url="https://delete.me/charts")
    result = delete_helm_repository(db_session, repo.id)
    assert result is True

    fetched = get_helm_repository_by_name(db_session, "delete-me")
    assert fetched is None
