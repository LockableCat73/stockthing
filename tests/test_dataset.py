import numpy as np
import pytest

from stockthing.config import Config
from stockthing.data import OHLCV, read_price_csv, synthetic_prices
from stockthing.dataset import FeatureScaler, Panel, walk_forward_folds
from stockthing.pipeline import build_universe


def make_panel(n_tickers=2, seq_len=20, horizons=(1, 5, 20)):
    prices = {f"S{i}": synthetic_prices(900 + 60 * i, seed=i) for i in range(n_tickers)}
    cfg = Config(context=False, seq_len=seq_len, horizons=horizons)
    uni = build_universe(prices, cfg)
    return Panel(uni.items, seq_len, horizons)


def test_windows_end_at_the_sample_bar_and_stay_inside_one_ticker():
    panel = make_panel()
    rows = panel.window_rows(np.arange(len(panel)))
    assert rows.shape == (len(panel), panel.seq_len)
    assert (rows[:, -1] == panel.row).all()
    ticker_of_row = np.concatenate([np.full(len(it.dates), k) for k, it in enumerate(panel.items)])
    assert (ticker_of_row[rows] == panel.tick[:, None]).all()


def test_targets_are_forward_log_returns():
    panel = make_panel(1, horizons=(1, 5))
    it = panel.items[0]
    for i in (0, 100, 400):
        p = panel.pos[i]
        assert panel.fwd[i, 0] == pytest.approx(np.log(it.close[p + 1] / it.close[p]))
        assert panel.fwd[i, 1] == pytest.approx(np.log(it.close[p + 5] / it.close[p]))
    assert np.isnan(panel.fwd[-1]).all()  # the future of the last bar is unknown
    assert np.isfinite(panel.fwd[-2, 0]) and np.isnan(panel.fwd[-2, 1])


def _target_end_dates(panel, idx, h):
    return np.array([panel.items[k].dates[p + h] for k, p in zip(panel.tick[idx], panel.pos[idx])])


def test_walk_forward_is_chronological_and_purged():
    panel = make_panel(2)
    folds = walk_forward_folds(panel, n_folds=2, fold_days=100, val_frac=0.2, min_train_days=300)
    assert len(folds) == 2
    for f in folds:
        val_start = f.scaler_end
        assert panel.date[f.train_idx].max() < val_start <= panel.date[f.val_idx].min()
        assert panel.date[f.val_idx].max() < f.test_start <= panel.date[f.test_idx].min()
        for j, h in enumerate(panel.horizons):
            tr = f.train_idx[f.train_mask[:, j]]
            va = f.val_idx[f.val_mask[:, j]]
            # no training label may be realised inside validation, no validation label inside test
            assert (_target_end_dates(panel, tr, h) < val_start).all()
            assert (_target_end_dates(panel, va, h) < f.test_start).all()
    # test blocks are consecutive and do not overlap
    assert folds[0].test_end == folds[1].test_start
    assert len(np.intersect1d(folds[0].test_idx, folds[1].test_idx)) == 0


def test_scaler_uses_only_the_rows_it_is_fit_on():
    rng = np.random.default_rng(0)
    train = rng.normal(0, 1, (500, 3))
    s = FeatureScaler().fit(train)
    z = s.transform(train)
    assert np.allclose(z.mean(0), 0, atol=0.05) and np.allclose(z.std(0), 1, atol=0.05)
    # extreme unseen values are clipped to the training range
    assert np.abs(s.transform(np.full((1, 3), 1e9))).max() < 5
    again = FeatureScaler.from_state(s.state())
    assert np.allclose(again.transform(train), z)


def test_read_yahoo_style_csv(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("Date,Open,High,Low,Close,Adj Close,Volume\n"
                   "2020-01-02,10,11,9,10.5,10.0,100\n"
                   "2020-01-03,10.5,10.4,10,10.2,9.8,200\n")
    df = read_price_csv(csv)
    assert list(df.columns) == OHLCV
    assert df["close"].iloc[0] == pytest.approx(10.0)  # dividend-adjusted
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    assert (df["low"] <= df[["open", "close"]].min(axis=1)).all()
