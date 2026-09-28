import numpy as np
import pandas as pd
import pytest

import data_loader as dl


def test_load_bis_toy(tmp_path):
    (tmp_path / "x.csv").write_text("TIME_PERIOD,OBS_VALUE\n2020-02,2.5\n2020-01,1.5\n")
    s = dl.load_bis("x.csv", tmp_path)
    assert list(s.index) == [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-02-01")]
    assert list(s.values) == [1.5, 2.5]


def test_load_fred_drops_missing_dot(tmp_path):
    (tmp_path / "fred_ABC.csv").write_text("observation_date,ABC\n2020-01-01,1.0\n2020-01-02,.\n2020-01-03,3.0\n")
    s = dl.load_fred("ABC", tmp_path)
    assert len(s) == 2 and s.iloc[-1] == 3.0


@pytest.fixture(scope="module")
def panel():
    return dl.load_monthly()


def test_panel_columns_and_no_nans(panel):
    assert list(panel.columns) == [dl.CPI_COL, dl.POLICY_COL, dl.CLP_COL, dl.COPPER_COL, dl.DOLLAR_COL]
    assert not panel.isna().any().any()


def test_panel_dates_monotone_unique_monthly(panel):
    assert panel.index.is_monotonic_increasing and panel.index.is_unique
    assert (panel.index.day == 1).all()
    months = panel.index.year * 12 + panel.index.month
    assert (np.diff(months) == 1).all()


def test_panel_levels_positive_and_plausible(panel):
    assert (panel[[dl.CPI_COL, dl.CLP_COL, dl.COPPER_COL, dl.DOLLAR_COL]] > 0).all().all()
    assert panel[dl.CLP_COL].between(300, 2000).all()


def test_monthly_mean_of_daily_dollar(tmp_path):
    days = pd.date_range("2020-01-01", "2020-03-31")
    m = pd.date_range("2020-01-01", periods=3, freq="MS")
    for sid, val in (("CCUSMA02CLM618N", 800.0), ("PCOPPUSDM", 6000.0)):
        pd.DataFrame({"observation_date": m.strftime("%Y-%m-%d"), sid: val}).to_csv(tmp_path / f"fred_{sid}.csv", index=False)
    pd.DataFrame({"observation_date": days.strftime("%Y-%m-%d"), "DTWEXBGS": 100.0 + np.arange(len(days))}).to_csv(
        tmp_path / "fred_DTWEXBGS.csv", index=False)
    for name in ("bis_cpi_CL", "bis_cbpol_CL"):
        pd.DataFrame({"TIME_PERIOD": ["2020-01", "2020-02", "2020-03"], "OBS_VALUE": [1.0, 2.0, 3.0]}).to_csv(
            tmp_path / f"{name}.csv", index=False)
    p = dl.load_monthly(tmp_path)
    assert p[dl.DOLLAR_COL].iloc[0] == pytest.approx(100 + np.mean(np.arange(31)))


def test_weo_has_three_countries_and_no_nan():
    w = dl.load_weo()
    assert {"CHL", "ARG", "URY"} <= set(w[dl.WEO_COUNTRY_COL])
    assert not w[dl.WEO_VALUE_COL].isna().any()
