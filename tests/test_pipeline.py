from dataclasses import replace

import numpy as np

from stockthing.config import Config
from stockthing.data import synthetic_prices
from stockthing.evaluation import backtest, backtest_table, forecast_metrics
from stockthing.pipeline import build_universe, forecast, load_bundle, save_bundle, train_final, walk_forward


def quick_cfg(**kw):
    base = replace(Config(context=False), seq_len=20, hidden=16, max_epochs=6, patience=2, folds=2,
                   fold_days=150, gbm_iter=40)
    return replace(base, **kw)


def test_end_to_end_walk_forward_train_save_load_forecast(tmp_path):
    prices = {"AAA": synthetic_prices(1300, seed=11), "BBB": synthetic_prices(1200, seed=12)}
    cfg = quick_cfg(models=("mlp", "tcn", "gru", "linear", "gbm"))
    uni = build_universe(prices, cfg)

    pred = walk_forward(uni, cfg)
    assert set(pred["model"]) == {"baseline", "mlp", "tcn", "gru", "linear", "gbm", "ensemble"}
    assert set(pred["ticker"]) == {"AAA", "BBB"}
    assert (pred["q10"] <= pred["q50"]).all() and (pred["q50"] <= pred["q90"]).all()
    metrics = forecast_metrics(pred, cfg.quantiles)
    assert len(metrics) == 7 * len(cfg.horizons)
    assert metrics["hit_rate"].between(0, 1).all()
    bt = backtest_table(pred, cfg.cost_bps)
    assert {"buy_hold", "long_flat", "long_short"} <= set(bt["strategy"])

    bundle = train_final(uni, cfg)
    loaded = load_bundle(save_bundle(bundle, tmp_path / "bundle"))
    f1, f2 = forecast(bundle, uni), forecast(loaded, uni)
    np.testing.assert_allclose(f1["p_up"], f2["p_up"], rtol=1e-5, atol=1e-6)
    assert len(f1) == 2 * len(cfg.horizons) * 7
    assert (f1["price_q10"] <= f1["price_q50"]).all() and (f1["price_q50"] <= f1["price_q90"]).all()


def test_backtest_accounting():
    import pandas as pd

    dates = pd.bdate_range("2021-01-01", periods=4).values
    pred = pd.DataFrame({"model": "m", "horizon": 1, "ticker": "X", "date": dates,
                         "p_up": [0.9, 0.9, 0.1, 0.9], "next_ret": np.log([1.01, 1.02, 0.97, 1.01])})
    stats, daily = backtest(pred, "m", 1, "long_flat", cost_bps=10)
    expected = np.array([0.01 - 0.001, 0.02, -0.001, 0.01 - 0.001])  # entry, hold, exit, re-entry
    np.testing.assert_allclose(daily["pnl"].to_numpy(), expected, atol=1e-12)
    assert stats["exposure"] == 0.75


def test_no_skill_on_an_unpredictable_series():
    """Look-ahead leaks show up as impossible accuracy on a pure random walk."""
    prices = {"RW": synthetic_prices(2400, seed=5, ar=0.0)}
    cfg = quick_cfg(models=("gbm", "linear", "mlp"), horizons=(1, 5), fold_days=400)
    m = forecast_metrics(walk_forward(build_universe(prices, cfg), cfg), cfg.quantiles)
    assert (m["z"] < 4).all(), m
    assert m["auc"].between(0.4, 0.6).all(), m


def test_finds_a_planted_signal():
    """AR(1) returns with phi=0.3: the best possible hit rate is ~59.7%."""
    prices = {"AR": synthetic_prices(2400, seed=6, ar=0.3)}
    cfg = quick_cfg(models=("linear", "gbm"), horizons=(1,), fold_days=400)
    m = forecast_metrics(walk_forward(build_universe(prices, cfg), cfg), cfg.quantiles).set_index("model")
    assert m.loc["linear", "hit_rate"] > 0.55 and m.loc["linear", "z"] > 2.5, m
    assert m.loc["gbm", "z"] > 2 and m.loc["gbm", "auc"] > 0.55, m
    assert m.loc["ensemble", "auc"] > 0.55, m
    assert m.loc["baseline", "z"] == 0, m
