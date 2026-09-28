"""Southern Cone comparison table from the IMF WEO snapshot."""
import pandas as pd

import data_loader as dl

# ---------------- CONFIG ----------------
COUNTRIES = {"CHL": "Chile", "ARG": "Argentina", "URY": "Uruguay"}
INDICATORS = {
    "NGDP_RPCH": "Real GDP growth (%)",
    "PCPIPCH": "CPI inflation, average (%)",
    "GGXCNL_NGDP": "General govt net lending/borrowing (% GDP)",
    "GGXWDG_NGDP": "General govt gross debt (% GDP)",
}
FIRST_YEAR = 2026  # current year of the as-of date; two forecast years follow
N_YEARS = 3
# ----------------------------------------


def build(weo, first_year=FIRST_YEAR, n_years=N_YEARS):
    years = list(range(first_year, first_year + n_years))
    sel = weo[weo[dl.WEO_INDICATOR_COL].isin(INDICATORS) & weo[dl.WEO_COUNTRY_COL].isin(COUNTRIES)
              & weo[dl.WEO_YEAR_COL].isin(years)]
    wide = sel.pivot_table(index=[dl.WEO_INDICATOR_COL, dl.WEO_COUNTRY_COL], columns=dl.WEO_YEAR_COL,
                           values=dl.WEO_VALUE_COL)
    return wide[years]


def run(weo, vintage):
    wide = build(weo)
    rows = []
    for ind, label in INDICATORS.items():
        for code, name in COUNTRIES.items():
            rows.append({"indicator": label, "country": name,
                         "values": {str(y): float(wide.loc[(ind, code), y]) for y in wide.columns}})
    return {"vintage": vintage, "years": [int(y) for y in wide.columns], "rows": rows}
