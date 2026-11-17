"""Command-line interface: ``python -m stockthing <command> TICKER ...``"""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from .config import DEFAULT_MODELS, Config
from .data import load_prices
from .evaluation import backtest_table, forecast_metrics, qname
from .features import indicator_snapshot


def log(msg: str = "") -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# formatting
# --------------------------------------------------------------------------- #


def table(rows: list[list[str]], headers: list[str], align: str | None = None) -> str:
    """Plain-text table. ``align`` is a string of 'l'/'r' per column."""
    cols = list(zip(*([headers] + rows))) if rows else [[h] for h in headers]
    widths = [max(len(str(x)) for x in c) for c in cols]
    align = align or "l" + "r" * (len(headers) - 1)

    def fmt(row):
        return "  ".join(str(x).ljust(w) if a == "l" else str(x).rjust(w) for x, w, a in zip(row, widths, align))

    return "\n".join([fmt(headers), "  ".join("-" * w for w in widths)] + [fmt(r) for r in rows])


def pct(x, digits=1, sign=False) -> str:
    if x is None or not np.isfinite(x):
        return "-"
    return f"{x * 100:+.{digits}f}%" if sign else f"{x * 100:.{digits}f}%"


def num(x, digits=2) -> str:
    return "-" if x is None or not np.isfinite(x) else f"{x:.{digits}f}"


def print_metrics(metrics: pd.DataFrame) -> None:
    rows = [[r.model, f"{r.horizon}d", r.n, pct(r.hit_rate), pct(r.always_up), pct(r.edge, sign=True), num(r.z, 1),
             num(r.auc, 3), num(r.ic, 3), num(r.r2_oos, 4), pct(r.coverage, 0)]
            for r in metrics.itertuples()]
    log(table(rows, ["model", "h", "n", "hit", "always-up", "edge", "z", "AUC", "IC", "R2oos", "cover"]))


def print_backtests(bt: pd.DataFrame, horizons=None) -> None:
    sel = bt if horizons is None else bt[bt["horizon"].isna() | bt["horizon"].isin(horizons)]
    rows = []
    for r in sel.itertuples():
        h = "-" if r.horizon is None or not np.isfinite(r.horizon) else f"{int(r.horizon)}d"
        rows.append([r.model, h, r.strategy, pct(r.total_return), pct(r.cagr), num(r.sharpe), pct(r.max_drawdown),
                     pct(getattr(r, "exposure", np.nan), 0), num(getattr(r, "trades_per_year", np.nan), 0)])
    log(table(rows, ["model", "signal", "strategy", "total", "CAGR", "Sharpe", "maxDD", "exposure", "trades/yr"],
              "lllrrrrrr"))


def print_forecast(fc: pd.DataFrame, cfg: Config, metrics: pd.DataFrame | None = None) -> None:
    lo, mid, hi = qname(cfg.quantiles[0]), qname(0.5), qname(cfg.quantiles[-1])
    band = f"{int(round(cfg.quantiles[0] * 100))}-{int(round(cfg.quantiles[-1] * 100))}% range"
    main = "ensemble" if "ensemble" in set(fc["model"]) else [m for m in fc["model"].unique() if m != "baseline"][0]
    for ticker, g in fc.groupby("ticker", sort=False):
        last_date = pd.Timestamp(g["date"].iloc[0])
        close = float(g["close"].iloc[0])
        log(f"\n{ticker}: last close {close:,.2f} on {last_date.date()}  (forecast by: {main})")
        base = {int(r.horizon): float(r.p_up) for r in g[g["model"] == "baseline"].itertuples()}
        rows = []
        for r in g[g["model"] == main].sort_values("horizon").itertuples():
            p = r.p_up
            hist = base.get(int(r.horizon), 0.5)
            view = "bullish" if p - hist >= 0.03 else "bearish" if p - hist <= -0.03 else "neutral"
            target = (last_date + pd.offsets.BDay(int(r.horizon))).date()
            track = "-"
            if metrics is not None:
                m = metrics[(metrics["model"] == main) & (metrics["horizon"] == r.horizon)]
                if len(m):
                    track = f"{pct(m['hit_rate'].iloc[0])} vs {pct(m['always_up'].iloc[0])}"
            rows.append([f"{int(r.horizon)}d", str(target), f"{getattr(r, 'price_' + mid):,.2f}",
                         f"{getattr(r, 'price_' + lo):,.2f} .. {getattr(r, 'price_' + hi):,.2f}",
                         pct(np.expm1(getattr(r, mid)), 2, sign=True), pct(p), pct(hist), view, track])
        log(table(rows, ["horizon", "~date", "median", band, "exp.ret", "P(up)", "hist.P(up)", "view",
                         "backtest hit vs always-up"], "llrrrrrll"))
        log("view = P(up) vs the historical up-rate for that horizon (needs a 3 pp gap to call it)")
        models = [m for m in g["model"].unique() if m not in ("ensemble",)]
        hs = sorted(g["horizon"].unique())
        rows = [[m] + [pct(float(g[(g["model"] == m) & (g["horizon"] == h)]["p_up"].iloc[0])) for h in hs]
                for m in models]
        log("P(up) by model:")
        log(table(rows, ["model"] + [f"{h}d" for h in hs]))


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def config_from_args(a) -> Config:
    cfg = Config()
    if a.quick:
        cfg = cfg.quick()
    overrides = {
        "start": a.start, "end": a.end, "seq_len": a.seq_len, "hidden": a.hidden, "max_epochs": a.epochs,
        "patience": a.patience, "folds": a.folds, "fold_days": a.fold_days, "seeds": a.seeds,
        "cost_bps": a.cost_bps, "seed": a.seed, "lr": a.lr,
    }
    cfg = replace(cfg, **{k: v for k, v in overrides.items() if v is not None})
    if a.horizons:
        cfg = replace(cfg, horizons=tuple(sorted(set(a.horizons))))
    if a.models:
        bad = [m for m in a.models if m not in DEFAULT_MODELS]
        if bad:
            raise SystemExit(f"unknown model(s) {bad}; choose from {list(DEFAULT_MODELS)}")
        cfg = replace(cfg, models=tuple(a.models))
    if a.no_context:
        cfg = replace(cfg, context=False)
    return cfg


