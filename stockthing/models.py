"""Neural network forecasters.

All networks map a window ``(batch, seq_len, n_features)`` to

* ``q``     - ``(batch, n_horizons, n_quantiles)`` quantiles of the
  vol-normalised forward return (monotone by construction), and
* ``logit`` - ``(batch, n_horizons)`` logit of P(forward return > 0).
"""

from __future__ import annotations

import math
from statistics import NormalDist

import torch
import torch.nn as nn
import torch.nn.functional as F

NN_MODELS = ("lstm", "gru", "tcn", "transformer", "mlp")


class ForecastHead(nn.Module):
    """Shared output head: median + softplus-spaced outer quantiles + direction logit.

    The last layer is initialised so that an untrained network outputs the
    no-skill forecast (standard-normal quantiles, P(up) = 0.5); training then
    only has to learn deviations from it.
    """

    def __init__(self, d_in: int, n_horizons: int, quantiles, dropout: float = 0.1):
        super().__init__()
        quantiles = tuple(quantiles)
        n_quantiles = len(quantiles)
        if n_quantiles % 2 != 1 or abs(quantiles[n_quantiles // 2] - 0.5) > 1e-9:
            raise ValueError("use an odd number of quantiles with 0.5 in the middle")
        self.nh, self.nq = n_horizons, n_quantiles
        self.net = nn.Sequential(
            nn.Linear(d_in, d_in), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_in, n_horizons * (n_quantiles + 1)),
        )
        zq = [NormalDist().inv_cdf(t) for t in quantiles]
        bias = torch.zeros(n_horizons, n_quantiles + 1)
        mid = n_quantiles // 2
        for i in range(n_quantiles):
            if i != mid:
                gap = zq[i + 1] - zq[i] if i < mid else zq[i] - zq[i - 1]
                bias[:, i] = math.log(math.expm1(gap))  # inverse softplus
        last = self.net[-1]
        with torch.no_grad():
            last.weight.mul_(0.1)
            last.bias.copy_(bias.flatten())

    def forward(self, z: torch.Tensor):
        out = self.net(z).view(z.shape[0], self.nh, self.nq + 1)
        raw, logit = out[..., :-1], out[..., -1]
        mid = self.nq // 2
        med = raw[..., mid:mid + 1]
        lower = med - torch.flip(torch.cumsum(F.softplus(torch.flip(raw[..., :mid], [-1])), -1), [-1])
        upper = med + torch.cumsum(F.softplus(raw[..., mid + 1:]), -1)
        return torch.cat([lower, med, upper], -1), logit


class RNNForecaster(nn.Module):
    """LSTM / GRU encoder with attention pooling over time."""

    def __init__(self, n_features, n_horizons, quantiles, hidden=64, layers=2, dropout=0.25, cell="lstm"):
        super().__init__()
        self.inp = nn.Sequential(nn.Linear(n_features, hidden), nn.GELU(), nn.Dropout(dropout))
        rnn = nn.LSTM if cell == "lstm" else nn.GRU
        self.rnn = rnn(hidden, hidden, num_layers=layers, batch_first=True, dropout=dropout if layers > 1 else 0.0)
        self.score = nn.Linear(hidden, 1)
        self.norm = nn.LayerNorm(2 * hidden)
        self.head = ForecastHead(2 * hidden, n_horizons, quantiles, dropout)

    def forward(self, x):
        h, _ = self.rnn(self.inp(x))
        w = torch.softmax(self.score(h).squeeze(-1), dim=1)
        ctx = (w.unsqueeze(-1) * h).sum(1)
        return self.head(self.norm(torch.cat([h[:, -1], ctx], -1)))


class _CausalBlock(nn.Module):
    def __init__(self, channels: int, kernel: int, dilation: int, dropout: float):
        super().__init__()
        self.pad = (kernel - 1) * dilation
        self.conv1 = nn.Conv1d(channels, channels, kernel, dilation=dilation)
        self.conv2 = nn.Conv1d(channels, channels, kernel, dilation=dilation)
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        y = self.drop(F.gelu(self.conv1(F.pad(x, (self.pad, 0)))))
        y = self.drop(F.gelu(self.conv2(F.pad(y, (self.pad, 0)))))
        return F.gelu(x + y)


class TCNForecaster(nn.Module):
    """Temporal convolutional network: stacked dilated causal convolutions."""

    def __init__(self, n_features, n_horizons, quantiles, hidden=64, seq_len=60, kernel=3, dropout=0.25):
        super().__init__()
        # enough levels for the receptive field to cover the whole window
        levels = max(2, math.ceil(math.log2((seq_len - 1) / (2 * (kernel - 1)) + 1)))
        self.inp = nn.Conv1d(n_features, hidden, 1)
        self.blocks = nn.Sequential(*[_CausalBlock(hidden, kernel, 2**i, dropout) for i in range(levels)])
        self.norm = nn.LayerNorm(2 * hidden)
        self.head = ForecastHead(2 * hidden, n_horizons, quantiles, dropout)

    def forward(self, x):
        y = self.blocks(self.inp(x.transpose(1, 2)))
        return self.head(self.norm(torch.cat([y[:, :, -1], y.mean(-1)], -1)))


class TransformerForecaster(nn.Module):
    """Pre-norm Transformer encoder over weekly patches (PatchTST-style): each
    token embeds ``patch`` consecutive bars, plus a learned summary token."""

    def __init__(self, n_features, n_horizons, quantiles, hidden=64, layers=2, heads=4, dropout=0.25,
                 seq_len=60, patch=5):
        super().__init__()
        self.patch = max(1, min(patch, seq_len))
        n_tokens = math.ceil(seq_len / self.patch) + 1
        self.inp = nn.Linear(n_features * self.patch, hidden)
        self.pos = nn.Parameter(torch.randn(1, n_tokens, hidden) * 0.02)
        self.cls = nn.Parameter(torch.zeros(1, 1, hidden))
        layer = nn.TransformerEncoderLayer(hidden, heads, 4 * hidden, dropout, activation="gelu",
                                           batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(hidden)
        self.head = ForecastHead(hidden, n_horizons, quantiles, dropout)

    def forward(self, x):
        b, L, f = x.shape
        pad = (-L) % self.patch
        if pad:  # left-pad so patches stay aligned to the most recent bar
            x = F.pad(x, (0, 0, pad, 0))
        tokens = self.inp(x.reshape(b, -1, self.patch * f))
        tokens = torch.cat([tokens, self.cls.expand(b, 1, -1)], 1)
        tokens = tokens + self.pos[:, -tokens.shape[1]:]
        return self.head(self.norm(self.encoder(tokens)[:, -1]))


class MLPForecaster(nn.Module):
    """Feed-forward net on the last few bars plus the window mean."""

    def __init__(self, n_features, n_horizons, quantiles, hidden=64, dropout=0.25, last_k=5):
        super().__init__()
        self.last_k = last_k
        d_in = n_features * (last_k + 1)
        self.net = nn.Sequential(
            nn.Linear(d_in, 4 * hidden), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(4 * hidden, 2 * hidden), nn.GELU(), nn.Dropout(dropout),
        )
        self.head = ForecastHead(2 * hidden, n_horizons, quantiles, dropout)

    def forward(self, x):
        z = torch.cat([x[:, -self.last_k:].flatten(1), x.mean(1)], -1)
        return self.head(self.net(z))


def build_model(name: str, n_features: int, n_horizons: int, quantiles, *, hidden: int = 64,
                layers: int = 2, dropout: float = 0.25, seq_len: int = 60) -> nn.Module:
    if name in ("lstm", "gru"):
        return RNNForecaster(n_features, n_horizons, quantiles, hidden, layers, dropout, cell=name)
    if name == "tcn":
        return TCNForecaster(n_features, n_horizons, quantiles, hidden, seq_len, dropout=dropout)
    if name == "transformer":
        heads = 4 if hidden % 4 == 0 else 1
        return TransformerForecaster(n_features, n_horizons, quantiles, hidden, layers, heads, dropout,
                                     seq_len=seq_len)
    if name == "mlp":
        return MLPForecaster(n_features, n_horizons, quantiles, hidden, dropout, last_k=min(5, seq_len))
    raise ValueError(f"unknown neural model {name!r}; choose from {NN_MODELS}")


def forecast_loss(q: torch.Tensor, logit: torch.Tensor, z: torch.Tensor, mask: torch.Tensor,
                  taus: torch.Tensor, bce_weight: float = 1.0) -> torch.Tensor:
    """Masked pinball (quantile) loss + weighted binary cross-entropy on direction."""
    m = mask.float()
    zf = torch.nan_to_num(z).clamp(-10.0, 10.0)
    diff = zf.unsqueeze(-1) - q
    pinball = torch.maximum(taus * diff, (taus - 1.0) * diff).mean(-1)
    bce = F.binary_cross_entropy_with_logits(logit, (zf > 0).float(), reduction="none")
    return ((pinball + bce_weight * bce) * m).sum() / m.sum().clamp(min=1.0)
