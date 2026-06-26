"""The daily reminder endpoint, triggered by an external cron (GitHub Actions).

Not called by the app itself; the caller proves itself with X-Cron-Secret.
`CRON_SECRET` and `REMINDER_DAYS_AHEAD` are read at request time so the schedule
can be reconfigured without a redeploy.
"""

import os
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException

from app import config
from app.services import drive, payments, reminders, telegram
from app.utils import days_until_due

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.post("/scan")
def scan_due_bills(x_cron_secret: str | None = Header(default=None)):
    expected = os.getenv("CRON_SECRET")
    if not expected or x_cron_secret != expected:
        raise HTTPException(status_code=401, detail="Não autorizado")

    days_ahead = int(os.getenv("REMINDER_DAYS_AHEAD", "3"))
    today = datetime.now(config.TIMEZONE)
    bills = config.supabase.table("bills").select("*").execute().data
    folder_names = drive.list_bill_folder_names(bills)

    notified = []
    overdue = []
    for bill, file_names in zip(bills, folder_names):
        days = days_until_due(bill["due_day"], today)
        if days <= days_ahead and not payments.has_receipt(file_names, today.month):
            notified.append({"name": bill["name"], "days_until_due": days})
        overdue.extend(payments.earlier_unpaid_months(bill, file_names, today.month))

    notified.sort(key=lambda b: b["days_until_due"])

    sent = bool(notified or overdue)
    if sent:
        telegram.send_telegram_message(reminders.build_reminder_message(notified, overdue))

    return {"checked": len(bills), "notified": notified, "overdue": overdue, "sent": sent}
