from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Environment, Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["meta"])


class Meta(BaseModel):
    api_version: Literal["1"] = "1"
    environment: Environment
    features: dict[str, bool]


@router.get("/meta", operation_id="getMeta")
async def meta(settings: Annotated[Settings, Depends(get_settings)]) -> Meta:
    """Public runtime configuration. Only public feature flags are listed."""
    return Meta(environment=settings.environment, features=settings.public_features)
