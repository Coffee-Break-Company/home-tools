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
    receipt_file_name,
    _urgency_dot,
    _due_phrase,
    _build_reminder_message,
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


# ── _urgency_dot / _due_phrase ────────────────────────────────────────────────

def test_urgency_dot_tiers():
    assert _urgency_dot(-1) == "🔴"
    assert _urgency_dot(0) == "🟠"
    assert _urgency_dot(1) == "🟡"
    assert _urgency_dot(2) == "🟡"
    assert _urgency_dot(3) == "⚪"


def test_due_phrase_overdue_singular():
    assert _due_phrase(-1) == "venceu há 1 dia"


def test_due_phrase_overdue_plural():
    assert _due_phrase(-3) == "venceu há 3 dias"


def test_due_phrase_today():
    assert _due_phrase(0) == "vence hoje"


def test_due_phrase_tomorrow():
    assert _due_phrase(1) == "vence amanhã"


def test_due_phrase_upcoming():
    assert _due_phrase(5) == "vence em 5 dias"


def test_due_phrase_plural():
    assert _due_phrase(-2, plural=True) == "venceram há 2 dias"
    assert _due_phrase(0, plural=True) == "vencem hoje"
    assert _due_phrase(1, plural=True) == "vencem amanhã"
    assert _due_phrase(5, plural=True) == "vencem em 5 dias"


# ── _build_reminder_message ───────────────────────────────────────────────────

def test_build_reminder_message_single_bill():
    msg = _build_reminder_message([{"name": "Água", "days_until_due": 1}])
    assert msg == "Sua conta <b>Água</b> vence amanhã\n\n<pre>🟡 Água  vence amanhã</pre>"


def test_build_reminder_message_multiple_bills_aligned():
    msg = _build_reminder_message([
        {"name": "Luz", "days_until_due": -2},
        {"name": "Internet", "days_until_due": 5},
    ])
    assert msg.startswith("Sua conta <b>Luz</b> venceu há 2 dias — e mais 1 conta na fila")
    assert "🔴 Luz       venceu há 2 dias" in msg
    assert "⚪ Internet  vence em 5 dias" in msg


def test_build_reminder_message_plural_queue():
    msg = _build_reminder_message([
        {"name": "Luz", "days_until_due": 0},
        {"name": "Água", "days_until_due": 1},
        {"name": "Internet", "days_until_due": 2},
    ])
    assert "— e mais 2 contas na fila" in msg


def test_build_reminder_message_groups_tied_urgency():
    msg = _build_reminder_message([
        {"name": "Água", "days_until_due": 1},
        {"name": "Luz", "days_until_due": 1},
    ])
    assert msg.startswith("Suas contas <b>Água</b> e <b>Luz</b> vencem amanhã")
    assert "na fila" not in msg


def test_build_reminder_message_groups_ties_and_counts_rest():
    msg = _build_reminder_message([
        {"name": "Água", "days_until_due": 0},
        {"name": "Luz", "days_until_due": 0},
        {"name": "Gás", "days_until_due": 0},
        {"name": "Internet", "days_until_due": 2},
    ])
    assert msg.startswith(
        "Suas contas <b>Água</b>, <b>Luz</b> e <b>Gás</b> vencem hoje — e mais 1 conta na fila"
    )


def test_build_reminder_message_escapes_html():
    msg = _build_reminder_message([{"name": "A&B <Casa>", "days_until_due": 0}])
    assert "<b>A&amp;B &lt;Casa&gt;</b>" in msg
    assert "A&B <Casa>" not in msg


def test_build_reminder_message_all_paid():
    assert _build_reminder_message([], []) == "Todas as contas estão em dia :)"


def test_build_reminder_message_overdue_only():
    msg = _build_reminder_message([], [
        {"name": "Água", "month": 4, "month_name": "Abril"},
        {"name": "Água", "month": 5, "month_name": "Maio"},
        {"name": "Energia", "month": 3, "month_name": "Marco"},
    ])
    assert "vence" not in msg  # no due-soon section
    assert msg.startswith("⚠️ <b>Contas de meses anteriores em aberto</b>")
    assert "Água     Abril, Maio" in msg  # months grouped per bill, aligned
    assert "Energia  Marco" in msg


def test_build_reminder_message_due_and_overdue():
    msg = _build_reminder_message(
        [{"name": "Internet", "days_until_due": 1}],
        [{"name": "Água", "month": 4, "month_name": "Abril"}],
    )
    assert msg.startswith("Sua conta <b>Internet</b> vence amanhã")
    assert "⚠️ <b>Contas de meses anteriores em aberto</b>" in msg


# ── send_telegram_message ─────────────────────────────────────────────────────

def test_send_telegram_message_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")

    with patch("main.httpx.post") as p_post:
        send_telegram_message("hello")

    p_post.assert_called_once()
    kwargs = p_post.call_args.kwargs
    assert kwargs["json"] == {"chat_id": "chat456", "text": "hello", "parse_mode": "HTML"}
    assert "token123" in p_post.call_args.args[0]


def test_send_telegram_message_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(HTTPException) as exc:
        send_telegram_message("hello")
    assert exc.value.status_code == 500


# ── POST /api/bills/{id}/receipt ──────────────────────────────────────────────

