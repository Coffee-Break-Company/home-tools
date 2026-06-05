import os
import json
import base64
import unicodedata
from uuid import uuid4
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from supabase import create_client
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

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

security = HTTPBearer()


async def verify_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        response = supabase.auth.get_user(token)
        user = response.user
        if user is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        email = user.email or ""
        allowed = supabase.table("allowed_emails").select("email").eq("email", email).execute()
        if not allowed.data:
            raise HTTPException(status_code=403, detail="Email não autorizado")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


# --- Google Drive ---

def get_drive_service():
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
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/api/auth/verify")
def auth_verify(user=Depends(verify_user)):
    return {"email": user.email}


@app.get("/api/bills")
def get_bills(_user=Depends(verify_user)):
    res = supabase.table("bills").select("*").execute()
    return res.data


@app.post("/api/bills", status_code=201)
def create_bill(bill: BillCreate, _user=Depends(verify_user)):
    res = supabase.table("bills").insert({
        "id": str(uuid4()),
        **bill.model_dump(),
    }).execute()
    return res.data[0]


@app.delete("/api/bills/{bill_id}")
def delete_bill(bill_id: str, _user=Depends(verify_user)):
    res = supabase.table("bills").delete().eq("id", bill_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@app.get("/api/bills/status")
def get_bills_status(_user=Depends(verify_user)):
    bills = supabase.table("bills").select("*").execute().data
    month = datetime.now().month
    return [
        {**bill, "paid": check_payment_exists(bill["drive_folder_id"], month)}
        for bill in bills
    ]
