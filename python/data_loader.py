"""Load the raw snapshots in data/ into tidy frames; all column names are constants."""
import json
from pathlib import Path

import pandas as pd

# ---------------- CONFIG ----------------
DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_END = None  # None means use the last month all series share
# ----------------------------------------

CPI_COL = "cpi_index"
POLICY_COL = "policy_rate"
CLP_COL = "usdclp"
COPPER_COL = "copper_usd_t"
DOLLAR_COL = "usd_broad_index"

BIS_TIME_COL = "TIME_PERIOD"
BIS_VALUE_COL = "OBS_VALUE"
FRED_DATE_COL = "observation_date"

WEO_INDICATOR_COL = "indicator"
WEO_COUNTRY_COL = "country"
WEO_YEAR_COL = "year"
WEO_VALUE_COL = "value"


def load_bis(filename, data_dir=DATA_DIR):
    df = pd.read_csv(Path(data_dir) / filename, usecols=[BIS_TIME_COL, BIS_VALUE_COL])
    idx = pd.to_datetime(df[BIS_TIME_COL] + "-01")
    return pd.Series(df[BIS_VALUE_COL].to_numpy(dtype=float), index=idx).sort_index()


def load_fred(sid, data_dir=DATA_DIR):
    df = pd.read_csv(Path(data_dir) / f"fred_{sid}.csv", na_values=["."])
    ser = pd.Series(df[sid].to_numpy(dtype=float), index=pd.to_datetime(df[FRED_DATE_COL]))
    return ser.dropna().sort_index()


def load_monthly(data_dir=DATA_DIR, end=SAMPLE_END):
    """Monthly panel on the common sample (broad dollar starts 2006)."""
    dollar_daily = load_fred("DTWEXBGS", data_dir)
    dollar = dollar_daily.resample("MS").mean()
    panel = pd.concat(
        {
            CPI_COL: load_bis("bis_cpi_CL.csv", data_dir),
            POLICY_COL: load_bis("bis_cbpol_CL.csv", data_dir),
            CLP_COL: load_fred("CCUSMA02CLM618N", data_dir),
            COPPER_COL: load_fred("PCOPPUSDM", data_dir),
            DOLLAR_COL: dollar,
        },
        axis=1,
    )
    panel = panel.dropna()
    if end is not None:
        panel = panel.loc[:end]
    panel.index.name = "month"
    return panel


def load_weo(data_dir=DATA_DIR):
    rows = []
    for path in sorted(Path(data_dir).glob("imf_*.json")):
        values = json.loads(path.read_text())["values"]
        for ind, by_country in values.items():
            if not ind or not by_country:
                continue
            for country, by_year in by_country.items():
                for year, val in by_year.items():
                    rows.append({WEO_INDICATOR_COL: ind, WEO_COUNTRY_COL: country,
                                 WEO_YEAR_COL: int(year), WEO_VALUE_COL: float(val)})
    return pd.DataFrame(rows)


def load_fetch_log(data_dir=DATA_DIR):
    return json.loads((Path(data_dir) / "fetch_log.json").read_text())
