"""Small VAR on inflation, USD/CLP and copper: expanding-window backtest vs naive, and 12m scenarios."""
import numpy as np
import pandas as pd
from scipy import stats

import data_loader as dl

# ---------------- CONFIG ----------------
LAGS = 2
LAG_SENSITIVITY = [1, 2, 3]
MIN_TRAIN = 120  # months before the first forecast origin
HORIZONS = [1, 3, 12]
SCENARIO_HORIZON = 12
COPPER_SHOCK_PCT = 20.0  # cumulative copper move over the horizon, in either direction
# ----------------------------------------

INFL = "infl"
FX = "fx"
CU = "cu"
VARS = [INFL, FX, CU]  # column order defines the VAR system
I_INFL, I_FX, I_CU = 0, 1, 2  # indices into VARS, derived from the list above


def make_returns(panel):
    """Monthly log changes x100 for the three VAR variables."""
    src = {INFL: dl.CPI_COL, FX: dl.CLP_COL, CU: dl.COPPER_COL}
    out = pd.DataFrame({k: 100 * np.diff(np.log(panel[v].to_numpy())) for k, v in src.items()},
                       index=panel.index[1:])
    return out[VARS]


def fit_var(Y, p):
    """OLS VAR(p) with constant. Returns B of shape (1 + k*p, k)."""
    T, k = Y.shape
    X = np.hstack([np.ones((T - p, 1))] + [Y[p - j - 1:T - j - 1] for j in range(p)])
    B, *_ = np.linalg.lstsq(X, Y[p:], rcond=None)
    return B


def contemporaneous_loadings(Y, B, p, idx):
    """Slope of each variable's residual on variable idx's residual (Cholesky order with idx first)."""
    T = Y.shape[0]
    X = np.hstack([np.ones((T - p, 1))] + [Y[p - j - 1:T - j - 1] for j in range(p)])
    resid = Y[p:] - X @ B
    return resid.T @ resid[:, idx] / (resid[:, idx] @ resid[:, idx])


def forecast_var(Y, B, p, h, override=None, gamma=None):
    """Iterated forecasts; override maps a variable index to an array of h values held fixed.

    gamma (loadings on the overridden variable's surprise) adds the same-month pass-through.
    """
    k = Y.shape[1]
    hist = [Y[-j - 1] for j in range(p)]  # most recent first
    out = np.zeros((h, k))
    for t in range(h):
        x = np.concatenate([[1.0]] + hist[:p])
        f = x @ B
        if override:
            for idx, path in override.items():
                delta = path[t] - f[idx]
                f[idx] = path[t]
                if gamma is not None:
                    keep = np.arange(len(f)) != idx
                    f[keep] += gamma[keep] * delta
        out[t] = f
        hist = [f] + hist[:-1]
    return out


def dm_test(e_model, e_bench, h):
    """Diebold-Mariano on squared errors, Bartlett HAC (h-1 lags), Harvey small-sample adjustment."""
    d = np.asarray(e_model) ** 2 - np.asarray(e_bench) ** 2
    n = len(d)
    dbar = d.mean()
    dc = d - dbar
    var = dc @ dc / n
    for lag in range(1, h):
        w = 1 - lag / h
        var += 2 * w * (dc[lag:] @ dc[:-lag]) / n
    stat = dbar / np.sqrt(var / n)
    adj = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat *= adj
    return float(stat), float(2 * (1 - stats.t.cdf(abs(stat), n - 1)))


def backtest(Y, p=LAGS, horizons=HORIZONS, min_train=MIN_TRAIN):
    """Expanding window; forecast cumulative change over h months for inflation and FX."""
    T = Y.shape[0]
    res = {}
    for h in horizons:
        rec = {v: {"actual": [], "model": [], "naive": [], "mean": []} for v in (I_INFL, I_FX)}
        for i in range(min_train, T - h + 1):
            train = Y[:i]
            B = fit_var(train, p)
            fc = forecast_var(train, B, p, h).sum(axis=0)
            for v in (I_INFL, I_FX):
                rec[v]["actual"].append(Y[i:i + h, v].sum())
                rec[v]["model"].append(fc[v])
                rec[v]["naive"].append(train[-h:, v].sum() if v == I_INFL else 0.0)
                rec[v]["mean"].append(train[:, v].mean() * h)
        res[h] = rec
    return res


