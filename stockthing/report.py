"""Self-contained HTML report: forecast fan chart, out-of-sample track record,
scorecard and indicator snapshot. Charts are drawn client-side as SVG at the
container's real width (with hover / keyboard read-outs); every chart has a
table-view twin rendered server-side."""

from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config
from .evaluation import backtest, qname
from .features import indicator_snapshot

SHORT_LABELS = {"gbm": "Boosting", "baseline": "Baseline"}
MODEL_LABELS = {
    "ensemble": "Ensemble", "lstm": "LSTM", "gru": "GRU", "tcn": "TCN", "transformer": "Transformer",
    "mlp": "MLP", "gbm": "Gradient boosting", "linear": "Linear", "baseline": "No-skill baseline",
}
HISTORY_BARS = 126  # about six months of daily bars on the fan chart


def _e(x) -> str:
    return html.escape(str(x), quote=True)


def _label(m: str) -> str:
    return MODEL_LABELS.get(m, m)


def _pct(x, d=1, sign=False) -> str:
    if x is None or not np.isfinite(x):
        return "–"
    s = f"{abs(x) * 100:.{d}f}%"
    if sign:
        return ("+" if x >= 0 else "−") + s
    return ("−" if x < 0 else "") + s


def _pp(x, d=1) -> str:
    if x is None or not np.isfinite(x):
        return "–"
    return ("+" if x >= 0 else "−") + f"{abs(x) * 100:.{d}f} pp"


def _num(x, d=2) -> str:
    if x is None or not np.isfinite(x):
        return "–"
    return ("−" if x < 0 else "") + f"{abs(x):,.{d}f}"


def _price(x) -> str:
    return _num(x, 2)


def _date(d) -> str:
    t = pd.Timestamp(d)
    return f"{t:%b} {t.day}, {t.year}"


def _clean(obj):
    """Replace NaN / inf with None so the payload is valid JSON."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def _main_model(models) -> str:
    models = list(models)
    return "ensemble" if "ensemble" in models else next(m for m in models if m != "baseline")


# --------------------------------------------------------------------------- #
# data for the client-side charts
# --------------------------------------------------------------------------- #


def _forecast_data(uni, cfg: Config, fc: pd.DataFrame) -> list[dict]:
    lo, mid, hi = qname(cfg.quantiles[0]), qname(0.5), qname(cfg.quantiles[-1])
    main = _main_model(fc["model"].unique())
    out = []
    for ticker, g in fc.groupby("ticker", sort=False):
        base = {int(r.horizon): float(r.p_up) for r in g[g["model"] == "baseline"].itertuples()}
        prices = uni.prices[ticker]
        hist = prices["close"].iloc[-HISTORY_BARS:]
        last = pd.Timestamp(g["date"].iloc[0])
        rows = []
        for r in g[g["model"] == main].sort_values("horizon").itertuples():
            h = int(r.horizon)
            rows.append({
                "h": h, "date": str((last + pd.offsets.BDay(h)).date()),
                "lo": float(getattr(r, "price_" + lo)), "mid": float(getattr(r, "price_" + mid)),
                "hi": float(getattr(r, "price_" + hi)), "p_up": float(r.p_up), "base": base.get(h, 0.5),
                "ret": float(np.expm1(getattr(r, mid))),
            })
        future = [str(d.date()) for d in pd.bdate_range(last + pd.offsets.BDay(1), periods=max(cfg.horizons))]
        out.append({
            "ticker": ticker, "close": float(g["close"].iloc[0]), "last": str(last.date()),
            "dates": [str(d.date()) for d in hist.index] + future,
            "history": [round(float(v), 4) for v in hist.to_numpy()],
            "horizons": rows, "model": main,
        })
    return out


def _equity_data(pred: pd.DataFrame, cfg: Config) -> dict:
    main = _main_model(pred["model"].unique())
    out = {"model": main, "horizons": {}}
    for h in sorted(cfg.horizons):
        series = {}
        dates = None
        for mode in ("long_flat", "long_short", "buy_hold"):
            _, daily = backtest(pred, main, h, mode, cfg.cost_bps)
            if daily.empty:
                continue
            dates = [str(pd.Timestamp(d).date()) for d in daily.index]
            series[mode] = [round(float(v) - 1.0, 5) for v in daily["equity"].to_numpy()]
        if dates:
            out["horizons"][str(h)] = {"dates": dates, **series}
    return out


def _edge_data(metrics: pd.DataFrame) -> dict:
    out = {}
    for h, g in metrics.groupby("horizon", sort=True):
        rows = []
        for r in g.itertuples():
            if r.model == "baseline":
                continue
            rows.append({"model": SHORT_LABELS.get(r.model, _label(r.model)), "key": r.model, "edge": float(r.edge), "hit": float(r.hit_rate),
                         "always": float(r.always_up), "auc": float(r.auc) if np.isfinite(r.auc) else None,
                         "n": int(r.n)})
        out[str(int(h))] = rows
    return out


# --------------------------------------------------------------------------- #
# server-side HTML pieces
# --------------------------------------------------------------------------- #


def _table(headers, rows, cls="", num_from=1) -> str:
    th = "".join(f'<th scope="col"{" class=num" if i >= num_from else ""}>{_e(h)}</th>' for i, h in enumerate(headers))
    body = []
    for row in rows:
        cells = []
        for i, c in enumerate(row):
            raw = isinstance(c, tuple)  # (html, extra-class) for pre-rendered cells
            content = c[0] if raw else _e(c)
            klass = (c[1] if raw else "") + (" num" if i >= num_from else "")
            tag = "th scope=\"row\"" if i == 0 else "td"
            cells.append(f'<{tag} class="{klass.strip()}">{content}</{tag.split()[0]}>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="table-wrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _chip(text, tone) -> str:
    return f'<span class="chip {tone}">{_e(text)}</span>'


VIEW_BAND = 0.03  # P(up) must differ from the historical base rate by this much to count as a view


def _tone(p: float, base: float) -> str:
    return "pos" if p - base >= VIEW_BAND else "neg" if p - base <= -VIEW_BAND else "neutral"


def _view(p: float, base: float) -> str:
    return {"pos": "Bullish", "neg": "Bearish", "neutral": "Neutral"}[_tone(p, base)]


def _p_cell(p: float, base: float = 0.5) -> tuple:
    strength = min(abs(p - base) / 0.12, 1.0)  # tint grows with distance from the base rate
    side = "pos" if p >= base else "neg"
    return (f'<span class="pcell {side}" style="--w:{strength * 34:.0f}%">{_e(_pct(p))}</span>', "")


def _forecast_section(fd: dict, fc: pd.DataFrame, metrics: pd.DataFrame | None, cfg: Config, idx: int, uni,
                      multi: bool) -> str:
    ticker = fd["ticker"]
    heading = ticker if multi else f"Next {max(cfg.horizons)} trading days"
    lo_q, hi_q = int(round(cfg.quantiles[0] * 100)), int(round(cfg.quantiles[-1] * 100))
    rows = []
    for r in fd["horizons"]:
        track = "–"
        if metrics is not None:
            m = metrics[(metrics["model"] == fd["model"]) & (metrics["horizon"] == r["h"])]
            if len(m):
                track = f'{_pct(m["hit_rate"].iloc[0])} vs {_pct(m["always_up"].iloc[0])}'
        rows.append([
            f'{r["h"]} day' + ("s" if r["h"] > 1 else ""), _date(r["date"]), _price(r["mid"]),
            f'{_price(r["lo"])} – {_price(r["hi"])}', _pct(r["ret"], 2, sign=True), _p_cell(r["p_up"], r["base"]),
            _pct(r["base"]), _pp(r["p_up"] - r["base"]), (_chip(_view(r["p_up"], r["base"]), _tone(r["p_up"], r["base"])), ""),
            track,
        ])
    table = _table(["Horizon", "Target date", "Median", f"{lo_q}–{hi_q}% range", "Expected", "P(up)", "Historical",
                    "Difference", "View", "Backtest hit vs always-up"], rows, "forecast-table")

    g = fc[fc["ticker"] == ticker]
    hs = sorted(g["horizon"].unique())
    model_rows = []
    base_p = {r["h"]: r["base"] for r in fd["horizons"]}
    for m in [x for x in g["model"].unique() if x not in ("ensemble", "baseline")] + ["baseline"]:
        if m not in set(g["model"]):
            continue
        cells = [_label(m)]
        for h in hs:
            p = float(g[(g["model"] == m) & (g["horizon"] == h)]["p_up"].iloc[0])
            cells.append(_p_cell(p, base_p.get(int(h), 0.5)))
        model_rows.append(cells)
    per_model = _table(["Model"] + [f"{h}d" for h in hs], model_rows, "compact")

    hist_dates = fd["dates"][:len(fd["history"])]
    hist_rows = [[_date(d), _price(v)] for d, v in zip(hist_dates[-10:], fd["history"][-10:])]
    twin = _table(["Date", "Close"], hist_rows + [[_date(r["date"]) + " (forecast)", f'{_price(r["mid"])} '
                                                  f'({_price(r["lo"])} – {_price(r["hi"])})'] for r in fd["horizons"]])
    first = fd["horizons"][0]
    lead = max(fd["horizons"], key=lambda r: r["h"])
    snapshot = indicator_snapshot(uni.prices[ticker])
    ind_rows = [[name, value, reading or "–"] for name, value, reading in snapshot]
    return f"""
