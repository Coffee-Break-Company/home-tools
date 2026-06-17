"""Google Drive access — the source of truth for whether a bill is paid.

A bill is paid for a month when its Drive folder holds a receipt named after
that month. These functions only do the Drive I/O; the pure decision logic over
the resulting file names lives in `app.services.payments`. Every function fails
soft (returns empty / False) on Drive errors, so the rest of the app degrades to
"unpaid" rather than crashing.
"""

import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import MONTHS_PT, SCOPES
from app.utils import normalize


def get_drive_service():
    """Build a Drive client from base64 env creds (prod) or a JSON file (local)."""
    credentials_b64 = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if credentials_b64:
        info = json.loads(base64.b64decode(credentials_b64))
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_CREDENTIALS_PATH"), scopes=SCOPES
        )
    return build("drive", "v3", credentials=credentials)


def check_payment_exists(drive_folder_id: str, month: int) -> bool:
    """True if the folder holds a receipt for the given month (single listing)."""
    try:
        service = get_drive_service()
        result = service.files().list(
            q=f"'{drive_folder_id}' in parents and trashed = false",
            fields="files(name)",
        ).execute()

        month_normalized = MONTHS_PT[month - 1]
        for file in result.get("files", []):
            if normalize(file["name"]).startswith(month_normalized):
                return True
        return False

    except HttpError:
        return False


def list_folder_file_names(drive_folder_id: str) -> set[str]:
    """Normalized names of every file in a folder, in a single listing.

    One call returns receipts for all months/years, so callers can check the
    whole year locally instead of querying Drive month by month. Builds its own
    service so it is safe to run from a worker thread (the googleapiclient
    http transport is not thread-safe). Pages through large folders. Returns an
    empty set on Drive errors, mirroring check_payment_exists' fail-as-unpaid.
    """
    try:
        service = get_drive_service()
        names: set[str] = set()
        page_token = None
        while True:
            result = service.files().list(
                q=f"'{drive_folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(name)",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            for file in result.get("files", []):
                names.add(normalize(file["name"]))
            page_token = result.get("nextPageToken")
            if not page_token:
                return names
    except HttpError:
        return set()


def list_bill_folder_names(bills: list[dict]) -> list[set[str]]:
    """File names in each bill's Drive folder, one listing per bill in parallel.

    The returned list is aligned with `bills`, so a single concurrent batch of
    listings serves both the current-month check and the earlier-months audit.
    """
    if not bills:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(bills))) as executor:
        return list(executor.map(
            lambda bill: list_folder_file_names(bill["drive_folder_id"]), bills
        ))
