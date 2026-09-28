import numpy as np
import pytest
from statsmodels.tsa.api import VAR

import analysis_forecast as f
import data_loader as dl


def det_var(T=60):
    """Noise-free VAR(1): y_t = c + A y_{t-1}, three variables."""
    A = np.array([[0.5, 0.1, 0.0], [0.0, 0.4, 0.2], [0.1, 0.0, 0.3]])
    c = np.array([1.0, 0.5, -0.2])
    Y = np.zeros((T, 3))
    Y[0] = [1.0, 2.0, 3.0]
    for t in range(1, T):
        Y[t] = c + A @ Y[t - 1]
    return Y, A, c


def test_fit_var_recovers_deterministic_system():
    Y, A, c = det_var()
    B = f.fit_var(Y[:20], 1)
    assert B[0] == pytest.approx(c, abs=1e-8)
    assert B[1:].T == pytest.approx(A, abs=1e-8)


def test_forecast_var_matches_hand_iteration():
    Y, A, c = det_var()
    B = f.fit_var(Y[:20], 1)
    fc = f.forecast_var(Y[:20], B, 1, 3)
    y = Y[19]
    for step in range(3):
        y = c + A @ y
        assert fc[step] == pytest.approx(y, abs=1e-8)


def test_forecast_matches_statsmodels_var():
    rng = np.random.default_rng(3)
    Y = rng.normal(size=(150, 3))
    B = f.fit_var(Y, 2)
    mine = f.forecast_var(Y, B, 2, 5)
    sm_fc = VAR(Y).fit(2, trend="c").forecast(Y[-2:], 5)
    assert mine == pytest.approx(sm_fc, abs=1e-8)


def test_override_holds_path_and_gamma_passes_through():
    Y, A, c = det_var()
    B = f.fit_var(Y[:20], 1)
    path = np.array([5.0, 5.0])
    base = f.forecast_var(Y[:20], B, 1, 2)
    over = f.forecast_var(Y[:20], B, 1, 2, {2: path}, gamma=np.array([0.5, -1.0, 1.0]))
    assert over[:, 2] == pytest.approx(path)
    delta0 = 5.0 - base[0, 2]
    assert over[0, 1] == pytest.approx(base[0, 1] - 1.0 * delta0)


def test_dm_test_hand_values():
    e_m, e_b = np.array([1.0, 2.0, 0.0, 1.0]), np.array([0.0, 1.0, 1.0, 0.0])
    d = e_m ** 2 - e_b ** 2  # [1, 3, -1, 1]
    n, dbar = 4, d.mean()
    var = np.sum((d - dbar) ** 2) / n
    expected = dbar / np.sqrt(var / n) * np.sqrt((n + 1 - 2 + 0) / n)
    stat, pval = f.dm_test(e_m, e_b, 1)
    assert stat == pytest.approx(expected)
    assert 0 < pval < 1


def test_backtest_perfect_model_and_no_lookahead():
    Y, _, _ = det_var(80)
    bt = f.backtest(Y, p=1, horizons=[2], min_train=30)
    s = f.summarize_backtest(bt)
    assert s["usdclp_cum_h2"]["rmse_model"] < 1e-6
    assert s["usdclp_cum_h2"]["n_forecasts"] == 80 - 30 - 2 + 1
    # data after the first origin window must not change the first forecast
    Y2 = Y.copy()
    Y2[40:] += 100
    bt2 = f.backtest(Y2, p=1, horizons=[2], min_train=30)
    assert bt[2][f.I_FX]["model"][0] == pytest.approx(bt2[2][f.I_FX]["model"][0])
    assert bt[2][f.I_INFL]["naive"][0] == pytest.approx(bt2[2][f.I_INFL]["naive"][0])


@pytest.fixture(scope="module")
def real():
    panel = dl.load_monthly()
    return panel, f.run(panel)


def test_real_backtest_sane(real):
    panel, out = real
    for v in out["backtest"].values():
        assert np.isfinite(v["rmse_model"]) and np.isfinite(v["rmse_naive"]) and v["rmse_naive"] > 0
        assert v["ratio_model_to_naive"] == pytest.approx(v["rmse_model"] / v["rmse_naive"])
        assert 0 <= v["dm_pvalue_vs_naive"] <= 1
    assert out["backtest"]["usdclp_cum_h12"]["n_forecasts"] == len(f.make_returns(panel)) - f.MIN_TRAIN - 12 + 1


def test_real_returns_independent_recompute(real):
    panel, _ = real
    R = f.make_returns(panel)
    assert not R.isna().any().any() and R.index.is_monotonic_increasing
    i = 10
    assert R[f.FX].iloc[i] == pytest.approx(100 * np.log(panel[dl.CLP_COL].iloc[i + 1] / panel[dl.CLP_COL].iloc[i]))


def test_real_scenarios_consistent(real):
    panel, out = real
    c = out["scenarios"]["cases"]
    last_cu = panel[dl.COPPER_COL].iloc[-1]
    assert c["base"]["copper_end"] == pytest.approx(last_cu)
    assert c["copper_down"]["copper_end"] == pytest.approx(0.8 * last_cu)
    assert c["copper_up"]["copper_end"] == pytest.approx(1.2 * last_cu)
    assert c["copper_down"]["usdclp_end"] > c["base"]["usdclp_end"] > c["copper_up"]["usdclp_end"]
    assert len(c["base"]["usdclp_path"]) == 12