def _run_dir(a, tickers) -> Path:
    if a.out:
        return Path(a.out)
    name = "_".join(Path(t).stem.upper().replace("^", "") for t in tickers[:4]) + ("_etc" if len(tickers) > 4 else "")
    return Path("runs") / f"{name}_{pd.Timestamp.now():%Y%m%d_%H%M%S}"


def cmd_fetch(a) -> None:
    rows = []
    for t in a.tickers:
        df = load_prices(t, refresh=a.refresh)
        rows.append([t.upper(), len(df), str(df.index[0].date()), str(df.index[-1].date()), f"{df['close'].iloc[-1]:,.2f}"])
    log(table(rows, ["ticker", "bars", "first", "last", "last close"]))


def cmd_indicators(a) -> None:
    for t in a.tickers:
        df = load_prices(t, refresh=a.refresh)
        log(f"\n{t.upper()} - {df.index[-1].date()} close {df['close'].iloc[-1]:,.2f}")
        log(table([list(r) for r in indicator_snapshot(df)], ["indicator", "value", "reading"], "lrl"))


def _evaluate(a, cfg, uni, out: Path):
    from .pipeline import walk_forward

    log(f"\nwalk-forward test: {cfg.folds} folds x {cfg.fold_days} days, models: {', '.join(cfg.models)}")
    t0 = time.time()
    pred = walk_forward(uni, cfg, log)
    log(f"done in {time.time() - t0:.0f}s")
    metrics = forecast_metrics(pred, cfg.quantiles)
    bt = backtest_table(pred, cfg.cost_bps)
    out.mkdir(parents=True, exist_ok=True)
    pred.to_csv(out / "oos_predictions.csv", index=False)
    metrics.to_csv(out / "metrics.csv", index=False)
    bt.to_csv(out / "backtest.csv", index=False)
    log("\nOut-of-sample forecast quality (hit = direction accuracy; beat 'always-up' to have an edge):")
    print_metrics(metrics)
    log(f"\nBacktests on the same out-of-sample days (costs {cfg.cost_bps:g} bps per trade):")
    print_backtests(bt, horizons=[min(cfg.horizons)] if not a.all_backtests else None)
    if len(uni.items) > 1:
        per = forecast_metrics(pred[pred["model"] == "ensemble"], cfg.quantiles, by=("ticker", "horizon"))
        per.to_csv(out / "metrics_by_ticker.csv", index=False)
    return pred, metrics, bt


def cmd_backtest(a) -> None:
    from .pipeline import load_universe

    cfg = config_from_args(a)
    out = _run_dir(a, a.tickers)
    uni = load_universe(a.tickers, cfg, a.refresh, log)
    pred, metrics, bt = _evaluate(a, cfg, uni, out)
    if a.report:
        from .report import write_report

        path = write_report(out / "report.html", uni, cfg, pred, metrics, bt, None)
        log(f"\nreport: {path}")
    log(f"\nresults saved in {out}/")


def cmd_train(a) -> None:
    from .pipeline import load_universe, save_bundle, train_final

    cfg = config_from_args(a)
    out = Path(a.out) if a.out else Path("models") / "_".join(t.upper() for t in a.tickers[:4])
    uni = load_universe(a.tickers, cfg, a.refresh, log)
    log("\ntraining final models on all history")
    bundle = train_final(uni, cfg, log)
    save_bundle(bundle, out)
    log(f"saved model bundle to {out}/")


