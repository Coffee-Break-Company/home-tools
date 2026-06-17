"""Pure helpers with no external dependencies."""

import calendar
import unicodedata
from datetime import datetime


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
