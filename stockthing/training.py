"""Forecasters (neural and classical) behind one fit / predict / save interface."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn

from .config import Config
from .dataset import Fold, Panel
from .models import NN_MODELS, build_model, forecast_loss


@dataclass
class FitContext:
    """Scaled features for one fold plus the panel they index into."""

    panel: Panel
    X: torch.Tensor  # (rows, d) float32, scaled
    cfg: Config

    def windows(self, idx: np.ndarray) -> torch.Tensor:
        return self.X[torch.from_numpy(self.panel.window_rows(idx))]

    def last(self, idx: np.ndarray) -> np.ndarray:
        return self.X[torch.from_numpy(self.panel.row[idx])].numpy()

    @property
    def n_features(self) -> int:
        return int(self.X.shape[1])


class Forecaster:
    """Predicts vol-normalised quantiles ``(N, H, Q)`` and ``P(up)`` ``(N, H)``."""

    name: str

    def fit(self, ctx: FitContext, fold: Fold, seed: int) -> str:  # returns a short training summary
        raise NotImplementedError

    def predict(self, ctx: FitContext, idx: np.ndarray):
        raise NotImplementedError

    def save(self, prefix: Path) -> None:
        joblib.dump(self.__dict__, prefix.with_suffix(".joblib"))

    @classmethod
    def load(cls, prefix: Path, cfg: Config, n_features: int) -> "Forecaster":
        obj = cls.__new__(cls)
        obj.__dict__.update(joblib.load(prefix.with_suffix(".joblib")))
        return obj


# --------------------------------------------------------------------------- #
# neural networks
# --------------------------------------------------------------------------- #


class NNForecaster(Forecaster):
    def __init__(self, name: str, cfg: Config, n_features: int | None = None):
        self.name, self.cfg = name, cfg
        self.nets: list[nn.Module] = []
        self.n_features = n_features

    def _new_net(self, n_features: int) -> nn.Module:
        c = self.cfg
        return build_model(self.name, n_features, len(c.horizons), c.quantiles, hidden=c.hidden,
                           layers=c.layers, dropout=c.dropout, seq_len=c.seq_len)

    @torch.no_grad()
    def _eval_loss(self, net, ctx, idx, mask, taus, z) -> float:
        net.eval()
        total, weight = 0.0, 0.0
        for s in range(0, len(idx), 2048):
            b = idx[s:s + 2048]
            m = torch.from_numpy(mask[s:s + 2048])
            q, logit = net(ctx.windows(b))
            w = float(m.sum())
            total += float(forecast_loss(q, logit, z[torch.from_numpy(b)], m, taus, self.cfg.bce_weight)) * w
            weight += w
        return total / max(weight, 1.0)

    def _train_one(self, ctx: FitContext, fold: Fold, seed: int):
        c = self.cfg
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        net = self._new_net(ctx.n_features)
        opt = torch.optim.AdamW(net.parameters(), lr=c.lr, weight_decay=c.weight_decay)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=max(1, c.patience // 3))
        taus = torch.tensor(c.quantiles, dtype=torch.float32)
        z = torch.from_numpy(ctx.panel.z.astype(np.float32))
        tr_idx, tr_mask = fold.train_idx, torch.from_numpy(fold.train_mask)
        has_val = len(fold.val_idx) > 0
        best, best_state, best_epoch, bad = math.inf, None, 0, 0
        epochs = c.max_epochs if has_val else max(1, c.max_epochs // 3)
        for epoch in range(epochs):
            net.train()
            perm = rng.permutation(len(tr_idx))
            for s in range(0, len(perm), c.batch_size):
                b = perm[s:s + c.batch_size]
                idx = tr_idx[b]
                xb = ctx.windows(idx)
                if c.input_noise > 0:
                    xb = xb + c.input_noise * torch.randn_like(xb)
                q, logit = net(xb)
                loss = forecast_loss(q, logit, z[torch.from_numpy(idx)], tr_mask[torch.from_numpy(b)], taus,
                                     c.bce_weight)
                opt.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                opt.step()
            if not has_val:
                continue
            val = self._eval_loss(net, ctx, fold.val_idx, fold.val_mask, taus, z)
            sched.step(val)
            if val < best - 1e-4:
                best, best_epoch, bad = val, epoch, 0
                best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
            else:
                bad += 1
                if bad >= c.patience:
                    break
        if best_state is not None:
            net.load_state_dict(best_state)
        net.eval()
        return net, best, best_epoch + 1

    def fit(self, ctx: FitContext, fold: Fold, seed: int) -> str:
        self.n_features = ctx.n_features
        self.nets, notes = [], []
        for s in range(max(1, self.cfg.seeds)):
            net, val, ep = self._train_one(ctx, fold, seed + 7919 * s)
            self.nets.append(net)
            notes.append(f"val {val:.4f} @ epoch {ep}")
        return "; ".join(notes)

    @torch.no_grad()
    def predict(self, ctx: FitContext, idx: np.ndarray):
        qs, ps = [], []
        for net in self.nets:
            net.eval()
            q_parts, p_parts = [], []
            for s in range(0, len(idx), 2048):
                q, logit = net(ctx.windows(idx[s:s + 2048]))
                q_parts.append(q.numpy())
                p_parts.append(torch.sigmoid(logit).numpy())
            qs.append(np.concatenate(q_parts) if q_parts else np.zeros((0, len(self.cfg.horizons), len(self.cfg.quantiles))))
            ps.append(np.concatenate(p_parts) if p_parts else np.zeros((0, len(self.cfg.horizons))))
        return np.mean(qs, 0), np.mean(ps, 0)

    def save(self, prefix: Path) -> None:
        torch.save({"name": self.name, "n_features": self.n_features,
                    "states": [n.state_dict() for n in self.nets]}, prefix.with_suffix(".pt"))

    @classmethod
    def load(cls, prefix: Path, cfg: Config, n_features: int) -> "NNForecaster":
        blob = torch.load(prefix.with_suffix(".pt"), map_location="cpu", weights_only=True)
        obj = cls(blob["name"], cfg, blob["n_features"])
        for st in blob["states"]:
            net = obj._new_net(blob["n_features"])
            net.load_state_dict(st)
            net.eval()
            obj.nets.append(net)
        return obj


# --------------------------------------------------------------------------- #
# classical models (use the latest bar's features only)
# --------------------------------------------------------------------------- #


def _train_val(fold: Fold):
    """Classical models have no early stopping, so they also learn from the
    (purged) validation slice."""
    return np.concatenate([fold.train_idx, fold.val_idx]), np.concatenate([fold.train_mask, fold.val_mask])


class GBMForecaster(Forecaster):
    """Histogram gradient boosting: one quantile regressor per (horizon, quantile)
    plus one direction classifier per horizon."""

    name = "gbm"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.models: list = []

    def fit(self, ctx: FitContext, fold: Fold, seed: int) -> str:
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

        idx, mask = _train_val(fold)
        X, z = ctx.last(idx), np.clip(ctx.panel.z[idx], -10, 10)
        params = dict(max_iter=self.cfg.gbm_iter, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=100,
                      l2_regularization=1.0, random_state=seed)
        self.models = []
        for j in range(z.shape[1]):
            m = mask[:, j]
            Xj, zj = X[m], z[m, j]
            regs = [HistGradientBoostingRegressor(loss="quantile", quantile=t, **params).fit(Xj, zj)
                    for t in self.cfg.quantiles]
            up = zj > 0
            clf = (HistGradientBoostingClassifier(**params).fit(Xj, up) if 0 < up.mean() < 1 else float(up.mean()))
            self.models.append((regs, clf))
        return f"{len(idx)} samples"

    def predict(self, ctx: FitContext, idx: np.ndarray):
        X = ctx.last(idx)
        q = np.stack([np.stack([r.predict(X) for r in regs], -1) for regs, _ in self.models], 1)
        p = np.stack([clf.predict_proba(X)[:, 1] if not isinstance(clf, float) else np.full(len(X), clf)
                      for _, clf in self.models], 1)
        return np.sort(q, axis=-1), p


class LinearForecaster(Forecaster):
    """Ridge regression for the median + residual quantiles, logistic regression for direction."""

    name = "linear"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.models: list = []

    def fit(self, ctx: FitContext, fold: Fold, seed: int) -> str:
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import LogisticRegression, Ridge

        idx, mask = _train_val(fold)
        X, z = ctx.last(idx), np.clip(ctx.panel.z[idx], -10, 10)
        self.models = []
        for j in range(z.shape[1]):
            m = mask[:, j]
            Xj, zj = X[m], z[m, j]
            reg = Ridge(alpha=100.0).fit(Xj, zj)
            offsets = np.quantile(zj - reg.predict(Xj), self.cfg.quantiles)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                clf = LogisticRegression(C=0.01, max_iter=2000).fit(Xj, zj > 0)
            self.models.append((reg, offsets, clf))
        return f"{len(idx)} samples"

    def predict(self, ctx: FitContext, idx: np.ndarray):
        X = ctx.last(idx)
        q = np.stack([reg.predict(X)[:, None] + off[None, :] for reg, off, _ in self.models], 1)
        p = np.stack([clf.predict_proba(X)[:, 1] for _, _, clf in self.models], 1)
        return q, p


class BaselineForecaster(Forecaster):
    """No-skill reference: historical quantiles and historical frequency of up moves."""

    name = "baseline"

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def fit(self, ctx: FitContext, fold: Fold, seed: int) -> str:
        idx, mask = _train_val(fold)
        z = ctx.panel.z[idx]
        self.q = np.stack([np.quantile(z[mask[:, j], j], self.cfg.quantiles) for j in range(z.shape[1])])
        self.p = np.array([np.mean(z[mask[:, j], j] > 0) for j in range(z.shape[1])])
        return "P(up) " + ", ".join(f"{h}d {p:.3f}" for h, p in zip(self.cfg.horizons, self.p))

    def predict(self, ctx: FitContext, idx: np.ndarray):
        n = len(idx)
        return np.broadcast_to(self.q, (n,) + self.q.shape).copy(), np.broadcast_to(self.p, (n, len(self.p))).copy()


def make_forecaster(name: str, cfg: Config) -> Forecaster:
    if name in NN_MODELS:
        return NNForecaster(name, cfg)
    return {"gbm": GBMForecaster, "linear": LinearForecaster, "baseline": BaselineForecaster}[name](cfg)


def load_forecaster(name: str, prefix: Path, cfg: Config, n_features: int) -> Forecaster:
    cls = NNForecaster if name in NN_MODELS else {"gbm": GBMForecaster, "linear": LinearForecaster,
                                                  "baseline": BaselineForecaster}[name]
    return cls.load(prefix, cfg, n_features)
