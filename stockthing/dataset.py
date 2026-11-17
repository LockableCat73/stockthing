"""Turning per-ticker feature frames into model-ready samples.

A *sample* is (ticker, bar t): the input is the window of scaled features for
bars ``t-L+1 .. t`` and the targets are the forward log returns from the close
of ``t`` to the close of ``t+h`` for every horizon ``h``. Several tickers can be
stacked into one :class:`Panel` for pooled training.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import WARMUP_BARS, compute_features, daily_vol, forward_returns


@dataclass
class TickerData:
    ticker: str
    dates: np.ndarray          # (T,) datetime64[ns]
    features: pd.DataFrame     # (T, d) unscaled features
    close: np.ndarray          # (T,)
    fwd: np.ndarray            # (T, H) forward log returns, NaN where not yet known
    sigma: np.ndarray          # (T,) daily vol estimate known at t
    next_ret: np.ndarray       # (T,) next-day log return (for backtests)


def build_ticker_frames(ticker: str, prices: pd.DataFrame, context: dict | None, horizons) -> dict:
    feats = compute_features(prices, context)
    return {
        "ticker": ticker,
        "prices": prices,
        "features": feats,
        "fwd": forward_returns(prices["close"], horizons),
        "sigma": daily_vol(prices["close"]),
        "next_ret": forward_returns(prices["close"], [1])[1],
    }


def select_feature_columns(frames: list[dict], max_nan_frac: float = 0.02) -> list[str]:
    """Columns that exist (and are mostly populated after warm-up) for every ticker."""
    keep = None
    for fr in frames:
        feats = fr["features"].iloc[WARMUP_BARS:]
        if feats.empty:
            continue
        ok = set(feats.columns[feats.isna().mean() <= max_nan_frac])
        keep = ok if keep is None else keep & ok
    if not keep:
        raise ValueError("no usable feature columns (not enough history?)")
    order = list(frames[0]["features"].columns)
    return [c for c in order if c in keep]


def finalize(frame: dict, columns: list[str], min_rows: int = 0) -> TickerData | None:
    """Select columns, drop the indicator warm-up period, forward-fill stray gaps."""
    feats = frame["features"].reindex(columns=columns)
    complete = feats.notna().all(axis=1).to_numpy()
    if not complete.any():
        return None
    first = int(np.argmax(complete))
    feats = feats.iloc[first:].ffill().fillna(0.0)
    if len(feats) < min_rows:
        warnings.warn(f"{frame['ticker']}: only {len(feats)} usable bars, skipping")
        return None
    idx = feats.index
    return TickerData(
        ticker=frame["ticker"],
        dates=pd.DatetimeIndex(idx).values.astype("datetime64[ns]"),
        features=feats,
        close=frame["prices"]["close"].reindex(idx).to_numpy(float),
        fwd=frame["fwd"].reindex(idx).to_numpy(float),
        sigma=frame["sigma"].reindex(idx).to_numpy(float),
        next_ret=frame["next_ret"].reindex(idx).to_numpy(float),
    )


class FeatureScaler:
    """Winsorise at the 0.5 / 99.5 percentiles then standardise. Fit on training rows only."""

    def __init__(self, lo=None, hi=None, mean=None, std=None):
        self.lo, self.hi, self.mean, self.std = lo, hi, mean, std

    def fit(self, X: np.ndarray) -> "FeatureScaler":
        self.lo, self.hi = np.nanpercentile(X, [0.5, 99.5], axis=0)
        Xc = np.clip(X, self.lo, self.hi)
        self.mean = np.nanmean(Xc, axis=0)
        self.std = np.nanstd(Xc, axis=0)
        self.std = np.where(self.std > 1e-12, self.std, 1.0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return ((np.clip(X, self.lo, self.hi) - self.mean) / self.std).astype(np.float32)

    def state(self) -> dict:
        return {"lo": self.lo, "hi": self.hi, "mean": self.mean, "std": self.std}

    @classmethod
    def from_state(cls, st) -> "FeatureScaler":
        return cls(*(np.asarray(st[k], dtype=float) for k in ("lo", "hi", "mean", "std")))


class Panel:
    """All tickers stacked row-wise; every bar with a full look-back window is a sample."""

    def __init__(self, items: list[TickerData], seq_len: int, horizons):
        if not items:
            raise ValueError("empty panel")
        self.items = items
        self.tickers = [it.ticker for it in items]
        self.seq_len = seq_len
        self.horizons = np.asarray(list(horizons), dtype=int)
        self.feature_names = list(items[0].features.columns)
        self.X_raw = np.concatenate([it.features.to_numpy(np.float64) for it in items])
        self.row_date = np.concatenate([it.dates for it in items])
        starts = np.cumsum([0] + [len(it.dates) for it in items])
        row, tick, pos = [], [], []
        for k, it in enumerate(items):
            p = np.arange(seq_len - 1, len(it.dates))
            row.append(starts[k] + p)
            tick.append(np.full(len(p), k))
            pos.append(p)
        self.row = np.concatenate(row)
        self.tick = np.concatenate(tick)
        self.pos = np.concatenate(pos)
        self.date = self.row_date[self.row]
        self.fwd = np.concatenate([it.fwd[p] for it, p in zip(items, pos)])
        self.sigma = np.concatenate([it.sigma[p] for it, p in zip(items, pos)])
        self.next_ret = np.concatenate([it.next_ret[p] for it, p in zip(items, pos)])
        self.close = np.concatenate([it.close[p] for it, p in zip(items, pos)])
        # vol-normalised targets: z = r / (sigma * sqrt(h))
        self.z = self.fwd / (self.sigma[:, None] * np.sqrt(self.horizons)[None, :])
        self.offsets = np.arange(-seq_len + 1, 1)

    def __len__(self) -> int:
        return len(self.row)

    # ------------------------------------------------------------------ splits
    def boundary_positions(self, date) -> np.ndarray:
        """Per ticker: index of the first bar on/after ``date``."""
        d = np.datetime64(date, "ns")
        return np.array([np.searchsorted(it.dates, d, side="left") for it in self.items])

    def target_mask(self, idx: np.ndarray, boundary=None) -> np.ndarray:
        """(len(idx), H) bool: target known *and* fully realised before ``boundary``.

        This purges training labels whose look-ahead window overlaps the
        following validation / test period.
        """
        known = ~np.isnan(self.fwd[idx])
        if boundary is None:
            return known
        bpos = self.boundary_positions(boundary)
        end = self.pos[idx][:, None] + self.horizons[None, :]
        return known & (end < bpos[self.tick[idx]][:, None])

    def where(self, start=None, end=None) -> np.ndarray:
        """Sample indices with ``start <= date < end``."""
        m = np.ones(len(self), dtype=bool)
        if start is not None:
            m &= self.date >= np.datetime64(start, "ns")
        if end is not None:
            m &= self.date < np.datetime64(end, "ns")
        return np.flatnonzero(m)

    def window_rows(self, idx: np.ndarray) -> np.ndarray:
        """(len(idx), L) row numbers into ``X_raw`` for each sample's window."""
        return self.row[idx][:, None] + self.offsets[None, :]

    def latest(self) -> np.ndarray:
        """Index of the most recent sample of every ticker."""
        return np.array([np.flatnonzero(self.tick == k)[-1] for k in range(len(self.items))])


