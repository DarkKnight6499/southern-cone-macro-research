"""Build SC_Macro_Note_Chile.docx from outputs/results.json (every number is formatted from the JSON)."""
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

import make_charts

# ---------------- CONFIG ----------------
ROOT = Path(__file__).resolve().parents[1]
RESULTS_FILE = ROOT / "python" / "outputs" / "results.json"
CHART_DIR = ROOT / "python" / "charts"
NOTE_FILE = ROOT / "SC_Macro_Note_Chile.docx"
AUTHOR = "Yazad Madan"
BODY_FONT, BODY_SIZE = "Calibri", 10.5
HEADING_SIZES = {"Heading 1": 14, "Heading 2": 12}
# ----------------------------------------


def n(x, d=1):
    return f"{x:,.{d}f}"


def pct(x, d=1):
    return f"{x:.{d}f}%"


def sgn(x, d=1):
    return f"{x:+.{d}f}"


class Note:
    def __init__(self):
        self.doc = Document()
        st = self.doc.styles["Normal"]
        st.font.name, st.font.size = BODY_FONT, Pt(BODY_SIZE)
        st.paragraph_format.space_after = Pt(6)
        for name, size in HEADING_SIZES.items():
            h = self.doc.styles[name]
            h.font.name, h.font.size, h.font.bold = BODY_FONT, Pt(size), True
            h.font.color.rgb = None  # inherit black, no colored headings
        for s in self.doc.sections:
            s.left_margin = s.right_margin = Inches(0.9)
            s.top_margin = s.bottom_margin = Inches(0.8)
        cp = self.doc.core_properties
        cp.author = AUTHOR
        cp.last_modified_by = AUTHOR
        cp.title = "Chile macro note"

    def title(self, text, sub):
        p = self.doc.add_paragraph()
        r = p.add_run(text)
        r.bold, r.font.size = True, Pt(19)
        p.paragraph_format.space_after = Pt(2)
        q = self.doc.add_paragraph()
        r = q.add_run(sub)
        r.italic, r.font.size = True, Pt(9.5)

    def h1(self, t):
        self.doc.add_heading(t, level=1)

    def h2(self, t):
        self.doc.add_heading(t, level=2)

    def para(self, text):
        return self.doc.add_paragraph(text)

    def bullet(self, lead, text):
        p = self.doc.add_paragraph(style="List Bullet")
        r = p.add_run(lead + " ")
        r.bold = True
        p.add_run(text)

    def source(self, text):
        p = self.doc.add_paragraph()
        r = p.add_run(text)
        r.italic, r.font.size = True, Pt(8.5)

    def chart(self, key, caption):
        self.doc.add_picture(str(CHART_DIR / make_charts.CHART_FILES[key]), width=Inches(6.0))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.source(caption)

    def table(self, header, rows, widths=None, size=9, numeric=True):
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(header):
            cell = t.rows[0].cells[i]
            cell.text = ""
            run = cell.paragraphs[0].add_run(h)
            run.bold, run.font.size = True, Pt(size)
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                run = cells[i].paragraphs[0].add_run(str(v))
                run.font.size = Pt(size)
                if i > 0 and numeric:
                    cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for row in t.rows[:-1]:  # keep the table on one page
            for c in row.cells:
                c.paragraphs[0].paragraph_format.keep_with_next = True
        for row in t.rows:
            for c in row.cells:
                c.paragraphs[0].paragraph_format.space_after = Pt(1)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Inches(w)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)


