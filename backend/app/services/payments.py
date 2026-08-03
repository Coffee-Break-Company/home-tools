"""Pure payment logic over a folder's file names (no I/O).

Given the set of receipt names returned by `app.services.drive`, these decide
which months are covered. Keeping them side-effect-free makes them trivial to
test and reuse across the status, missing-payments and reminder flows.
"""

from datetime import date, datetime

from app.config import MONTHS_PT


def has_receipt(file_names: set[str], month: int) -> bool:
    """True if a receipt for the given month is among the file names.

    Receipts are named by month only ("Junho.pdf"); the year lives in the
    folder, so each bill folder holds a single year's receipts. Matches the
    month name as a prefix, accent-insensitively (see normalize).
    """
    month_normalized = MONTHS_PT[month - 1]
    return any(name.startswith(month_normalized) for name in file_names)


def _start_date(bill: dict) -> date | None:
    """The bill's `start_date` as a date, or None when it has none.

    Supabase returns DATE columns as ISO strings; bills registered before the
    column existed carry no value at all.
    """
    value = bill.get("start_date")
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def first_charged_month(bill: dict, year: int) -> int:
    """First month of `year` the bill is expected to have a receipt for.

    A bill is only charged from its `start_date` on: months before it existed
    never had a payment to make, so they must not be reported as unpaid.
    Bills without a start date are charged from January, as before.
    Returns 13 — a month that never matches — when the bill only starts in a
    later year.
    """
    start = _start_date(bill)
    if start is None or start.year < year:
        return 1
    return start.month if start.year == year else 13


def has_started(bill: dict, today: datetime) -> bool:
    """True once today's month has reached the bill's start month."""
    return first_charged_month(bill, today.year) <= today.month


def earlier_unpaid_months(bill: dict, file_names: set[str], today: datetime) -> list[dict]:
    """Elapsed months of the year (before today's month) with no receipt.

    The current month is left out: it may not be due yet and is shown elsewhere.
    Months before the bill's start date are left out too (see
    `first_charged_month`), so a newly added bill never reports a backlog.
    """
    return [
        {
            "name": bill["name"],
            "month": month,
            "month_name": MONTHS_PT[month - 1].capitalize(),
        }
        for month in range(first_charged_month(bill, today.year), today.month)
        if not has_receipt(file_names, month)
    ]
