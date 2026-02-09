from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.audit_log import AuditLogListResponse
from app.crud import audit_log as audit_crud
from typing import Optional

router = APIRouter()


@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    page: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
):
    logs = audit_crud.get_audit_logs(db, skip=skip, limit=limit, page_filter=page, action_filter=action)
    total = audit_crud.get_audit_log_count(db, page_filter=page, action_filter=action)
    return AuditLogListResponse(logs=logs, total=total)


@router.delete("/logs")
async def clear_audit_logs(db: Session = Depends(get_db)):
    count = audit_crud.clear_audit_logs(db)
    return {"message": f"Cleared {count} audit log entries"}
