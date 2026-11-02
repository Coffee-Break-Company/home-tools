from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.utils import parse_amount
from main import app

HEADERS = {"X-Shortcut-Token": "token"}


@pytest.fixture
def client(monkeypatch, fresh_supabase):
    monkeypatch.setenv("SHORTCUT_TOKEN", "token")
    # insert() echoes back what it was given, like Supabase does.
    insert = fresh_supabase.table.return_value.insert
    insert.return_value.execute.side_effect = lambda: type(
        "Res", (), {"data": [insert.call_args.args[0]]}
    )()
    with TestClient(app) as c:
        yield c


def _inserted(fresh_supabase) -> dict:
    return fresh_supabase.table.return_value.insert.call_args.args[0]


# ── parse_amount ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ("R$ 42,90", "42.90"),
    ("R$ 1.234,56", "1234.56"),
    ("R$ 1.234", "1234.00"),
    ("42.90", "42.90"),
    ("1,234.56", "1234.56"),
    ("7", "7.00"),
    (42.9, "42.90"),
    (15, "15.00"),
])
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_amount_empty_is_none(raw):
    assert parse_amount(raw) is None


@pytest.mark.parametrize("raw", ["abc", "R$ 0,00", "-10", "1,2,3.4.5"])
def test_parse_amount_invalid_raises(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


# ── auth ──────────────────────────────────────────────────────────────────────

def test_ingest_without_configured_token_returns_401(monkeypatch):
    monkeypatch.delenv("SHORTCUT_TOKEN", raising=False)
    with TestClient(app) as c:
        res = c.post("/api/expenses/ingest", json={"amount": "R$ 1,00"}, headers=HEADERS)
    assert res.status_code == 401


def test_ingest_wrong_token_returns_401(client, fresh_supabase):
    res = client.post("/api/expenses/ingest", json={"amount": "R$ 1,00"},
                      headers={"X-Shortcut-Token": "wrong"})
    assert res.status_code == 401
    fresh_supabase.table.return_value.insert.assert_not_called()


# ── POST /api/expenses/ingest ─────────────────────────────────────────────────

def test_ingest_saves_expense(client, fresh_supabase):
    res = client.post("/api/expenses/ingest", headers=HEADERS, json={
        "amount": "R$ 42,90",
        "merchant": "  Padaria X ",
        "card": "Nubank",
        "occurred_at": "2026-11-02T14:32:00-03:00",
    })

    assert res.status_code == 201
    row = _inserted(fresh_supabase)
    assert row["amount"] == "42.90"
    assert row["merchant"] == "Padaria X"
    assert row["card"] == "Nubank"
    assert row["occurred_at"] == "2026-11-02T14:32:00-03:00"
    assert row["source"] == "apple_pay"
    assert row["is_test"] is False
    assert row["raw"]["amount"] == "R$ 42,90"
    assert res.json()["warning"] is None
    fresh_supabase.table.assert_called_with("expenses")


def test_ingest_test_flag_marks_row(client, fresh_supabase):
    client.post("/api/expenses/ingest", headers=HEADERS,
                json={"amount": "R$ 1,00", "test": True})
    assert _inserted(fresh_supabase)["is_test"] is True


def test_ingest_unparseable_amount_still_saves(client, fresh_supabase):
    res = client.post("/api/expenses/ingest", headers=HEADERS,
                      json={"amount": "???", "merchant": "Loja"})
    assert res.status_code == 201
    assert _inserted(fresh_supabase)["amount"] is None
    assert res.json()["warning"]


def test_ingest_naive_date_assumes_sao_paulo(client, fresh_supabase):
    client.post("/api/expenses/ingest", headers=HEADERS,
                json={"amount": "R$ 1,00", "occurred_at": "2026-11-02T14:32:00"})
    assert _inserted(fresh_supabase)["occurred_at"] == "2026-11-02T14:32:00-03:00"


def test_ingest_unparseable_date_falls_back_to_now(client, fresh_supabase):
    res = client.post("/api/expenses/ingest", headers=HEADERS,
                      json={"amount": "R$ 1,00", "occurred_at": "2 de nov. de 2026 14:32"})
    assert res.status_code == 201
    assert _inserted(fresh_supabase)["occurred_at"].endswith("-03:00")


# ── DELETE /api/expenses/test ─────────────────────────────────────────────────

def test_delete_test_expenses(client, fresh_supabase):
    delete = fresh_supabase.table.return_value.delete
    delete.return_value.eq.return_value.execute.return_value.data = [{"id": "a"}, {"id": "b"}]

    res = client.delete("/api/expenses/test", headers=HEADERS)

    assert res.status_code == 200
    assert res.json() == {"deleted": 2}
    delete.return_value.eq.assert_called_once_with("is_test", True)


def test_delete_test_expenses_requires_token(client, fresh_supabase):
    res = client.delete("/api/expenses/test", headers={"X-Shortcut-Token": "wrong"})
    assert res.status_code == 401
    fresh_supabase.table.return_value.delete.assert_not_called()


# ── GET /api/expenses ─────────────────────────────────────────────────────────

def _list_query(fresh_supabase):
    """The chain select().eq().gte().lt().order() and its execute()."""
    select = fresh_supabase.table.return_value.select
    eq = select.return_value.eq
    gte = eq.return_value.gte
    lt = gte.return_value.lt
    order = lt.return_value.order
    return eq, gte, lt, order


def test_list_expenses_filters_month_and_real_rows(auth_client, fresh_supabase):
    eq, gte, lt, order = _list_query(fresh_supabase)
    rows = [{"id": "1", "amount": 42.9, "merchant": "Padaria"}]
    order.return_value.execute.return_value.data = rows

    res = auth_client.get("/api/expenses?month=2026-11")

    assert res.status_code == 200
    assert res.json() == rows
    eq.assert_called_once_with("is_test", False)
    gte.assert_called_once_with("occurred_at", "2026-11-01T00:00:00-03:00")
    lt.assert_called_once_with("occurred_at", "2026-12-01T00:00:00-03:00")
    order.assert_called_once_with("occurred_at", desc=True)


def test_list_expenses_december_rolls_into_next_year(auth_client, fresh_supabase):
    _, _, lt, _ = _list_query(fresh_supabase)
    auth_client.get("/api/expenses?month=2026-12")
    lt.assert_called_once_with("occurred_at", "2027-01-01T00:00:00-03:00")


def test_list_expenses_test_flag_returns_only_test_rows(auth_client, fresh_supabase):
    eq, _, _, _ = _list_query(fresh_supabase)
    auth_client.get("/api/expenses?month=2026-11&test=true")
    eq.assert_called_once_with("is_test", True)


@pytest.mark.parametrize("month", ["2026-13", "2026-1", "novembro"])
def test_list_expenses_invalid_month_returns_400(auth_client, month):
    res = auth_client.get(f"/api/expenses?month={month}")
    assert res.status_code == 400


def test_list_expenses_requires_login():
    with TestClient(app) as c:
        res = c.get("/api/expenses")
    assert res.status_code == 401


# ── logs ──────────────────────────────────────────────────────────────────────

def test_ingest_logs_registered_expense(client, caplog):
    with caplog.at_level("INFO", logger="app.routers.expenses"):
        client.post("/api/expenses/ingest", headers=HEADERS,
                    json={"amount": "R$ 42,90", "merchant": "Padaria", "card": "Nubank"})
    assert "Gasto registrado" in caplog.text
    assert "valor=42.90" in caplog.text


def test_ingest_logs_unparseable_amount_and_date(client, caplog):
    client.post("/api/expenses/ingest", headers=HEADERS,
                json={"amount": "???", "occurred_at": "ontem"})
    assert "Valor não reconhecido '???'" in caplog.text
    assert "Data não reconhecida 'ontem'" in caplog.text


def test_ingest_logs_wrong_token_without_leaking_it(client, caplog):
    client.post("/api/expenses/ingest", json={"amount": "1"},
                headers={"X-Shortcut-Token": "segredo-errado"})
    assert "Token do atalho inválido (header presente)" in caplog.text
    assert "segredo-errado" not in caplog.text


def test_ingest_logs_and_returns_502_when_supabase_fails(client, fresh_supabase, caplog):
    fresh_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError("down")
    res = client.post("/api/expenses/ingest", headers=HEADERS,
                      json={"amount": "R$ 10,00", "merchant": "Loja"})
    assert res.status_code == 502
    assert "Falha ao salvar o gasto" in caplog.text
    assert "'merchant': 'Loja'" in caplog.text


def test_ingest_logs_validation_errors(client, caplog):
    res = client.post("/api/expenses/ingest", headers=HEADERS, json={"test": "talvez"})
    assert res.status_code == 422
    assert "Requisição do atalho rejeitada (422)" in caplog.text
    assert "talvez" in caplog.text


def test_validation_errors_on_other_routes_are_not_logged(auth_client, caplog):
    auth_client.post("/api/bills", json={"name": "Água"})
    assert "rejeitada" not in caplog.text
