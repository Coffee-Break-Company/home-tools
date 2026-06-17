"""Authentication: validate the Supabase JWT and enforce the email allow-list.

`verify_user` is the dependency every protected endpoint depends on. It reads
`config.supabase` at call time so tests can replace the client with a mock.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config

security = HTTPBearer()


async def verify_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        response = config.supabase.auth.get_user(token)
        user = response.user
        if user is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        email = user.email or ""
        allowed = config.supabase.table("allowed_emails").select("email").eq("email", email).execute()
        if not allowed.data:
            raise HTTPException(status_code=403, detail="Email não autorizado")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