<section class="forecast" aria-labelledby="fc-{idx}">
  <div class="section-head">
    <div>
      <p class="eyebrow">Forecast · {_e(_label(fd["model"]))} of {len(set(fc["model"])) - 2} models</p>
      <h2 id="fc-{idx}">{_e(heading)}</h2>
    </div>
    <dl class="quote">
      <div><dt>Last close</dt><dd>{_price(fd["close"])}</dd><dd class="sub">{_date(fd["last"])}</dd></div>
      <div><dt>Next day</dt><dd>{_chip(_view(first["p_up"], first["base"]), _tone(first["p_up"], first["base"]))}</dd><dd class="sub">P(up) {_pct(first["p_up"])}, history {_pct(first["base"])}</dd></div>
      <div><dt>{lead["h"]}-day median</dt><dd>{_price(lead["mid"])}</dd><dd class="sub">{_pct(lead["ret"], 1, sign=True)} · range {_price(lead["lo"])}–{_price(lead["hi"])}</dd></div>
    </dl>
  </div>
  <figure class="card chart-card">
    <figcaption>Closing price for the last six months and the forecast for the next {max(cfg.horizons)} trading days: dashed line is the median, the shaded fan the {lo_q}–{hi_q}% range.</figcaption>
    <div class="chart" data-chart="fan" data-index="{idx}" style="height:320px"></div>
    <details><summary>Table view</summary>{twin}</details>
  </figure>
  <div class="block">
    <h3>Forecast by horizon</h3>
    {table}
    <p class="note">View compares P(up) with how often {_e(ticker)} rose over the same horizon historically
    (the no-skill baseline): Bullish or Bearish needs a gap of at least {VIEW_BAND * 100:.0f} pp.</p>
  </div>
  <div class="two-up">
    <div class="block">
      <h3>P(up) by model</h3>
      {per_model}
    </div>
    <div class="block">
      <h3>Indicator readings, {_date(fd["last"])}</h3>
      {_table(["Indicator", "Value", "Reading"], ind_rows, "compact", num_from=1)}
    </div>
  </div>
