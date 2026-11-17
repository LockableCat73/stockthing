import pytest
import torch

from stockthing.models import NN_MODELS, build_model, forecast_loss

Q = (0.1, 0.5, 0.9)


@pytest.mark.parametrize("name", NN_MODELS)
def test_shapes_and_monotone_quantiles(name):
    net = build_model(name, 12, 3, Q, hidden=16, seq_len=20)
    q, logit = net(torch.randn(7, 20, 12))
    assert q.shape == (7, 3, 3) and logit.shape == (7, 3)
    assert (q[..., 1:] >= q[..., :-1]).all()


@pytest.mark.parametrize("name", NN_MODELS)
def test_untrained_network_starts_at_the_no_skill_forecast(name):
    torch.manual_seed(0)
    net = build_model(name, 12, 2, Q, hidden=16, seq_len=20, dropout=0.0).eval()
    with torch.no_grad():
        q, logit = net(torch.randn(64, 20, 12))
    assert torch.allclose(q.mean((0, 1)), torch.tensor([-1.2816, 0.0, 1.2816]), atol=0.35)
    assert (torch.sigmoid(logit) - 0.5).abs().max() < 0.15


@pytest.mark.parametrize("name", NN_MODELS)
def test_networks_can_learn(name):
    torch.manual_seed(0)
    net = build_model(name, 8, 1, Q, hidden=32, seq_len=10, dropout=0.0)
    x = torch.randn(128, 10, 8)
    z = 2.0 * x[:, -1, :1] + x[:, -3, 1:2]  # depends on recent bars
    mask = torch.ones(128, 1, dtype=torch.bool)
    taus = torch.tensor(Q)
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    losses = []
    for _ in range(200):
        q, logit = net(x)
        loss = forecast_loss(q, logit, z, mask, taus)
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(loss.item())
    assert losses[-1] < 0.5 * losses[0]


def test_loss_ignores_masked_targets():
    q = torch.zeros(4, 2, 3)
    logit = torch.zeros(4, 2)
    z = torch.tensor([[1.0, float("nan")]] * 4)
    mask = torch.tensor([[True, False]] * 4)
    loss = forecast_loss(q, logit, z, mask, torch.tensor(Q))
    assert torch.isfinite(loss)
