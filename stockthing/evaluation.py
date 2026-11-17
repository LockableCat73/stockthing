"""Forecast-quality metrics and trading backtests on out-of-sample predictions."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def qname(tau: float) -> str:
    return f"q{int(round(tau * 100)):02d}"


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    if y.min() == y.max():
        return float("nan")
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(y, p))


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def forecast_metrics(pred: pd.DataFrame, quantiles, by=("model", "horizon")) -> pd.DataFrame:
    """Per model and horizon:

    * ``hit_rate``  - share of correct up/down calls (P(up) > 0.5 means "up")
    * ``always_up`` - hit rate of the trivial "always up" call (the bar to beat)
    * ``edge``      - hit_rate minus the best constant call
    * ``z``         - the edge in standard errors, using n/h effective samples
    * ``auc``       - ranking quality of P(up)
    * ``ic``        - Spearman correlation of predicted median vs realised return
    * ``r2_oos``    - out-of-sample R^2 of the median vs a zero forecast
    * ``coverage``  - share of outcomes inside the outer quantile band (target: q_hi - q_lo)
    """
    lo, mid, hi = qname(quantiles[0]), qname(0.5), qname(quantiles[-1])
    rows = []
    for key, g in pred.groupby(list(by), sort=False):
        g = g[np.isfinite(g["actual"].to_numpy())]
        if len(g) < 10:
            continue
        h = int(g["horizon"].iloc[0])
        y, p, m = g["actual"].to_numpy(), g["p_up"].to_numpy(), g[mid].to_numpy()
        up = y > 0
        n_eff = max(len(g) / h, 1.0)
        hit = float(np.mean((p > 0.5) == up))
        always = float(up.mean())
        best = max(always, 1.0 - always)
        rows.append({
            **dict(zip(by, key if isinstance(key, tuple) else (key,))),
            "n": len(g),
            "hit_rate": hit,
            "always_up": always,
            "edge": hit - best,
            "z": (hit - best) / np.sqrt(max(best * (1.0 - best), 1e-9) / n_eff),
            "auc": _auc(up, p),
            "ic": _spearman(m, y),
            "r2_oos": float(1.0 - np.sum((y - m) ** 2) / np.sum(y**2)),
            "coverage": float(np.mean((y >= g[lo].to_numpy()) & (y <= g[hi].to_numpy()))),
            "brier": float(np.mean((p - up) ** 2)),
            "mean_p_up": float(p.mean()),
        })
    return pd.DataFrame(rows)


def perf_stats(r: pd.Series, pos: pd.Series | None = None, turnover: pd.Series | None = None) -> dict:
    """Summary statistics of a daily simple-return series."""
    r = r.dropna()
    if len(r) < 2:
        return {}
    eq = (1.0 + r).cumprod()
    years = len(r) / TRADING_DAYS
    sd = r.std()
    downside = r[r < 0].std()
    out = {
        "total_return": float(eq.iloc[-1] - 1.0),
        "cagr": float(eq.iloc[-1] ** (1.0 / years) - 1.0) if eq.iloc[-1] > 0 else -1.0,
        "ann_vol": float(sd * np.sqrt(TRADING_DAYS)),
        "sharpe": float(r.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan"),
        "sortino": float(r.mean() / downside * np.sqrt(TRADING_DAYS)) if downside > 0 else float("nan"),
        "max_drawdown": float((eq / eq.cummax() - 1.0).min()),
        "days": int(len(r)),
    }
    if pos is not None:
        out["exposure"] = float(pos.abs().mean())
    if turnover is not None:
        out["trades_per_year"] = float(turnover.sum() / years)
    return out


def _positions(p_up: np.ndarray, mode: str, threshold: float = 0.0) -> np.ndarray:
    if mode == "buy_hold":
        return np.ones_like(p_up)
    long = p_up > 0.5 + threshold
    if mode == "long_flat":
        return long.astype(float)
    if mode == "long_short":
        return np.where(long, 1.0, np.where(p_up < 0.5 - threshold, -1.0, 0.0))
    raise ValueError(f"unknown strategy {mode!r}")


def backtest(pred: pd.DataFrame, model: str, horizon: int, mode: str = "long_flat", cost_bps: float = 5.0,
             threshold: float = 0.0):
    """Daily-rebalanced strategy driven by one model's P(up) at one horizon.

    The position decided at the close of day t earns the return from close t to
    close t+1, minus ``cost_bps`` per unit of position change. With several
    tickers, the portfolio is an equal-weight average of the per-ticker
    strategies. Returns ``(stats, daily_frame)``.
    """
    g = pred[(pred["model"] == model) & (pred["horizon"] == horizon)]
    g = g[np.isfinite(g["next_ret"].to_numpy())].sort_values(["ticker", "date"])
    if g.empty:
        return {}, pd.DataFrame()
    pos = pd.Series(_positions(g["p_up"].to_numpy(), mode, threshold), index=g.index)
    prev = pos.groupby(g["ticker"]).shift(1).fillna(0.0)
    turnover = (pos - prev).abs()
    pnl = pos * np.expm1(g["next_ret"]) - cost_bps / 1e4 * turnover
    daily = pd.DataFrame({"date": g["date"], "pnl": pnl, "pos": pos, "turnover": turnover})
    daily = daily.groupby("date").agg(pnl=("pnl", "mean"), pos=("pos", "mean"), turnover=("turnover", "mean"))
    daily["equity"] = (1.0 + daily["pnl"]).cumprod()
    return perf_stats(daily["pnl"], daily["pos"], daily["turnover"]), daily


def backtest_table(pred: pd.DataFrame, cost_bps: float = 5.0, modes=("long_flat", "long_short")) -> pd.DataFrame:
    """Backtest every (model, horizon) signal plus buy & hold over the same days."""
    rows = []
    models = [m for m in pred["model"].unique() if m != "baseline"]
    horizons = sorted(pred["horizon"].unique())
    stats, _ = backtest(pred, pred["model"].iloc[0], horizons[0], "buy_hold", cost_bps)
    rows.append({"model": "buy_and_hold", "horizon": None, "strategy": "buy_hold", **stats})
    for m in models:
        for h in horizons:
            for mode in modes:
                stats, _ = backtest(pred, m, h, mode, cost_bps)
                rows.append({"model": m, "horizon": h, "strategy": mode, **stats})
    return pd.DataFrame(rows)
