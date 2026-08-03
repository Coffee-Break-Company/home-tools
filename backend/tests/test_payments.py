from datetime import date, datetime

from app import config
from app.services.payments import (
    earlier_unpaid_months,
    first_charged_month,
    has_receipt,
    has_started,
)


def _bill(start_date=None) -> dict:
    return {"id": "1", "name": "Água", "due_day": 10, "drive_folder_id": "f1",
            "start_date": start_date}


# ── has_receipt ───────────────────────────────────────────────────────────────

def test_has_receipt_matches_month_name_prefix():
    assert has_receipt({"junho 2026.pdf"}, 6) is True
    assert has_receipt({"junho 2026.pdf"}, 7) is False


# ── first_charged_month ───────────────────────────────────────────────────────

def test_first_charged_month_without_start_date_is_january():
    assert first_charged_month(_bill(), 2026) == 1


def test_first_charged_month_uses_start_month_in_the_same_year():
    assert first_charged_month(_bill("2026-08-03"), 2026) == 8


def test_first_charged_month_in_a_later_year_is_january():
    assert first_charged_month(_bill("2026-08-03"), 2027) == 1


def test_first_charged_month_before_the_start_year_matches_no_month():
    assert first_charged_month(_bill("2027-02-01"), 2026) == 13


def test_first_charged_month_accepts_a_date_object():
    assert first_charged_month(_bill(date(2026, 5, 20)), 2026) == 5


# ── has_started ───────────────────────────────────────────────────────────────

def test_has_started_is_true_from_the_start_month_on():
    today = datetime(2026, 8, 3, tzinfo=config.TIMEZONE)
    assert has_started(_bill("2026-08-20"), today) is True
    assert has_started(_bill("2026-09-01"), today) is False


# ── earlier_unpaid_months ─────────────────────────────────────────────────────

def test_earlier_unpaid_months_skips_months_before_the_start_date():
    today = datetime(2026, 8, 3, tzinfo=config.TIMEZONE)
    months = earlier_unpaid_months(_bill("2026-05-10"), set(), today)
    assert [m["month_name"] for m in months] == ["Maio", "Junho", "Julho"]


def test_earlier_unpaid_months_empty_for_a_bill_added_this_month():
    today = datetime(2026, 8, 3, tzinfo=config.TIMEZONE)
    assert earlier_unpaid_months(_bill("2026-08-03"), set(), today) == []


def test_earlier_unpaid_months_covers_the_whole_year_after_the_start_year():
    today = datetime(2027, 3, 15, tzinfo=config.TIMEZONE)
    months = earlier_unpaid_months(_bill("2026-08-03"), set(), today)
    assert [m["month_name"] for m in months] == ["Janeiro", "Fevereiro"]


def test_earlier_unpaid_months_without_start_date_covers_every_elapsed_month():
    today = datetime(2026, 4, 1, tzinfo=config.TIMEZONE)
    months = earlier_unpaid_months(_bill(), set(), today)
    assert [m["month_name"] for m in months] == ["Janeiro", "Fevereiro", "Marco"]
