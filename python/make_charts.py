"""Four clean charts for the note, saved to python/charts/."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import data_loader as dl

# ---------------- CONFIG ----------------
CHART_DIR = Path(__file__).resolve().parent / "charts"
REBASE_FROM = "2015-01-01"
POLICY_FROM = "2016-01-01"
HIST_MONTHS = 36
DPI = 200
BLUE, ORANGE, GREY, GREEN = "#1f4e79", "#c55a11", "#666666", "#2e7d32"
# ----------------------------------------

CHART_FILES = {"copper_peso": "chart1_copper_peso.png", "beta": "chart2_rolling_beta.png",
               "policy": "chart3_policy.png", "scenario": "chart4_scenarios.png"}


def _style(ax, title, ylabel):
    ax.set_title(title, fontsize=10, fontweight="bold", loc="left")
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _save(fig, name):
    CHART_DIR.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(CHART_DIR / CHART_FILES[name], dpi=DPI)
    plt.close(fig)


def make_all(panel, roll, policy_df, results):
    p = panel.loc[REBASE_FROM:]
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    for col, color, label in ((dl.CLP_COL, BLUE, "USD/CLP"), (dl.COPPER_COL, ORANGE, "Copper, USD/t")):
        s = 100 * p[col] / p[col].iloc[0]
        ax.plot(s.index, s, color=color, lw=1.5)
        ax.annotate(label, (s.index[-1], s.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=8, color=color, va="center")
    _style(ax, "USD/CLP and copper, monthly average, rebased to 100 in Jan 2015", "Index")
    ax.set_xlim(right=p.index[-1] + pd.DateOffset(months=14))
    _save(fig, "copper_peso")

    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    ax.plot(roll.index, roll["beta_copper"], color=BLUE, lw=1.5)
    ax.fill_between(roll.index, roll["beta_copper"] - 1.96 * roll["se_copper"],
                    roll["beta_copper"] + 1.96 * roll["se_copper"], color=BLUE, alpha=0.15, lw=0)
    ax.axhline(0, color=GREY, lw=0.8)
    _style(ax, "Rolling 60-month copper beta of USD/CLP (HC3, 95% band)", "Beta")
    _save(fig, "beta")

    q = policy_df.loc[POLICY_FROM:]
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    for col, color, label, ls in (("policy_rate", BLUE, "Policy rate", "-"), ("cpi_yoy", ORANGE, "CPI y/y", "-"),
                                  ("real_policy_rate", GREEN, "Real policy rate", "-"),
                                  ("taylor_rate", GREY, "Taylor-rule rate", "--")):
        ax.plot(q.index, q[col], color=color, lw=1.4, ls=ls, label=label)
    ax.axhline(0, color=GREY, lw=0.6)
    ax.legend(fontsize=7, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    _style(ax, "Policy rate, inflation, real rate and Taylor-rule rate (%)", "Percent")
    _save(fig, "policy")

    sc = results["forecast"]["scenarios"]
    hist = panel[dl.CLP_COL].iloc[-HIST_MONTHS:]
    months = pd.to_datetime(sc["months"])
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    ax.plot(hist.index, hist, color="black", lw=1.4)
    for name, color, label in (("copper_down", ORANGE, "Copper -20%"), ("base", BLUE, "Base (copper flat)"),
                               ("copper_up", GREEN, "Copper +20%")):
        path = [sc["origin_usdclp"]] + sc["cases"][name]["usdclp_path"]
        idx = [hist.index[-1]] + list(months)
        ax.plot(idx, path, color=color, lw=1.5)
        ax.annotate(label, (idx[-1], path[-1]), xytext=(4, 0), textcoords="offset points", fontsize=8,
                    color=color, va="center")
    ax.hlines(sc["naive_usdclp"], hist.index[-1], months[-1], color=GREY, ls=":", lw=1)
    ax.set_xlim(right=months[-1] + pd.DateOffset(months=5))
    _style(ax, "USD/CLP: 12-month scenarios (dotted: random walk)", "CLP per USD")
    _save(fig, "scenario")
