from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class HelmReleaseCreate(BaseModel):
    release_name: str
    namespace: str = "default"
    repo_name: Optional[str] = None
    repo_url: Optional[str] = None
    chart_name: str
    chart_version: Optional[str] = None
    catalog_id: Optional[str] = None
    values_yaml: Optional[str] = None
    values_json: Optional[str] = None


class HelmReleaseUpdate(BaseModel):
    chart_version: Optional[str] = None
    values_yaml: Optional[str] = None
    values_json: Optional[str] = None


class HelmReleaseResponse(BaseModel):
    id: int
    release_name: str
    namespace: str
    repo_name: Optional[str] = None
    repo_url: Optional[str] = None
    chart_name: str
    chart_version: Optional[str] = None
    catalog_id: Optional[str] = None
    values_yaml: Optional[str] = None
    values_json: Optional[str] = None
    status: str
    status_message: Optional[str] = None
    revision: Optional[int] = None
    app_version: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
