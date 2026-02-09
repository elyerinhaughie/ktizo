from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    action: str
    page: str
    details: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