def build(res):
    cp, pol, fc, cmp_, lv, meta = (res[k] for k in ("copper_peso", "policy", "forecast", "comparison", "levels", "meta"))
    full, roll, gr = cp["full"], cp["rolling"], cp["granger"]
    b_cu, b_usd = full["coef"]["d_copper"], full["coef"]["d_dollar"]
    bt, sc = fc["backtest"], fc["scenarios"]
    cases = sc["cases"]
    g1, g2 = gr["copper_causes_clp"], gr["clp_causes_copper"]
    gmin, gmax = min(g1.values()), max(g1.values())
    rev_sig = [k for k, v in g2.items() if v < 0.05]
    weo = {(r["indicator"], r["country"]): r["values"] for r in cmp_["rows"]}
    y0, y1, y2 = (str(y) for y in cmp_["years"])
    gdp, cpi_, fis, debt = (r for r in ("Real GDP growth (%)", "CPI inflation, average (%)",
                                        "General govt net lending/borrowing (% GDP)",
                                        "General govt gross debt (% GDP)"))
    asof = meta["data_retrieved_on"]

    doc = Note()
    doc.title("Chile: copper moves the peso, but not enough to forecast it",
              f"Southern Cone macro note. Illustrative research, as of {asof}. Latest data: CPI and policy rate "
              f"{pol['last_month'][:7]}; USD/CLP and copper (monthly averages) {meta['panel_end'][:7]}.")

    doc.h1("Key views")
    doc.bullet("Copper matters, contemporaneously.",
               f"A 1% rise in copper is associated with a {n(abs(b_cu), 2)}% stronger peso in the same month, holding the "
               f"broad dollar fixed (HC3 t-statistic {n(full['t_hc3']['d_copper'])}, {full['n_obs']} monthly observations). "
               f"The broad dollar dominates: its coefficient is {n(b_usd, 2)}. The two together explain "
               f"{n(100 * full['r_squared'], 0)}% of monthly peso moves.")
    doc.bullet("The relationship is stable in sign but not in size.",
               f"The rolling 60-month copper beta is negative in {n(100 * roll['share_windows_beta_negative'], 0)}% of windows "
               f"and significant at 5% in {n(100 * roll['share_windows_significant_5pct'], 0)}%, but it ranges from "
               f"{n(roll['beta_copper_min'], 2)} to {n(roll['beta_copper_max'], 2)}. The post-{cp['split_date'][:4]} estimate is "
               f"{n(cp['post_split']['coef']['d_copper'], 2)} against {n(cp['pre_split']['coef']['d_copper'], 2)} before.")
    doc.bullet("Copper does not lead the peso.",
               f"Granger tests find no predictive content of copper for the peso (p-values {n(gmin, 2)} to {n(gmax, 2)} across "
               f"lags 1 to {len(g1)}). The link is a same-month co-movement, not a forecasting signal.")
    doc.bullet("Policy is roughly neutral to slightly loose.",
               f"The policy rate is {pct(pol['policy_rate'], 2)} with CPI at {pct(pol['cpi_yoy'], 2)} y/y, a real rate of "
               f"{pct(pol['real_policy_rate'], 2)}. An inflation-only Taylor rule (neutral real rate "
               f"{n(pol['params']['neutral_real_rate'])}%, target {n(pol['params']['target'])}%) gives {pct(pol['taylor_rate'], 2)}, "
               f"so policy sits {n(abs(pol['policy_minus_taylor']), 2)} pp below the rule. Our view is a hold, with easing "
               f"contingent on inflation moving back to target.")
    doc.bullet("Our forecast model does not beat a random walk for the peso.",
               f"In an expanding-window backtest the VAR has a 12-month USD/CLP RMSE ratio of "
               f"{n(bt['usdclp_cum_h12']['ratio_model_to_naive'], 2)} versus the random walk (DM p-value "
               f"{n(bt['usdclp_cum_h12']['dm_pvalue_vs_naive'], 2)}). It does beat a naive benchmark for 1-month inflation "
               f"(ratio {n(bt['inflation_cum_h1']['ratio_model_to_naive'], 2)}, p {n(bt['inflation_cum_h1']['dm_pvalue_vs_naive'], 4)}), "
               f"but the 12-month inflation gain (ratio {n(bt['inflation_cum_h12']['ratio_model_to_naive'], 2)}) is not statistically significant.")
    doc.bullet("Scenarios bracket the peso, they do not predict it.",
               f"With copper -20% the model puts USD/CLP at {n(cases['copper_down']['usdclp_end'], 0)} in 12 months; flat copper "
               f"gives {n(cases['base']['usdclp_end'], 0)}; +20% gives {n(cases['copper_up']['usdclp_end'], 0)}. The backtest error "
               f"band is wider than the whole range between cases.")
    doc.bullet("Southern Cone.",
               f"IMF WEO ({cmp_['vintage']}) has {y0} real growth of {pct(weo[(gdp, 'Chile')][y0])} in Chile, "
               f"{pct(weo[(gdp, 'Argentina')][y0])} in Argentina and {pct(weo[(gdp, 'Uruguay')][y0])} in Uruguay, with "
               f"inflation of {pct(weo[(cpi_, 'Chile')][y0])}, {pct(weo[(cpi_, 'Argentina')][y0])} and "
               f"{pct(weo[(cpi_, 'Uruguay')][y0])} respectively.")

    doc.h1("What changed")
    doc.para(f"Over the twelve months to {meta['panel_end'][:7]}, the monthly average copper price rose "
             f"{n(lv['copper_12m_change_pct'])}% to USD {n(lv['copper_last'], 0)} per tonne, while USD/CLP moved "
             f"{sgn(lv['usdclp_12m_change_pct'])}% to {n(lv['usdclp_last'], 1)} and the broad dollar index moved "
             f"{sgn(lv['usd_broad_12m_change_pct'])}%. The full-sample copper elasticity would have implied a peso move of about "
             f"{sgn(lv['peso_move_implied_by_copper_beta_pct'])}%, so the peso rallied by roughly half as much as copper alone "
             f"suggests. USD/CLP peaked at {n(lv['usdclp_max'], 0)} in {lv['usdclp_max_month'][:7]}.")
    doc.para(f"On policy, the rate stands at {pct(pol['policy_rate'], 2)} against {pct(pol['policy_rate_12m_ago'], 2)} a year earlier. "
             f"Annual CPI inflation is {pct(pol['cpi_yoy'], 2)} against {pct(pol['cpi_yoy_12m_ago'], 2)} a year earlier, and has "
             f"ranged from {pct(pol['cpi_yoy_min_last_24m'], 2)} to {pct(pol['cpi_yoy_max_last_24m'], 2)} over the last 24 months. "
             f"(Sources: BIS for CPI and the policy rate, FRED for copper and the exchange rate; see appendix.)")

    doc.h1("Copper, peso and inflation drivers")
    doc.para(f"We regress monthly log changes in USD/CLP on log changes in copper and in the Federal Reserve broad dollar index, "
             f"with HC3 heteroskedasticity-robust errors, over {cp['sample'][0][:7]} to {cp['sample'][1][:7]}. Copper alone explains "
             f"{n(100 * cp['copper_only']['r_squared'], 0)}% of peso variance (coefficient {n(cp['copper_only']['coef']['d_copper'], 2)}); "
             f"adding the dollar lifts this to {n(100 * full['r_squared'], 0)}% and shrinks the copper coefficient to "
             f"{n(b_cu, 2)}, which means part of copper's apparent effect is the shared dollar cycle.")
    doc.table(["Sample", "Copper beta", "t (HC3)", "Dollar beta", "t (HC3)", "R-squared", "Obs"], [
        [lab, n(x["coef"]["d_copper"], 2), n(x["t_hc3"]["d_copper"], 1), n(x["coef"]["d_dollar"], 2),
         n(x["t_hc3"]["d_dollar"], 1), n(x["r_squared"], 2), x["n_obs"]]
        for lab, x in (("Full sample", full), (f"Before {cp['split_date'][:4]}", cp["pre_split"]),
                       (f"{cp['split_date'][:4]} onward", cp["post_split"]))])
    doc.chart("copper_peso", "Source: FRED (IMF copper price, OECD exchange rate); monthly averages; author calculations.")
    doc.para(f"The rolling estimate is stable in sign but drifts: the latest {roll['window_months']}-month beta is "
             f"{n(roll['beta_copper_latest'], 2)}, the most negative of {roll['n_windows']} windows. That is consistent with "
             f"copper mattering more for the peso in recent years, but the confidence bands in the chart overlap for most of the "
             f"sample, so we do not read the drift as proven.")
    doc.chart("beta", "Source: FRED; author calculations. Band is plus or minus 1.96 HC3 standard errors.")
    rev = ", ".join(f"lag {k}" for k in rev_sig)
    doc.para(f"Granger causality points the other way from the usual narrative. Copper changes do not help predict peso changes "
             f"(p-values {n(gmin, 2)} to {n(gmax, 2)}), whereas peso changes have some predictive content for copper at {rev} "
             f"(p-values from {n(min(g2.values()), 3)}). With twelve tests across two directions we treat the reverse result as "
             f"suggestive at best. On inflation, the VAR used below finds a small lagged link from copper to CPI: cutting copper by "
             f"20% lowers 12-month CPI inflation by {n(cases['base']['cpi_yoy_end_pct'] - cases['copper_down']['cpi_yoy_end_pct'], 2)} pp "
             f"relative to flat copper. We read that as a reduced-form correlation, not a causal channel, and it is not validated out of sample.")

    doc.h1("Policy path view")
    doc.para(f"The real policy rate, defined as the policy rate minus trailing 12-month CPI inflation, is "
             f"{pct(pol['real_policy_rate'], 2)}, against an average of {pct(pol['avg_real_rate_since'], 2)} since "
             f"{pol['avg_start'][:4]}. Using a Taylor-type rule i = r* + pi + 0.5 (pi - target), with r* = "
             f"{n(pol['params']['neutral_real_rate'])}% and target = {n(pol['params']['target'])}% as explicit assumptions and the "
             f"output gap set to zero, the implied rate is {pct(pol['taylor_rate'], 2)} and the policy rate is "
             f"{n(abs(pol['policy_minus_taylor']), 2)} pp below it.")
    sens = pol["sensitivity"]
    doc.table(["Assumed neutral real rate", "Policy rate minus Taylor rate (pp)"],
              [[f"{k}%", sgn(v, 2)] for k, v in sens.items()])
    doc.chart("policy", "Source: BIS (policy rate, CPI index); author calculations. Taylor rate uses stated assumptions.")
    doc.para(f"Our view is a hold. Inflation is above the {n(pol['params']['target'])}% target, the real rate is below the assumed "
             f"neutral, and the model's flat-copper base case has CPI inflation at {pct(cases['base']['cpi_yoy_end_pct'], 2)} "
             f"twelve months out. Limits: the neutral rate is an assumption rather than an estimate, the rule omits the output gap "
             f"(no keyless monthly gap series was available), and monthly CPI y/y is noisy, so single-month gaps should not be over-read.")

    doc.h1("Forecast backtest and 12-month scenarios")
    doc.para(f"The model is a VAR({fc['lags']}) on monthly log changes in CPI, USD/CLP and copper. It is re-estimated each month on an "
             f"expanding window; the first forecast origin is {fc['first_forecast_origin'][:7]} (after {fc['min_train_months']} months of "
             f"history) and the sample ends {fc['sample_end'][:7]}. Errors are on cumulative changes over the horizon, in log points x100. "
             f"The benchmark is a random walk for the peso and the last h-month inflation for CPI.")
    rows = []
    for key, lab in (("usdclp_cum_h1", "USD/CLP, 1m"), ("usdclp_cum_h3", "USD/CLP, 3m"), ("usdclp_cum_h12", "USD/CLP, 12m"),
                     ("inflation_cum_h1", "Inflation, 1m"), ("inflation_cum_h3", "Inflation, 3m"),
                     ("inflation_cum_h12", "Inflation, 12m")):
        b = bt[key]
        rows.append([lab, n(b["rmse_model"], 2), n(b["rmse_naive"], 2), n(b["ratio_model_to_naive"], 2),
                     n(b["dm_pvalue_vs_naive"], 3), "Yes" if b["beats_naive"] else "No", b["n_forecasts"]])
    doc.table(["Target and horizon", "RMSE model", "RMSE naive", "Ratio", "DM p-value", "Beats naive", "N"], rows)
    sens_l = fc["lag_sensitivity_h12_ratio"]
    doc.para(f"The honest reading is mixed. The model does not beat the random walk for the peso at any horizon "
             f"(ratios {n(bt['usdclp_cum_h1']['ratio_model_to_naive'], 2)}, {n(bt['usdclp_cum_h3']['ratio_model_to_naive'], 2)} and "
             f"{n(bt['usdclp_cum_h12']['ratio_model_to_naive'], 2)}). For inflation it wins at one month "
             f"(statistically significant), loses narrowly at three months, and wins at twelve months by a margin that is not "
             f"significant given overlapping forecasts. Changing the lag order from 1 to 3 leaves the 12-month peso ratio between "
             f"{n(min(v['usdclp_cum_h12'] for v in sens_l.values()), 2)} and {n(max(v['usdclp_cum_h12'] for v in sens_l.values()), 2)}.")
    doc.para(f"Scenarios hold copper on a stated path for {len(sc['months'])} months (flat, -{n(sc['copper_shock_pct'], 0)}% or "
             f"+{n(sc['copper_shock_pct'], 0)}% cumulative, spread evenly in logs). The VAR then generates the peso and inflation, and "
             f"a same-month pass-through of copper surprises to the peso (loading {n(sc['copper_loading_fx'], 2)}, from the "
             f"VAR residuals) is added. The 90% band uses the 12-month backtest RMSE of the peso forecast, not a model-based interval.")
    srows = []
    for key, lab in (("copper_down", "Copper down"), ("base", "Base (copper flat)"), ("copper_up", "Copper up")):
        c = cases[key]
        srows.append([lab, n(c["copper_end"], 0), (sgn(c["copper_change_pct"], 0) if round(c["copper_change_pct"]) else "0") + "%", n(c["usdclp_end"], 0),
                      sgn(c["usdclp_change_pct"]) + "%", f"{n(c['usdclp_band_low'], 0)} to {n(c['usdclp_band_high'], 0)}",
                      pct(c["cpi_yoy_end_pct"], 2)])
    srows.append(["Naive reference", "n/a", "n/a", n(sc["naive_usdclp"], 0), "0.0%", "n/a", pct(sc["naive_cpi_yoy_pct"], 2)])
    doc.table(["Case", "Copper USD/t", "Copper chg", "USD/CLP 12m", "vs spot", "90% band", "CPI y/y 12m"], srows)
    doc.chart("scenario", "Source: FRED; author's VAR scenarios. Origin is the last monthly average; dotted line is the random walk.")
    doc.para(f"Because the model does not beat the random walk for the peso, the base case drift (USD/CLP {sgn(cases['base']['usdclp_change_pct'])}% "
             f"with flat copper) is the VAR's historical depreciation trend and should not be read as a forecast. The scenario "
             f"spread is best read as the conditional sensitivity of the peso to copper, about {n(abs(sc['copper_loading_fx']), 2)}% per 1% "
             f"copper move on the same-month channel.")

    doc.h1("Risks")
    for lead, text in (
        ("Copper reversal.", f"After a {n(lv['copper_12m_change_pct'], 0)}% rise in twelve months, a correction would weaken the peso through the "
                             f"channel above; the scenario table quantifies this."),
        ("Global dollar.", f"The broad dollar coefficient ({n(b_usd, 2)}) is larger than copper's, so a dollar rally could overwhelm copper support."),
        ("Inflation persistence.", f"CPI is {pct(pol['cpi_yoy'], 2)} y/y against a {n(pol['params']['target'])}% target; if it stays above, the "
                                   f"case for easing weakens and the real rate stays low."),
        ("Model and data risk.", f"Monthly averages smooth the data, the copper beta drifts over time, the neutral rate is an assumption, and the "
                                 f"Southern Cone figures are IMF projections that are revised."),
    ):
        doc.bullet(lead, text)

    doc.h1("Southern Cone comparison")
    doc.para(f"IMF WEO, {cmp_['vintage']}. Chile pairs moderate growth with inflation near target and a rising debt ratio; Argentina "
             f"shows fast disinflation from a high base and a fiscal balance near zero; Uruguay runs steadier inflation with a larger deficit. "
             f"Figures for {y0} to {y2} are IMF estimates and projections.")
    crow = []
    for ind in (gdp, cpi_, fis, debt):
        for ctry in ("Chile", "Argentina", "Uruguay"):
            v = weo[(ind, ctry)]
            crow.append([ind if ctry == "Chile" else "", ctry, n(v[y0]), n(v[y1]), n(v[y2])])
    doc.table(["Indicator", "Country", y0, y1, y2], crow, widths=[2.9, 1.0, 0.7, 0.7, 0.7], size=8.5)

    doc.h1("Appendix: sources, method and disclaimer")
    doc.h2("Sources (retrieved by code on " + asof + ")")
    src_rows = [[s["file"], s["description"], s["url"]] for s in meta["sources"]]
    doc.table(["Snapshot", "Description", "Endpoint"], src_rows, widths=[1.5, 2.4, 3.0], size=7.5, numeric=False)
    failed = ", ".join(s["url"].replace("yfinance ", "") for s in meta["failed_sources"])
    doc.para(f"Not used: Yahoo Finance daily quotes ({failed}) were rate limited when fetched, so no daily or futures data enter any "
             f"result. The Banco Central de Chile database was not used because it needs credentials. FRED's Chile CPI series end in "
             f"2023, so CPI comes from the BIS long CPI series, which is updated to {pol['last_month'][:7]}.")
    doc.h2("Method notes")
    doc.para("Exchange rate is national currency per USD (OECD via FRED, monthly average); copper is the IMF global price (USD per tonne, "
             "monthly average); the dollar control is the Federal Reserve broad nominal dollar index averaged by month. Regressions use "
             "monthly log changes, HC3 errors, and a 60-month rolling window. Real rate = policy rate minus trailing 12-month CPI "
             "inflation. The VAR is estimated by OLS with a constant; scenarios hold copper on a stated path and add a Cholesky-style "
             "same-month pass-through. Diebold-Mariano tests use Bartlett HAC variance and the Harvey small-sample correction.")
    doc.h2("Disclaimer")
    doc.para(f"This note is illustrative research written for portfolio purposes as of {asof}. The analysis and views are the author's own, "
             f"are not investment advice, and come with no guarantee of accuracy. Data are public and may be revised.")
    return doc.doc


def main():
    res = json.loads(RESULTS_FILE.read_text())
    build(res).save(NOTE_FILE)
    print("wrote", NOTE_FILE)


if __name__ == "__main__":
    main()
