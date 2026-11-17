"""Feature engineering: OHLCV (+ market context) -> stationary, scale-free
indicator features, plus forecast targets.

Raw prices are never fed to the models. Every indicator is expressed as a
ratio, return, oscillator value or z-score so that features are comparable
across decades and across tickers (which is what makes pooled training work).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ta

WARMUP_BARS = 260  # longest lookback used below (252-day windows) plus slack


def _log_ret(c: pd.Series, n: int = 1) -> pd.Series:
    return np.log(c / c.shift(n))


def compute_features(df: pd.DataFrame, context: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    """Build the full indicator feature matrix for one ticker.

    ``df`` needs open/high/low/close/volume columns. ``context`` optionally maps
    ``"spy"``, ``"vix"``, ``"tnx"`` to their OHLCV frames.
    """
    o, h, l, c, v = (df[k].astype(float) for k in ("open", "high", "low", "close", "volume"))
    lr = _log_ret(c)
    f: dict[str, pd.Series] = {}

    # ---- returns & momentum over many horizons --------------------------------
    for k in range(5):
        f[f"ret_lag{k}"] = lr.shift(k)
    for n in (2, 3, 5, 10, 20, 60, 120, 252):
        f[f"ret_{n}d"] = _log_ret(c, n)
    vol20 = lr.rolling(20, min_periods=20).std()
    for n in (5, 20, 60):
        f[f"ret_{n}d_z"] = ta.safe_div(f[f"ret_{n}d"], vol20 * np.sqrt(n))

    # ---- moving-average structure --------------------------------------------
    smas = {n: ta.sma(c, n) for n in (5, 10, 20, 50, 100, 200)}
    for n, s in smas.items():
        f[f"dist_sma{n}"] = c / s - 1.0
    for n in (12, 26, 50):
        f[f"dist_ema{n}"] = c / ta.ema(c, n) - 1.0
    f["dist_wma20"] = c / ta.wma(c, 20) - 1.0
    f["dist_dema20"] = c / ta.dema(c, 20) - 1.0
    f["dist_tema20"] = c / ta.tema(c, 20) - 1.0
    f["dist_hma20"] = c / ta.hma(c, 20) - 1.0
    f["dist_kama10"] = c / ta.kama(c, 10) - 1.0
    f["sma5_vs_20"] = smas[5] / smas[20] - 1.0
    f["sma20_vs_50"] = smas[20] / smas[50] - 1.0
    f["sma50_vs_200"] = smas[50] / smas[200] - 1.0  # golden / death cross state
    f["sma50_slope"] = smas[50] / smas[50].shift(5) - 1.0
    f["sma200_slope"] = smas[200] / smas[200].shift(20) - 1.0
    f["zscore20"] = ta.safe_div(c - smas[20], c.rolling(20, min_periods=20).std())
    for n in (20, 60):
        slope, r2 = ta.linreg(np.log(c), n)
        f[f"linreg_slope{n}"] = slope * 252.0
        f[f"linreg_r2_{n}"] = r2

    # ---- trend indicators -----------------------------------------------------
    m_line, m_sig, m_hist = ta.macd(c)
    f["macd"] = m_line / c
    f["macd_signal"] = m_sig / c
    f["macd_hist"] = m_hist / c
    p_line, _, p_hist = ta.ppo(c)
    f["ppo"] = p_line
    f["ppo_hist"] = p_hist
    pdi, mdi, adx = ta.adx(h, l, c)
    f["adx"] = adx / 100.0
    f["di_spread"] = (pdi - mdi) / 100.0
    a_up, a_dn = ta.aroon(h, l)
    f["aroon_up"] = a_up / 100.0
    f["aroon_down"] = a_dn / 100.0
    f["aroon_osc"] = (a_up - a_dn) / 100.0
    f["trix"] = ta.trix(c)
    vi_p, vi_m = ta.vortex(h, l, c)
    f["vortex_spread"] = vi_p - vi_m
    f["mass_index"] = ta.mass_index(h, l)
    f["dpo"] = ta.dpo(c) / c
    k_line, k_sig = ta.kst(c)
    f["kst"] = k_line / 100.0
    f["kst_hist"] = (k_line - k_sig) / 100.0
    ichi = ta.ichimoku(h, l)
    cloud_top = np.maximum(ichi["cloud_a"], ichi["cloud_b"])
    cloud_bot = np.minimum(ichi["cloud_a"], ichi["cloud_b"])
    f["ichi_tenkan"] = c / ichi["tenkan"] - 1.0
    f["ichi_kijun"] = c / ichi["kijun"] - 1.0
    f["ichi_tk_spread"] = ichi["tenkan"] / ichi["kijun"] - 1.0
    f["ichi_above_cloud"] = c / cloud_top - 1.0
    f["ichi_below_cloud"] = c / cloud_bot - 1.0
    f["ichi_future_cloud"] = (ichi["span_a"] - ichi["span_b"]) / c
    sar, sar_trend = ta.parabolic_sar(h, l)
    f["psar_dist"] = c / sar - 1.0
    f["psar_trend"] = sar_trend
    st_line, st_dir = ta.supertrend(h, l, c)
    f["supertrend_dist"] = c / st_line - 1.0
    f["supertrend_dir"] = st_dir

    # ---- oscillators ----------------------------------------------------------
    for n in (7, 14, 28):
        f[f"rsi{n}"] = ta.rsi(c, n) / 100.0
    st_k, st_d = ta.stochastic(h, l, c)
    f["stoch_k"] = st_k / 100.0
    f["stoch_kd"] = (st_k - st_d) / 100.0
    sr_k, sr_d = ta.stoch_rsi(c)
    f["stochrsi_k"] = sr_k / 100.0
    f["stochrsi_kd"] = (sr_k - sr_d) / 100.0
    f["williams_r"] = ta.williams_r(h, l, c) / 100.0
    f["cci20"] = ta.cci(h, l, c) / 100.0
    f["ultimate_osc"] = ta.ultimate_oscillator(h, l, c) / 100.0
    f["awesome_osc"] = ta.awesome_oscillator(h, l) / c
    f["tsi"] = ta.tsi(c) / 100.0
    f["cmo"] = ta.cmo(c) / 100.0
    f["connors_rsi"] = ta.connors_rsi(c) / 100.0
    ema13 = ta.ema(c, 13)
    f["elder_bull"] = (h - ema13) / c
    f["elder_bear"] = (l - ema13) / c
    f["streak"] = ta.streak(c).clip(-10, 10) / 10.0
    f["ret_rank100"] = ta.percent_rank(lr, 100) / 100.0

    # ---- volatility -----------------------------------------------------------
    atr14 = ta.atr(h, l, c, 14)
    f["natr14"] = atr14 / c
    f["atr_ratio_5_50"] = ta.safe_div(ta.atr(h, l, c, 5), ta.atr(h, l, c, 50))
    _, _, _, bb_pctb, bb_width = ta.bollinger(c)
    f["bb_pctb"] = bb_pctb
    f["bb_width"] = bb_width
    k_mid, k_up, k_lo = ta.keltner(h, l, c)
    f["keltner_pos"] = ta.safe_div(c - k_mid, k_up - k_mid)
    keltner_width = (k_up - k_lo) / k_mid
    f["keltner_width"] = keltner_width
    f["squeeze"] = ta.safe_div(bb_width, keltner_width)  # <1: Bollinger inside Keltner
    for n in (20, 55):
        d_hi, d_lo = ta.donchian(h, l, n)
        f[f"donchian{n}_pos"] = ta.safe_div(c - d_lo, d_hi - d_lo)
    d_hi, d_lo = ta.donchian(h, l, 20)
    f["donchian20_width"] = (d_hi - d_lo) / c
    for n in (10, 20, 60):
        f[f"rvol{n}"] = ta.realized_vol(lr, n)
    f["vol_ratio_10_60"] = ta.safe_div(f["rvol10"], f["rvol60"])
    f["parkinson20"] = ta.parkinson_vol(h, l)
    f["garman_klass20"] = ta.garman_klass_vol(o, h, l, c)
    f["rogers_satchell20"] = ta.rogers_satchell_vol(o, h, l, c)
    f["yang_zhang20"] = ta.yang_zhang_vol(o, h, l, c)
    f["ulcer14"] = ta.ulcer_index(c)
    f["chaikin_vol"] = ta.chaikin_volatility(h, l) / 100.0
    f["skew20"] = lr.rolling(20, min_periods=20).skew()
    f["skew60"] = lr.rolling(60, min_periods=60).skew()
    f["kurt60"] = lr.rolling(60, min_periods=60).kurt()
    f["autocorr60"] = lr.rolling(60, min_periods=60).corr(lr.shift(1))

    # ---- volume (only meaningful when the ticker reports volume) ---------------
    if (v > 0).mean() > 0.9:
        vs20 = ta.sma(v, 20)
        logv = np.log(v.where(v > 0))
        vsum20 = v.rolling(20, min_periods=20).sum()
        f["vol_rel20"] = np.log(ta.safe_div(v, vs20))
        f["vol_z60"] = ta.safe_div(logv - logv.rolling(60, min_periods=60).mean(),
                                   logv.rolling(60, min_periods=60).std())
        f["vol_trend"] = ta.safe_div(ta.sma(v, 5), vs20) - 1.0
        obv = ta.obv(c, v)
        f["obv_flow20"] = ta.safe_div(obv - obv.shift(20), vsum20)
        pvt = ta.pvt(c, v)
        f["pvt_flow20"] = ta.safe_div(pvt - pvt.shift(20), vsum20)
        f["cmf20"] = ta.cmf(h, l, c, v)
        f["chaikin_osc"] = ta.safe_div(ta.chaikin_oscillator(h, l, c, v), vs20)
        f["mfi14"] = ta.mfi(h, l, c, v) / 100.0
        f["force13"] = ta.safe_div(ta.force_index(c, v), c * vs20)
        f["emv14"] = ta.safe_div(ta.ease_of_movement(h, l, v) * vs20, c * c)
        f["vwap20_dist"] = c / ta.rolling_vwap(h, l, c, v) - 1.0

    # ---- candles & range ------------------------------------------------------
    rng = h - l
    f["candle_body"] = ta.safe_div(c - o, rng).fillna(0.0)
    f["upper_shadow"] = ta.safe_div(h - np.maximum(o, c), rng).fillna(0.0)
    f["lower_shadow"] = ta.safe_div(np.minimum(o, c) - l, rng).fillna(0.0)
    f["range_pct"] = rng / c
    f["gap"] = np.log(o / c.shift(1))
    f["intraday_ret"] = np.log(c / o)

    # ---- longer-range position --------------------------------------------------
    f["dist_52w_high"] = c / h.rolling(252, min_periods=252).max() - 1.0
    f["dist_52w_low"] = c / l.rolling(252, min_periods=252).min() - 1.0
    f["drawdown_ath"] = c / c.cummax() - 1.0

    # ---- calendar (known in advance, no leakage) --------------------------------
    idx = pd.DatetimeIndex(df.index)
    f["dow_sin"] = pd.Series(np.sin(2 * np.pi * idx.day_of_week / 5.0), index=df.index)
    f["dow_cos"] = pd.Series(np.cos(2 * np.pi * idx.day_of_week / 5.0), index=df.index)
    f["month_sin"] = pd.Series(np.sin(2 * np.pi * (idx.month - 1) / 12.0), index=df.index)
    f["month_cos"] = pd.Series(np.cos(2 * np.pi * (idx.month - 1) / 12.0), index=df.index)
    f["month_progress"] = pd.Series((idx.day - 1) / 30.0, index=df.index)

    if context:
        f.update(_context_features(df.index, c, lr, context))

    out = pd.DataFrame(f, index=df.index)
    return out.replace([np.inf, -np.inf], np.nan).astype(float)


def _align(series: pd.Series, index: pd.Index) -> pd.Series:
    """Re-index a context series onto the ticker's calendar using only past values."""
    return series.reindex(series.index.union(index)).ffill(limit=5).reindex(index)


