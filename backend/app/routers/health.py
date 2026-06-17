"""Health check used by Render's healthCheckPath."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
@router.head("/health")
def health():
    return {"status": "ok"}
