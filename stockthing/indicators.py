"""Technical indicators, implemented with pandas / numpy only.

Every function is strictly causal: the value at bar ``t`` depends only on bars
``<= t``. ``tests/test_indicators.py`` checks this by recomputing everything on
truncated histories and comparing.

Inputs are float ``pd.Series`` sharing one ``DatetimeIndex``. Outputs keep that
index; warm-up bars are NaN.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def safe_div(a, b):
    """``a / b`` with +-inf mapped to NaN (division by zero yields NaN)."""
    out = a / b
    if isinstance(out, (pd.Series, pd.DataFrame)):
        return out.replace([np.inf, -np.inf], np.nan)
    return np.where(np.isfinite(out), out, np.nan)


def _roll(s: pd.Series, n: int):
    return s.rolling(n, min_periods=n)


# --------------------------------------------------------------------------- #
# moving averages
# --------------------------------------------------------------------------- #


def sma(s: pd.Series, n: int) -> pd.Series:
    """Simple moving average."""
    return _roll(s, n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    """Exponential moving average (span ``n``, recursive form)."""
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def wilder(s: pd.Series, n: int) -> pd.Series:
    """Wilder's smoothing (RMA): an EMA with ``alpha = 1/n``."""
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def wma(s: pd.Series, n: int) -> pd.Series:
    """Linearly weighted moving average (most recent bar weighted ``n``)."""
    w = np.arange(1, n + 1, dtype=float)
    w /= w.sum()
    return _roll(s, n).apply(lambda x: float(np.dot(x, w)), raw=True)


def dema(s: pd.Series, n: int) -> pd.Series:
    """Double exponential moving average."""
    e1 = ema(s, n)
    return 2.0 * e1 - ema(e1, n)


def tema(s: pd.Series, n: int) -> pd.Series:
    """Triple exponential moving average."""
    e1 = ema(s, n)
    e2 = ema(e1, n)
    return 3.0 * e1 - 3.0 * e2 + ema(e2, n)


