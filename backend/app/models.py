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
    # Field names match the JSON the iPhone Shortcut sends, so they stay in
    # Portuguese. `valor` arrives as the formatted text iOS produces
    # ("R$ 42,90") and is parsed server-side; `data` is optional ISO 8601 (missing or
    # unparseable means "now"). `teste` marks the row as fake so it never mixes
    # with real spending.
    valor: str | float | None = None
    estabelecimento: str | None = None
    cartao: str | None = None
    data: str | None = None
    origem: str = "apple_pay"
    teste: bool = False
