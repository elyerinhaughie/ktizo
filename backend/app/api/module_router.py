"""HTTP API routes for module (Helm) management."""
import asyncio
import json
import logging
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.crud import helm as crud
from app.schemas.helm import HelmReleaseCreate, HelmReleaseResponse
from app.services.module_catalog import get_catalog, get_catalog_entry
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/modules/catalog")
async def module_catalog():
    """Return the full module catalog."""
    return get_catalog()


@router.get("/modules", response_model=List[HelmReleaseResponse])
async def list_modules(db: Session = Depends(get_db)):
    """List all installed module releases."""
    return crud.get_helm_releases(db)


@router.get("/modules/{release_id}", response_model=HelmReleaseResponse)
async def get_module(release_id: int, db: Session = Depends(get_db)):
    """Get a module release by ID."""
    release = crud.get_helm_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


@router.get("/modules/{release_id}/log")
async def get_module_log(release_id: int, db: Session = Depends(get_db)):
    """Get the install/operation log for a module release."""
    release = crud.get_helm_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return {
        "id": release.id,
        "release_name": release.release_name,
        "log": release.log_output or "",
    }


@router.post("/modules/install", response_model=HelmReleaseResponse)
async def install_module(params: HelmReleaseCreate, db: Session = Depends(get_db)):
    """Install a Helm chart. Creates DB record and launches background install."""
    existing = crud.get_helm_release_by_name(db, params.release_name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Release '{params.release_name}' already exists")

    release = crud.create_helm_release(db, params)

    await log_action(db, "module_install_started", "Modules",
        json.dumps({"release_name": release.release_name, "chart": release.chart_name}),
        "module", str(release.id))

    from app.api.ws_handler import _do_helm_install, _broadcast
    await _broadcast("module_installing", {
        "id": release.id,
        "release_name": release.release_name,
        "chart_name": release.chart_name,
    })
    asyncio.create_task(_do_helm_install(release.id, params.model_dump()))

    return release


@router.post("/modules/{release_id}/uninstall")
async def uninstall_module(release_id: int, db: Session = Depends(get_db)):
    """Uninstall a module release."""
    release = crud.get_helm_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    if release.status in ("uninstalling",):
        raise HTTPException(status_code=409, detail="Already uninstalling")

    from app.api.ws_handler import _do_helm_uninstall, _broadcast
    crud.update_helm_release_status(db, release_id, "uninstalling", "Uninstalling...")
    await _broadcast("module_status_changed", {
        "id": release.id,
        "release_name": release.release_name,
        "status": "uninstalling",
    })
    asyncio.create_task(_do_helm_uninstall(release_id))

    return {"message": f"Uninstalling {release.release_name}..."}


@router.delete("/modules/{release_id}/force")
async def force_delete_module(release_id: int, db: Session = Depends(get_db)):
    """Force-delete a module record from DB without Helm uninstall."""
    release = crud.get_helm_release(db, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    name = release.release_name
    crud.delete_helm_release(db, release_id)

    await log_action(db, "module_force_deleted", "Modules",
        json.dumps({"release_name": name}), "module", str(release_id))

    return {"message": f"Force-deleted {name}"}
