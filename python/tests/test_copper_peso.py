import numpy as np
import pandas as pd
import pytest

import analysis_copper_peso as a
import data_loader as dl


def toy_panel():
    idx = pd.date_range("2020-01-01", periods=3, freq="MS")
    return pd.DataFrame({dl.CLP_COL: [100.0, 200.0, 100.0], dl.COPPER_COL: [10.0, 10.0, 20.0],
                         dl.DOLLAR_COL: [50.0, 25.0, 25.0]}, index=idx)


def test_log_changes_hand_values():
    d = a.log_changes(toy_panel())
    ln2 = 100 * np.log(2)
    assert d[a.D_CLP].tolist() == pytest.approx([ln2, -ln2])
    assert d[a.D_COPPER].tolist() == pytest.approx([0.0, ln2])
    assert d[a.D_DOLLAR].tolist() == pytest.approx([-ln2, 0.0])


def synthetic(n=200, seed=0, noise=0.5):
    rng = np.random.default_rng(seed)
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    y = 0.3 + (-0.2) * x1 + 1.0 * x2 + noise * rng.normal(size=n)
    idx = pd.date_range("2000-01-01", periods=n, freq="MS")
    return pd.DataFrame({a.D_CLP: y, a.D_COPPER: x1, a.D_DOLLAR: x2}, index=idx)


def hc3_by_hand(d):
    X = np.column_stack([np.ones(len(d)), d[a.D_COPPER], d[a.D_DOLLAR]])
    y = d[a.D_CLP].to_numpy()
    XtXi = np.linalg.inv(X.T @ X)
    beta = XtXi @ X.T @ y
    e = y - X @ beta
    h = np.einsum("ij,jk,ik->i", X, XtXi, X)
    scaled = X * (e / (1 - h))[:, None]
    return beta, np.sqrt(np.diag(XtXi @ (scaled.T @ scaled) @ XtXi))


def test_fit_hc3_matches_independent_computation():
    d = synthetic()
    res = a.fit_hc3(d)
    beta, se = hc3_by_hand(d)
    assert res.params.to_numpy() == pytest.approx(beta)
    assert res.bse.to_numpy() == pytest.approx(se)


def test_fit_recovers_noiseless_coefficients():
    d = synthetic(noise=0.0)
    res = a.fit_hc3(d)
    assert res.params[a.D_COPPER] == pytest.approx(-0.2) and res.params[a.D_DOLLAR] == pytest.approx(1.0)


def test_rolling_beta_matches_lstsq_on_window():
    d = synthetic(n=80)
    roll = a.rolling_betas(d, window=30)
    sub = d.iloc[20:50]
    X = np.column_stack([np.ones(30), sub[a.D_COPPER], sub[a.D_DOLLAR]])
    beta = np.linalg.lstsq(X, sub[a.D_CLP].to_numpy(), rcond=None)[0]
    assert roll.loc[sub.index[-1], "beta_copper"] == pytest.approx(beta[1])
    assert len(roll) == 80 - 30 + 1


def test_granger_detects_planted_lead():
    rng = np.random.default_rng(1)
    x = rng.normal(size=300)
    y = np.zeros(300)
    for t in range(1, 300):
        y[t] = 0.8 * x[t - 1] + 0.3 * rng.normal()
    d = pd.DataFrame({a.D_CLP: y, a.D_COPPER: x})
    g = a.granger(d, maxlag=2)
    assert g["copper_causes_clp"][1] < 1e-6


def test_real_results_sane():
    res, d, roll = a.run(dl.load_monthly())
    assert not d.isna().any().any()
    assert d.index.is_monotonic_increasing
    assert 0 <= res["full"]["r_squared"] <= 1
    assert res["full"]["n_obs"] == len(d)
    assert len(roll) == len(d) - a.ROLL_WINDOW + 1
