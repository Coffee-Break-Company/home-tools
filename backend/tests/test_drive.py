import base64
import json
from unittest.mock import MagicMock, patch

from app import config
from app.services import drive
from app.services.drive import (
    check_payment_exists,
    get_drive_service,
    list_bill_folder_names,
    list_folder_file_names,
)

from tests.conftest import drive_service_mock


# ── get_drive_service ─────────────────────────────────────────────────────────

def test_get_drive_service_from_base64_env(monkeypatch):
    fake_info = {"type": "service_account", "project_id": "test-project"}
    b64 = base64.b64encode(json.dumps(fake_info).encode()).decode()
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", b64)

    mock_creds = MagicMock()
    mock_service = MagicMock()

    with (
        patch.object(drive.service_account.Credentials, "from_service_account_info", return_value=mock_creds) as p_info,
        patch.object(drive, "build", return_value=mock_service),
    ):
        result = get_drive_service()
        p_info.assert_called_once_with(fake_info, scopes=config.SCOPES)
        assert result == mock_service


def test_get_drive_service_from_file(monkeypatch):
    monkeypatch.delenv("GOOGLE_CREDENTIALS_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "/fake/creds.json")

    mock_creds = MagicMock()
    mock_service = MagicMock()

    with (
        patch.object(drive.service_account.Credentials, "from_service_account_file", return_value=mock_creds) as p_file,
        patch.object(drive, "build", return_value=mock_service),
    ):
        result = get_drive_service()
        p_file.assert_called_once_with("/fake/creds.json", scopes=config.SCOPES)
        assert result == mock_service


# ── check_payment_exists ──────────────────────────────────────────────────────

def test_check_payment_found():
    with patch.object(drive, "get_drive_service", return_value=drive_service_mock([{"name": "Marco 2024.pdf"}])):
        assert check_payment_exists("folder-id", 3) is True


def test_check_payment_not_found_different_month():
    with patch.object(drive, "get_drive_service", return_value=drive_service_mock([{"name": "Janeiro 2024.pdf"}])):
        assert check_payment_exists("folder-id", 3) is False


def test_check_payment_empty_folder():
    with patch.object(drive, "get_drive_service", return_value=drive_service_mock([])):
        assert check_payment_exists("folder-id", 6) is False


def test_check_payment_http_error_returns_false():
    from googleapiclient.errors import HttpError

    svc = MagicMock()
    resp = MagicMock()
    resp.status = 403
    svc.files.return_value.list.return_value.execute.side_effect = HttpError(resp, b"Forbidden")

    with patch.object(drive, "get_drive_service", return_value=svc):
        assert check_payment_exists("folder-id", 1) is False


# ── list_folder_file_names ────────────────────────────────────────────────────

def test_list_folder_file_names_pages_and_normalizes():
    svc = MagicMock()
    svc.files.return_value.list.return_value.execute.side_effect = [
        {"nextPageToken": "page2", "files": [{"name": "Junho 2026.pdf"}]},
        {"files": [{"name": "Maio 2026.pdf"}]},  # no token -> last page
    ]

    with patch.object(drive, "get_drive_service", return_value=svc):
        names = list_folder_file_names("folder-id")

    assert names == {"junho 2026.pdf", "maio 2026.pdf"}
    assert svc.files.return_value.list.return_value.execute.call_count == 2


def test_list_folder_file_names_http_error_returns_empty_set():
    from googleapiclient.errors import HttpError

    svc = MagicMock()
    resp = MagicMock()
    resp.status = 403
    svc.files.return_value.list.return_value.execute.side_effect = HttpError(resp, b"Forbidden")

    with patch.object(drive, "get_drive_service", return_value=svc):
        assert list_folder_file_names("folder-id") == set()


# ── list_bill_folder_names ────────────────────────────────────────────────────

def test_list_bill_folder_names_empty_bills_returns_empty_list():
    assert list_bill_folder_names([]) == []


def test_list_bill_folder_names_aligns_with_bills_order():
    bills = [
        {"id": "1", "drive_folder_id": "f1"},
        {"id": "2", "drive_folder_id": "f2"},
    ]
    per_folder = {"f1": {"junho 2026.pdf"}, "f2": {"maio 2026.pdf"}}

    with patch.object(drive, "list_folder_file_names", side_effect=lambda fid: per_folder[fid]):
        result = list_bill_folder_names(bills)

    assert result == [{"junho 2026.pdf"}, {"maio 2026.pdf"}]