def _context_features(index, c, lr, context) -> dict[str, pd.Series]:
    f: dict[str, pd.Series] = {}
    spy = context.get("spy")
    if spy is not None and len(spy) > 260:
        sc = spy["close"].astype(float)
        slr = _log_ret(sc)
        raw = {
            "spy_ret1": slr,
            "spy_ret5": _log_ret(sc, 5),
            "spy_ret20": _log_ret(sc, 20),
            "spy_dist_sma50": sc / ta.sma(sc, 50) - 1.0,
            "spy_dist_sma200": sc / ta.sma(sc, 200) - 1.0,
            "spy_rsi14": ta.rsi(sc, 14) / 100.0,
            "spy_rvol20": ta.realized_vol(slr, 20),
        }
        for k, s in raw.items():
            f[k] = _align(s, index)
        spy_c = _align(sc, index)
        spy_lr = np.log(spy_c / spy_c.shift(1))
        f["rel_ret20"] = _log_ret(c, 20) - np.log(spy_c / spy_c.shift(20))
        f["rel_ret60"] = _log_ret(c, 60) - np.log(spy_c / spy_c.shift(60))
        cov = lr.rolling(60, min_periods=60).cov(spy_lr)
        f["beta60"] = ta.safe_div(cov, spy_lr.rolling(60, min_periods=60).var())
        f["corr60"] = lr.rolling(60, min_periods=60).corr(spy_lr)
    vix = context.get("vix")
    if vix is not None and len(vix) > 260:
        vc = vix["close"].astype(float)
        raw = {
            "vix_log": np.log(vc),
            "vix_z60": ta.safe_div(vc - ta.sma(vc, 60), vc.rolling(60, min_periods=60).std()),
            "vix_chg1": _log_ret(vc, 1),
            "vix_chg5": _log_ret(vc, 5),
            "vix_vs_sma20": vc / ta.sma(vc, 20) - 1.0,
        }
        for k, s in raw.items():
            f[k] = _align(s, index)
    tnx = context.get("tnx")
    if tnx is not None and len(tnx) > 260:
        yc = tnx["close"].astype(float)
        raw = {
            "tnx_chg5": yc - yc.shift(5),
            "tnx_chg20": yc - yc.shift(20),
            "tnx_z252": ta.safe_div(yc - ta.sma(yc, 252), yc.rolling(252, min_periods=252).std()),
        }
        for k, s in raw.items():
            f[k] = _align(s, index)
    return f


