"""Re-validate the tier strategy against the live API's 4y history.

Imports the same classify() the daily monitor runs, so the strategy under
test is the strategy that runs daily.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from dca_monitor import API, classify, fetch_with_retry


@dataclass(frozen=True)
class Result:
    invested: float
    btc: float

    @property
    def avg_cost(self) -> float:
        return self.invested / self.btc if self.btc else 0.0


def simulate(
    rows: list[tuple[float, float, float]], base: float = 10.0, uniform: bool = False
) -> Result:
    invested = btc = 0.0
    for mvrv, sth, price in rows:
        amount = base if uniform else base * classify(mvrv, sth).multiplier
        invested += amount
        btc += amount / price
    return Result(invested, btc)


def load_rows() -> list[tuple[float, float, float]]:
    mvrv_raw = fetch_with_retry(f"{API}/mvrv")
    sth_raw = fetch_with_retry(f"{API}/sth-mvrv")
    price_raw = fetch_with_retry(f"{API}/btc-price")
    assert isinstance(mvrv_raw, list) and isinstance(sth_raw, list) and isinstance(price_raw, list)
    mvrv_list: list[dict[str, Any]] = cast(list[dict[str, Any]], mvrv_raw)
    sth_list: list[dict[str, Any]] = cast(list[dict[str, Any]], sth_raw)
    price_list: list[dict[str, Any]] = cast(list[dict[str, Any]], price_raw)
    mvrv = {r["d"]: float(r["mvrv"]) for r in mvrv_list}
    sth = {r["d"]: float(r["sthMvrv"]) for r in sth_list}
    price = {r["d"]: float(r["btcPrice"]) for r in price_list}
    dates = sorted(mvrv.keys() & sth.keys() & price.keys())
    return [(mvrv[d], sth[d], price[d]) for d in dates]


def main() -> None:
    rows = load_rows()
    uni = simulate(rows, uniform=True)
    strat = simulate(rows)
    edge = (uni.avg_cost - strat.avg_cost) / uni.avg_cost * 100
    print(f"window: {len(rows)} days (bitcoin-data.com free history)")
    print(f"{'':10s}{'invested':>12s}{'btc':>12s}{'avg cost':>12s}")
    print(f"{'uniform':10s}{uni.invested:12,.0f}{uni.btc:12.4f}{uni.avg_cost:12,.0f}")
    print(f"{'strategy':10s}{strat.invested:12,.0f}{strat.btc:12.4f}{strat.avg_cost:12,.0f}")
    print(f"avg-cost edge vs uniform: {edge:+.1f}%")


if __name__ == "__main__":
    main()
