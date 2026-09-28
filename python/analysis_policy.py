"""Real policy rate and a simple inflation-only Taylor-rule gap (illustrative, stated assumptions)."""
import numpy as np
import pandas as pd

import data_loader as dl

# ---------------- CONFIG ----------------
INFLATION_TARGET = 3.0  # percent, BCCh target; explicit parameter
NEUTRAL_REAL_RATE = 1.0  # percent, assumption, not an estimate from a source
NEUTRAL_SENSITIVITY = [0.5, 1.0, 1.5]
INFLATION_WEIGHT = 0.5  # Taylor (1993) weight on the inflation gap
AVG_START = "2010-01-01"
# ----------------------------------------

YOY_COL = "cpi_yoy"
REAL_COL = "real_policy_rate"
TAYLOR_COL = "taylor_rate"
GAP_COL = "policy_minus_taylor"


def yoy(cpi):
    return 100 * (cpi / cpi.shift(12) - 1)


def taylor_rate(inflation, r_star=NEUTRAL_REAL_RATE, target=INFLATION_TARGET, phi=INFLATION_WEIGHT):
    """i = r* + pi + phi * (pi - target); output gap assumed zero (no keyless monthly gap series)."""
    return r_star + inflation + phi * (inflation - target)


def build(panel, r_star=NEUTRAL_REAL_RATE):
    out = pd.DataFrame(index=panel.index)
    out[dl.POLICY_COL] = panel[dl.POLICY_COL]
    out[YOY_COL] = yoy(panel[dl.CPI_COL])
    out[REAL_COL] = out[dl.POLICY_COL] - out[YOY_COL]
    out[TAYLOR_COL] = taylor_rate(out[YOY_COL], r_star)
    out[GAP_COL] = out[dl.POLICY_COL] - out[TAYLOR_COL]
    return out.dropna()


def run(panel_full):
    """panel_full: policy and CPI columns only, so it can run past the copper sample."""
    df = build(panel_full)
    last = df.iloc[-1]
    since = df.loc[AVG_START:]
    return {
        "last_month": str(df.index[-1].date()),
        "policy_rate": float(last[dl.POLICY_COL]),
        "cpi_yoy": float(last[YOY_COL]),
        "real_policy_rate": float(last[REAL_COL]),
        "taylor_rate": float(last[TAYLOR_COL]),
        "policy_minus_taylor": float(last[GAP_COL]),
        "avg_real_rate_since": float(since[REAL_COL].mean()),
        "avg_start": AVG_START,
        "cpi_yoy_max_last_24m": float(df[YOY_COL].iloc[-24:].max()),
        "cpi_yoy_min_last_24m": float(df[YOY_COL].iloc[-24:].min()),
        "policy_rate_12m_ago": float(df[dl.POLICY_COL].iloc[-13]),
        "cpi_yoy_12m_ago": float(df[YOY_COL].iloc[-13]),
        "params": {"target": INFLATION_TARGET, "neutral_real_rate": NEUTRAL_REAL_RATE,
                   "inflation_weight": INFLATION_WEIGHT, "output_gap": "assumed zero"},
        "sensitivity": {str(r): float(df[dl.POLICY_COL].iloc[-1] - taylor_rate(df[YOY_COL].iloc[-1], r))
                        for r in NEUTRAL_SENSITIVITY},
    }, df