</section>"""


def _kpis(metrics: pd.DataFrame, bt: pd.DataFrame, cfg: Config, main: str) -> str:
    h = min(cfg.horizons)
    m = metrics[(metrics["model"] == main) & (metrics["horizon"] == h)]
    s = bt[(bt["model"] == main) & (bt["horizon"] == h) & (bt["strategy"] == "long_flat")]
    b = bt[bt["strategy"] == "buy_hold"]
    tiles = []

    def tile(label, value, delta, good, note):
        tone = "" if good is None else ("good" if good else "bad")
        arrow = "" if good is None else ("▲ " if delta.startswith("+") else "▼ ")
        return (f'<div class="kpi"><p class="kpi-label">{_e(label)}</p><p class="kpi-value">{_e(value)}</p>'
                f'<p class="kpi-delta {tone}">{_e(arrow + delta)}</p><p class="kpi-note">{_e(note)}</p></div>')

    if len(m):
        r = m.iloc[0]
        tiles.append(tile(f"{h}-day direction hit rate", _pct(r.hit_rate), _pp(r.hit_rate - r.always_up),
                          r.hit_rate >= r.always_up, f"vs always-up {_pct(r.always_up)} over {int(r.n)} days"))
    if len(s) and len(b):
        sr, br = s.iloc[0], b.iloc[0]
        tiles.append(tile("Strategy return (long or cash)", _pct(sr.total_return, 1, sign=True),
                          _pp(sr.total_return - br.total_return), sr.total_return >= br.total_return,
                          f"vs buy and hold {_pct(br.total_return, 1, sign=True)}, after {cfg.cost_bps:g} bps costs"))
        tiles.append(tile("Strategy Sharpe ratio", _num(sr.sharpe), f"{sr.sharpe - br.sharpe:+.2f}".replace("-", "−"),
                          sr.sharpe >= br.sharpe, f"vs buy and hold {_num(br.sharpe)}; invested {_pct(sr.exposure, 0)} of days"))
    if len(m):
        r = m.iloc[0]
        target = cfg.quantiles[-1] - cfg.quantiles[0]
        tiles.append(tile("Forecast range coverage", _pct(r.coverage, 0), _pp(r.coverage - target, 0), None,
                          f"share of outcomes inside the {_pct(target, 0)} band (target {_pct(target, 0)})"))
    return '<div class="kpis">' + "".join(tiles) + "</div>"


def _track_section(pred, metrics, bt, cfg: Config, equity: dict) -> str:
    main = equity["model"]
    start, end = pd.Timestamp(pred["date"].min()), pd.Timestamp(pred["date"].max())
    n_folds = pred["fold"].nunique()
    buttons = "".join(
        f'<button type="button" id="eq-h{h}" data-h="{h}" aria-pressed="{"true" if i == 0 else "false"}">{h}-day signal</button>'
        for i, h in enumerate(sorted(cfg.horizons)))
    twins = []
    for i, h in enumerate(sorted(cfg.horizons)):
        e = equity["horizons"].get(str(h))
        if not e:
            continue
        dates = pd.DatetimeIndex(e["dates"])
        month_end = pd.Series(np.arange(len(dates)), index=dates).groupby(dates.to_period("M")).last().to_numpy()
        rows = [[_date(e["dates"][k]), _pct(e["long_flat"][k], 1, True), _pct(e["long_short"][k], 1, True),
                 _pct(e["buy_hold"][k], 1, True)] for k in month_end]
        twins.append(f'<div data-twin="{h}"{"" if i == 0 else " hidden"}>'
                     + _table(["Month end", "Long or cash", "Long or short", "Buy and hold"], rows, "compact") + "</div>")
    rows = []
    view = bt[bt["strategy"] != "buy_hold"].copy()
    for r in pd.concat([bt[bt["strategy"] == "buy_hold"], view]).itertuples():
        hz = "–" if pd.isna(r.horizon) else f"{int(r.horizon)}d"
        strat = {"buy_hold": "Buy and hold", "long_flat": "Long or cash", "long_short": "Long or short"}[r.strategy]
        model = "–" if r.model == "buy_and_hold" else _label(r.model)
        rows.append([model, (hz, ""), (strat, ""), _pct(r.total_return, 1, True), _pct(r.cagr, 1, True), _num(r.sharpe),
                     _pct(r.max_drawdown, 1), _pct(getattr(r, "exposure", np.nan), 0),
                     _num(getattr(r, "trades_per_year", np.nan), 0)])
    bt_table = _table(["Model", "Signal", "Strategy", "Total", "CAGR", "Sharpe", "Max drawdown", "Invested",
                       "Trades / yr"], rows, "compact", num_from=3)
    return f"""
<section aria-labelledby="track">
  <p class="eyebrow">Out-of-sample · walk-forward</p>
  <h2 id="track">Track record</h2>
  <p class="lede">{n_folds} test blocks from {_date(start)} to {_date(end)}. Each block's models were trained only on
  data from before it, with labels that overlap the block purged, then predicted it blind.</p>
  {_kpis(metrics, bt, cfg, main)}
  <figure class="card chart-card">
    <div class="controls"><span class="controls-label" id="eq-label">Trade on</span>
      <div class="seg" role="group" aria-labelledby="eq-label">{buttons}</div></div>
    <figcaption>Cumulative return of trading the {_e(_label(main).lower())}'s P(up) each day (long when P(up) &gt; 50%,
    otherwise cash or short), after {cfg.cost_bps:g} bps per trade, against buying and holding.</figcaption>
    <div class="chart" data-chart="equity" style="height:300px"></div>
    <details><summary>Table view</summary>{"".join(twins)}</details>
  </figure>
  <details class="bt-details">
    <summary>All backtests ({len(rows)} strategy and signal combinations)</summary>
    {bt_table}
  </details>
</section>"""


def _scorecard_section(metrics: pd.DataFrame, cfg: Config) -> str:
    rows = []
    order = {m: i for i, m in enumerate(["ensemble", "lstm", "gru", "tcn", "transformer", "mlp", "gbm", "linear",
                                         "baseline"])}
    for r in sorted(metrics.itertuples(), key=lambda r: (r.horizon, order.get(r.model, 99))):
        edge_tone = "pos" if r.edge > 0.005 else "neg" if r.edge < -0.005 else "neutral"
        rows.append([_label(r.model), (f"{int(r.horizon)}d", ""), f"{int(r.n):,}", _pct(r.hit_rate),
                     _pct(r.always_up), (_chip(_pp(r.edge), edge_tone), ""), _num(r.z, 1), _num(r.auc, 3),
                     _num(r.ic, 3), _num(r.r2_oos, 4), _pct(r.coverage, 0)])
    table = _table(["Model", "Horizon", "Days", "Hit rate", "Always-up", "Edge", "z", "AUC", "IC", "R² oos",
                    "Coverage"], rows, "compact", num_from=2)
    panels = "".join(
        f'<figure class="card chart-card small"><figcaption><strong>{h}-day</strong> horizon</figcaption>'
        f'<div class="chart" data-chart="edge" data-h="{h}"></div></figure>' for h in sorted(cfg.horizons))
    return f"""
<section aria-labelledby="score">
  <p class="eyebrow">Out-of-sample · per model</p>
  <h2 id="score">Scorecard</h2>
  <p class="lede">Edge is the hit rate minus the better of always calling up or always calling down, in percentage
  points. Bars right of zero beat that trivial call. With a few hundred test days, edges inside about ±3 pp are
  indistinguishable from luck; z above 2 is the first hint of something real.</p>
  <div class="small-multiples">{panels}</div>
  <details open><summary>Full scorecard (table view of the charts above)</summary>{table}</details>
