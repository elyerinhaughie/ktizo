"""Volume configuration handlers for WebSocket API."""

import json
import logging
from fastapi import WebSocket

import app.api.ws_handler as _ws

logger = logging.getLogger(__name__)


async def _volumes_list(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import volume as crud
        configs = crud.get_volume_configs(db)
        await _ws._respond(ws, req_id, configs)
    finally:
        db.close()


async def _volumes_get(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import volume as crud
        config = crud.get_volume_config(db, params["volume_id"])
        if not config:
            return await _ws._respond(ws, req_id, error="Volume config not found")
        await _ws._respond(ws, req_id, config)
    finally:
        db.close()


async def _volumes_get_by_name(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import volume as crud
        config = crud.get_volume_config_by_name(db, params["name"])
        if not config:
            return await _ws._respond(ws, req_id, error=f"Volume config '{params['name']}' not found")
        await _ws._respond(ws, req_id, config)
    finally:
        db.close()


async def _volumes_create(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import volume as crud
        from app.schemas.volume import VolumeConfigCreate
        existing = crud.get_volume_config_by_name(db, params.get("name", ""))
        if existing:
            return await _ws._respond(ws, req_id, error=f"Volume config '{params['name']}' already exists")
        created = crud.create_volume_config(db, VolumeConfigCreate(**params))
        await _ws.log_action(db, "created_volume_config", "Storage Settings",
            json.dumps({"name": str(created.name)}), "volume_config", str(created.id))
        await _ws._respond(ws, req_id, created)
        await _ws._broadcast("volume_updated", created)
    finally:
        db.close()


async def _volumes_update(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import volume as crud
        from app.schemas.volume import VolumeConfigUpdate
        volume_id = params.pop("volume_id")
        updated = crud.update_volume_config(db, volume_id, VolumeConfigUpdate(**params))
        if not updated:
            return await _ws._respond(ws, req_id, error="Volume config not found")
        await _ws.log_action(db, "updated_volume_config", "Storage Settings",
            json.dumps({"name": str(updated.name)}), "volume_config", str(volume_id))
        await _ws._respond(ws, req_id, updated)
        await _ws._broadcast("volume_updated", updated)
    finally:
        db.close()


async def _volumes_delete(params: dict, ws: WebSocket, req_id: str):
    db = _ws._db()
    try:
        from app.crud import volume as crud
        volume_id = params["volume_id"]
        success = crud.delete_volume_config(db, volume_id)
        if not success:
            return await _ws._respond(ws, req_id, error="Volume config not found")
        await _ws.log_action(db, "deleted_volume_config", "Storage Settings",
            None, "volume_config", str(volume_id))
        await _ws._respond(ws, req_id, {"message": "Volume configuration deleted"})
        await _ws._broadcast("volume_updated", {"deleted_id": volume_id})
    finally:
        db.close()


VOLUME_ACTIONS = {
    "volumes.list": _volumes_list,
    "volumes.get": _volumes_get,
    "volumes.get_by_name": _volumes_get_by_name,
    "volumes.create": _volumes_create,
    "volumes.update": _volumes_update,
    "volumes.delete": _volumes_delete,
}