@dataclass
class Fold:
    train_idx: np.ndarray
    train_mask: np.ndarray
    val_idx: np.ndarray
    val_mask: np.ndarray
    test_idx: np.ndarray
    scaler_end: np.datetime64     # scaler is fit on rows dated before this
    test_start: np.datetime64 | None
    test_end: np.datetime64 | None


def _split_train_val(panel: Panel, end, val_frac: float):
    """Chronological train / validation split of all samples dated before ``end``.

    Labels are purged so that no training target overlaps validation and no
    validation target overlaps whatever comes after ``end``.
    """
    pre = panel.where(end=end)
    dates = np.unique(panel.date[pre])
    if len(dates) < 50:
        raise ValueError("not enough history before the split point")
    v0 = dates[int(len(dates) * (1.0 - val_frac))]
    tr = pre[panel.date[pre] < v0]
    va = pre[panel.date[pre] >= v0]
    tr_m = panel.target_mask(tr, v0)
    va_m = panel.target_mask(va, end)
    tr, tr_m = tr[tr_m.any(1)], tr_m[tr_m.any(1)]
    va, va_m = va[va_m.any(1)], va_m[va_m.any(1)]
    return tr, tr_m, va, va_m, v0


def walk_forward_folds(panel: Panel, n_folds: int, fold_days: int, val_frac: float = 0.15,
                       min_train_days: int = 750) -> list[Fold]:
    """Expanding-window walk-forward: the last ``n_folds * fold_days`` trading
    days are split into consecutive test blocks; each block's models are
    trained only on data that precedes it."""
    all_dates = np.unique(panel.date)
    n_folds = max(1, n_folds)
    while n_folds > 1 and len(all_dates) - n_folds * fold_days < min_train_days:
        n_folds -= 1
    if len(all_dates) - n_folds * fold_days < min_train_days:
        fold_days = max(20, (len(all_dates) - min_train_days) // n_folds)
        if fold_days <= 20:
            raise ValueError(f"only {len(all_dates)} usable days; need more history for walk-forward testing")
    first_test = len(all_dates) - n_folds * fold_days
    folds = []
    for k in range(n_folds):
        t0 = all_dates[first_test + k * fold_days]
        t1 = all_dates[first_test + (k + 1) * fold_days] if k + 1 < n_folds else None
        tr, tr_m, va, va_m, v0 = _split_train_val(panel, t0, val_frac)
        folds.append(Fold(tr, tr_m, va, va_m, panel.where(t0, t1), scaler_end=v0, test_start=t0, test_end=t1))
    return folds


def final_fold(panel: Panel, val_frac: float = 0.15) -> Fold:
    """Train on everything (minus a recent validation slice for early stopping)."""
    tr, tr_m, va, va_m, v0 = _split_train_val(panel, None, val_frac)
    return Fold(tr, tr_m, va, va_m, np.array([], dtype=int), scaler_end=v0, test_start=None, test_end=None)
