"""CRUD operations for Helm releases and repositories"""
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.db.models import HelmRelease, HelmRepository
from app.schemas.helm import HelmReleaseCreate, HelmReleaseUpdate
from typing import List, Optional


def get_helm_releases(db: Session, skip: int = 0, limit: int = 100) -> List[HelmRelease]:
    return db.query(HelmRelease).offset(skip).limit(limit).all()


def get_helm_release(db: Session, release_id: int) -> Optional[HelmRelease]:
    return db.query(HelmRelease).filter(HelmRelease.id == release_id).first()


def get_helm_release_by_name(db: Session, release_name: str) -> Optional[HelmRelease]:
    return db.query(HelmRelease).filter(HelmRelease.release_name == release_name).first()


def create_helm_release(db: Session, release: HelmReleaseCreate) -> HelmRelease:
    db_release = HelmRelease(
        release_name=release.release_name,
        namespace=release.namespace,
        repo_name=release.repo_name,
        repo_url=release.repo_url,
        chart_name=release.chart_name,
        chart_version=release.chart_version,
        catalog_id=release.catalog_id,
        values_yaml=release.values_yaml,
        values_json=release.values_json,
        status="pending",
    )
    db.add(db_release)
    db.commit()
    db.refresh(db_release)
    return db_release


def update_helm_release(db: Session, release_id: int, release: HelmReleaseUpdate) -> Optional[HelmRelease]:
    db_release = get_helm_release(db, release_id)
    if not db_release:
        return None
    update_data = release.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_release, field, value)
    db.commit()
    db.refresh(db_release)
    return db_release


def update_helm_release_status(
    db: Session,
    release_id: int,
    status: str,
    message: str = None,
    revision: int = None,
    app_version: str = None,
    deployed_at=None,
    log_output: str = None,
) -> Optional[HelmRelease]:
    db_release = get_helm_release(db, release_id)
    if not db_release:
        return None
    db_release.status = status
    if message is not None:
        db_release.status_message = message
    if log_output is not None:
        db_release.log_output = log_output
    if revision is not None:
        db_release.revision = revision
    if app_version is not None:
        db_release.app_version = app_version
    if deployed_at is not None:
        db_release.deployed_at = deployed_at
    db.commit()
    db.refresh(db_release)
    return db_release


def delete_helm_release(db: Session, release_id: int) -> bool:
    db_release = get_helm_release(db, release_id)
    if not db_release:
        return False
    db.delete(db_release)
    db.commit()
    return True


# --- Repositories ---

def get_helm_repositories(db: Session) -> List[HelmRepository]:
    return db.query(HelmRepository).all()


def get_helm_repository_by_name(db: Session, name: str) -> Optional[HelmRepository]:
    return db.query(HelmRepository).filter(HelmRepository.name == name).first()


def add_helm_repository(db: Session, name: str, url: str) -> HelmRepository:
    db_repo = HelmRepository(name=name, url=url)
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    return db_repo


def delete_helm_repository(db: Session, repo_id: int) -> bool:
    db_repo = db.query(HelmRepository).filter(HelmRepository.id == repo_id).first()
    if not db_repo:
        return False
    db.delete(db_repo)
    db.commit()
    return True
