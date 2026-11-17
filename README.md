# stockthing

Stock forecasting from historical prices, ~150 technical-indicator features and a
stack of neural networks, with an honest out-of-sample backtest.

```
OHLCV history (Yahoo Finance, split/dividend adjusted)  +  S&P 500, VIX, 10y yield
        │
        ▼
~150 causal features: returns, MAs, MACD, RSI, stochastics, ADX, Ichimoku, SAR,
Supertrend, Bollinger/Keltner/Donchian, ATR + 5 volatility estimators, OBV, MFI,
CMF, VWAP, candles, 52-week range, calendar, market context …
        │  60-day windows, scaled on training data only
        ▼
LSTM · GRU · TCN · Transformer · MLP  +  gradient boosting · linear  →  ensemble
        │  each predicts 10/50/90% quantiles of the 1, 5 and 20-day return + P(up)
        ▼
walk-forward backtest (purged labels)  →  forecast  →  HTML report
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch   # or your CUDA build
pip install -e .
```

```bash
python -m stockthing run AAPL
```

`run` downloads the data, runs a 4-year walk-forward backtest, trains the final
models on all history, prints the forecast and writes everything (including
`report.html` and the trained models) to `runs/<ticker>_<timestamp>/`. On a
4-core CPU this takes about 7 minutes per ticker; add `--quick` for a
90-second first look.

Other commands:

| command | what it does |
|---|---|
| `python -m stockthing fetch AAPL MSFT` | download and cache price history in `./data` |
| `python -m stockthing indicators AAPL` | latest RSI, MACD, ADX, Bollinger, MFI … with a plain reading |
| `python -m stockthing backtest AAPL --report` | walk-forward evaluation only |
| `python -m stockthing train AAPL --out models/aapl` | fit on all history and save a model bundle |
| `python -m stockthing predict AAPL --model-dir models/aapl` | forecast with a saved bundle (trains one if missing) |

Several tickers train one pooled model (features are scale-free, so this works
and gives the networks much more data):

```bash
python -m stockthing run AAPL MSFT NVDA GOOGL AMZN
```

Useful options: `--models lstm tcn gbm`, `--horizons 1 5 20`, `--seq-len 60`,
`--epochs 40`, `--seeds 3` (average several networks per architecture),
`--folds 4 --fold-days 252`, `--cost-bps 5`, `--start 2005-01-01`,
`--end 2024-12-31` (pretend "today" is earlier), `--no-context`, `--quick`.
Any CSV with date/open/high/low/close/volume columns works in place of a ticker.

## What the output means

For each horizon the ensemble gives a median price, a 10–90% range and P(up),
the probability that the price is higher at that horizon. The backtest scores
every model on days it never saw:

* **hit rate** – share of correct up/down calls; compare with **always-up**,
  the hit rate of simply betting the stock rises (stocks drift upwards, so this
  is often 52–56% and hard to beat);
* **edge** – hit rate minus the better trivial call; **z** – that edge in
  standard errors (overlapping horizons counted as n/h samples), so |z| < 2 is
  indistinguishable from luck;
* **AUC / IC** – ranking skill of P(up) and of the predicted median;
* **coverage** – share of outcomes inside the 10–90% band (should be ~80%);
* **backtests** – trade P(up) daily (long or cash, long or short) after costs,
  against buy and hold over the same days.

Expect hit rates around 50–54% and edges inside ±3 pp: daily stock returns are
close to unpredictable from past prices. This project is built so that it
*cannot* fool you about that (see below). It is a research tool, not financial
advice.

## How look-ahead bias is prevented

* every indicator uses only bars up to *t* (tested by recomputing every feature
  on truncated histories);
* the target for bar *t* is the log return from close *t* to close *t+h*;
* walk-forward folds train only on data before the test block, and any training
  or validation label whose *t+h* falls in the following block is purged;
* feature scaling is fit on training rows only; early stopping uses a later,
  purged validation slice;
* a test trains on a pure random walk and checks that nothing beats a coin flip,
  and another plants an AR(1) signal and checks the models find it.

## Layout

```
stockthing/
  data.py        Yahoo download, CSV import, cache, synthetic data
  indicators.py  ~45 technical indicators (pandas / numpy)
  features.py    feature matrix, targets, indicator snapshot
  dataset.py     windows, purged walk-forward splits, scaler
  models.py      LSTM, GRU, TCN, Transformer, MLP + quantile/direction head
  training.py    training loops; gradient boosting, linear and no-skill baselines
  evaluation.py  forecast metrics and backtests
  pipeline.py    walk-forward, final fit, forecast, model bundles
  report.py      self-contained HTML report
  cli.py         command line
tests/           pytest suite (python -m pytest)
```
