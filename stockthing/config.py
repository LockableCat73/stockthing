"""Run configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace

from .models import NN_MODELS

CLASSICAL_MODELS = ("gbm", "linear")
DEFAULT_MODELS = NN_MODELS + CLASSICAL_MODELS


@dataclass
class Config:
    # data
    start: str | None = "2000-01-01"
    end: str | None = None
    context: bool = True                    # add S&P 500 / VIX / 10y-yield features
    # targets
    horizons: tuple[int, ...] = (1, 5, 20)  # trading days ahead
    quantiles: tuple[float, ...] = (0.1, 0.5, 0.9)
    # models
    models: tuple[str, ...] = DEFAULT_MODELS
    seq_len: int = 60
    hidden: int = 64
    layers: int = 2
    dropout: float = 0.25
    # optimisation
    lr: float = 1e-3
    weight_decay: float = 1e-3
    batch_size: int = 256
    max_epochs: int = 40
    patience: int = 5
    bce_weight: float = 1.0
    input_noise: float = 0.05
    val_frac: float = 0.15
    seeds: int = 1                          # networks trained per architecture (averaged)
    gbm_iter: int = 150
    # walk-forward evaluation
    folds: int = 4
    fold_days: int = 252
    # backtest
    cost_bps: float = 5.0                   # per unit of turnover
    seed: int = 7

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        names = {f.name for f in fields(cls)}
        return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in d.items() if k in names})

    def quick(self) -> "Config":
        """Small, fast settings for smoke tests and quick looks."""
        return replace(self, seq_len=30, hidden=32, max_epochs=15, patience=3, folds=min(self.folds, 2),
                       gbm_iter=60)
