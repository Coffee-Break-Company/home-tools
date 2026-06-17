"""Bill endpoints: CRUD, receipt upload, and the derived payment views.

Payment status is never stored — it is derived from each bill's Drive folder
(see app.services.drive / app.services.payments).
"""

import io
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app import config
from app.auth import verify_user
from app.models import BillCreate
from app.services import drive, payments
from app.services.receipts import RECEIPT_MAX_BYTES, RECEIPT_TYPES, receipt_file_name

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.get("")
def get_bills(_user=Depends(verify_user)):
    res = config.supabase.table("bills").select("*").execute()
    return res.data


@router.post("", status_code=201)
def create_bill(bill: BillCreate, _user=Depends(verify_user)):
    res = config.supabase.table("bills").insert({
        "id": str(uuid4()),
        **bill.model_dump(),
    }).execute()
    return res.data[0]


@router.delete("/{bill_id}")
def delete_bill(bill_id: str, _user=Depends(verify_user)):
    res = config.supabase.table("bills").delete().eq("id", bill_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/{bill_id}/receipt", status_code=201)
async def upload_receipt(
    bill_id: str,
    month: int = Form(...),
    file: UploadFile = File(...),
    _user=Depends(verify_user),
):
    if not 1 <= month <= 12:
        raise HTTPException(status_code=400, detail="Mês inválido")
    extension = RECEIPT_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=400, detail="Envie um PDF ou uma imagem (JPG, PNG, WebP)")
    content = await file.read()
    if len(content) > RECEIPT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo maior que 10 MB")

    res = config.supabase.table("bills").select("*").eq("id", bill_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    bill = res.data[0]

    name = receipt_file_name(month, datetime.now(config.TIMEZONE), extension)
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=file.content_type)
    try:
        created = drive.get_drive_service().files().create(
            body={"name": name, "parents": [bill["drive_folder_id"]]},
            media_body=media,
            fields="id, name",
            supportsAllDrives=True,
        ).execute()
    except HttpError:
        raise HTTPException(status_code=502, detail="Falha ao enviar o arquivo para o Drive")

    return {"ok": True, "file_id": created.get("id"), "file_name": created.get("name")}


@router.get("/status")
def get_bills_status(_user=Depends(verify_user)):
    bills = config.supabase.table("bills").select("*").execute().data
    month = datetime.now().month
    return [
        {**bill, "paid": drive.check_payment_exists(bill["drive_folder_id"], month)}
        for bill in bills
    ]


@router.get("/missing")
def get_missing_payments(_user=Depends(verify_user)):
    """Unpaid receipts from earlier months of the current year, per bill.

    Only fully-elapsed months are reported (January through last month); the
    current month is left out since it may not be due yet and is already shown
    in the bills list. Each bill folder is specific to the current year.

    One Drive listing per bill (not per month) and the listings run in
    parallel, so the cost is a single concurrent batch of N calls.

    Note: bills carry no start date, so months before a bill existed are
    reported as missing too.
    """
    current_month = datetime.now(config.TIMEZONE).month
    bills = config.supabase.table("bills").select("*").execute().data
    folder_names = drive.list_bill_folder_names(bills)

    missing = []
    for bill, file_names in zip(bills, folder_names):
        missing.extend(payments.earlier_unpaid_months(bill, file_names, current_month))
    return missing
