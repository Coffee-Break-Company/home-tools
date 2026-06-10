import os
import html
import json
import base64
import calendar
import unicodedata
from uuid import uuid4
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from fastapi import FastAPI, HTTPException, Depends, Header
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

TIMEZONE = ZoneInfo("America/Sao_Paulo")

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

MONTHS_PT = [
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def normalize(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


def days_until_due(due_day: int, today: datetime) -> int:
    """Days until the bill's due day within the current month.

    Negative means the due day already passed this month (overdue).
    A due_day beyond the month's length is clamped to the last day
    (e.g. 31 in February becomes 28/29).
    """
    last_day = calendar.monthrange(today.year, today.month)[1]
    effective_due = min(due_day, last_day)
    return effective_due - today.day


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


# --- Telegram ---

def send_telegram_message(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise HTTPException(status_code=500, detail="Telegram não configurado")
    httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    ).raise_for_status()


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


def _urgency_dot(days: int) -> str:
    if days < 0:
        return "🔴"
    if days == 0:
        return "🟠"
    if days <= 2:
        return "🟡"
    return "⚪"


def _due_phrase(days: int, plural: bool = False) -> str:
    if days < 0:
        n = abs(days)
        verb = "venceram" if plural else "venceu"
        return f"{verb} há {n} {'dia' if n == 1 else 'dias'}"
    verb = "vencem" if plural else "vence"
    if days == 0:
        return f"{verb} hoje"
    if days == 1:
        return f"{verb} amanhã"
    return f"{verb} em {days} dias"


def _build_reminder_message(notified: list[dict]) -> str:
    """Telegram HTML message: headline + monospace table sorted by urgency.

    Expects `notified` already sorted by days_until_due ascending.
    The headline groups every bill tied at the highest urgency.
    """
    top_days = notified[0]["days_until_due"]
    top = [b for b in notified if b["days_until_due"] == top_days]
    names = [f"<b>{html.escape(b['name'])}</b>" for b in top]
    subject = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " e " + names[-1]
    prefix = "Suas contas" if len(top) > 1 else "Sua conta"
    headline = f"{prefix} {subject} {_due_phrase(top_days, plural=len(top) > 1)}"
    others = len(notified) - len(top)
    if others:
        headline += f" — e mais {others} {'conta' if others == 1 else 'contas'} na fila"

    width = max(len(b["name"]) for b in notified)
    rows = "\n".join(
        f"{_urgency_dot(b['days_until_due'])} "
        + html.escape(f"{b['name'].ljust(width)}  {_due_phrase(b['days_until_due'])}")
        for b in notified
    )
    return f"{headline}\n\n<pre>{rows}</pre>"


@app.post("/api/cron/scan")
def scan_due_bills(x_cron_secret: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if not expected or x_cron_secret != expected:
        raise HTTPException(status_code=401, detail="Não autorizado")

    days_ahead = int(os.getenv("REMINDER_DAYS_AHEAD", "3"))
    today = datetime.now(TIMEZONE)
    bills = supabase.table("bills").select("*").execute().data

    notified = []
    for bill in bills:
        days = days_until_due(bill["due_day"], today)
        if days > days_ahead:
            continue
        if check_payment_exists(bill["drive_folder_id"], today.month):
            continue
        notified.append({"name": bill["name"], "days_until_due": days})

    if notified:
        notified.sort(key=lambda b: b["days_until_due"])
        send_telegram_message(_build_reminder_message(notified))

    return {"checked": len(bills), "notified": notified}
