from sqlalchemy.orm import Session
from app.crud.audit_log import create_audit_log
from app.services.websocket_manager import websocket_manager
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def log_action(
    db: Session,
    action: str,
    page: str,
    details: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
):
    log = create_audit_log(db, action, page, details, entity_type, entity_id)
    try:
        await websocket_manager.broadcast_event({
            "type": "audit_log_created",
            "log": {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "action": log.action,
                "page": log.page,
                "details": log.details,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
            },
        })
    except Exception as e:
        logger.warning(f"Failed to broadcast audit log event: {e}")
    return log