def summarize_backtest(bt):
    names = {I_INFL: "inflation_cum", I_FX: "usdclp_cum"}
    naive_label = {I_INFL: "last h-month inflation", I_FX: "random walk (zero change)"}
    out = {}
    for h, rec in bt.items():
        for v, r in rec.items():
            a = np.array(r["actual"])
            rmse = {k: float(np.sqrt(np.mean((a - np.array(r[k])) ** 2))) for k in ("model", "naive", "mean")}
            e_m, e_n = a - np.array(r["model"]), a - np.array(r["naive"])
            stat, pval = dm_test(e_m, e_n, h)
            out[f"{names[v]}_h{h}"] = {
                "n_forecasts": int(len(a)), "naive_definition": naive_label[v],
                "rmse_model": rmse["model"], "rmse_naive": rmse["naive"], "rmse_hist_mean": rmse["mean"],
                "ratio_model_to_naive": rmse["model"] / rmse["naive"],
                "beats_naive": bool(rmse["model"] < rmse["naive"]),
                "dm_stat_vs_naive": stat, "dm_pvalue_vs_naive": pval,
            }
    return out


def scenarios(panel, Y, p=LAGS, h=SCENARIO_HORIZON, shock_pct=COPPER_SHOCK_PCT, rmse_fx_h12=None):
    B = fit_var(Y, p)
    gamma = contemporaneous_loadings(Y, B, p, I_CU)
    last_fx = float(panel[dl.CLP_COL].iloc[-1])
    last_cu = float(panel[dl.COPPER_COL].iloc[-1])
    months = pd.date_range(panel.index[-1], periods=h + 1, freq="MS")[1:]
    step = {"down": np.log(1 - shock_pct / 100) * 100 / h, "up": np.log(1 + shock_pct / 100) * 100 / h}
    out = {"origin": str(panel.index[-1].date()), "origin_usdclp": last_fx, "origin_copper": last_cu, "base_copper_assumption": "held flat at last level",
           "months": [str(m.date()) for m in months], "lags": p, "copper_shock_pct": shock_pct, "cases": {}}
    cases = {"base": {I_CU: np.zeros(h)}, "copper_down": {I_CU: np.full(h, step["down"])},
             "copper_up": {I_CU: np.full(h, step["up"])}}
    for name, ov in cases.items():
        f = forecast_var(Y, B, p, h, ov, gamma)
        cum = f.cumsum(axis=0)
        case = {
            "usdclp_path": (last_fx * np.exp(cum[:, I_FX] / 100)).tolist(),
            "copper_path": (last_cu * np.exp(cum[:, I_CU] / 100)).tolist(),
            "usdclp_end": float(last_fx * np.exp(cum[-1, I_FX] / 100)),
            "usdclp_change_pct": float((np.exp(cum[-1, I_FX] / 100) - 1) * 100),
            "copper_end": float(last_cu * np.exp(cum[-1, I_CU] / 100)),
            "copper_change_pct": float((np.exp(cum[-1, I_CU] / 100) - 1) * 100),
            "cpi_yoy_end_pct": float((np.exp(cum[-1, I_INFL] / 100) - 1) * 100),
        }
        if rmse_fx_h12 is not None:  # backtest RMSE band, not a model-based interval
            case["usdclp_band_low"] = float(case["usdclp_end"] * np.exp(-1.645 * rmse_fx_h12 / 100))
            case["usdclp_band_high"] = float(case["usdclp_end"] * np.exp(1.645 * rmse_fx_h12 / 100))
        out["cases"][name] = case
    out["naive_usdclp"] = last_fx
    out["naive_cpi_yoy_pct"] = float((np.exp(Y[-12:, I_INFL].sum() / 100) - 1) * 100)
    out["copper_loading_fx"] = float(gamma[I_FX])
    out["copper_loading_infl"] = float(gamma[I_INFL])
    out["var_intercept_monthly"] = {v: float(B[0, j]) for j, v in enumerate(VARS)}
    return out


def run(panel):
    R = make_returns(panel)
    Y = R.to_numpy()
    main = summarize_backtest(backtest(Y, LAGS))
    sens = {}
    for p in LAG_SENSITIVITY:
        s = summarize_backtest(backtest(Y, p, horizons=[12]))
        sens[str(p)] = {k: v["ratio_model_to_naive"] for k, v in s.items()}
    sc = scenarios(panel, Y, LAGS, rmse_fx_h12=main["usdclp_cum_h12"]["rmse_model"])
    first_origin = str(R.index[MIN_TRAIN].date())
    return {"lags": LAGS, "min_train_months": MIN_TRAIN, "first_forecast_origin": first_origin,
            "sample_end": str(R.index[-1].date()), "backtest": main, "lag_sensitivity_h12_ratio": sens,
            "scenarios": sc}