</section>"""


def _method_section(uni, cfg: Config, pred) -> str:
    start = min(pd.Timestamp(i.dates[0]) for i in uni.items)
    folds = []
    span0 = start.value
    span1 = pd.Timestamp(pred["date"].max()).value
    for k, g in pred.groupby("fold"):
        t0, t1 = pd.Timestamp(g["date"].min()), pd.Timestamp(g["date"].max())
        a = (t0.value - span0) / (span1 - span0) * 100
        b = (t1.value - span0) / (span1 - span0) * 100
        folds.append(f'<div class="fold"><span class="fold-name">Block {int(k) + 1}</span>'
                     f'<span class="fold-track" aria-hidden="true"><span class="fold-train" style="width:{a:.2f}%"></span>'
                     f'<span class="fold-test" style="left:{a:.2f}%;width:{max(b - a, 0.6):.2f}%"></span></span>'
                     f'<span class="fold-dates">train {start:%Y}–{t0:%b %Y} · test {t0:%b %Y}–{t1:%b %Y}</span></div>')
    models = ", ".join(_label(m) for m in cfg.models)
    return f"""
<section aria-labelledby="method" class="method">
  <p class="eyebrow">How it works</p>
  <h2 id="method">Method and caveats</h2>
  <div class="folds" role="list" aria-label="Walk-forward blocks">{"".join(folds)}</div>
  <div class="prose">
    <p><strong>Data.</strong> Daily bars from Yahoo Finance, adjusted for splits and dividends, from {start:%B %Y}.
    Market context comes from the S&amp;P 500 ETF (SPY), the VIX and the 10-year Treasury yield.</p>
    <p><strong>Features.</strong> {len(uni.feature_names)} indicator features per day: returns over 1 to 252 days,
    moving-average structure (SMA, EMA, WMA, DEMA, TEMA, Hull, KAMA), MACD, PPO, ADX, Aroon, TRIX, vortex, KST, Ichimoku,
    parabolic SAR, Supertrend, RSI, stochastics, Williams %R, CCI, ultimate and awesome oscillators, TSI, CMO, Connors RSI,
    Bollinger, Keltner and Donchian channels, ATR and five volatility estimators, OBV, A/D, Chaikin, MFI, force index,
    VWAP distance, candle shape, 52-week range, calendar and market context. Every feature uses only past bars.</p>
    <p><strong>Models.</strong> {models}, each predicting the {", ".join(f"{h}-day" for h in cfg.horizons)} forward
    return as quantiles ({", ".join(_pct(q, 0) for q in cfg.quantiles)}) plus P(up) from a {cfg.seq_len}-day window.
    Targets are scaled by recent volatility, so the fan widens when markets are rough. The ensemble averages all models.</p>
    <p><strong>Testing.</strong> Expanding-window walk-forward with purged labels; feature scaling is fit on training
    days only and the networks early-stop on a later validation slice. The backtests trade at the close with
    {cfg.cost_bps:g} bps per unit of turnover and ignore slippage, borrow costs and taxes.</p>
    <p><strong>Read with care.</strong> Daily stock moves are mostly noise. Direction hit rates in the low 50s are
    normal and often no better than always calling up. This report is a statistical experiment, not financial advice.</p>
  </div>
