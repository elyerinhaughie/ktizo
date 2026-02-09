"""Shared helpers used by all handler modules."""
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

from app.db.database import SessionLocal
from app.services.websocket_manager import websocket_manager
from app.services.audit_service import log_action  # noqa: F401 — re-exported

logger = logging.getLogger(__name__)


def _db():
    return SessionLocal()


def _serialize(obj) -> Any:
    """Best-effort serialisation of SQLAlchemy models / Pydantic models / enums."""
    if obj is None:
        return None
    if isinstance(obj, list):
        return [_serialize(o) for o in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):  # Pydantic model
        return obj.model_dump()
    if hasattr(obj, "__table__"):
        d = {}
        for c in obj.__table__.columns:
            val = getattr(obj, c.name)
            if hasattr(val, "value"):  # enum
                val = val.value
            elif hasattr(val, "isoformat"):  # datetime
                val = val.isoformat()
            d[c.name] = val
        return d
    if hasattr(obj, "value"):  # bare enum
        return obj.value
    return obj


async def _respond(ws: WebSocket, req_id: Optional[str], data: Any = None, error: str = None):
    """Send a response matched by request id."""
    msg: Dict[str, Any] = {"id": req_id, "data": _serialize(data), "error": error}
    await ws.send_json(msg)


async def _broadcast(event_type: str, data: Any = None):
    await websocket_manager.broadcast_event({"type": event_type, "data": _serialize(data)})