def cmd_predict(a) -> None:
    from .pipeline import forecast, load_bundle, load_universe, save_bundle, train_final

    model_dir = Path(a.model_dir) if a.model_dir else None
    if model_dir and (model_dir / "bundle.json").exists():
        bundle = load_bundle(model_dir)
        cfg = bundle.cfg
        log(f"loaded models from {model_dir} (trained through {bundle.meta.get('trained_through')})")
        uni = load_universe(a.tickers, cfg, a.refresh, log, feature_names=bundle.feature_names)
    else:
        cfg = config_from_args(a)
        uni = load_universe(a.tickers, cfg, a.refresh, log)
        log("\ntraining models on all history (pass --model-dir to reuse a saved bundle)")
        bundle = train_final(uni, cfg, log)
        if model_dir:
            save_bundle(bundle, model_dir)
            log(f"saved model bundle to {model_dir}/")
    fc = forecast(bundle, uni)
    print_forecast(fc, cfg)


def cmd_run(a) -> None:
    """Everything: walk-forward backtest, final training, forecast, HTML report."""
    from .pipeline import forecast, load_universe, save_bundle, train_final
    from .report import write_report

    cfg = config_from_args(a)
    out = _run_dir(a, a.tickers)
    uni = load_universe(a.tickers, cfg, a.refresh, log)
    pred, metrics, bt = _evaluate(a, cfg, uni, out)
    log("\ntraining final models on all history")
    bundle = train_final(uni, cfg, log)
    save_bundle(bundle, out / "models")
    fc = forecast(bundle, uni)
    fc.to_csv(out / "forecast.csv", index=False)
    print_forecast(fc, cfg, metrics)
    path = write_report(out / "report.html", uni, cfg, pred, metrics, bt, fc)
    log(f"\nreport: {path}\nresults and models saved in {out}/")
    log("\nNot financial advice: these are statistical estimates with wide error bars; check the backtest table "
        "before trusting any signal.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stockthing", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, models=True):
        sp.add_argument("tickers", nargs="+", help="Yahoo symbols (AAPL, SPY, ^GSPC, BTC-USD, ...) or CSV paths")
        sp.add_argument("--refresh", action="store_true", help="re-download data even if cached")
        if not models:
            return
        g = sp.add_argument_group("model / training")
        g.add_argument("--models", nargs="+", metavar="M", help=f"subset of {list(DEFAULT_MODELS)}")
        g.add_argument("--horizons", nargs="+", type=int, metavar="H", help="forecast horizons in trading days (default 1 5 20)")
        g.add_argument("--start", help="first date of history to use (default 2000-01-01)")
        g.add_argument("--end", help="last date of history to use (simulate an earlier 'today')")
        g.add_argument("--seq-len", type=int, help="look-back window in bars (default 60)")
        g.add_argument("--hidden", type=int, help="network width (default 64)")
        g.add_argument("--epochs", type=int, help="max epochs (default 40, early stopping)")
        g.add_argument("--patience", type=int, help="early-stopping patience (default 5)")
        g.add_argument("--lr", type=float, help="learning rate (default 1e-3)")
        g.add_argument("--seeds", type=int, help="networks per architecture to average (default 1)")
        g.add_argument("--folds", type=int, help="walk-forward folds (default 4)")
        g.add_argument("--fold-days", type=int, help="trading days per test fold (default 252)")
        g.add_argument("--cost-bps", type=float, help="trading cost per unit turnover in bps (default 5)")
        g.add_argument("--seed", type=int, help="random seed")
        g.add_argument("--no-context", action="store_true", help="skip S&P 500 / VIX / 10y-yield features")
        g.add_argument("--quick", action="store_true", help="small fast settings for a first look")
        g.add_argument("--threads", type=int, help="CPU threads for PyTorch")
        g.add_argument("--out", help="output directory")
        g.add_argument("--all-backtests", action="store_true", help="show backtests for every horizon")

    common(sub.add_parser("fetch", help="download and cache price history"), models=False)
    common(sub.add_parser("indicators", help="latest indicator readings"), models=False)
    sp = sub.add_parser("backtest", help="walk-forward out-of-sample evaluation")
    common(sp)
    sp.add_argument("--report", action="store_true", help="also write an HTML report")
    common(sub.add_parser("train", help="train on all history and save a model bundle"))
    sp = sub.add_parser("predict", help="forecast the next 1/5/20 days")
    common(sp)
    sp.add_argument("--model-dir", help="load (or save) a trained bundle here")
    common(sub.add_parser("run", help="backtest + train + forecast + HTML report"))
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if getattr(a, "threads", None):
        torch.set_num_threads(a.threads)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    {"fetch": cmd_fetch, "indicators": cmd_indicators, "backtest": cmd_backtest, "train": cmd_train,
     "predict": cmd_predict, "run": cmd_run}[a.command](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
