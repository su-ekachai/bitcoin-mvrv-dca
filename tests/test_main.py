import dca_monitor
from dca_monitor import MarketData, main

MD = MarketData(
    mvrv_history=[1.0, 1.55, 1.27],
    mvrv=1.27,
    prev_mvrv=1.55,
    sth_mvrv=0.98,
    prev_sth=1.02,
    price=66403.0,
    data_date="2026-07-21",
)


def test_main_happy_path(monkeypatch):
    captured = {}
    monkeypatch.setenv("BASE_AMOUNT", "20")
    monkeypatch.setenv("CURRENCY", "USD")
    monkeypatch.setattr(dca_monitor, "fetch_indicators", lambda: MD)

    def fake_notify(env, discord_payload, telegram_text, row):
        captured["discord"] = discord_payload
        captured["row"] = row
        return ["discord"]

    monkeypatch.setattr(dca_monitor, "notify_all", fake_notify)
    assert main() == 0
    # 1.27 -> cheap x1.5 (tier changed from normal at 1.55); 0.98 -> x1.25
    assert captured["row"]["amount"] == 37.5
    assert captured["row"]["tier"] == "BUY MORE"
    title = captured["discord"]["embeds"][0]["title"]
    assert title == "BUY MORE — 37.50 USD today (1.88× base)"
    assert captured["discord"]["embeds"][0]["fields"][2]["value"] == "from DCA NORMAL"


def test_main_fetch_failure_sends_error_alert_and_exits_1(monkeypatch):
    def dead():
        raise RuntimeError("fetch failed after 4 attempts: url")

    captured = {}
    monkeypatch.setattr(dca_monitor, "fetch_indicators", dead)

    def fake_notify(env, discord_payload, telegram_text, row):
        captured["discord"] = discord_payload
        captured["row"] = row
        return ["discord"]

    monkeypatch.setattr(dca_monitor, "notify_all", fake_notify)
    assert main() == 1
    assert captured["row"] is None
    assert captured["discord"]["embeds"][0]["title"] == "DATA ERROR — no signal today"


def test_main_error_alert_failure_still_exits_1(monkeypatch):
    monkeypatch.setattr(
        dca_monitor, "fetch_indicators", lambda: (_ for _ in ()).throw(OSError("x"))
    )

    def also_dead(*args):
        raise RuntimeError("all channels failed")

    monkeypatch.setattr(dca_monitor, "notify_all", also_dead)
    assert main() == 1


def test_main_tolerates_empty_env_vars(monkeypatch):
    captured = {}
    monkeypatch.setenv("BASE_AMOUNT", "")
    monkeypatch.setenv("CURRENCY", "")
    monkeypatch.setattr(dca_monitor, "fetch_indicators", lambda: MD)

    def fake_notify(env, discord_payload, telegram_text, row):
        captured["row"] = row
        return ["discord"]

    monkeypatch.setattr(dca_monitor, "notify_all", fake_notify)
    assert main() == 0
    assert captured["row"]["amount"] == 18.75  # base 10 x 1.875
