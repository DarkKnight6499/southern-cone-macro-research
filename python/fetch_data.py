"""Fetch raw public data snapshots into python/data/ (run once, then everything works offline)."""
import datetime as dt
import json
import time
from pathlib import Path

import requests

# ---------------- CONFIG ----------------
DATA_DIR = Path(__file__).resolve().parent / "data"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_SERIES = {
    "PCOPPUSDM": "Global price of copper, USD per metric ton, monthly (IMF via FRED)",
    "CCUSMA02CLM618N": "Chile national currency per USD, monthly average (OECD via FRED)",
    "DTWEXBGS": "Nominal broad US dollar index, daily (Federal Reserve Board via FRED)",
}
BIS_URL = "https://stats.bis.org/api/v2/data/dataflow/BIS/{flow}/1.0/{key}?format=csv"
BIS_SERIES = {
    "bis_cbpol_CL": ("WS_CBPOL", "M.CL", "Chile central bank policy rate, monthly (BIS, source Banco Central de Chile)"),
    "bis_cpi_CL": ("WS_LONG_CPI", "M.CL.628", "Chile consumer price index, monthly, index level (BIS long CPI series)"),
}
IMF_URL = "https://www.imf.org/external/datamapper/api/v1/{ind}"
IMF_INDICATORS = ["NGDP_RPCH", "PCPIPCH", "GGXCNL_NGDP", "GGXWDG_NGDP"]
YF_TICKERS = {"USDCLP=X": "yf_usdclp.csv", "HG=F": "yf_copper_futures.csv", "DX-Y.NYB": "yf_dxy.csv"}
YF_START = "2003-01-01"
RETRIES = 3
HEADERS = {"User-Agent": "curl/8.0"}  # IMF edge rejects browser-like and python default agents
# ----------------------------------------


def get(url):
    last = None
    for i in range(RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            return r
        except Exception as exc:  # retry on transient FRED slowness
            last = exc
            time.sleep(3 * (i + 1))
    raise last


def main():
    DATA_DIR.mkdir(exist_ok=True)
    today = dt.date.today().isoformat()
    log = {"retrieved_on": today, "sources": []}

    def record(name, url, desc, status, extra=None):
        log["sources"].append({"file": name, "url": url, "description": desc, "status": status, **(extra or {})})
        print(status, name)

    for sid, desc in FRED_SERIES.items():
        url = FRED_URL.format(sid=sid)
        try:
            (DATA_DIR / f"fred_{sid}.csv").write_bytes(get(url).content)
            record(f"fred_{sid}.csv", url, desc, "ok")
        except Exception as exc:
            record(f"fred_{sid}.csv", url, desc, f"FAILED: {exc}")
    for name, (flow, key, desc) in BIS_SERIES.items():
        url = BIS_URL.format(flow=flow, key=key)
        try:
            (DATA_DIR / f"{name}.csv").write_bytes(get(url).content)
            record(f"{name}.csv", url, desc, "ok")
        except Exception as exc:
            record(f"{name}.csv", url, desc, f"FAILED: {exc}")
    for ind in IMF_INDICATORS:
        url = IMF_URL.format(ind=ind)
        try:
            (DATA_DIR / f"imf_{ind}.json").write_bytes(get(url).content)
            record(f"imf_{ind}.json", url, "IMF World Economic Outlook DataMapper", "ok")
        except Exception as exc:
            record(f"imf_{ind}.json", url, "IMF World Economic Outlook DataMapper", f"FAILED: {exc}")
    try:
        meta = get("https://www.imf.org/external/datamapper/api/v1/indicators").json()["indicators"]
        log["imf_weo_vintage"] = meta["NGDP_RPCH"]["source"]
    except Exception as exc:
        log["imf_weo_vintage"] = f"FAILED: {exc}"
    try:  # optional cross-check only, often rate limited
        import yfinance as yf
        for tk, fname in YF_TICKERS.items():
            df = yf.download(tk, start=YF_START, progress=False, auto_adjust=True)
            if len(df) == 0:
                record(fname, "yfinance " + tk, "optional daily cross-check", "FAILED: empty (rate limited)")
            else:
                df.columns = [c[0] for c in df.columns]
                df.to_csv(DATA_DIR / fname)
                record(fname, "yfinance " + tk, "optional daily cross-check", "ok")
    except Exception as exc:
        record("yfinance", "yfinance", "optional daily cross-check", f"FAILED: {exc}")
    (DATA_DIR / "fetch_log.json").write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
