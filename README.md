# Southern Cone Macro Research

A reproducible macro research project on Chile with a small Southern Cone (Chile, Argentina, Uruguay) comparison. It pulls public data by code, runs the econometrics, backtests a forecasting model against naive benchmarks, and builds a sell-side style research note (`SC_Macro_Note_Chile.docx`, about 6 pages) programmatically from the results.

## What it does

1. **Data layer**: `python/fetch_data.py` downloads raw snapshots into `python/data/` (with a `fetch_log.json` recording each endpoint and the retrieval date). Everything after that runs offline. `python/data_loader.py` loads them with named column constants.
2. **Copper and the peso** (`analysis_copper_peso.py`): regression of monthly USD/CLP log changes on copper and broad-dollar log changes with HC3 robust errors, 60-month rolling beta, Granger causality in both directions.
3. **Inflation and policy** (`analysis_policy.py`): real policy rate and an inflation-only Taylor-rule gap with explicit assumptions (neutral real rate 1.0%, inflation target 3.0%, output gap set to zero) plus a sensitivity table.
4. **Forecast** (`analysis_forecast.py`): a VAR(2) on CPI, USD/CLP and copper, tested with an expanding-window backtest (first origin after 120 months) against a random walk (peso) and last-h-month inflation (CPI), with Diebold-Mariano tests. 12-month scenarios (copper flat, -20%, +20%) come from the same model.
5. **Southern Cone table** (`analysis_comparison.py`): IMF WEO real GDP growth, CPI inflation, fiscal balance and gross debt for the current year and the next two.
6. **Note** (`build_note.py`): every number in the note is formatted from `python/outputs/results.json`; a test rebuilds the note and checks it against the JSON.

## Data sources (all keyless, retrieved by code)

| Data | Source |
|---|---|
| Chile CPI index (monthly), central bank policy rate (monthly) | BIS data portal (`WS_LONG_CPI`, `WS_CBPOL`; policy rate compiled from the Banco Central de Chile) |
| Copper price (monthly, USD per tonne), USD/CLP (monthly average), broad US dollar index (daily, averaged monthly) | FRED CSV endpoint (`PCOPPUSDM`, `CCUSMA02CLM618N`, `DTWEXBGS`) |
| Growth, inflation, fiscal balance, debt | IMF World Economic Outlook DataMapper API, April 2026 vintage |

Snapshots in `python/data/` were retrieved on 2026-09-28. Yahoo Finance daily quotes (USDCLP=X, HG=F, DX-Y.NYB) were attempted but rate limited, so no result uses them. FRED's Chile CPI series stop in 2023, which is why CPI comes from BIS. The Banco Central de Chile database needs credentials and is not used.

## How to run

```
cd python
py -3 -m pip install pandas numpy scipy statsmodels matplotlib python-docx requests pytest yfinance
py -3 fetch_data.py        # optional, refreshes python/data/ (needs internet)
py -3 run_all.py           # analyses, outputs/results.json, charts/
py -3 build_note.py        # writes ../SC_Macro_Note_Chile.docx
py -3 -m pytest -q         # 34 tests
```

## Headline results (sample 2006-02 to 2026-07)

- **Copper and the peso**: a 1% copper rise goes with a 0.15% stronger peso in the same month, holding the broad dollar fixed (HC3 t = -4.9, 246 observations). Copper and the dollar together explain 52% of monthly peso moves; copper alone explains 37%. The dollar coefficient is 0.98.
- **Stability**: the rolling 60-month copper beta is negative in every window (range -0.31 to -0.12) and significant at 5% in 97% of them, but the magnitude has grown (post-2020 -0.28, pre-2020 -0.13).
- **No predictive content**: copper does not Granger-cause the peso (p-values 0.42 to 0.87, lags 1 to 6). The link is contemporaneous.
- **Policy**: policy rate 4.50%, CPI 4.13% y/y (2026-08), real rate 0.37%. The inflation-only Taylor rate is 5.70%, so policy is 1.20 pp below the rule under the stated assumptions.
- **Backtest**: the VAR does not beat the random walk for USD/CLP at 1, 3 or 12 months (RMSE ratios 1.01, 1.03, 1.01). It beats the naive benchmark for 1-month inflation (ratio 0.80, DM p 0.0001), but the 12-month inflation gain (ratio 0.89) is not statistically significant (p 0.61).
- **Scenarios** (12 months, USD/CLP from 931): copper -20% gives 1,022; flat copper 973; copper +20% 934. The 90% backtest error band (about 790 to 1,210) is wider than the spread between cases, and the base drift is the model's historical trend, not a forecast.

## Limitations

- Monthly averages smooth the data, and the copper beta drifts over time.
- The neutral real rate is an assumption; the Taylor rule omits the output gap (no keyless monthly gap series).
- The dollar control is a broad trade-weighted index, so its coefficient is a control rather than a structural estimate.
- The VAR is small and reduced form; the copper to inflation link is a correlation, not a causal channel, and is not validated out of sample.
- Argentina and Uruguay are comparison only, using IMF projections that are revised.

## Layout

```
python/            fetch, loader, analyses, charts, note builder
python/tests/      pytest suite (hand-computed toy cases, independent recomputation, data sanity checks)
python/data/       raw snapshots and fetch_log.json
python/outputs/    results.json
python/charts/     PNG charts embedded in the note
SC_Macro_Note_Chile.docx
```

## Disclaimer

This is illustrative research as of 2026-09-28. The analysis and views are the author's own, are not investment advice, and come with no guarantee of accuracy. Data are public and may be revised.