def hma(s: pd.Series, n: int) -> pd.Series:
    """Hull moving average."""
    return wma(2.0 * wma(s, max(n // 2, 1)) - wma(s, n), max(int(np.sqrt(n)), 1))


def kama(close: pd.Series, n: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
    """Kaufman adaptive moving average."""
    change = (close - close.shift(n)).abs()
    noise = _roll(close.diff().abs(), n).sum()
    er = safe_div(change, noise).fillna(0.0).where(noise.notna())
    fast_sc, slow_sc = 2.0 / (fast + 1), 2.0 / (slow + 1)
    sc = ((er * (fast_sc - slow_sc) + slow_sc) ** 2).to_numpy()
    c = close.to_numpy(dtype=float)
    out = np.full(len(c), np.nan)
    valid = np.flatnonzero(~np.isnan(sc))
    if len(valid):
        i0 = valid[0]
        out[i0] = c[i0]
        for i in range(i0 + 1, len(c)):
            k = sc[i] if not np.isnan(sc[i]) else 0.0
            out[i] = out[i - 1] + k * (c[i] - out[i - 1])
    return pd.Series(out, index=close.index)


# --------------------------------------------------------------------------- #
# trend
# --------------------------------------------------------------------------- #


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line and histogram."""
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def ppo(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Percentage price oscillator (MACD in percent of the slow EMA)."""
    slow_ema = ema(close, slow)
    line = 100.0 * safe_div(ema(close, fast) - slow_ema, slow_ema)
    sig = ema(line, signal)
    return line, sig, line - sig


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev = close.shift(1)
    return pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Average true range (Wilder)."""
    return wilder(true_range(high, low, close), n)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14):
    """Directional movement system: (+DI, -DI, ADX)."""
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    rng = wilder(true_range(high, low, close), n)
    plus_di = 100.0 * safe_div(wilder(plus_dm, n), rng)
    minus_di = 100.0 * safe_div(wilder(minus_dm, n), rng)
    dx = 100.0 * safe_div((plus_di - minus_di).abs(), plus_di + minus_di)
    return plus_di, minus_di, wilder(dx, n)


def aroon(high: pd.Series, low: pd.Series, n: int = 25):
    """Aroon up / down (0..100): how recently the n-bar high / low occurred."""

    def bars_since_extreme(fn):
        # position of the most recent extreme inside the (n+1)-bar window
        return lambda x: float(len(x) - 1 - fn(x[::-1]))

    up = 100.0 * high.rolling(n + 1, min_periods=n + 1).apply(bars_since_extreme(np.argmax), raw=True) / n
    dn = 100.0 * low.rolling(n + 1, min_periods=n + 1).apply(bars_since_extreme(np.argmin), raw=True) / n
    return up, dn


def trix(close: pd.Series, n: int = 15) -> pd.Series:
    """TRIX: 1-bar % change of a triple-smoothed EMA."""
    e3 = ema(ema(ema(close, n), n), n)
    return 100.0 * (e3 / e3.shift(1) - 1.0)


def vortex(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14):
    """Vortex indicator (VI+, VI-)."""
    tr = _roll(true_range(high, low, close), n).sum()
    vp = _roll((high - low.shift(1)).abs(), n).sum()
    vm = _roll((low - high.shift(1)).abs(), n).sum()
    return safe_div(vp, tr), safe_div(vm, tr)


def mass_index(high: pd.Series, low: pd.Series, fast: int = 9, slow: int = 25) -> pd.Series:
    """Mass index (range expansion / reversal bulge detector)."""
    e1 = ema(high - low, fast)
    return _roll(safe_div(e1, ema(e1, fast)), slow).sum()


def dpo(close: pd.Series, n: int = 20) -> pd.Series:
    """Detrended price oscillator (causal form: past price minus current SMA)."""
    return close.shift(n // 2 + 1) - sma(close, n)


def roc(close: pd.Series, n: int) -> pd.Series:
    """Rate of change in percent."""
    return 100.0 * (close / close.shift(n) - 1.0)


def kst(close: pd.Series):
    """Know Sure Thing oscillator and its signal line."""
    k = (
        sma(roc(close, 10), 10)
        + 2 * sma(roc(close, 15), 10)
        + 3 * sma(roc(close, 20), 10)
        + 4 * sma(roc(close, 30), 15)
    )
    return k, sma(k, 9)


def ichimoku(high: pd.Series, low: pd.Series, conv: int = 9, base: int = 26, span: int = 52, disp: int = 26):
    """Ichimoku lines. The lagging (chikou) span is omitted because aligning it
    at bar t would use future prices. ``cloud_a/cloud_b`` are the spans that are
    plotted *at* bar t (computed ``disp`` bars earlier); ``span_a/span_b`` are the
    spans computed now (plotted ``disp`` bars ahead)."""

    def mid(n):
        return (_roll(high, n).max() + _roll(low, n).min()) / 2.0

    tenkan, kijun = mid(conv), mid(base)
    span_a = (tenkan + kijun) / 2.0
    span_b = mid(span)
    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "span_a": span_a,
        "span_b": span_b,
        "cloud_a": span_a.shift(disp),
        "cloud_b": span_b.shift(disp),
    }


def parabolic_sar(high: pd.Series, low: pd.Series, step: float = 0.02, max_af: float = 0.2):
    """Wilder's parabolic stop-and-reverse. Returns (sar, trend) with trend +1/-1."""
    h = high.to_numpy(dtype=float)
    lo = low.to_numpy(dtype=float)
    n = len(h)
    sar = np.full(n, np.nan)
    trend = np.full(n, np.nan)
    if n < 2:
        return pd.Series(sar, index=high.index), pd.Series(trend, index=high.index)
    up = True
    af = step
    ep = h[0]
    s = lo[0]
    for i in range(1, n):
        s = s + af * (ep - s)
        if up:
            s = min(s, lo[i - 1], lo[i - 2] if i >= 2 else lo[i - 1])
            if lo[i] < s:
                up, s, ep, af = False, ep, lo[i], step
            elif h[i] > ep:
                ep, af = h[i], min(af + step, max_af)
        else:
            s = max(s, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > s:
                up, s, ep, af = True, ep, h[i], step
            elif lo[i] < ep:
                ep, af = lo[i], min(af + step, max_af)
        sar[i] = s
        trend[i] = 1.0 if up else -1.0
    return pd.Series(sar, index=high.index), pd.Series(trend, index=high.index)


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 10, mult: float = 3.0):
    """ATR-band trend follower. Returns (line, direction) with direction +1/-1."""
    a = atr(high, low, close, n).to_numpy()
    hl2 = ((high + low) / 2.0).to_numpy()
    c = close.to_numpy(dtype=float)
    upper_basic, lower_basic = hl2 + mult * a, hl2 - mult * a
    T = len(c)
    upper = np.full(T, np.nan)
    lower = np.full(T, np.nan)
    line = np.full(T, np.nan)
    direction = np.full(T, np.nan)
    prev = None
    for i in range(T):
        if np.isnan(a[i]):
            continue
        if prev is None:
            upper[i], lower[i], d = upper_basic[i], lower_basic[i], 1.0
        else:
            upper[i] = upper_basic[i] if (upper_basic[i] < upper[prev] or c[prev] > upper[prev]) else upper[prev]
            lower[i] = lower_basic[i] if (lower_basic[i] > lower[prev] or c[prev] < lower[prev]) else lower[prev]
            d = direction[prev]
            if d < 0 and c[i] > upper[i]:
                d = 1.0
            elif d > 0 and c[i] < lower[i]:
                d = -1.0
        direction[i] = d
        line[i] = lower[i] if d > 0 else upper[i]
        prev = i
    return pd.Series(line, index=close.index), pd.Series(direction, index=close.index)


def linreg(s: pd.Series, n: int):
    """Rolling OLS of ``s`` on time: (slope per bar, R^2)."""
    t = pd.Series(np.arange(len(s), dtype=float), index=s.index)
    cov = s.rolling(n, min_periods=n).cov(t)
    var_t = n * (n + 1) / 12.0  # sample variance of 0..n-1
    corr = s.rolling(n, min_periods=n).corr(t)
    return cov / var_t, corr**2


# --------------------------------------------------------------------------- #
# momentum / oscillators
# --------------------------------------------------------------------------- #


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    """Relative strength index (Wilder), 0..100."""
    delta = s.diff()
    gain = wilder(delta.clip(lower=0.0), n)
    loss = wilder((-delta).clip(lower=0.0), n)
    out = 100.0 - 100.0 / (1.0 + safe_div(gain, loss))
    out = out.where(loss > 0, 100.0)
    out = out.where(~((gain == 0) & (loss == 0)), 50.0)
    return out.where(gain.notna() & loss.notna())


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14, smooth_k: int = 3, smooth_d: int = 3):
    """Slow stochastic oscillator (%K, %D), 0..100."""
    ll, hh = _roll(low, n).min(), _roll(high, n).max()
    k = _roll(100.0 * safe_div(close - ll, hh - ll), smooth_k).mean()
    return k, _roll(k, smooth_d).mean()


def stoch_rsi(close: pd.Series, n: int = 14, smooth_k: int = 3, smooth_d: int = 3):
    """Stochastic RSI (%K, %D), 0..100."""
    r = rsi(close, n)
    lo, hi = _roll(r, n).min(), _roll(r, n).max()
    k = _roll(100.0 * safe_div(r - lo, hi - lo), smooth_k).mean()
    return k, _roll(k, smooth_d).mean()


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Williams %R, -100..0."""
    hh, ll = _roll(high, n).max(), _roll(low, n).min()
    return -100.0 * safe_div(hh - close, hh - ll)


def cci(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 20) -> pd.Series:
    """Commodity channel index."""
    tp = (high + low + close) / 3.0
    mad = _roll(tp, n).apply(lambda x: float(np.mean(np.abs(x - x.mean()))), raw=True)
    return safe_div(tp - _roll(tp, n).mean(), 0.015 * mad)


def ultimate_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, s: int = 7, m: int = 14, l: int = 28):
    """Larry Williams' ultimate oscillator, 0..100."""
    prev = close.shift(1)
    lo = pd.concat([low, prev], axis=1).min(axis=1)
    hi = pd.concat([high, prev], axis=1).max(axis=1)
    bp, tr = close - lo, hi - lo

    def avg(n):
        return safe_div(_roll(bp, n).sum(), _roll(tr, n).sum())

    return 100.0 * (4 * avg(s) + 2 * avg(m) + avg(l)) / 7.0


def awesome_oscillator(high: pd.Series, low: pd.Series, fast: int = 5, slow: int = 34) -> pd.Series:
    mp = (high + low) / 2.0
    return sma(mp, fast) - sma(mp, slow)


def tsi(close: pd.Series, long: int = 25, short: int = 13) -> pd.Series:
    """True strength index, -100..100."""
    m = close.diff()
    return 100.0 * safe_div(ema(ema(m, long), short), ema(ema(m.abs(), long), short))


def cmo(close: pd.Series, n: int = 14) -> pd.Series:
    """Chande momentum oscillator, -100..100."""
    d = close.diff()
    up = _roll(d.clip(lower=0.0), n).sum()
    dn = _roll((-d).clip(lower=0.0), n).sum()
    return 100.0 * safe_div(up - dn, up + dn)


def streak(close: pd.Series) -> pd.Series:
    """Signed count of consecutive up (+) / down (-) closes."""
    d = np.sign(close.diff().to_numpy())
    out = np.zeros(len(d))
    for i in range(1, len(d)):
        if d[i] > 0:
            out[i] = out[i - 1] + 1 if out[i - 1] > 0 else 1
        elif d[i] < 0:
            out[i] = out[i - 1] - 1 if out[i - 1] < 0 else -1
    return pd.Series(out, index=close.index)


def percent_rank(s: pd.Series, n: int = 100) -> pd.Series:
    """Percent of the previous n-1 values below the current one (0..100)."""
    return _roll(s, n).apply(lambda x: float((x[:-1] < x[-1]).mean() * 100.0), raw=True)


def connors_rsi(close: pd.Series, n_rsi: int = 3, n_streak: int = 2, n_rank: int = 100) -> pd.Series:
    """Connors RSI = mean(RSI(close,3), RSI(streak,2), PercentRank(ROC1,100))."""
    return (rsi(close, n_rsi) + rsi(streak(close), n_streak) + percent_rank(roc(close, 1), n_rank)) / 3.0


# --------------------------------------------------------------------------- #
# volatility
# --------------------------------------------------------------------------- #


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    """Bollinger bands: (mid, upper, lower, %B, bandwidth)."""
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    upper, lower = mid + k * sd, mid - k * sd
    return mid, upper, lower, safe_div(close - lower, upper - lower), safe_div(upper - lower, mid)


def keltner(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 20, atr_n: int = 10, k: float = 2.0):
    """Keltner channel: (mid, upper, lower)."""
    mid = ema(close, n)
    a = atr(high, low, close, atr_n)
    return mid, mid + k * a, mid - k * a


def donchian(high: pd.Series, low: pd.Series, n: int = 20):
    """Donchian channel: (upper, lower)."""
    return _roll(high, n).max(), _roll(low, n).min()


def realized_vol(logret: pd.Series, n: int) -> pd.Series:
    """Annualised close-to-close volatility."""
    return _roll(logret, n).std() * np.sqrt(252.0)


def parkinson_vol(high: pd.Series, low: pd.Series, n: int = 20) -> pd.Series:
    x = np.log(high / low) ** 2
    return np.sqrt(_roll(x, n).mean() / (4.0 * np.log(2.0)) * 252.0)


def garman_klass_vol(open_, high, low, close, n: int = 20) -> pd.Series:
    x = 0.5 * np.log(high / low) ** 2 - (2.0 * np.log(2.0) - 1.0) * np.log(close / open_) ** 2
    return np.sqrt(_roll(x, n).mean().clip(lower=0.0) * 252.0)


def rogers_satchell_vol(open_, high, low, close, n: int = 20) -> pd.Series:
    x = np.log(high / close) * np.log(high / open_) + np.log(low / close) * np.log(low / open_)
    return np.sqrt(_roll(x, n).mean().clip(lower=0.0) * 252.0)


def yang_zhang_vol(open_, high, low, close, n: int = 20) -> pd.Series:
    overnight = np.log(open_ / close.shift(1))
    intraday = np.log(close / open_)
    rs = np.log(high / close) * np.log(high / open_) + np.log(low / close) * np.log(low / open_)
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    var = _roll(overnight, n).var() + k * _roll(intraday, n).var() + (1 - k) * _roll(rs, n).mean()
    return np.sqrt(var.clip(lower=0.0) * 252.0)


def ulcer_index(close: pd.Series, n: int = 14) -> pd.Series:
    dd = 100.0 * (close / _roll(close, n).max() - 1.0)
    return np.sqrt(_roll(dd**2, n).mean())


def chaikin_volatility(high: pd.Series, low: pd.Series, n: int = 10) -> pd.Series:
    e = ema(high - low, n)
    return 100.0 * (e / e.shift(n) - 1.0)


# --------------------------------------------------------------------------- #
# volume
# --------------------------------------------------------------------------- #


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-balance volume."""
    return (np.sign(close.diff()).fillna(0.0) * volume).cumsum()


def money_flow_multiplier(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    return safe_div((close - low) - (high - close), high - low).fillna(0.0)


def adl(high, low, close, volume) -> pd.Series:
    """Accumulation / distribution line."""
    return (money_flow_multiplier(high, low, close) * volume).cumsum()


def cmf(high, low, close, volume, n: int = 20) -> pd.Series:
    """Chaikin money flow, -1..1."""
    mfv = money_flow_multiplier(high, low, close) * volume
    return safe_div(_roll(mfv, n).sum(), _roll(volume, n).sum())


def chaikin_oscillator(high, low, close, volume, fast: int = 3, slow: int = 10) -> pd.Series:
    a = adl(high, low, close, volume)
    return ema(a, fast) - ema(a, slow)


def mfi(high, low, close, volume, n: int = 14) -> pd.Series:
    """Money flow index (volume-weighted RSI), 0..100."""
    tp = (high + low + close) / 3.0
    flow = tp * volume
    d = tp.diff()
    pos = _roll(flow.where(d > 0, 0.0), n).sum()
    neg = _roll(flow.where(d < 0, 0.0), n).sum()
    out = 100.0 - 100.0 / (1.0 + safe_div(pos, neg))
    out = out.where(neg > 0, 100.0)
    out = out.where(~((pos == 0) & (neg == 0)), 50.0)
    return out.where(pos.notna())


def force_index(close: pd.Series, volume: pd.Series, n: int = 13) -> pd.Series:
    return ema(close.diff() * volume, n)


def ease_of_movement(high, low, volume, n: int = 14) -> pd.Series:
    mid = (high + low) / 2.0
    return sma(safe_div(mid.diff() * (high - low), volume), n)


def rolling_vwap(high, low, close, volume, n: int = 20) -> pd.Series:
    tp = (high + low + close) / 3.0
    return safe_div(_roll(tp * volume, n).sum(), _roll(volume, n).sum())


def pvt(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Price-volume trend."""
    return ((close / close.shift(1) - 1.0).fillna(0.0) * volume).cumsum()
