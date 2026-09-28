"""Run every analysis on the local snapshots and write outputs/results.json plus charts."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analysis_comparison
import analysis_copper_peso
import analysis_forecast
import analysis_policy
import data_loader as dl
import make_charts

# ---------------- CONFIG ----------------
OUT_DIR = Path(__file__).resolve().parent / "outputs"
RESULTS_FILE = OUT_DIR / "results.json"
# ----------------------------------------


def main():
    OUT_DIR.mkdir(exist_ok=True)
    panel = dl.load_monthly()
    log = dl.load_fetch_log()
    copper, d, roll = analysis_copper_peso.run(panel)
    cpi_pol = pd.concat({dl.CPI_COL: dl.load_bis("bis_cpi_CL.csv"),
                         dl.POLICY_COL: dl.load_bis("bis_cbpol_CL.csv")}, axis=1).dropna()
    policy, policy_df = analysis_policy.run(cpi_pol)
    forecast = analysis_forecast.run(panel)
    comparison = analysis_comparison.run(dl.load_weo(), log["imf_weo_vintage"])
    results = {
        "meta": {"data_retrieved_on": log["retrieved_on"], "panel_start": str(panel.index[0].date()),
                 "panel_end": str(panel.index[-1].date()), "n_months": int(len(panel)),
                 "sources": [s for s in log["sources"] if s["status"] == "ok"],
                 "failed_sources": [s for s in log["sources"] if s["status"] != "ok"]},
        "copper_peso": copper, "policy": policy, "forecast": forecast, "comparison": comparison,
        "levels": {"usdclp_last": float(panel[dl.CLP_COL].iloc[-1]),
                   "usdclp_min": float(panel[dl.CLP_COL].min()), "usdclp_max": float(panel[dl.CLP_COL].max()),
                   "usdclp_max_month": str(panel[dl.CLP_COL].idxmax().date()),
                   "copper_last": float(panel[dl.COPPER_COL].iloc[-1]),
                   "copper_12m_change_pct": float(100 * (panel[dl.COPPER_COL].iloc[-1] / panel[dl.COPPER_COL].iloc[-13] - 1)),
                   "usd_broad_12m_change_pct": float(100 * (panel[dl.DOLLAR_COL].iloc[-1] / panel[dl.DOLLAR_COL].iloc[-13] - 1)),
                   "usdclp_12m_change_pct": float(100 * (panel[dl.CLP_COL].iloc[-1] / panel[dl.CLP_COL].iloc[-13] - 1))},
    }
    beta = copper["full"]["coef"][analysis_copper_peso.D_COPPER]
    cu_log = 100 * np.log(1 + results["levels"]["copper_12m_change_pct"] / 100)
    results["levels"]["peso_move_implied_by_copper_beta_pct"] = float((np.exp(beta * cu_log / 100) - 1) * 100)
    RESULTS_FILE.write_text(json.dumps(results, indent=2))
    make_charts.make_all(panel, roll, policy_df, results)
    print("wrote", RESULTS_FILE)


if __name__ == "__main__":
    main()
