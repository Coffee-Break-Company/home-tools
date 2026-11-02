"""Expense ingestion, called by an iPhone Shortcut (Wallet "Transaction" trigger).

The Shortcut can't do the Google/Supabase login, so — like the cron endpoint —
the caller proves itself with a shared secret: X-Shortcut-Token must match the
SHORTCUT_TOKEN env var (read at request time, so it can be rotated without a
redeploy).

The automation runs silently on the phone, so a rejected request means a lost
expense. Ingestion is therefore lenient: an amount that can't be parsed is
stored as null (with the raw payload kept) instead of failing the request.

Rows sent with `teste: true` are stored with is_test=true; any query over real
spending must filter them out, and DELETE /api/expenses/test wipes them.
"""

import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException

from app import config
from app.models import ExpenseIngest
from app.utils import parse_amount

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


def _check_token(token: str | None) -> None:
    expected = os.getenv("SHORTCUT_TOKEN")
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="Não autorizado")


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


def _parse_occurred_at(text: str | None) -> datetime:
    """ISO 8601 from the Shortcut; missing or unparseable falls back to now."""
    try:
        occurred_at = datetime.fromisoformat((text or "").strip())
    except ValueError:
        return datetime.now(config.TIMEZONE)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=config.TIMEZONE)
    return occurred_at


@router.post("/ingest", status_code=201)
def ingest_expense(payload: ExpenseIngest, x_shortcut_token: str | None = Header(default=None)):
    _check_token(x_shortcut_token)

    warning = None
    try:
        amount = parse_amount(payload.valor)
    except ValueError:
        amount = None
    if amount is None:
        warning = "Valor ausente ou não reconhecido; gasto salvo sem valor"

    occurred_at = _parse_occurred_at(payload.data)

    row = {
        "id": str(uuid4()),
        "amount": str(amount) if amount is not None else None,
        "merchant": _clean(payload.estabelecimento),
        "card": _clean(payload.cartao),
        "occurred_at": occurred_at.isoformat(),
        "source": payload.origem,
        "is_test": payload.teste,
        "raw": payload.model_dump(mode="json"),
    }
    saved = config.supabase.table("expenses").insert(row).execute().data[0]
    return {**saved, "warning": warning}


@router.delete("/test")
def delete_test_expenses(x_shortcut_token: str | None = Header(default=None)):
    _check_token(x_shortcut_token)
    res = config.supabase.table("expenses").delete().eq("is_test", True).execute()
    return {"deleted": len(res.data)}
