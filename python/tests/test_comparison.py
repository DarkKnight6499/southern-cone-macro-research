import json

import pandas as pd
import pytest

import analysis_comparison as c
import data_loader as dl


def test_build_toy():
    rows = [{dl.WEO_INDICATOR_COL: "NGDP_RPCH", dl.WEO_COUNTRY_COL: "CHL", dl.WEO_YEAR_COL: y, dl.WEO_VALUE_COL: v}
            for y, v in ((2025, 1.0), (2026, 2.0), (2027, 3.0), (2028, 4.0))]
    wide = c.build(pd.DataFrame(rows))
    assert list(wide.columns) == [2026, 2027, 2028]
    assert wide.loc[("NGDP_RPCH", "CHL")].tolist() == [2.0, 3.0, 4.0]


def test_real_table_complete_and_matches_raw_file():
    out = c.run(dl.load_weo(), "test")
    assert len(out["rows"]) == 12
    assert all(len(r["values"]) == 3 for r in out["rows"])
    raw = json.loads((dl.DATA_DIR / "imf_NGDP_RPCH.json").read_text())["values"]["NGDP_RPCH"]["ARG"]["2027"]
    arg = next(r for r in out["rows"] if r["country"] == "Argentina" and r["indicator"].startswith("Real GDP"))
    assert arg["values"]["2027"] == pytest.approx(raw)
