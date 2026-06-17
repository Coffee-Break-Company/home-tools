"""Receipt upload constraints and naming.

`receipt_file_name` must keep producing names that
`app.services.drive.check_payment_exists` matches.
"""

from datetime import datetime

from app.config import MONTHS_PT

RECEIPT_MAX_BYTES = 10 * 1024 * 1024
RECEIPT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def receipt_file_name(month: int, today: datetime, extension: str) -> str:
    """Name the receipt as check_payment_exists expects ("Junho 2026.pdf").

    A month ahead of the current one is assumed to belong to the previous
    year (e.g. uploading December's receipt in January).
    """
    year = today.year - 1 if month > today.month else today.year
    return f"{MONTHS_PT[month - 1].capitalize()} {year}{extension}"
