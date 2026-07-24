from backtest import simulate

# (mvrv, sth, price): cheap day, normal day, stop day
ROWS = [(0.8, 0.85, 100.0), (1.7, 1.05, 200.0), (2.6, 1.2, 400.0)]


def test_uniform_invests_base_every_day():
    r = simulate(ROWS, base=10.0, uniform=True)
    assert r.invested == 30.0
    assert r.btc == 10 / 100 + 10 / 200 + 10 / 400


def test_strategy_scales_and_stops():
    r = simulate(ROWS, base=10.0)
    # day1: 2.0*1.5=3.0 -> $30; day2: 1.0*1.0 -> $10; day3: stop -> $0
    assert r.invested == 40.0
    assert r.btc == 30 / 100 + 10 / 200


def test_avg_cost():
    r = simulate([(0.8, 0.85, 100.0)], base=10.0)
    assert r.avg_cost == 100.0
