from dca_monitor import (
    Context,
    build_discord,
    build_error_discord,
    build_error_telegram,
    build_telegram,
    classify,
    sheet_row,
)

CTX = Context(
    data_date="2026-07-21",
    price=66403.0,
    base_amount=10.0,
    currency="USD",
    amount=18.75,
    mvrv_percentile=18.0,
    tier_changed=False,
    prev_tier="BUY MORE",
)
SIG = classify(1.27, 0.98)


def test_discord_headline_leads_with_decision():
    embed = build_discord(SIG, CTX)["embeds"][0]
    assert embed["title"] == "BUY MORE — 18.75 USD today (1.88× base)"
    assert embed["color"] == 0x2ECC71


def test_discord_description_explains_both_indicators():
    desc = build_discord(SIG, CTX)["embeds"][0]["description"]
    assert "MVRV 1.27" in desc and "×1.5" in desc
    assert "STH-MVRV 0.98" in desc and "×1.25" in desc


def test_discord_fields_and_footer():
    embed = build_discord(SIG, CTX)["embeds"][0]
    names = [f["name"] for f in embed["fields"]]
    assert names == ["BTC Price", "MVRV 4y pctile", "Tier change"]
    values = [f["value"] for f in embed["fields"]]
    assert values == ["$66,403", "18%", "—"]
    assert embed["footer"]["text"] == "Data 2026-07-21 · bitcoin-data.com"


def test_discord_tier_change_shown():
    ctx = Context(
        data_date=CTX.data_date,
        price=CTX.price,
        base_amount=CTX.base_amount,
        currency=CTX.currency,
        amount=CTX.amount,
        mvrv_percentile=CTX.mvrv_percentile,
        tier_changed=True,
        prev_tier="DCA NORMAL",
    )
    embed = build_discord(SIG, ctx)["embeds"][0]
    assert embed["fields"][2]["value"] == "from DCA NORMAL"


def test_discord_stop_tier():
    sig = classify(2.7, 1.2)
    ctx = Context(
        data_date=CTX.data_date,
        price=CTX.price,
        base_amount=CTX.base_amount,
        currency=CTX.currency,
        amount=0.0,
        mvrv_percentile=CTX.mvrv_percentile,
        tier_changed=CTX.tier_changed,
        prev_tier=CTX.prev_tier,
    )
    embed = build_discord(sig, ctx)["embeds"][0]
    assert embed["title"] == "STOP — no buy today (0× base)"
    assert embed["color"] == 0xE74C3C


def test_discord_limits():
    embed = build_discord(SIG, CTX)["embeds"][0]
    assert len(embed["title"]) <= 256
    assert len(embed["description"]) <= 4096
    assert all(len(f["value"]) <= 1024 for f in embed["fields"])


def test_telegram_structure():
    text = build_telegram(SIG, CTX)
    assert text.startswith("<b>BUY MORE — 18.75 USD today</b> (1.88× base)")
    assert "<code>1.27</code>" in text and "<code>0.98</code>" in text
    assert "<i>Data 2026-07-21 · bitcoin-data.com</i>" in text
    assert "Tier change" not in text
    assert len(text) <= 4096


def test_telegram_tier_change_line():
    ctx = Context(
        data_date=CTX.data_date,
        price=CTX.price,
        base_amount=CTX.base_amount,
        currency=CTX.currency,
        amount=CTX.amount,
        mvrv_percentile=CTX.mvrv_percentile,
        tier_changed=True,
        prev_tier="DCA NORMAL",
    )
    assert "Tier change: from DCA NORMAL" in build_telegram(SIG, ctx)


def test_error_builders_state_cause_and_recovery():
    reason = "bitcoin-data.com unreachable after 4 attempts."
    embed = build_error_discord(reason)["embeds"][0]
    assert embed["title"] == "DATA ERROR — no signal today"
    assert embed["color"] == 0x95A5A6
    assert reason in embed["description"]
    assert "retry tomorrow" in embed["description"]
    text = build_error_telegram(reason)
    assert reason in text and "retry tomorrow" in text


def test_error_builders_clamp_long_reason():
    reason = "x" * 5000
    desc = build_error_discord(reason)["embeds"][0]["description"]
    assert len(desc) <= 4096
    text = build_error_telegram(reason)
    assert len(text) <= 4096


def test_error_builders_clamp_escapable_reason():
    reason = "&" * 5000  # html-escapes to 5x length
    assert len(build_error_discord(reason)["embeds"][0]["description"]) <= 4096
    assert len(build_error_telegram(reason)) <= 4096


def test_sheet_row():
    row = sheet_row(SIG, CTX)
    assert row == {
        "date": "2026-07-21",
        "price": 66403.0,
        "mvrv": 1.27,
        "sth_mvrv": 0.98,
        "tier": "BUY MORE",
        "multiplier": 1.875,
        "amount": 18.75,
    }
