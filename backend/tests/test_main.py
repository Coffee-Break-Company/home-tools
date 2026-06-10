import base64
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
from main import (
    app,
    normalize,
    days_until_due,
    send_telegram_message,
    _reminder_line,
    get_drive_service,
    check_payment_exists,
    verify_user,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_supabase():
    """Replace main.supabase with a fresh MagicMock for each test."""
    mock = MagicMock()
    main.supabase = mock
    return mock


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.email = "allowed@example.com"
    return user


@pytest.fixture
def auth_client(mock_user):
    """TestClient with verify_user dependency bypassed."""
    app.dependency_overrides[verify_user] = lambda: mock_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _drive_service_mock(files: list) -> MagicMock:
    svc = MagicMock()
    svc.files.return_value.list.return_value.execute.return_value = {"files": files}
    return svc


# ── normalize ─────────────────────────────────────────────────────────────────

def test_normalize_removes_accents_and_lowercases():
    assert normalize("Março") == "marco"


def test_normalize_plain_ascii():
    assert normalize("HELLO") == "hello"


def test_normalize_empty_string():
    assert normalize("") == ""


# ── get_drive_service ─────────────────────────────────────────────────────────

def test_get_drive_service_from_base64_env(monkeypatch):
    fake_info = {"type": "service_account", "project_id": "test-project"}
    b64 = base64.b64encode(json.dumps(fake_info).encode()).decode()
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", b64)

    mock_creds = MagicMock()
    mock_service = MagicMock()

    with (
        patch("main.service_account.Credentials.from_service_account_info", return_value=mock_creds) as p_info,
        patch("main.build", return_value=mock_service),
    ):
        result = get_drive_service()
        p_info.assert_called_once_with(fake_info, scopes=main.SCOPES)
        assert result == mock_service


def test_get_drive_service_from_file(monkeypatch):
    monkeypatch.delenv("GOOGLE_CREDENTIALS_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "/fake/creds.json")

    mock_creds = MagicMock()
    mock_service = MagicMock()

    with (
        patch("main.service_account.Credentials.from_service_account_file", return_value=mock_creds) as p_file,
        patch("main.build", return_value=mock_service),
    ):
        result = get_drive_service()
        p_file.assert_called_once_with("/fake/creds.json", scopes=main.SCOPES)
        assert result == mock_service


# ── check_payment_exists ──────────────────────────────────────────────────────

def test_check_payment_found():
    with patch("main.get_drive_service", return_value=_drive_service_mock([{"name": "Marco 2024.pdf"}])):
        assert check_payment_exists("folder-id", 3) is True


def test_check_payment_not_found_different_month():
    with patch("main.get_drive_service", return_value=_drive_service_mock([{"name": "Janeiro 2024.pdf"}])):
        assert check_payment_exists("folder-id", 3) is False


def test_check_payment_empty_folder():
    with patch("main.get_drive_service", return_value=_drive_service_mock([])):
        assert check_payment_exists("folder-id", 6) is False


def test_check_payment_http_error_returns_false():
    from googleapiclient.errors import HttpError

    svc = MagicMock()
    resp = MagicMock()
    resp.status = 403
    svc.files.return_value.list.return_value.execute.side_effect = HttpError(resp, b"Forbidden")

    with patch("main.get_drive_service", return_value=svc):
        assert check_payment_exists("folder-id", 1) is False


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


# ── GET /health  HEAD /health ─────────────────────────────────────────────────

def test_health_get():
    with TestClient(app) as c:
        res = c.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_head():
    with TestClient(app) as c:
        res = c.head("/health")
    assert res.status_code == 200


# ── GET /api/auth/verify ──────────────────────────────────────────────────────

def test_auth_verify_success(auth_client, mock_user):
    res = auth_client.get("/api/auth/verify")
    assert res.status_code == 200
    assert res.json() == {"email": mock_user.email}


def test_auth_verify_no_token():
    with TestClient(app) as c:
        res = c.get("/api/auth/verify")
    assert res.status_code == 401


# ── GET /api/bills ────────────────────────────────────────────────────────────

def test_get_bills_success(auth_client, fresh_supabase):
    bills = [{"id": "1", "name": "Internet", "due_day": 10, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills
    res = auth_client.get("/api/bills")
    assert res.status_code == 200
    assert res.json() == bills


def test_get_bills_no_token():
    with TestClient(app) as c:
        res = c.get("/api/bills")
    assert res.status_code == 401


# ── POST /api/bills ───────────────────────────────────────────────────────────

def test_create_bill_success(auth_client, fresh_supabase):
    created = {"id": "new-id", "name": "Water", "due_day": 5, "drive_folder_id": "f2"}
    fresh_supabase.table.return_value.insert.return_value.execute.return_value.data = [created]

    res = auth_client.post("/api/bills", json={"name": "Water", "due_day": 5, "drive_folder_id": "f2"})
    assert res.status_code == 201
    assert res.json()["name"] == "Water"


def test_create_bill_no_token():
    with TestClient(app) as c:
        res = c.post("/api/bills", json={"name": "Water", "due_day": 5, "drive_folder_id": "f2"})
    assert res.status_code == 401


# ── DELETE /api/bills/{bill_id} ───────────────────────────────────────────────

def test_delete_bill_success(auth_client, fresh_supabase):
    fresh_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [
        {"id": "bill-id"}
    ]
    res = auth_client.delete("/api/bills/bill-id")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_delete_bill_not_found(auth_client, fresh_supabase):
    fresh_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    res = auth_client.delete("/api/bills/nonexistent")
    assert res.status_code == 404


def test_delete_bill_no_token():
    with TestClient(app) as c:
        res = c.delete("/api/bills/bill-id")
    assert res.status_code == 401


# ── GET /api/bills/status ─────────────────────────────────────────────────────

def test_get_bills_status_success(auth_client, fresh_supabase):
    bills = [
        {"id": "1", "name": "Internet", "due_day": 10, "drive_folder_id": "f1"},
        {"id": "2", "name": "Water", "due_day": 5, "drive_folder_id": "f2"},
    ]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with patch("main.check_payment_exists", side_effect=[True, False]):
        res = auth_client.get("/api/bills/status")

    assert res.status_code == 200
    data = res.json()
    assert data[0]["paid"] is True
    assert data[1]["paid"] is False


def test_get_bills_status_no_token():
    with TestClient(app) as c:
        res = c.get("/api/bills/status")
    assert res.status_code == 401


# ── days_until_due ────────────────────────────────────────────────────────────

from datetime import datetime  # noqa: E402


def test_days_until_due_upcoming():
    assert days_until_due(20, datetime(2024, 6, 15)) == 5


def test_days_until_due_overdue():
    assert days_until_due(10, datetime(2024, 6, 15)) == -5


def test_days_until_due_clamps_to_end_of_month():
    # February 2024 has 29 days; due_day 31 -> effective 29.
    assert days_until_due(31, datetime(2024, 2, 15)) == 14


# ── _reminder_line ────────────────────────────────────────────────────────────

def test_reminder_line_overdue_singular():
    assert _reminder_line("Água", -1) == "🔴 Água — atrasada há 1 dia"


def test_reminder_line_overdue_plural():
    assert _reminder_line("Água", -3) == "🔴 Água — atrasada há 3 dias"


def test_reminder_line_due_today():
    assert _reminder_line("Energia", 0) == "⚠️ Energia — vence hoje"


def test_reminder_line_upcoming_singular():
    assert _reminder_line("Internet", 1) == "🟡 Internet — vence em 1 dia"


def test_reminder_line_upcoming_plural():
    assert _reminder_line("Internet", 2) == "🟡 Internet — vence em 2 dias"


# ── send_telegram_message ─────────────────────────────────────────────────────

def test_send_telegram_message_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")

    with patch("main.httpx.post") as p_post:
        send_telegram_message("hello")

    p_post.assert_called_once()
    kwargs = p_post.call_args.kwargs
    assert kwargs["json"] == {"chat_id": "chat456", "text": "hello"}
    assert "token123" in p_post.call_args.args[0]


def test_send_telegram_message_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(HTTPException) as exc:
        send_telegram_message("hello")
    assert exc.value.status_code == 500


# ── POST /api/cron/scan ───────────────────────────────────────────────────────

def test_scan_no_secret_configured_returns_401(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    with TestClient(app) as c:
        res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "anything"})
    assert res.status_code == 401


def test_scan_wrong_secret_returns_401(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "correct")
    with TestClient(app) as c:
        res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "wrong"})
    assert res.status_code == 401


def test_scan_notifies_unpaid_due_soon(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 15, tzinfo=main.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 16, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch("main.datetime") as p_dt,
        patch("main.check_payment_exists", return_value=False),
        patch("main.send_telegram_message") as p_send,
    ):
        p_dt.now.return_value = now
        with TestClient(app) as c:
            res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "secret"})

    assert res.status_code == 200
    body = res.json()
    assert body["checked"] == 1
    assert body["notified"] == [{"name": "Energia", "days_until_due": 1}]
    p_send.assert_called_once()


def test_scan_skips_paid_bill(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 15, tzinfo=main.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 16, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch("main.datetime") as p_dt,
        patch("main.check_payment_exists", return_value=True),
        patch("main.send_telegram_message") as p_send,
    ):
        p_dt.now.return_value = now
        with TestClient(app) as c:
            res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "secret"})

    assert res.status_code == 200
    assert res.json()["notified"] == []
    p_send.assert_not_called()


def test_scan_skips_bill_far_from_due(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 1, tzinfo=main.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 28, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch("main.datetime") as p_dt,
        patch("main.check_payment_exists", return_value=False) as p_check,
        patch("main.send_telegram_message") as p_send,
    ):
        p_dt.now.return_value = now
        with TestClient(app) as c:
            res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "secret"})

    assert res.status_code == 200
    assert res.json()["notified"] == []
    p_check.assert_not_called()
    p_send.assert_not_called()
