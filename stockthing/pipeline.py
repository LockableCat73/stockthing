"""End-to-end orchestration: data -> features -> walk-forward evaluation ->
final training -> forecast, plus saving / loading trained model bundles."""

from __future__ import annotations

import json
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from . import __version__
from .config import Config
from .data import load_context, load_prices
from .dataset import FeatureScaler, Fold, Panel, TickerData, build_ticker_frames, final_fold, finalize, \
    select_feature_columns, walk_forward_folds
from .evaluation import qname
from .training import FitContext, Forecaster, load_forecaster, make_forecaster


def _noop(*_a, **_k):
    pass


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #


@dataclass
class Universe:
    items: list[TickerData]
    prices: dict[str, pd.DataFrame]
    context: dict[str, pd.DataFrame] | None
    feature_names: list[str] = field(default_factory=list)


def build_universe(prices: dict[str, pd.DataFrame], cfg: Config, context: dict | None = None,
                   feature_names: list[str] | None = None) -> Universe:
    """Feature frames for already-loaded price data (useful for CSV / synthetic input)."""
    frames = [build_ticker_frames(t, df, context if cfg.context else None, cfg.horizons) for t, df in prices.items()]
    cols = feature_names or select_feature_columns(frames)
    items = []
    for fr in frames:
        missing = [c for c in cols if c not in fr["features"]]
        if missing:
            raise ValueError(f"{fr['ticker']}: features required by the model are unavailable: {missing[:5]}")
        it = finalize(fr, cols, min_rows=cfg.seq_len + 100)
        if it is not None:
            items.append(it)
    if not items:
        raise ValueError("no ticker has enough history")
    return Universe(items, prices, context, cols)


def load_universe(tickers: list[str], cfg: Config, refresh: bool = False, log=_noop,
                  feature_names: list[str] | None = None) -> Universe:
    context = load_context(refresh=refresh) if cfg.context else None
    if context is not None:
        log(f"market context: {', '.join(context) or 'none available'}")
    prices = {}
    for t in tickers:
        df = load_prices(t, cfg.start, cfg.end, refresh=refresh)
        name = Path(t).stem.upper() if t.lower().endswith(".csv") else t.upper()
        prices[name] = df
        log(f"{name}: {len(df)} bars {df.index[0].date()} -> {df.index[-1].date()}, last close {df['close'].iloc[-1]:.2f}")
    uni = build_universe(prices, cfg, context, feature_names)
    log(f"features: {len(uni.feature_names)} per bar, {sum(len(i.dates) for i in uni.items)} usable bars")
    return uni


# --------------------------------------------------------------------------- #
# fitting / predicting
# --------------------------------------------------------------------------- #


def fit_models(panel: Panel, fold: Fold, cfg: Config, log=_noop, seed_offset: int = 0):
    scaler = FeatureScaler().fit(panel.X_raw[panel.row_date < fold.scaler_end])
    ctx = FitContext(panel, torch.from_numpy(scaler.transform(panel.X_raw)), cfg)
    models: dict[str, Forecaster] = {}
    for i, name in enumerate(("baseline",) + tuple(m for m in cfg.models if m != "baseline")):
        t0 = time.time()
        fc = make_forecaster(name, cfg)
        note = fc.fit(ctx, fold, seed=cfg.seed + 1000 * i + seed_offset)
        models[name] = fc
        log(f"    {name:<12} {time.time() - t0:6.1f}s  {note}")
    return models, scaler, ctx


def predict_models(models: dict[str, Forecaster], ctx: FitContext, idx: np.ndarray) -> dict:
    out = {name: fc.predict(ctx, idx) for name, fc in models.items()}
    members = [n for n in out if n != "baseline"]
    if len(members) > 1:
        out["ensemble"] = (np.mean([out[n][0] for n in members], 0), np.mean([out[n][1] for n in members], 0))
    return out


