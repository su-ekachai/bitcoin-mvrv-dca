import pytest

import dca_monitor
from dca_monitor import notify_all

ENV_ALL = {
    "DISCORD_WEBHOOK_URL": "https://discord/hook",
    "TELEGRAM_BOT_TOKEN": "tok",
    "TELEGRAM_CHAT_ID": "42",
    "SHEETS_WEBHOOK_URL": "https://script.google/hook",
}
PAYLOAD = {"embeds": []}
ROW = {"date": "2026-07-21"}


def test_sends_all_configured(monkeypatch):
    sent = []
    monkeypatch.setattr(dca_monitor, "send_discord", lambda u, p: sent.append("discord"))
    monkeypatch.setattr(dca_monitor, "send_telegram", lambda t, c, x: sent.append("telegram"))
    monkeypatch.setattr(dca_monitor, "send_sheet", lambda u, r: sent.append("sheets"))
    assert notify_all(ENV_ALL, PAYLOAD, "text", ROW) == ["discord", "telegram", "sheets"]
    assert sent == ["discord", "telegram", "sheets"]


def test_skips_unconfigured(monkeypatch):
    monkeypatch.setattr(dca_monitor, "send_telegram", lambda t, c, x: None)
    env = {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "42"}
    assert notify_all(env, PAYLOAD, "text", ROW) == ["telegram"]


def test_one_failure_does_not_block_others(monkeypatch):
    def boom(u, p):
        raise OSError("discord down")

    monkeypatch.setattr(dca_monitor, "send_discord", boom)
    monkeypatch.setattr(dca_monitor, "send_telegram", lambda t, c, x: None)
    monkeypatch.setattr(dca_monitor, "send_sheet", lambda u, r: None)
    assert notify_all(ENV_ALL, PAYLOAD, "text", ROW) == ["telegram", "sheets"]


def test_all_failing_raises(monkeypatch):
    def boom(*args):
        raise OSError("down")

    monkeypatch.setattr(dca_monitor, "send_discord", boom)
    monkeypatch.setattr(dca_monitor, "send_telegram", boom)
    monkeypatch.setattr(dca_monitor, "send_sheet", boom)
    with pytest.raises(RuntimeError, match="all channels failed"):
        notify_all(ENV_ALL, PAYLOAD, "text", ROW)


def test_no_channels_configured_returns_empty():
    assert notify_all({}, PAYLOAD, "text", ROW) == []


def test_row_none_skips_sheets(monkeypatch):
    monkeypatch.setattr(dca_monitor, "send_discord", lambda u, p: None)
    env = {"DISCORD_WEBHOOK_URL": "https://d", "SHEETS_WEBHOOK_URL": "https://s"}
    assert notify_all(env, PAYLOAD, "text", None) == ["discord"]


def test_telegram_send_uses_html_parse_mode(monkeypatch):
    captured = {}

    def fake_http(url, payload=None, timeout=30):
        captured["url"] = url
        captured["payload"] = payload

    monkeypatch.setattr(dca_monitor, "http_json", fake_http)
    dca_monitor.send_telegram("tok", "42", "<b>hi</b>")
    assert captured["url"] == "https://api.telegram.org/bottok/sendMessage"
    assert captured["payload"] == {"chat_id": "42", "text": "<b>hi</b>", "parse_mode": "HTML"}


def test_skipped_channels_logged(monkeypatch, caplog):
    monkeypatch.setattr(dca_monitor, "send_discord", lambda u, p: None)
    env = {"DISCORD_WEBHOOK_URL": "https://d", "TELEGRAM_BOT_TOKEN": "tok"}  # chat id missing
    with caplog.at_level("INFO", logger="mvrv-dca"):
        sent = notify_all(env, PAYLOAD, "text", ROW)
    assert sent == ["discord"]
    messages = " ".join(r.message for r in caplog.records)
    assert "telegram" in messages and "skip" in messages
    assert "sheets" in messages
