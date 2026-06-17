"""Builds the Telegram HTML body for the daily reminder.

`build_reminder_message` is the only public entry point; the rest are private
formatting helpers. Pure functions over plain dicts, so they carry no I/O.
"""

import html


def _urgency_dot(days: int) -> str:
    if days < 0:
        return "🔴"
    if days == 0:
        return "🟠"
    if days <= 2:
        return "🟡"
    return "⚪"


def _due_phrase(days: int, plural: bool = False) -> str:
    if days < 0:
        n = abs(days)
        verb = "venceram" if plural else "venceu"
        return f"{verb} há {n} {'dia' if n == 1 else 'dias'}"
    verb = "vencem" if plural else "vence"
    if days == 0:
        return f"{verb} hoje"
    if days == 1:
        return f"{verb} amanhã"
    return f"{verb} em {days} dias"


def _due_reminder_section(notified: list[dict]) -> str:
    """Headline + monospace table sorted by urgency.

    Expects `notified` non-empty and already sorted by days_until_due ascending.
    The headline groups every bill tied at the highest urgency.
    """
    top_days = notified[0]["days_until_due"]
    top = [b for b in notified if b["days_until_due"] == top_days]
    names = [f"<b>{html.escape(b['name'])}</b>" for b in top]
    subject = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " e " + names[-1]
    prefix = "Suas contas" if len(top) > 1 else "Sua conta"
    headline = f"{prefix} {subject} {_due_phrase(top_days, plural=len(top) > 1)}"
    others = len(notified) - len(top)
    if others:
        headline += f" — e mais {others} {'conta' if others == 1 else 'contas'} na fila"

    width = max(len(b["name"]) for b in notified)
    rows = "\n".join(
        f"{_urgency_dot(b['days_until_due'])} "
        + html.escape(f"{b['name'].ljust(width)}  {_due_phrase(b['days_until_due'])}")
        for b in notified
    )
    return f"{headline}\n\n<pre>{rows}</pre>"


def _overdue_section(overdue: list[dict]) -> str:
    """Warning block for receipts still missing from earlier months.

    Expects `overdue` items as {name, month_name}; groups months by bill so each
    bill shows once ("Água  Abril, Maio").
    """
    by_bill: dict[str, list[str]] = {}
    for item in overdue:
        by_bill.setdefault(item["name"], []).append(item["month_name"])
    width = max(len(name) for name in by_bill)
    rows = "\n".join(
        html.escape(f"{name.ljust(width)}  {', '.join(months)}")
        for name, months in by_bill.items()
    )
    return f"⚠️ <b>Contas de meses anteriores em aberto</b>\n<pre>{rows}</pre>"


def build_reminder_message(notified: list[dict], overdue: list[dict] | None = None) -> str:
    """Telegram HTML message: a due-soon section and/or an earlier-months section.

    Either part is omitted when empty, so the message can carry just the bills
    due soon, just the overdue earlier months, or both. With neither, it returns
    an all-clear so the daily scan still confirms nothing is pending.
    """
    sections = []
    if notified:
        sections.append(_due_reminder_section(notified))
    if overdue:
        sections.append(_overdue_section(overdue))
    if not sections:
        return "Todas as contas estão em dia :)"
    return "\n\n".join(sections)
