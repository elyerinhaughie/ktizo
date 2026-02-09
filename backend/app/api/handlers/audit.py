"""Audit log WebSocket handlers."""
import logging
from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


async def _audit_list(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import audit_log as crud
        logs = crud.get_audit_logs(db,
            skip=params.get("skip", 0),
            limit=params.get("limit", 50),
            page_filter=params.get("page"),
            action_filter=params.get("action"),
        )
        total = crud.get_audit_log_count(db,
            page_filter=params.get("page"),
            action_filter=params.get("action"),
        )
        await _ws._respond(ws, req_id, {"logs": logs, "total": total})
    finally:
        db.close()


async def _audit_clear(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import audit_log as crud
        count = crud.clear_audit_logs(db)
        await _ws._respond(ws, req_id, {"message": f"Cleared {count} audit log entries"})
        await _ws._broadcast("audit_cleared", {})
    finally:
        db.close()


AUDIT_ACTIONS = {
    "audit.list": _audit_list,
    "audit.clear": _audit_clear,
}
