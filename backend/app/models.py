"""Pydantic request/response models."""

from datetime import date

from pydantic import BaseModel


class BillCreate(BaseModel):
    # start_date marks the first month the bill is charged for; omitted means
    # "starts today", so earlier months are never reported as unpaid.
    name: str
    due_day: int
    drive_folder_id: str
    start_date: date | None = None


class ExpenseIngest(BaseModel):
    # Sent by the iPhone Shortcut. `amount` arrives as the formatted text iOS
    # produces ("R$ 42,90") and is parsed server-side; `occurred_at` is optional
    # ISO 8601 (missing or unparseable means "now"). `test` marks the row as
    # fake so it never mixes with real spending.
    amount: str | float | None = None
    merchant: str | None = None
    card: str | None = None
    occurred_at: str | None = None
    source: str = "apple_pay"
    test: bool = False
