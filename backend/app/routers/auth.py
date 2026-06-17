"""Auth verification endpoint."""

from fastapi import APIRouter, Depends

from app.auth import verify_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/verify")
def auth_verify(user=Depends(verify_user)):
    return {"email": user.email}