def _upload_receipt(client, bill_id="1", month=6, filename="comprovante.pdf",
                    content=b"%PDF-fake", ctype="application/pdf"):
    return client.post(
        f"/api/bills/{bill_id}/receipt",
        data={"month": str(month)},
        files={"file": (filename, content, ctype)},
    )


def test_receipt_file_name_current_year():
    assert receipt_file_name(6, datetime(2026, 6, 9), ".pdf") == "Junho 2026.pdf"


def test_receipt_file_name_future_month_uses_previous_year():
    assert receipt_file_name(12, datetime(2026, 1, 5), ".pdf") == "Dezembro 2025.pdf"


def test_upload_receipt_success(auth_client, fresh_supabase):
    fresh_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "name": "Água", "due_day": 10, "drive_folder_id": "folder-1"}
    ]
    svc = MagicMock()
    svc.files.return_value.create.return_value.execute.return_value = {"id": "drive-id", "name": "Junho 2026.pdf"}

    with patch("main.get_drive_service", return_value=svc):
        res = _upload_receipt(auth_client)

    assert res.status_code == 201
    body = res.json()
    assert body["ok"] is True
    assert body["file_id"] == "drive-id"

    create_kwargs = svc.files.return_value.create.call_args.kwargs
    assert create_kwargs["body"]["parents"] == ["folder-1"]
    assert create_kwargs["body"]["name"].endswith(".pdf")


def test_upload_receipt_invalid_month(auth_client):
    res = _upload_receipt(auth_client, month=13)
    assert res.status_code == 400


def test_upload_receipt_unsupported_type(auth_client):
    res = _upload_receipt(auth_client, filename="notas.txt", ctype="text/plain")
    assert res.status_code == 400


def test_upload_receipt_too_large(auth_client):
    res = _upload_receipt(auth_client, content=b"x" * (10 * 1024 * 1024 + 1))
    assert res.status_code == 413


def test_upload_receipt_bill_not_found(auth_client, fresh_supabase):
    fresh_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    res = _upload_receipt(auth_client, bill_id="missing")
    assert res.status_code == 404


def test_upload_receipt_drive_error_returns_502(auth_client, fresh_supabase):
    from googleapiclient.errors import HttpError

    fresh_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "1", "name": "Água", "due_day": 10, "drive_folder_id": "folder-1"}
    ]
    svc = MagicMock()
    resp = MagicMock()
    resp.status = 403
    svc.files.return_value.create.return_value.execute.side_effect = HttpError(resp, b"Forbidden")

    with patch("main.get_drive_service", return_value=svc):
        res = _upload_receipt(auth_client)

    assert res.status_code == 502


def test_upload_receipt_requires_auth():
    with TestClient(app) as c:
        res = _upload_receipt(c)
    assert res.status_code == 401


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


# Receipts for every elapsed month up to (and including) `through`, so a bill
# with these names has nothing due or overdue.
def _paid_through(through: int) -> set[str]:
    return {main.MONTHS_PT[m - 1] for m in range(1, through + 1)}


def test_scan_notifies_unpaid_due_soon(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 15, tzinfo=main.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 16, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch("main.datetime") as p_dt,
        patch("main.list_bill_folder_names", return_value=[_paid_through(5)]),
        patch("main.send_telegram_message") as p_send,
    ):
        p_dt.now.return_value = now
        with TestClient(app) as c:
            res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "secret"})

    assert res.status_code == 200
    body = res.json()
    assert body["checked"] == 1
    assert body["notified"] == [{"name": "Energia", "days_until_due": 1}]
    assert body["overdue"] == []
    p_send.assert_called_once()


def test_scan_skips_paid_bill(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 15, tzinfo=main.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 16, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch("main.datetime") as p_dt,
        patch("main.list_bill_folder_names", return_value=[_paid_through(6)]),
        patch("main.send_telegram_message") as p_send,
    ):
        p_dt.now.return_value = now
        with TestClient(app) as c:
            res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "secret"})

    assert res.status_code == 200
    assert res.json()["notified"] == []
    assert res.json()["overdue"] == []
    p_send.assert_called_once_with("Todas as contas estão em dia :)")


def test_scan_skips_bill_far_from_due(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 1, tzinfo=main.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 28, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch("main.datetime") as p_dt,
        patch("main.list_bill_folder_names", return_value=[_paid_through(5)]),
        patch("main.send_telegram_message") as p_send,
    ):
        p_dt.now.return_value = now
        with TestClient(app) as c:
            res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "secret"})

    assert res.status_code == 200
    assert res.json()["notified"] == []
    assert res.json()["overdue"] == []
    p_send.assert_called_once_with("Todas as contas estão em dia :)")


def test_scan_notifies_overdue_earlier_months(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 15, tzinfo=main.TIMEZONE)
    # Due day 25: not within the 3-day window, so only earlier months matter.
    bills = [{"id": "1", "name": "Água", "due_day": 25, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch("main.datetime") as p_dt,
        patch("main.list_bill_folder_names", return_value=[set()]),
        patch("main.send_telegram_message") as p_send,
    ):
        p_dt.now.return_value = now
        with TestClient(app) as c:
            res = c.post("/api/cron/scan", headers={"X-Cron-Secret": "secret"})

    assert res.status_code == 200
    body = res.json()
    assert body["notified"] == []
    assert [o["month_name"] for o in body["overdue"]] == [
        "Janeiro", "Fevereiro", "Marco", "Abril", "Maio",
    ]
    p_send.assert_called_once()
