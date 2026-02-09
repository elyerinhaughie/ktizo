from sqlalchemy.orm import Session
from app.db.models import AuditLog
from typing import Optional, List


def create_audit_log(
    db: Session,
    action: str,
    page: str,
    details: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> AuditLog:
    log = AuditLog(
        action=action,
        page=page,
        details=details,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_audit_logs(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    page_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
) -> List[AuditLog]:
    query = db.query(AuditLog)
    if page_filter:
        query = query.filter(AuditLog.page == page_filter)
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()


def get_audit_log_count(
    db: Session,
    page_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
) -> int:
    query = db.query(AuditLog)
    if page_filter:
        query = query.filter(AuditLog.page == page_filter)
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    return query.count()


def clear_audit_logs(db: Session) -> int:
    count = db.query(AuditLog).count()
    db.query(AuditLog).delete()
    db.commit()
    return count
