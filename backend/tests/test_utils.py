from datetime import datetime

from app.utils import days_until_due, normalize


# ── normalize ─────────────────────────────────────────────────────────────────

def test_normalize_removes_accents_and_lowercases():
    assert normalize("Março") == "marco"


def test_normalize_plain_ascii():
    assert normalize("HELLO") == "hello"


def test_normalize_empty_string():
    assert normalize("") == ""


# ── days_until_due ────────────────────────────────────────────────────────────

def test_days_until_due_upcoming():
    assert days_until_due(20, datetime(2024, 6, 15)) == 5


def test_days_until_due_overdue():
    assert days_until_due(10, datetime(2024, 6, 15)) == -5


def test_days_until_due_clamps_to_end_of_month():
    # February 2024 has 29 days; due_day 31 -> effective 29.
    assert days_until_due(31, datetime(2024, 2, 15)) == 14
