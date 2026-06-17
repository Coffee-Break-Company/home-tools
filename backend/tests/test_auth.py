from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import verify_user
from main import app


# ── verify_user ───────────────────────────────────────────────────────────────

async def test_verify_user_success(fresh_supabase):
    user = MagicMock()
    user.email = "allowed@example.com"
    fresh_supabase.auth.get_user.return_value.user = user
    fresh_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"email": "allowed@example.com"}
    ]

    creds = MagicMock()
    creds.credentials = "valid-token"
    result = await verify_user(creds)
    assert result == user


async def test_verify_user_user_none_raises_401(fresh_supabase):
    fresh_supabase.auth.get_user.return_value.user = None

    creds = MagicMock()
    creds.credentials = "bad-token"
    with pytest.raises(HTTPException) as exc:
        await verify_user(creds)
    assert exc.value.status_code == 401


async def test_verify_user_email_not_authorized_raises_403(fresh_supabase):
    user = MagicMock()
    user.email = "banned@example.com"
    fresh_supabase.auth.get_user.return_value.user = user
    fresh_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    creds = MagicMock()
    creds.credentials = "valid-token"
    with pytest.raises(HTTPException) as exc:
        await verify_user(creds)
    assert exc.value.status_code == 403


async def test_verify_user_unexpected_exception_raises_401(fresh_supabase):
    fresh_supabase.auth.get_user.side_effect = RuntimeError("network error")

    creds = MagicMock()
    creds.credentials = "any-token"
    with pytest.raises(HTTPException) as exc:
        await verify_user(creds)
    assert exc.value.status_code == 401


# ── GET /api/auth/verify ──────────────────────────────────────────────────────

def test_auth_verify_success(auth_client, mock_user):
    res = auth_client.get("/api/auth/verify")
    assert res.status_code == 200
    assert res.json() == {"email": mock_user.email}


def test_auth_verify_no_token():
    with TestClient(app) as c:
        res = c.get("/api/auth/verify")
    assert res.status_code == 401
