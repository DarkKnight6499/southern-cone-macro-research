import pandas as pd
import pytest

import analysis_policy as p
import data_loader as dl


def test_yoy_hand_value():
    idx = pd.date_range("2020-01-01", periods=13, freq="MS")
    cpi = pd.Series([100.0] * 12 + [103.0], index=idx)
    assert p.yoy(cpi).iloc[-1] == pytest.approx(3.0)
    assert p.yoy(cpi).iloc[:12].isna().all()


def test_taylor_hand_value():
    # 1 + 5 + 0.5 * (5 - 3) = 7
    assert p.taylor_rate(5.0, r_star=1.0, target=3.0, phi=0.5) == pytest.approx(7.0)
    assert p.taylor_rate(3.0, r_star=1.0, target=3.0, phi=0.5) == pytest.approx(4.0)


def test_build_real_rate_and_gap():
    idx = pd.date_range("2020-01-01", periods=13, freq="MS")
    panel = pd.DataFrame({dl.CPI_COL: [100.0] * 12 + [105.0], dl.POLICY_COL: 6.0}, index=idx)
    out = p.build(panel, r_star=1.0)
    assert len(out) == 1
    assert out[p.REAL_COL].iloc[0] == pytest.approx(1.0)
    assert out[p.TAYLOR_COL].iloc[0] == pytest.approx(1 + 5 + 0.5 * 2)
    assert out[p.GAP_COL].iloc[0] == pytest.approx(6 - 7)


def test_real_data_sanity():
    cp = pd.concat({dl.CPI_COL: dl.load_bis("bis_cpi_CL.csv"), dl.POLICY_COL: dl.load_bis("bis_cbpol_CL.csv")},
                   axis=1).dropna()
    res, df = p.run(cp)
    assert not df.isna().any().any() and df.index.is_monotonic_increasing
    assert res["real_policy_rate"] == pytest.approx(res["policy_rate"] - res["cpi_yoy"])
    assert res["policy_minus_taylor"] == pytest.approx(res["policy_rate"] - res["taylor_rate"])
