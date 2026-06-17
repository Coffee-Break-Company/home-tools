"""Pure payment logic over a folder's file names (no I/O).

Given the set of receipt names returned by `app.services.drive`, these decide
which months are covered. Keeping them side-effect-free makes them trivial to
test and reuse across the status, missing-payments and reminder flows.
"""

from app.config import MONTHS_PT


def has_receipt(file_names: set[str], month: int) -> bool:
    """True if a receipt for the given month is among the file names.

    Receipts are named by month only ("Junho.pdf"); the year lives in the
    folder, so each bill folder holds a single year's receipts. Matches the
    month name as a prefix, accent-insensitively (see normalize).
    """
    month_normalized = MONTHS_PT[month - 1]
    return any(name.startswith(month_normalized) for name in file_names)


def earlier_unpaid_months(bill: dict, file_names: set[str], current_month: int) -> list[dict]:
    """Elapsed months of the year (before current_month) with no receipt.

    The current month is left out: it may not be due yet and is shown elsewhere.
    Bills carry no start date, so months before a bill existed count as unpaid.
    """
    return [
        {
            "name": bill["name"],
            "month": month,
            "month_name": MONTHS_PT[month - 1].capitalize(),
        }
        for month in range(1, current_month)
        if not has_receipt(file_names, month)
    ]
