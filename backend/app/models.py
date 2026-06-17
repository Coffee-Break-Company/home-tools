"""Pydantic request/response models."""

from pydantic import BaseModel


class BillCreate(BaseModel):
    name: str
    due_day: int
    drive_folder_id: str
