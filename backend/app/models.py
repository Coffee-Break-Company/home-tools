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
