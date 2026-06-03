import os
import unicodedata
import yaml
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DATA_DIR = Path(__file__).parent.parent / "data"
BILLS_FILE = DATA_DIR / "bills.yaml"

MONTHS_PT = [
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def normalize(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


app = FastAPI(title="Home Tools API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- YAML storage ---

def load_bills() -> list[dict]:
    if not BILLS_FILE.exists():
        return []
    with open(BILLS_FILE) as f:
        return yaml.safe_load(f) or []


def save_bills(bills: list[dict]):
    DATA_DIR.mkdir(exist_ok=True)
    with open(BILLS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(bills, f, allow_unicode=True, default_flow_style=False)


# --- Google Drive ---

def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def check_payment_exists(drive_folder_id: str, month: int) -> bool:
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


# --- Models ---

class BillCreate(BaseModel):
    name: str
    due_day: int
    drive_folder_id: str


# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/bills")
def get_bills():
    return load_bills()


@app.post("/api/bills", status_code=201)
def create_bill(bill: BillCreate):
    bills = load_bills()
    new_bill = {"id": str(uuid4()), **bill.model_dump()}
    bills.append(new_bill)
    save_bills(bills)
    return new_bill


@app.delete("/api/bills/{bill_id}")
def delete_bill(bill_id: str):
    bills = load_bills()
    updated = [b for b in bills if b["id"] != bill_id]
    if len(updated) == len(bills):
        raise HTTPException(status_code=404, detail="Not found")
    save_bills(updated)
    return {"ok": True}


@app.get("/api/bills/status")
def get_bills_status():
    bills = load_bills()
    month = datetime.now().month
    return [
        {**bill, "paid": check_payment_exists(bill["drive_folder_id"], month)}
        for bill in bills
    ]
