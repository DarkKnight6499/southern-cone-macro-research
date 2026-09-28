"""Copper and the peso: HC3 regression, rolling beta stability, Granger causality."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests

import data_loader as dl

# ---------------- CONFIG ----------------
ROLL_WINDOW = 60  # months
GRANGER_MAXLAG = 6
SPLIT_DATE = "2020-01-01"  # post-pandemic subsample split
# ----------------------------------------

D_CLP = "d_clp"
D_COPPER = "d_copper"
D_DOLLAR = "d_dollar"
CONST = "const"
REGRESSORS = [D_COPPER, D_DOLLAR]


def log_changes(panel):
    """Monthly log changes in percent (x100)."""
    out = pd.DataFrame(index=panel.index[1:])
    out[D_CLP] = 100 * np.diff(np.log(panel[dl.CLP_COL].to_numpy()))
    out[D_COPPER] = 100 * np.diff(np.log(panel[dl.COPPER_COL].to_numpy()))
    out[D_DOLLAR] = 100 * np.diff(np.log(panel[dl.DOLLAR_COL].to_numpy()))
    return out


def fit_hc3(d):
    X = sm.add_constant(d[REGRESSORS])
    return sm.OLS(d[D_CLP], X).fit(cov_type="HC3")


def fit_copper_only(d):
    return sm.OLS(d[D_CLP], sm.add_constant(d[[D_COPPER]])).fit(cov_type="HC3")


def summarize_fit(res):
    return {
        "n_obs": int(res.nobs),
        "r_squared": float(res.rsquared),
        "coef": {k: float(v) for k, v in res.params.items()},
        "t_hc3": {k: float(v) for k, v in res.tvalues.items()},
        "p_hc3": {k: float(v) for k, v in res.pvalues.items()},
    }


def rolling_betas(d, window=ROLL_WINDOW):
    """Rolling HC3 OLS; window ends at the labelled month."""
    rows = []
    for end in range(window, len(d) + 1):
        res = fit_hc3(d.iloc[end - window:end])
        rows.append({"month": d.index[end - 1], "beta_copper": res.params[D_COPPER],
                     "se_copper": res.bse[D_COPPER], "beta_dollar": res.params[D_DOLLAR]})
    return pd.DataFrame(rows).set_index("month")


def granger(d, maxlag=GRANGER_MAXLAG):
    """p-values of F tests for the null that the second column does not cause the first."""
    def run(effect, cause):  # verbose flag removed in statsmodels 0.15
        res = grangercausalitytests(d[[effect, cause]], maxlag=maxlag)
        return {int(k): float(v[0]["ssr_ftest"][1]) for k, v in res.items()}
    return {"copper_causes_clp": run(D_CLP, D_COPPER), "clp_causes_copper": run(D_COPPER, D_CLP)}


def run(panel):
    d = log_changes(panel)
    full = fit_hc3(d)
    roll = rolling_betas(d)
    t_roll = roll["beta_copper"] / roll["se_copper"]
    pre = fit_hc3(d.loc[:SPLIT_DATE].iloc[:-1])
    post = fit_hc3(d.loc[SPLIT_DATE:])
    return {
        "sample": [str(d.index[0].date()), str(d.index[-1].date())],
        "full": summarize_fit(full),
        "copper_only": summarize_fit(fit_copper_only(d)),
        "pre_split": summarize_fit(pre),
        "post_split": summarize_fit(post),
        "split_date": SPLIT_DATE,
        "rolling": {
            "window_months": ROLL_WINDOW,
            "n_windows": int(len(roll)),
            "beta_copper_min": float(roll["beta_copper"].min()),
            "beta_copper_max": float(roll["beta_copper"].max()),
            "beta_copper_latest": float(roll["beta_copper"].iloc[-1]),
            "share_windows_significant_5pct": float((t_roll.abs() > 1.96).mean()),
            "share_windows_beta_negative": float((roll["beta_copper"] < 0).mean()),
        },
        "granger": granger(d),
    }, d, roll
