import pytest

from dca_monitor import API, fetch_indicators

FAKE = {
    f"{API}/mvrv": [
        {"d": "2026-07-19", "unixTs": 1, "mvrv": 1.30},
        {"d": "2026-07-20", "unixTs": 2, "mvrv": 1.55},
        {"d": "2026-07-21", "unixTs": 3, "mvrv": 1.27},
    ],
    f"{API}/sth-mvrv": [
        {"d": "2026-07-19", "unixTs": 1, "sthMvrv": 0.90},
        {"d": "2026-07-20", "unixTs": 2, "sthMvrv": 1.02},
        {"d": "2026-07-21", "unixTs": 3, "sthMvrv": 0.98},
    ],
    f"{API}/btc-price": [
        {"d": "2026-07-20", "unixTs": 2, "btcPrice": "67000.0"},
        {"d": "2026-07-21", "unixTs": 3, "btcPrice": "66403.096"},
    ],
}


def test_fetch_indicators_maps_latest_and_previous():
    md = fetch_indicators(fetch=FAKE.__getitem__)
    assert md.mvrv == 1.27
    assert md.prev_mvrv == 1.55
    assert md.sth_mvrv == 0.98
    assert md.prev_sth == 1.02
    assert md.price == 66403.096
    assert md.data_date == "2026-07-21"
    assert md.mvrv_history == [1.30, 1.55, 1.27]


def test_fetch_indicators_rejects_short_history():
    short = dict(FAKE)
    short[f"{API}/mvrv"] = [{"d": "2026-07-21", "unixTs": 3, "mvrv": 1.27}]
    with pytest.raises(ValueError, match="history too short"):
        fetch_indicators(fetch=short.__getitem__)
