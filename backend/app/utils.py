"""Pure helpers with no external dependencies."""

import calendar
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation


def normalize(s: str) -> str:
    """Lowercase and strip accents, so file-name matching is accent-insensitive."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


def days_until_due(due_day: int, today: datetime) -> int:
    """Days until the bill's due day within the current month.

    Negative means the due day already passed this month (overdue).
    A due_day beyond the month's length is clamped to the last day
    (e.g. 31 in February becomes 28/29).
    """
    last_day = calendar.monthrange(today.year, today.month)[1]
    effective_due = min(due_day, last_day)
    return effective_due - today.day


def parse_amount(value: str | int | float | None) -> Decimal | None:
    """Parse a money amount as iOS Shortcuts sends it, e.g. "R$ 1.234,56".

    Accepts plain numbers too ("42.90", 42.9). With both separators present the
    last one is the decimal mark; with only "." and exactly three digits after
    it, it is a thousands separator (pt-BR "1.234"). Returns None for empty
    input, raises ValueError for anything that is not a positive amount.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        text = str(value)
    else:
        text = re.sub(r"[^\d,.\-]", "", value)
        if not text:
            if value.strip():
                raise ValueError(f"Valor inválido: {value!r}")
            return None
        last_comma, last_dot = text.rfind(","), text.rfind(".")
        if last_comma != -1 and last_dot != -1:
            decimal_mark = "," if last_comma > last_dot else "."
            thousands = "." if decimal_mark == "," else ","
            text = text.replace(thousands, "").replace(decimal_mark, ".")
        elif last_comma != -1:
            text = text.replace(".", "").replace(",", ".")
        elif last_dot != -1 and (text.count(".") > 1 or len(text) - last_dot - 1 == 3):
            text = text.replace(".", "")
    try:
        amount = Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Valor inválido: {value!r}")
    if amount <= 0:
        raise ValueError(f"Valor inválido: {value!r}")
    return amount
