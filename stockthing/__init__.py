"""stockthing - stock forecasting from technical indicators with neural networks.

Pipeline: OHLCV history -> ~120 causal indicator features -> sequence windows ->
LSTM / GRU / TCN / Transformer / MLP (+ gradient boosting and linear baselines)
-> multi-horizon quantile forecasts and P(up) -> walk-forward backtest.
"""

__version__ = "0.1.0"