# --------------------------------------------------------------------------- #
# targets
# --------------------------------------------------------------------------- #


def forward_returns(close: pd.Series, horizons) -> pd.DataFrame:
    """Log return from the close of bar t to the close of bar t+h (NaN when unknown)."""
    lc = np.log(close.astype(float))
    return pd.DataFrame({h: lc.shift(-h) - lc for h in horizons}, index=close.index)


def daily_vol(close: pd.Series, halflife: int = 20, floor: float = 0.002) -> pd.Series:
    """EWMA estimate of daily log-return volatility known at the close of bar t.

    Targets are divided by ``vol * sqrt(h)`` so the networks learn
    regime-independent, roughly unit-variance targets.
    """
    lr = np.log(close.astype(float)).diff()
    return lr.ewm(halflife=halflife, min_periods=10).std().clip(lower=floor)


# --------------------------------------------------------------------------- #
# human-readable snapshot
# --------------------------------------------------------------------------- #


def indicator_snapshot(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Latest values of popular indicators with a plain-English reading."""
    o, h, l, c, v = (df[k].astype(float) for k in ("open", "high", "low", "close", "volume"))
    rows: list[tuple[str, str, str]] = []

    def last(s):
        s = s.dropna()
        return float(s.iloc[-1]) if len(s) else float("nan")

    r = last(ta.rsi(c, 14))
    rows.append(("RSI(14)", f"{r:.1f}", "overbought" if r > 70 else "oversold" if r < 30 else "neutral"))
    _, _, hist = ta.macd(c)
    hv, hprev = last(hist), float(hist.dropna().iloc[-2]) if hist.notna().sum() > 1 else float("nan")
    trend = "bullish" if hv > 0 else "bearish"
    if np.sign(hv) != np.sign(hprev):
        trend += " (just crossed)"
    rows.append(("MACD histogram", f"{hv:+.3f}", trend))
    k, _ = ta.stochastic(h, l, c)
    kv = last(k)
    rows.append(("Stochastic %K", f"{kv:.1f}", "overbought" if kv > 80 else "oversold" if kv < 20 else "neutral"))
    pdi, mdi, adx = ta.adx(h, l, c)
    av = last(adx)
    strength = "strong trend" if av > 25 else "weak / no trend" if av < 20 else "developing trend"
    rows.append(("ADX(14)", f"{av:.1f}", f"{strength}, {'+DI' if last(pdi) > last(mdi) else '-DI'} leads"))
    _, _, _, pctb, _ = ta.bollinger(c)
    bv = last(pctb)
    rows.append(("Bollinger %B", f"{bv:.2f}",
                 "above upper band" if bv > 1 else "below lower band" if bv < 0 else "inside bands"))
    s50, s200 = last(ta.sma(c, 50)), last(ta.sma(c, 200))
    cl = float(c.iloc[-1])
    rows.append(("vs SMA50", f"{(cl / s50 - 1) * 100:+.1f}%", "above" if cl > s50 else "below"))
    rows.append(("vs SMA200", f"{(cl / s200 - 1) * 100:+.1f}%",
                 ("above" if cl > s200 else "below") + ("; golden cross" if s50 > s200 else "; death cross")))
    _, st_dir = ta.supertrend(h, l, c)
    rows.append(("Supertrend", "up" if last(st_dir) > 0 else "down", ""))
    rows.append(("ATR(14) % of price", f"{last(ta.atr(h, l, c, 14)) / cl * 100:.2f}%", "typical daily range"))
    rows.append(("20d realised vol", f"{last(ta.realized_vol(np.log(c).diff(), 20)) * 100:.1f}%", "annualised"))
    if (v > 0).mean() > 0.9:
        mv = last(ta.mfi(h, l, c, v))
        rows.append(("MFI(14)", f"{mv:.1f}", "overbought" if mv > 80 else "oversold" if mv < 20 else "neutral"))
        cv = last(ta.cmf(h, l, c, v))
        rows.append(("Chaikin money flow", f"{cv:+.2f}", "accumulation" if cv > 0 else "distribution"))
    hi52 = float(h.iloc[-252:].max())
    rows.append(("vs 52-week high", f"{(cl / hi52 - 1) * 100:+.1f}%", ""))
    return rows
