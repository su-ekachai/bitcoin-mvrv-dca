import pytest

from dca_monitor import TIER_LABELS, classify


@pytest.mark.parametrize(
    ("mvrv", "tier", "mult"),
    [
        (0.5, "very_cheap", 2.0),
        (0.999, "very_cheap", 2.0),
        (1.0, "cheap", 1.5),  # lower bound inclusive
        (1.499, "cheap", 1.5),
        (1.5, "normal", 1.0),
        (1.999, "normal", 1.0),
        (2.0, "expensive", 0.5),
        (2.499, "expensive", 0.5),
        (2.5, "very_expensive", 0.0),
        (5.88, "very_expensive", 0.0),
    ],
)
def test_mvrv_tiers(mvrv, tier, mult):
    s = classify(mvrv, 1.05)
    assert s.mvrv_tier == tier
    assert s.mvrv_mult == mult


@pytest.mark.parametrize(
    ("sth", "mult"),
    [
        (0.5, 1.5),
        (0.899, 1.5),
        (0.9, 1.25),
        (0.999, 1.25),
        (1.0, 1.0),
        (1.099, 1.0),
        (1.1, 0.5),
        (2.0, 0.5),
    ],
)
def test_sth_multiplier(sth, mult):
    assert classify(1.7, sth).sth_mult == mult


def test_combined_multiplier():
    s = classify(1.27, 0.98)
    assert s.multiplier == 1.5 * 1.25
    assert not s.stop


def test_stop_dominates_sth():
    s = classify(2.6, 0.5)  # never observed historically, but stop must win
    assert s.stop
    assert s.multiplier == 0.0


def test_labels_cover_all_tiers():
    assert set(TIER_LABELS) == {"very_cheap", "cheap", "normal", "expensive", "very_expensive"}
