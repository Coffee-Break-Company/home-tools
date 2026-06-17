from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.services import telegram
from app.services.telegram import send_telegram_message


def test_send_telegram_message_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")

    with patch.object(telegram, "httpx") as p_httpx:
        send_telegram_message("hello")

    p_httpx.post.assert_called_once()
    kwargs = p_httpx.post.call_args.kwargs
    assert kwargs["json"] == {"chat_id": "chat456", "text": "hello", "parse_mode": "HTML"}
    assert "token123" in p_httpx.post.call_args.args[0]


def test_send_telegram_message_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(HTTPException) as exc:
        send_telegram_message("hello")
    assert exc.value.status_code == 500
