import numpy as np
import pandas as pd
import pytest

from stockthing import indicators as ta
from stockthing.data import synthetic_prices
from stockthing.features import compute_features, indicator_snapshot


@pytest.fixture(scope="module")
def prices():
    return synthetic_prices(900, seed=3)


@pytest.fixture(scope="module")
def context():
    return {
        "spy": synthetic_prices(1000, seed=21, start="2009-11-02"),
        "vix": synthetic_prices(1000, seed=22, start="2009-11-02"),
        "tnx": synthetic_prices(1000, seed=23, start="2009-11-02"),
    }


@pytest.mark.parametrize("cut", [400, 650, 899])
def test_every_feature_is_causal(prices, context, cut):
    """A feature at bar t must not change when bars after t are removed."""
    full = compute_features(prices, context)
    part = compute_features(prices.iloc[:cut], context)
    np.testing.assert_allclose(part.iloc[-1].to_numpy(), full.iloc[cut - 1].to_numpy(),
                               rtol=1e-7, atol=1e-10, equal_nan=True)


def test_feature_matrix_is_rich_and_finite(prices, context):
    f = compute_features(prices, context)
    assert f.shape[1] >= 120
    tail = f.iloc[300:]
    assert np.isfinite(tail.to_numpy()).mean() > 0.99


def test_moving_averages_known_values():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    assert ta.sma(s, 3).iloc[-1] == pytest.approx(4.0)
    assert ta.wma(s, 3).iloc[-1] == pytest.approx((3 * 1 + 4 * 2 + 5 * 3) / 6)
    # span 3 -> alpha 0.5, recursive: 1, 1.5, 2.25, 3.125, 4.0625
    assert ta.ema(s, 3).iloc[-1] == pytest.approx(4.0625)
    assert np.isnan(ta.sma(s, 3).iloc[1])


def test_rsi_extremes():
    up = pd.Series(np.arange(1, 60, dtype=float))
    down = pd.Series(np.arange(60, 1, -1, dtype=float))
    assert (ta.rsi(up, 14).dropna() == 100).all()
    assert (ta.rsi(down, 14).dropna() == 0).all()
    assert (ta.rsi(pd.Series(np.ones(40)), 14).dropna() == 50).all()


def test_oscillator_ranges(prices):
    h, l, c, v = prices["high"], prices["low"], prices["close"], prices["volume"]
    k, d = ta.stochastic(h, l, c)
    assert k.dropna().between(0, 100).all() and d.dropna().between(0, 100).all()
    assert ta.williams_r(h, l, c).dropna().between(-100, 0).all()
    assert ta.mfi(h, l, c, v).dropna().between(0, 100).all()
    assert ta.cmf(h, l, c, v).dropna().between(-1, 1).all()
    assert ta.ultimate_oscillator(h, l, c).dropna().between(0, 100).all()
    up, dn = ta.aroon(h, l)
    assert up.dropna().between(0, 100).all() and dn.dropna().between(0, 100).all()
    pdi, mdi, adx = ta.adx(h, l, c)
    assert adx.dropna().between(0, 100).all()
    assert (ta.atr(h, l, c).dropna() > 0).all()
    _, upper, lower, _, _ = ta.bollinger(c)
    assert (upper.dropna() >= lower.dropna()).all()


def test_aroon_and_trend_followers_on_a_steady_uptrend():
    idx = pd.bdate_range("2020-01-01", periods=120)
    c = pd.Series(np.linspace(100, 160, 120), index=idx)
    h, l = c * 1.01, c * 0.99
    up, dn = ta.aroon(h, l, 25)
    assert up.iloc[-1] == 100 and dn.iloc[-1] == 0
    _, trend = ta.parabolic_sar(h, l)
    _, direction = ta.supertrend(h, l, c)
    assert trend.iloc[-1] == 1 and direction.iloc[-1] == 1
    slope, r2 = ta.linreg(np.log(c), 20)
    assert slope.iloc[-1] > 0 and r2.iloc[-1] > 0.99


def test_true_range_counts_gaps():
    c = pd.Series([10.0, 12.0])
    h = pd.Series([10.5, 12.5])
    l = pd.Series([9.5, 11.5])
    assert ta.true_range(h, l, c).iloc[1] == pytest.approx(12.5 - 10.0)


def test_snapshot_runs(prices):
    rows = indicator_snapshot(prices)
    assert len(rows) >= 10 and all(len(r) == 3 for r in rows)
