import http.client
import urllib.error

import pytest

import dca_monitor
from dca_monitor import RETRY_WAITS, fetch_with_retry


def test_retry_waits_are_spec_values():
    assert RETRY_WAITS == (2, 8, 30)


def test_fetch_with_retry_succeeds_after_failures(monkeypatch):
    calls = {"n": 0}

    def flaky(url, payload=None, timeout=30):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("boom")
        return {"ok": True}

    monkeypatch.setattr(dca_monitor, "http_json", flaky)
    waits: list[float] = []
    result = fetch_with_retry("https://x", sleep=waits.append)
    assert result == {"ok": True}
    assert waits == [2, 8]


def test_fetch_with_retry_raises_after_four_attempts(monkeypatch):
    calls = {"n": 0}

    def always_down(url, payload=None, timeout=30):
        calls["n"] += 1
        raise urllib.error.URLError("down")

    monkeypatch.setattr(dca_monitor, "http_json", always_down)
    waits: list[float] = []
    with pytest.raises(RuntimeError, match="4 attempts"):
        fetch_with_retry("https://x", sleep=waits.append)
    assert calls["n"] == 4
    assert waits == [2, 8, 30]


def test_fetch_with_retry_retries_connection_reset(monkeypatch):
    calls = {"n": 0}

    def resets_then_ok(url, payload=None, timeout=30):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionResetError("reset mid-read")
        if calls["n"] == 2:
            raise http.client.IncompleteRead(b"partial")
        return {"ok": True}

    monkeypatch.setattr(dca_monitor, "http_json", resets_then_ok)
    waits: list[float] = []
    assert fetch_with_retry("https://x", sleep=waits.append) == {"ok": True}
    assert waits == [2, 8]
