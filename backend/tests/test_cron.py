from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import config
from app.routers import cron
from app.services import drive, telegram
from main import app


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
    return {config.MONTHS_PT[m - 1] for m in range(1, through + 1)}


def test_scan_notifies_unpaid_due_soon(monkeypatch, fresh_supabase):
    monkeypatch.setenv("CRON_SECRET", "secret")
    now = datetime(2024, 6, 15, tzinfo=config.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 16, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch.object(cron, "datetime") as p_dt,
        patch.object(drive, "list_bill_folder_names", return_value=[_paid_through(5)]),
        patch.object(telegram, "send_telegram_message") as p_send,
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
    now = datetime(2024, 6, 15, tzinfo=config.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 16, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch.object(cron, "datetime") as p_dt,
        patch.object(drive, "list_bill_folder_names", return_value=[_paid_through(6)]),
        patch.object(telegram, "send_telegram_message") as p_send,
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
    now = datetime(2024, 6, 1, tzinfo=config.TIMEZONE)
    bills = [{"id": "1", "name": "Energia", "due_day": 28, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch.object(cron, "datetime") as p_dt,
        patch.object(drive, "list_bill_folder_names", return_value=[_paid_through(5)]),
        patch.object(telegram, "send_telegram_message") as p_send,
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
    now = datetime(2024, 6, 15, tzinfo=config.TIMEZONE)
    # Due day 25: not within the 3-day window, so only earlier months matter.
    bills = [{"id": "1", "name": "Água", "due_day": 25, "drive_folder_id": "f1"}]
    fresh_supabase.table.return_value.select.return_value.execute.return_value.data = bills

    with (
        patch.object(cron, "datetime") as p_dt,
        patch.object(drive, "list_bill_folder_names", return_value=[set()]),
        patch.object(telegram, "send_telegram_message") as p_send,
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
