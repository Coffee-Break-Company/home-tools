from app.services.reminders import _due_phrase, _urgency_dot, build_reminder_message


# ── _urgency_dot / _due_phrase ────────────────────────────────────────────────

def test_urgency_dot_tiers():
    assert _urgency_dot(-1) == "🔴"
    assert _urgency_dot(0) == "🟠"
    assert _urgency_dot(1) == "🟡"
    assert _urgency_dot(2) == "🟡"
    assert _urgency_dot(3) == "⚪"


def test_due_phrase_overdue_singular():
    assert _due_phrase(-1) == "venceu há 1 dia"


def test_due_phrase_overdue_plural():
    assert _due_phrase(-3) == "venceu há 3 dias"


def test_due_phrase_today():
    assert _due_phrase(0) == "vence hoje"


def test_due_phrase_tomorrow():
    assert _due_phrase(1) == "vence amanhã"


def test_due_phrase_upcoming():
    assert _due_phrase(5) == "vence em 5 dias"


def test_due_phrase_plural():
    assert _due_phrase(-2, plural=True) == "venceram há 2 dias"
    assert _due_phrase(0, plural=True) == "vencem hoje"
    assert _due_phrase(1, plural=True) == "vencem amanhã"
    assert _due_phrase(5, plural=True) == "vencem em 5 dias"


# ── build_reminder_message ────────────────────────────────────────────────────

def test_build_reminder_message_single_bill():
    msg = build_reminder_message([{"name": "Água", "days_until_due": 1}])
    assert msg == "Sua conta <b>Água</b> vence amanhã\n\n<pre>🟡 Água  vence amanhã</pre>"


def test_build_reminder_message_multiple_bills_aligned():
    msg = build_reminder_message([
        {"name": "Luz", "days_until_due": -2},
        {"name": "Internet", "days_until_due": 5},
    ])
    assert msg.startswith("Sua conta <b>Luz</b> venceu há 2 dias — e mais 1 conta na fila")
    assert "🔴 Luz       venceu há 2 dias" in msg
    assert "⚪ Internet  vence em 5 dias" in msg


def test_build_reminder_message_plural_queue():
    msg = build_reminder_message([
        {"name": "Luz", "days_until_due": 0},
        {"name": "Água", "days_until_due": 1},
        {"name": "Internet", "days_until_due": 2},
    ])
    assert "— e mais 2 contas na fila" in msg


def test_build_reminder_message_groups_tied_urgency():
    msg = build_reminder_message([
        {"name": "Água", "days_until_due": 1},
        {"name": "Luz", "days_until_due": 1},
    ])
    assert msg.startswith("Suas contas <b>Água</b> e <b>Luz</b> vencem amanhã")
    assert "na fila" not in msg


def test_build_reminder_message_groups_ties_and_counts_rest():
    msg = build_reminder_message([
        {"name": "Água", "days_until_due": 0},
        {"name": "Luz", "days_until_due": 0},
        {"name": "Gás", "days_until_due": 0},
        {"name": "Internet", "days_until_due": 2},
    ])
    assert msg.startswith(
        "Suas contas <b>Água</b>, <b>Luz</b> e <b>Gás</b> vencem hoje — e mais 1 conta na fila"
    )


def test_build_reminder_message_escapes_html():
    msg = build_reminder_message([{"name": "A&B <Casa>", "days_until_due": 0}])
    assert "<b>A&amp;B &lt;Casa&gt;</b>" in msg
    assert "A&B <Casa>" not in msg


def test_build_reminder_message_all_paid():
    assert build_reminder_message([], []) == "Todas as contas estão em dia :)"


def test_build_reminder_message_overdue_only():
    msg = build_reminder_message([], [
        {"name": "Água", "month": 4, "month_name": "Abril"},
        {"name": "Água", "month": 5, "month_name": "Maio"},
        {"name": "Energia", "month": 3, "month_name": "Marco"},
    ])
    assert "vence" not in msg  # no due-soon section
    assert msg.startswith("⚠️ <b>Contas de meses anteriores em aberto</b>")
    assert "Água     Abril, Maio" in msg  # months grouped per bill, aligned
    assert "Energia  Marco" in msg


def test_build_reminder_message_due_and_overdue():
    msg = build_reminder_message(
        [{"name": "Internet", "days_until_due": 1}],
        [{"name": "Água", "month": 4, "month_name": "Abril"}],
    )
    assert msg.startswith("Sua conta <b>Internet</b> vence amanhã")
    assert "⚠️ <b>Contas de meses anteriores em aberto</b>" in msg
