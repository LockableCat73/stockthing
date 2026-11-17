"""Price data: Yahoo Finance download (no API key), CSV import, local cache and
synthetic series for tests / offline demos."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) stockthing/0.1"

# Market-wide series used as extra features (key -> Yahoo symbol).
CONTEXT_SYMBOLS = {"spy": "SPY", "vix": "^VIX", "tnx": "^TNX"}


def data_dir() -> Path:
    d = Path(os.environ.get("STOCKTHING_DATA", "data"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(symbol: str) -> Path:
    return data_dir() / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', symbol.upper())}.csv"


# --------------------------------------------------------------------------- #
# cleaning
# --------------------------------------------------------------------------- #


def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Sort, de-duplicate, dividend-adjust and sanity-fix an OHLCV frame.

    If an ``adj_close`` column is present, open/high/low/close are scaled by
    ``adj_close / close`` so that returns include dividends and splits.
    """
    df = df.copy()
    df.index = pd.DatetimeIndex(df.index).tz_localize(None) if getattr(df.index, "tz", None) else pd.DatetimeIndex(df.index)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in OHLCV + ["adj_close"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    df = df[df["close"].notna() & (df["close"] > 0)]
    if "adj_close" in df:
        factor = df["adj_close"] / df["close"]
        factor = factor.where(np.isfinite(factor) & (factor > 0), 1.0)
        for col in ("open", "high", "low", "close"):
            if col in df:
                df[col] = df[col] * factor
    for col in ("open", "high", "low"):
        if col not in df:
            df[col] = df["close"]
        df[col] = df[col].where(df[col] > 0, df["close"])
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    if "volume" not in df:
        df["volume"] = 0.0
    df["volume"] = df["volume"].fillna(0.0).clip(lower=0.0)
    df.index.name = "date"
    return df[OHLCV]


# --------------------------------------------------------------------------- #
# Yahoo Finance
# --------------------------------------------------------------------------- #


def fetch_yahoo(symbol: str, start: str = "1970-01-01", end: str | None = None, *, timeout: float = 30.0,
                retries: int = 4, drop_incomplete: bool = True) -> pd.DataFrame:
    """Download daily bars from Yahoo's public chart endpoint.

    The bar for a session that is still in progress is dropped (its "close" is
    just the latest trade) unless ``drop_incomplete=False``.
    """
    p1 = int(pd.Timestamp(start).tz_localize("UTC").timestamp())
    p2 = int((pd.Timestamp(end).tz_localize("UTC") if end else pd.Timestamp.now(tz="UTC")).timestamp()) + 86400
    query = urllib.parse.urlencode({"period1": p1, "period2": p2, "interval": "1d",
                                    "events": "div,splits", "includeAdjustedClose": "true"})
    url = YAHOO_CHART.format(symbol=urllib.parse.quote(symbol, safe="")) + "?" + query
    last_err: Exception | None = None
    payload = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise ValueError(f"unknown symbol {symbol!r} (HTTP 404 from Yahoo)") from e
            last_err = e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as e:
            last_err = e
        time.sleep(1.5 * 2**attempt)
    if payload is None:
        raise ConnectionError(f"could not download {symbol}: {last_err}")

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise ValueError(f"Yahoo error for {symbol}: {chart['error']}")
    res = (chart.get("result") or [None])[0]
    if not res or not res.get("timestamp"):
        raise ValueError(f"no price data returned for {symbol!r}")

    meta = res.get("meta", {})
    tz = meta.get("exchangeTimezoneName") or "America/New_York"
    stamps = np.asarray(res["timestamp"], dtype="int64")
    dates = pd.to_datetime(stamps, unit="s", utc=True).tz_convert(tz).tz_localize(None).normalize()
    quote = res["indicators"]["quote"][0]
    n = len(stamps)
    frame = {k: np.array(quote.get(k) or [None] * n, dtype=float) for k in OHLCV}
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    if adj is not None:
        frame["adj_close"] = np.array(adj, dtype=float)
    df = pd.DataFrame(frame, index=dates)

    if drop_incomplete and len(df):
        regular = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
        start_ts, end_ts = regular.get("start"), regular.get("end")
        if start_ts and end_ts and stamps[-1] >= start_ts and time.time() < end_ts:
            df = df.iloc[:-1]
    return clean_ohlcv(df)


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #


def read_price_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV with a date column and open/high/low/close[/adj close]/volume
    columns (names are matched case-insensitively, e.g. Yahoo or Stooq exports)."""
    raw = pd.read_csv(path)
    raw.columns = [re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") for c in raw.columns]
    date_col = next((c for c in ("date", "datetime", "timestamp", "time") if c in raw.columns), raw.columns[0])
    idx = pd.DatetimeIndex(pd.to_datetime(raw[date_col], utc=True)).tz_convert(None)
    aliases = {"adj_close": ("adj_close", "adjclose", "adjusted_close", "adj"), "volume": ("volume", "vol")}
    out = pd.DataFrame(index=idx)
    for col in ("open", "high", "low", "close", "volume", "adj_close"):
        for name in aliases.get(col, (col,)):
            if name in raw.columns:
                out[col] = pd.to_numeric(raw[name], errors="coerce").to_numpy()
                break
    if "close" not in out:
        raise ValueError(f"{path}: no 'close' column found (columns: {list(raw.columns)})")
    return clean_ohlcv(out)


# --------------------------------------------------------------------------- #
# public loader
# --------------------------------------------------------------------------- #


def load_prices(symbol: str, start: str | None = None, end: str | None = None, *, refresh: bool = False,
                max_age_hours: float = 12.0) -> pd.DataFrame:
    """Daily OHLCV for ``symbol`` (a ticker, or a path to a CSV file).

    Downloads are cached under ``$STOCKTHING_DATA`` (default ``./data``) and
    reused for ``max_age_hours``. If a download fails, a stale cache is used.
    """
    if symbol.lower().endswith(".csv") or Path(symbol).is_file():
        df = read_price_csv(symbol)
    else:
        path = _cache_path(symbol)
        fresh = path.exists() and (time.time() - path.stat().st_mtime) / 3600.0 < max_age_hours
        if fresh and not refresh:
            df = read_price_csv(path)
        else:
            try:
                df = fetch_yahoo(symbol)
                df.to_csv(path)
            except Exception as e:  # network / API problems -> fall back to cache
                if not path.exists():
                    raise
                warnings.warn(f"download of {symbol} failed ({e}); using cached copy {path}")
                df = read_price_csv(path)
    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]
    if df.empty:
        raise ValueError(f"no data for {symbol!r} in the requested date range")
    return df


def load_context(start: str | None = None, end: str | None = None, *, refresh: bool = False,
                 symbols: dict[str, str] | None = None) -> dict[str, pd.DataFrame]:
    """Market context series (S&P 500 ETF, VIX, 10-year yield). Missing ones are skipped."""
    out: dict[str, pd.DataFrame] = {}
    for key, sym in (symbols or CONTEXT_SYMBOLS).items():
        try:
            out[key] = load_prices(sym, start, end, refresh=refresh)
        except Exception as e:
            warnings.warn(f"market context {sym} unavailable: {e}")
    return out


# --------------------------------------------------------------------------- #
# synthetic data
# --------------------------------------------------------------------------- #


def synthetic_prices(n: int = 3000, seed: int = 0, *, ar: float = 0.0, drift: float = 2e-4,
                     start: str = "2010-01-04") -> pd.DataFrame:
    """GARCH(1,1)-style random walk with optional AR(1) return predictability.

    ``ar=0`` gives an unpredictable series (useful to check for look-ahead
    leaks: nothing should beat a coin flip); ``ar>0`` plants a learnable signal.
    """
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n)
    r = np.zeros(n)
    var = np.full(n, 1e-4)
    for t in range(1, n):
        var[t] = 2e-6 + 0.08 * (r[t - 1] - drift) ** 2 + 0.90 * var[t - 1]
        r[t] = drift + ar * (r[t - 1] - drift) + np.sqrt(var[t]) * eps[t]
    close = 100.0 * np.exp(np.cumsum(r))
    sd = np.sqrt(var)
    open_ = close * np.exp(-r * rng.uniform(0.2, 0.8, n))  # part of the move happens intraday
    hi = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0, 0.6, n)) * sd)
    lo = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0, 0.6, n)) * sd)
    volume = np.exp(14.0 + 25.0 * np.abs(r) + rng.normal(0, 0.3, n))
    idx = pd.bdate_range(start, periods=n, name="date")
    return pd.DataFrame({"open": open_, "high": hi, "low": lo, "close": close, "volume": volume}, index=idx)
