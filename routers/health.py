from fastapi import APIRouter
from core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "version": settings.app_version}