</section>"""


# --------------------------------------------------------------------------- #
# page template
# --------------------------------------------------------------------------- #

CSS = r"""
:root {
  /* Layout: a quant tear sheet - masthead, one lead fan chart per ticker, KPI row and equity curve,
     scorecard small multiples, method notes; one 1120px column whose two-up grids stack on phones. */
  --page: #f6f6f3;
  --surface: #fcfcfb;
  --ink: #0b0b0b;
  --ink-2: #52514e;
  --muted: #6f6e69;
  --tick: #898781;
  --grid: #e1e0d9;
  --axis: #c3c2b7;
  --border: rgba(11, 11, 11, 0.10);
  --s1: #2a78d6;
  --s2: #eb6834;
  --ctx: #898781;
  --pos: #2a78d6;
  --neg: #e34948;
  --good: #006300;
  --bad: #d03b3b;
  --font-display: "Space Grotesk", "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #a3a29b; --tick: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255, 255, 255, 0.10); --s1: #3987e5; --s2: #d95926;
    --ctx: #898781; --pos: #3987e5; --neg: #e66767; --good: #0ca30c; --bad: #e66767; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #a3a29b; --tick: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255, 255, 255, 0.10); --s1: #3987e5; --s2: #d95926;
  --ctx: #898781; --pos: #3987e5; --neg: #e66767; --good: #0ca30c; --bad: #e66767; color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.55 var(--font-body); }
.wrap { max-width: 1120px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; grid-template-columns: minmax(0, 1fr); gap: 56px; }
h1, h2, h3 { font-family: var(--font-display); font-weight: 600; letter-spacing: -0.01em; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(2.2rem, 6vw, 3.4rem); line-height: 1.02; }
h2 { font-size: 1.6rem; line-height: 1.15; }
h3 { font-size: 1rem; margin-bottom: 10px; }
p { margin: 0; }
.eyebrow { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-weight: 600; margin-bottom: 6px; }
.lede { color: var(--ink-2); max-width: 68ch; margin-top: 8px; }
section { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; min-width: 0; }
section > *, details, .wrap > * { min-width: 0; }
.masthead { display: grid; gap: 10px; border-bottom: 1px solid var(--border); padding-bottom: 24px; }
.masthead .sub { color: var(--ink-2); max-width: 75ch; }
.tickers { display: flex; flex-wrap: wrap; gap: 8px; }
.section-head { display: flex; flex-wrap: wrap; align-items: end; justify-content: space-between; gap: 18px 32px; }
.section-head h2 { font-size: 2.1rem; }
.quote { display: flex; flex-wrap: wrap; gap: 14px 32px; margin: 0; }
.quote div { display: grid; gap: 2px; min-width: 0; }
.quote dt { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
.quote dd { margin: 0; font-size: 1.35rem; font-weight: 600; font-family: var(--font-display); }
.quote dd.sub { font-size: 13px; font-weight: 400; color: var(--ink-2); font-family: var(--font-body); }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }
.chart-card { margin: 0; padding: 16px 16px 12px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; min-width: 0; }
.chart-card figcaption { color: var(--ink-2); font-size: 13px; max-width: 80ch; }
.chart { position: relative; width: 100%; min-width: 0; }
.chart svg { display: block; overflow: visible; touch-action: pan-y; }
.chart svg:focus-visible { outline: 2px solid var(--s1); outline-offset: 4px; border-radius: 4px; }
.chart .grid { stroke: var(--grid); stroke-width: 1; }
.chart .axis { stroke: var(--axis); stroke-width: 1; }
.chart text { font: 11px var(--font-body); fill: var(--tick); font-variant-numeric: tabular-nums; }
.chart text.end-label { fill: var(--ink-2); font-size: 12px; }
.chart text.row-label { fill: var(--ink-2); font-size: 12px; }
.chart text.value { fill: var(--ink-2); font-size: 11px; }
.chart .line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.chart .line.dash { stroke-dasharray: 5 4; }
.chart .band { opacity: 0.14; }
.chart .dot { stroke: var(--surface); stroke-width: 2; }
.chart .cross { stroke: var(--axis); stroke-width: 1; }
.chart .hit { fill: transparent; cursor: crosshair; }
.chart .bar-row { cursor: default; outline: none; }
.chart .bar-row .row-hit { fill: transparent; }
.chart .bar-row:hover .bar, .chart .bar-row:focus .bar { opacity: 0.78; }
.chart .bar-row:focus .row-hit { fill: var(--grid); opacity: 0.5; }
.tip { position: absolute; z-index: 2; pointer-events: none; background: var(--surface); color: var(--ink);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 12px; line-height: 1.4;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12); min-width: 140px; max-width: 260px; }
.tip-title { color: var(--ink-2); margin-bottom: 4px; }
.tip-row { display: flex; align-items: center; gap: 8px; white-space: nowrap; }
.tip-row strong { font-variant-numeric: tabular-nums; }
.tip-key { width: 14px; height: 2px; border-radius: 1px; flex: none; }
.tip-name { color: var(--ink-2); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12px; color: var(--ink-2); margin-bottom: 6px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 16px; height: 2px; border-radius: 1px; display: inline-block; }
.legend i.dash { background: linear-gradient(90deg, currentColor 60%, transparent 0) 0 0 / 6px 2px repeat-x; }
.legend i.box { height: 10px; width: 14px; border-radius: 2px; opacity: 0.3; }
.controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
.controls-label { font-size: 13px; color: var(--ink-2); }
.seg { display: inline-flex; border: 1px solid var(--border); border-radius: 8px; padding: 2px; gap: 2px; background: var(--page); }
.seg button { font: 500 13px var(--font-body); color: var(--ink-2); background: transparent; border: 0; border-radius: 6px; padding: 5px 10px; cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--surface); color: var(--ink); box-shadow: 0 0 0 1px var(--border); }
.seg button:focus-visible { outline: 2px solid var(--s1); outline-offset: 1px; }
details > summary { cursor: pointer; color: var(--ink-2); font-size: 13px; font-weight: 500; padding: 4px 0; }
details > summary:focus-visible { outline: 2px solid var(--s1); outline-offset: 2px; border-radius: 4px; }
details[open] > summary { margin-bottom: 8px; }
.table-wrap { overflow-x: auto; min-width: 0; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { padding: 7px 10px; text-align: left; border-bottom: 1px solid var(--grid); white-space: nowrap; }
thead th { font-weight: 600; color: var(--muted); font-size: 12px; border-bottom: 1px solid var(--axis); }
tbody th { font-weight: 500; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.two-up { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px 32px; align-items: start; }
.block { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr); gap: 0; }
.note { font-size: 12px; color: var(--muted); margin-top: 8px; max-width: 80ch; }
.chip { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 500; line-height: 1.6;
  background: color-mix(in srgb, var(--ink) 7%, transparent); color: var(--ink); }
.chip.pos { background: color-mix(in srgb, var(--pos) 18%, transparent); }
.chip.neg { background: color-mix(in srgb, var(--neg) 18%, transparent); }
.pcell { display: inline-block; min-width: 56px; padding: 1px 6px; border-radius: 4px; text-align: right;
  background: linear-gradient(90deg, transparent calc(100% - var(--w)), color-mix(in srgb, var(--pos) 30%, transparent) 0); }
.pcell.neg { background: linear-gradient(270deg, transparent calc(100% - var(--w)), color-mix(in srgb, var(--neg) 30%, transparent) 0); }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; display: grid; gap: 2px; align-content: start; }
.kpi-label { font-size: 13px; color: var(--ink-2); }
.kpi-value { font: 600 1.9rem/1.2 var(--font-display); }
.kpi-delta { font-size: 13px; font-weight: 600; color: var(--ink-2); }
.kpi-delta.good { color: var(--good); }
.kpi-delta.bad { color: var(--bad); }
.kpi-note { font-size: 12px; color: var(--muted); }
.small-multiples { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.chart-card.small figcaption { font-size: 13px; color: var(--ink-2); }
.folds { display: grid; gap: 8px; }
.fold { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 2px 12px; align-items: center; font-size: 12px; }
.fold-name { color: var(--ink-2); font-weight: 600; }
.fold-track { position: relative; height: 8px; border-radius: 4px; background: var(--grid); overflow: hidden; }
.fold-train { position: absolute; left: 0; top: 0; bottom: 0; background: color-mix(in srgb, var(--ctx) 55%, transparent); }
.fold-test { position: absolute; top: 0; bottom: 0; background: var(--s1); border-radius: 4px; }
.fold-dates { grid-column: 2; color: var(--muted); }
.prose { display: grid; gap: 10px; max-width: 72ch; color: var(--ink-2); }
.prose strong { color: var(--ink); }
.footer { color: var(--muted); font-size: 12px; border-top: 1px solid var(--border); padding-top: 16px; }
@media (max-width: 760px) {
  .two-up { grid-template-columns: minmax(0, 1fr); }
  .wrap { gap: 44px; padding-block: 24px 48px; }
  .section-head h2 { font-size: 1.8rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
"""

JS = r"""
(() => {
  const DATA = JSON.parse(document.getElementById('report-data').textContent);
  const NS = 'http://www.w3.org/2000/svg';
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const C = (name) => `var(--${name})`;
  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function txt(parent, x, y, s, cls, anchor, baseline) {
    const t = el('text', {x, y, class: cls || '', 'text-anchor': anchor || 'start', 'dominant-baseline': baseline || 'auto'}, parent);
    t.textContent = s;
    return t;
  }
  const minus = (s) => s.replace('-', '−');
  const pct = (v, d = 1) => v == null ? '–' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v * 100).toFixed(d) + '%';
  const pp = (v, d = 1) => (v >= 0 ? '+' : '−') + Math.abs(v * 100).toFixed(d) + ' pp';
  const share = (v, d = 1) => v == null ? '–' : (v * 100).toFixed(d) + '%';
  const money = (v) => minus(v.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}));
  const parse = (s) => { const [y, m, d] = s.split('-').map(Number); return {y, m, d}; };
  const longDate = (s) => { const p = parse(s); return `${MONTHS[p.m - 1]} ${p.d}, ${p.y}`; };

  function nice(lo, hi, count) {
    if (!isFinite(lo) || !isFinite(hi)) { lo = 0; hi = 1; }
    if (lo === hi) { const a = Math.abs(lo) || 1; lo -= a * 0.05; hi += a * 0.05; }
    const raw = (hi - lo) / Math.max(1, count);
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / mag;
    const step = (f >= 7.5 ? 10 : f >= 3.5 ? 5 : f >= 1.5 ? 2 : 1) * mag;
    const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step;
    const ticks = [];
    for (let v = a; v <= b + step * 1e-6; v += step) ticks.push(Math.round(v / step) * step);
    return {lo: a, hi: b, ticks, step};
  }

  function tooltip(host) {
    let t = host.querySelector(':scope > .tip');
    if (!t) { t = document.createElement('div'); t.className = 'tip'; t.hidden = true; host.appendChild(t); }
    return t;
  }
  function fillTip(tip, title, rows) {
    tip.replaceChildren();
    const h = document.createElement('div'); h.className = 'tip-title'; h.textContent = title; tip.appendChild(h);
    for (const r of rows) {
      const row = document.createElement('div'); row.className = 'tip-row';
      if (r.color) { const k = document.createElement('span'); k.className = 'tip-key'; k.style.background = r.color; row.appendChild(k); }
      const v = document.createElement('strong'); v.textContent = r.value; row.appendChild(v);
      const n = document.createElement('span'); n.className = 'tip-name'; n.textContent = r.name; row.appendChild(n);
      tip.appendChild(row);
    }
  }
  function placeTip(host, tip, x, y) {
    tip.hidden = false;
    const w = tip.offsetWidth, hw = host.clientWidth;
    let left = x + 14;
    if (left + w > hw) left = x - 14 - w;
    tip.style.left = Math.max(0, left) + 'px';
    tip.style.top = Math.max(0, y) + 'px';
  }

  function legend(host, items) {
    const box = document.createElement('div'); box.className = 'legend';
    for (const it of items) {
      const s = document.createElement('span');
      const i = document.createElement('i');
      i.style.color = it.color;
      if (it.dash) i.className = 'dash';
      else { i.style.background = it.color; if (it.box) i.className = 'box'; }
      s.appendChild(i); s.appendChild(document.createTextNode(it.name));
      box.appendChild(s);
    }
    host.appendChild(box);
    return box;
  }

  // Line chart over an index-based (trading-day) x axis.
  function lineChart(host, spec) {
    host.replaceChildren();
    const lg = spec.legend ? legend(host, spec.legend) : null;
    const W = Math.max(260, host.clientWidth);
    const H = Math.max(200, (spec.height || 300) - (lg ? lg.offsetHeight + 6 : 0));
    const narrow = W < 560;
    const wantLabels = spec.endLabels && !narrow;
    const m = {t: 10, r: wantLabels ? 112 : 14, b: 26, l: spec.yWidth || 58};
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const n = spec.dates.length;
    let lo = Infinity, hi = -Infinity;
    const take = (v) => { if (v != null && isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); } };
    spec.series.forEach(s => s.values.forEach(take));
    if (spec.band) { spec.band.lo.forEach(take); spec.band.hi.forEach(take); }
    (spec.include || []).forEach(take);
    const y = nice(lo, hi, Math.max(3, Math.round(ih / 56)));
    const X = (i) => m.l + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw);
    const Y = (v) => m.t + ih - ((v - y.lo) / (y.hi - y.lo)) * ih;
    const svg = el('svg', {width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': spec.label, tabindex: 0}, host);
    for (const t of y.ticks) {
      el('line', {x1: m.l, x2: m.l + iw, y1: Y(t), y2: Y(t), class: t === 0 && spec.zeroAxis ? 'axis' : 'grid'}, svg);
      txt(svg, m.l - 8, Y(t), spec.yfmt(t, y.step), '', 'end', 'middle');
    }
    el('line', {x1: m.l, x2: m.l + iw, y1: m.t + ih, y2: m.t + ih, class: 'axis'}, svg);
    const nt = Math.max(2, Math.min(8, Math.floor(iw / 96)));
    const first = parse(spec.dates[0]), last = parse(spec.dates[n - 1]);
    const longSpan = (last.y - first.y) * 12 + (last.m - first.m) > 14;
    for (let k = 0; k < nt; k++) {
      const i = Math.round(k * (n - 1) / (nt - 1));
      const p = parse(spec.dates[i]);
      const label = longSpan ? `${MONTHS[p.m - 1]} ’${String(p.y).slice(2)}` : `${MONTHS[p.m - 1]} ${p.d}`;
      txt(svg, X(i), m.t + ih + 17, label, '', k === 0 ? 'start' : k === nt - 1 ? 'end' : 'middle');
    }
    if (spec.band) {
      const up = [], dn = [];
      spec.band.lo.forEach((v, i) => { if (v != null) { dn.push([X(i), Y(v)]); up.push([X(i), Y(spec.band.hi[i])]); } });
      const d = 'M' + dn.map(p => p.map(q => q.toFixed(1)).join(',')).join('L') + 'L' +
        up.reverse().map(p => p.map(q => q.toFixed(1)).join(',')).join('L') + 'Z';
      el('path', {d, class: 'band', style: `fill:${spec.band.color}`}, svg);
    }
    for (const s of spec.series) {
      let d = '', pen = false;
      s.values.forEach((v, i) => {
        if (v == null) { pen = false; return; }
        d += (pen ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(v).toFixed(1); pen = true;
      });
      el('path', {d, class: 'line' + (s.dash ? ' dash' : ''), style: `stroke:${s.color}`}, svg);
    }
    for (const p of spec.points || []) el('circle', {cx: X(p.i), cy: Y(p.v), r: 4, class: 'dot', style: `fill:${p.color}`}, svg);
    if (wantLabels) {
      const ends = spec.series.map(s => {
        let i = s.values.length - 1; while (i >= 0 && s.values[i] == null) i--;
        return {s, i, y: Y(s.values[i])};
      }).sort((a, b) => a.y - b.y);
      const clash = ends.some((e, k) => k > 0 && e.y - ends[k - 1].y < 15);
      if (!clash) for (const e of ends) txt(svg, X(e.i) + 8, e.y, `${e.s.short || e.s.name} ${spec.yfmt(e.s.values[e.i])}`, 'end-label', 'start', 'middle');
    }
    const cross = el('line', {y1: m.t, y2: m.t + ih, class: 'cross', visibility: 'hidden'}, svg);
    const hit = el('rect', {x: m.l, y: m.t, width: Math.max(1, iw), height: ih, class: 'hit'}, svg);
    const tip = tooltip(host);
    const stops = spec.snap || Array.from({length: n}, (_, i) => i);
    let cur = -1;
    const show = (i) => {
      cur = i;
      cross.setAttribute('x1', X(i)); cross.setAttribute('x2', X(i)); cross.setAttribute('visibility', 'visible');
      fillTip(tip, longDate(spec.dates[i]), spec.rows(i));
      placeTip(host, tip, X(i), (lg ? lg.offsetHeight + 6 : 0) + m.t);
    };
    const hide = () => { cross.setAttribute('visibility', 'hidden'); tip.hidden = true; };
    const nearest = (px) => {
      const raw = (px - m.l) / iw * (n - 1);
      let best = stops[0];
      for (const s of stops) if (Math.abs(s - raw) < Math.abs(best - raw)) best = s;
      return best;
    };
    const move = (e) => { const r = svg.getBoundingClientRect(); show(nearest(e.clientX - r.left)); };
    hit.addEventListener('pointermove', move);
    hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', hide);
    svg.addEventListener('focus', () => show(stops[stops.length - 1]));
    svg.addEventListener('blur', hide);
    svg.addEventListener('keydown', (e) => {
      let k = stops.indexOf(cur);
      if (e.key === 'ArrowRight') k = Math.min(stops.length - 1, k + 1);
      else if (e.key === 'ArrowLeft') k = Math.max(0, k - 1);
      else if (e.key === 'Home') k = 0;
      else if (e.key === 'End') k = stops.length - 1;
      else if (e.key === 'Escape') { hide(); return; }
      else return;
      e.preventDefault(); show(stops[k]);
    });
  }

  function fanChart(host) {
    const f = DATA.forecast[+host.dataset.index];
    const nh = f.history.length, n = f.dates.length;
    const hist = f.dates.map((_, i) => i < nh ? f.history[i] : null);
    const med = f.dates.map(() => null), lo = f.dates.map(() => null), hi = f.dates.map(() => null);
    med[nh - 1] = lo[nh - 1] = hi[nh - 1] = f.close;
    const byIndex = {};
    for (const h of f.horizons) { const i = nh - 1 + h.h; med[i] = h.mid; lo[i] = h.lo; hi[i] = h.hi; byIndex[i] = h; }
    // straight segments between forecast horizons
    let prev = nh - 1;
    for (const h of f.horizons) {
      const i = nh - 1 + h.h;
      for (let j = prev + 1; j < i; j++) {
        const t = (j - prev) / (i - prev);
        med[j] = med[prev] + t * (med[i] - med[prev]); lo[j] = lo[prev] + t * (lo[i] - lo[prev]); hi[j] = hi[prev] + t * (hi[i] - hi[prev]);
      }
      prev = i;
    }
    const snap = Array.from({length: nh}, (_, i) => i).concat(f.horizons.map(h => nh - 1 + h.h));
    const fmt = (v, step) => v.toLocaleString('en-US', {maximumFractionDigits: step && step < 1 ? 2 : 0});
    lineChart(host, {
      label: `${f.ticker} closing price and forecast`, dates: f.dates, height: 320, yWidth: 60,
      legend: [{name: 'Close', color: C('s1')}, {name: 'Forecast median', color: C('s1'), dash: true},
               {name: `${DATA.band} range`, color: C('s1'), box: true}],
      series: [{name: 'Close', values: hist, color: C('s1')}, {name: 'Median', values: med, color: C('s1'), dash: true}],
      band: {lo, hi, color: C('s1')},
      points: f.horizons.map(h => ({i: nh - 1 + h.h, v: h.mid, color: C('s1')})),
      yfmt: fmt, snap,
      rows: (i) => {
        if (i < nh) return [{value: money(f.history[i]), name: 'close', color: C('s1')}];
        const h = byIndex[i];
        return [{value: money(h.mid), name: `median, ${h.h}-day`, color: C('s1')},
                {value: `${money(h.lo)} – ${money(h.hi)}`, name: `${DATA.band} range`},
                {value: share(h.p_up, 0), name: 'chance of a gain'},
                {value: pct(h.ret, 2), name: 'expected return'}];
      },
    });
  }

  let eqH = null;
  function equityChart(host) {
    const hs = Object.keys(DATA.equity.horizons);
    if (!hs.length) return;
    if (eqH == null || !DATA.equity.horizons[eqH]) eqH = hs[0];
    const e = DATA.equity.horizons[eqH];
    const series = [
      {name: 'Long or cash', short: 'Long/cash', values: e.long_flat, color: C('s1')},
      {name: 'Long or short', short: 'Long/short', values: e.long_short, color: C('s2')},
      {name: 'Buy and hold', short: 'Buy & hold', values: e.buy_hold, color: C('ctx')},
    ];
    lineChart(host, {
      label: 'Cumulative return of model strategies and buy and hold', dates: e.dates, height: 300, endLabels: true,
      legend: series.map(s => ({name: s.name, color: s.color})), series, include: [0], zeroAxis: true,
      yfmt: (v, step) => pct(v, step && step < 0.05 ? 1 : 0),
      rows: (i) => series.map(s => ({value: pct(s.values[i]), name: s.name, color: s.color})),
    });
  }

  function edgeChart(host) {
    const rows = DATA.edges[host.dataset.h] || [];
    host.replaceChildren();
    const W = Math.max(240, host.clientWidth);
    const rowH = 28, top = 4, bottom = 24;
    const H = top + rows.length * rowH + bottom;
    const labelW = Math.min(122, Math.max(84, W * 0.32)), padV = 50;
    const iw = Math.max(60, W - labelW - 2 * padV);
    const zero = labelW + padV + iw / 2;
    const A = DATA.edgeDomain;
    const S = (v) => (v / A) * (iw / 2);
    const svg = el('svg', {width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': `Edge versus the trivial call, ${host.dataset.h}-day horizon`}, host);
    for (const t of [-A, -A / 2, 0, A / 2, A]) {
      const x = zero + S(t);
      el('line', {x1: x, x2: x, y1: top, y2: H - bottom, class: t === 0 ? 'axis' : 'grid'}, svg);
      txt(svg, x, H - 7, t === 0 ? '0' : pp(t, 0).replace(' pp', ''), '', 'middle');
    }
    const tip = tooltip(host);
    rows.forEach((r, k) => {
      const yc = top + k * rowH + rowH / 2;
      const g = el('g', {class: 'bar-row', tabindex: 0, role: 'img',
        'aria-label': `${r.model}: edge ${pp(r.edge)}, hit rate ${share(r.hit)}`}, svg);
      el('rect', {x: 0, y: yc - rowH / 2, width: W, height: rowH, class: 'row-hit'}, g);
      txt(g, 0, yc, r.model, 'row-label', 'start', 'middle');
      const len = S(Math.max(-A, Math.min(A, r.edge)));
      const th = 12, rr = Math.min(4, Math.abs(len));
      if (Math.abs(len) >= 0.5) {
        const x0 = zero, x1 = zero + len, y0 = yc - th / 2, y1 = yc + th / 2, dir = len > 0 ? 1 : -1;
        const d = `M${x0},${y0}H${x1 - dir * rr}Q${x1},${y0} ${x1},${y0 + rr}V${y1 - rr}Q${x1},${y1} ${x1 - dir * rr},${y1}H${x0}Z`;
        el('path', {d, class: 'bar', style: `fill:${r.edge >= 0 ? C('pos') : C('neg')}`}, g);
      }
      const vx = zero + len + (r.edge >= 0 ? 6 : -6);
      txt(g, vx, yc, pp(r.edge), 'value', r.edge >= 0 ? 'start' : 'end', 'middle');
      const showTip = () => {
        fillTip(tip, `${r.model} · ${host.dataset.h}-day`, [
          {value: pp(r.edge), name: 'edge'},
          {value: share(r.hit), name: 'hit rate'},
          {value: share(r.always), name: 'always-up'},
          {value: r.auc == null ? '–' : r.auc.toFixed(3), name: 'AUC'},
        ]);
        placeTip(host, tip, Math.min(W - 150, Math.max(zero + len, zero)), yc + 8);
      };
      g.addEventListener('pointerenter', showTip);
      g.addEventListener('pointerleave', () => { tip.hidden = true; });
      g.addEventListener('focus', showTip);
      g.addEventListener('blur', () => { tip.hidden = true; });
    });
  }

  const RENDER = {fan: fanChart, equity: equityChart, edge: edgeChart};
  const charts = Array.from(document.querySelectorAll('[data-chart]'));
  const draw = (c) => { try { RENDER[c.dataset.chart](c); } catch (err) { console.error(err); } };
  charts.forEach(draw);
  const widths = new Map(charts.map(c => [c, c.clientWidth]));
  let timer = null;
  const ro = new ResizeObserver(() => {
    clearTimeout(timer);
    timer = setTimeout(() => charts.forEach(c => { if (widths.get(c) !== c.clientWidth) { widths.set(c, c.clientWidth); draw(c); } }), 120);
  });
  charts.forEach(c => ro.observe(c));
  document.querySelectorAll('.seg button[data-h]').forEach(b => b.addEventListener('click', () => {
    eqH = b.dataset.h;
    document.querySelectorAll('.seg button[data-h]').forEach(o => o.setAttribute('aria-pressed', String(o === b)));
    document.querySelectorAll('[data-twin]').forEach(t => { t.hidden = t.dataset.twin !== eqH; });
    charts.filter(c => c.dataset.chart === 'equity').forEach(draw);
  }));
})();
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;'
         'family=Space+Grotesk:wght@500;600&amp;display=swap">')


def render_report(uni, cfg: Config, pred: pd.DataFrame, metrics: pd.DataFrame, bt: pd.DataFrame,
                  fc: pd.DataFrame | None = None, standalone: bool = True) -> str:
    """Build the report HTML. ``standalone=False`` omits the document skeleton
    (doctype / html / head / body) for hosts that add their own."""
    tickers = [i.ticker for i in uni.items]
    lo_q, hi_q = int(round(cfg.quantiles[0] * 100)), int(round(cfg.quantiles[-1] * 100))
    equity = _equity_data(pred, cfg)
    edges = _edge_data(metrics)
    all_edges = [abs(r["edge"]) for rows in edges.values() for r in rows] or [0.02]
    domain = max(0.02, float(np.ceil(max(all_edges) * 100 / 2) * 2) / 100)
    data = {"forecast": _forecast_data(uni, cfg, fc) if fc is not None else [], "equity": equity, "edges": edges,
            "edgeDomain": domain, "band": f"{lo_q}–{hi_q}%"}
    first = min(pd.Timestamp(p.index[0]) for p in uni.prices.values())
    last = max(pd.Timestamp(p.index[-1]) for p in uni.prices.values())
    n_models = len(cfg.models)
    name = ", ".join(tickers[:6]) + (f" and {len(tickers) - 6} more" if len(tickers) > 6 else "")
    title = f"{', '.join(tickers[:3])}{' +' + str(len(tickers) - 3) if len(tickers) > 3 else ''} forecast"
    sections = []
    if fc is not None:
        for i, fd in enumerate(data["forecast"]):
            sections.append(_forecast_section(fd, fc, metrics, cfg, i, uni, multi=len(data["forecast"]) > 1))
    sections.append(_track_section(pred, metrics, bt, cfg, equity))
    sections.append(_scorecard_section(metrics, cfg))
    sections.append(_method_section(uni, cfg, pred))
    payload = json.dumps(_clean(data), separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    generated = pd.Timestamp.now()
    body = f"""
<main class="wrap">
  <header class="masthead">
    <p class="eyebrow">stockthing · model forecast · generated {_date(generated)} {generated:%H:%M}</p>
    <h1>{_e(name)}</h1>
    <p class="sub">Daily history {first:%b %Y} to {_date(last)}, {len(uni.feature_names)} indicator features per day,
    {n_models} models plus their ensemble, tested out of sample on {pred["fold"].nunique()} walk-forward blocks.</p>
  </header>
  {"".join(sections)}
  <p class="footer">Generated by stockthing. Forecasts are statistical estimates with wide error bars, not investment advice.</p>
</main>
<script type="application/json" id="report-data">{payload}</script>
<script>{JS}</script>"""
    head = (f'<title>{_e(title)}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'{FONTS}\n<style>{CSS}</style>')
    if not standalone:
        return head + body
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'{head}\n</head>\n<body>{body}\n</body>\n</html>\n')


def write_report(path, uni, cfg: Config, pred, metrics, bt, fc=None, standalone: bool = True) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(uni, cfg, pred, metrics, bt, fc, standalone), encoding="utf-8")
    return path
