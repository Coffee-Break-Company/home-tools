from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.services import drive
from app.services.receipts import receipt_file_name
from main import app


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

    with patch.object(drive, "check_payment_exists", side_effect=[True, False]):
        res = auth_client.get("/api/bills/status")

    assert res.status_code == 200
    data = res.json()
    assert data[0]["paid"] is True
    assert data[1]["paid"] is False


def test_get_bills_status_no_token():
    with TestClient(app) as c:
        res = c.get("/api/bills/status")
    assert res.status_code == 401


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

    with patch.object(drive, "get_drive_service", return_value=svc):
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

    with patch.object(drive, "get_drive_service", return_value=svc):
        res = _upload_receipt(auth_client)

    assert res.status_code == 502


def test_upload_receipt_requires_auth():
    with TestClient(app) as c:
        res = _upload_receipt(c)
    assert res.status_code == 401