def predictions_frame(panel: Panel, idx: np.ndarray, outputs: dict, cfg: Config, fold: int = -1) -> pd.DataFrame:
    """Long table: one row per (model, ticker, date, horizon) with quantiles in log-return units."""
    scale = panel.sigma[idx][:, None] * np.sqrt(panel.horizons)[None, :]
    tickers = np.asarray(panel.tickers, dtype=object)[panel.tick[idx]]
    frames = []
    for name, (q, p) in outputs.items():
        for j, h in enumerate(panel.horizons):
            d = {"model": name, "ticker": tickers, "date": panel.date[idx], "horizon": int(h), "fold": fold}
            for k, tau in enumerate(cfg.quantiles):
                d[qname(tau)] = q[:, j, k] * scale[:, j]
            d["p_up"] = p[:, j]
            d["actual"] = panel.fwd[idx, j]
            d["next_ret"] = panel.next_ret[idx]
            d["close"] = panel.close[idx]
            d["sigma"] = panel.sigma[idx]
            frames.append(pd.DataFrame(d))
    return pd.concat(frames, ignore_index=True)


def walk_forward(uni: Universe, cfg: Config, log=_noop) -> pd.DataFrame:
    """Out-of-sample predictions from an expanding-window walk-forward test."""
    panel = Panel(uni.items, cfg.seq_len, cfg.horizons)
    folds = walk_forward_folds(panel, cfg.folds, cfg.fold_days, cfg.val_frac)
    frames = []
    for k, fold in enumerate(folds):
        end = "end" if fold.test_end is None else str(fold.test_end)[:10]
        log(f"  fold {k + 1}/{len(folds)}: train {len(fold.train_idx)} / val {len(fold.val_idx)} samples, "
            f"test {str(fold.test_start)[:10]} -> {end} ({len(fold.test_idx)} samples)")
        models, _, ctx = fit_models(panel, fold, cfg, log, seed_offset=k)
        frames.append(predictions_frame(panel, fold.test_idx, predict_models(models, ctx, fold.test_idx), cfg, k))
    return pd.concat(frames, ignore_index=True)


@dataclass
class Bundle:
    cfg: Config
    models: dict[str, Forecaster]
    scaler: FeatureScaler
    feature_names: list[str]
    meta: dict


def train_final(uni: Universe, cfg: Config, log=_noop) -> Bundle:
    """Fit every model on all available history (recent slice held out for early stopping)."""
    panel = Panel(uni.items, cfg.seq_len, cfg.horizons)
    fold = final_fold(panel, cfg.val_frac)
    log(f"  final fit: train {len(fold.train_idx)} / val {len(fold.val_idx)} samples")
    models, scaler, _ = fit_models(panel, fold, cfg, log, seed_offset=99)
    meta = {
        "version": __version__,
        "tickers": panel.tickers,
        "trained_through": str(np.max(panel.date))[:10],
        "created": pd.Timestamp.now().isoformat(timespec="seconds"),
    }
    return Bundle(cfg, models, scaler, uni.feature_names, meta)


def forecast(bundle: Bundle, uni: Universe) -> pd.DataFrame:
    """Forecast from the latest bar of every ticker in ``uni``."""
    cfg = bundle.cfg
    panel = Panel(uni.items, cfg.seq_len, cfg.horizons)
    ctx = FitContext(panel, torch.from_numpy(bundle.scaler.transform(panel.X_raw)), cfg)
    idx = panel.latest()
    df = predictions_frame(panel, idx, predict_models(bundle.models, ctx, idx), cfg)
    for tau in cfg.quantiles:  # quantiles as price levels
        df[f"price_{qname(tau)}"] = df["close"] * np.exp(df[qname(tau)])
    return df.drop(columns=["actual", "next_ret", "fold"])


# --------------------------------------------------------------------------- #
# persistence
# --------------------------------------------------------------------------- #


def save_bundle(bundle: Bundle, path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    info = {"config": bundle.cfg.to_dict(), "features": bundle.feature_names, "models": list(bundle.models),
            **bundle.meta}
    (path / "bundle.json").write_text(json.dumps(info, indent=2))
    np.savez(path / "scaler.npz", **bundle.scaler.state())
    for name, fc in bundle.models.items():
        fc.save(path / name)
    return path


def load_bundle(path: str | Path) -> Bundle:
    path = Path(path)
    info = json.loads((path / "bundle.json").read_text())
    cfg = Config.from_dict(info["config"])
    scaler = FeatureScaler.from_state(np.load(path / "scaler.npz"))
    n_features = len(info["features"])
    models = {name: load_forecaster(name, path / name, cfg, n_features) for name in info["models"]}
    meta = {k: v for k, v in info.items() if k not in ("config", "features", "models")}
    if meta.get("version") != __version__:
        warnings.warn(f"bundle was saved by stockthing {meta.get('version')}, running {__version__}")
    return Bundle(cfg, models, scaler, info["features"], meta)
