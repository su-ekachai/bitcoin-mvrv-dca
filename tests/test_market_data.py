from typing import Any, cast

import pytest

from dca_monitor import MarketData, _series, percentile


def test_percentile_basic():
    assert percentile([1.0, 2.0, 3.0, 4.0], 2.0) == 50.0


def test_percentile_extremes():
    hist = [1.0, 2.0, 3.0]
    assert percentile(hist, 0.5) == 0.0
    assert percentile(hist, 3.0) == 100.0


def test_series_casts_strings():
    raw = [{"d": "2026-07-20", "btcPrice": "66000.5"}, {"d": "2026-07-21", "btcPrice": "66403.1"}]
    assert _series(raw, "btcPrice") == [66000.5, 66403.1]


def test_market_data_is_frozen():
    md = MarketData([1.0, 1.2], 1.2, 1.0, 0.98, 0.95, 66403.0, "2026-07-21")
    with pytest.raises(AttributeError):
        cast(Any, md).mvrv = 2.0
