import json
import re
import zipfile

import pytest
from docx import Document

import build_note as bn

pytestmark = pytest.mark.skipif(not bn.NOTE_FILE.exists(), reason="note not built")


@pytest.fixture(scope="module")
def res():
    return json.loads(bn.RESULTS_FILE.read_text())


@pytest.fixture(scope="module")
def text():
    doc = Document(bn.NOTE_FILE)
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    return "\n".join(parts)


def test_sample_numbers_match_results_json(res, text):
    fx = res["forecast"]["scenarios"]["cases"]
    bt = res["forecast"]["backtest"]
    pol = res["policy"]
    cp = res["copper_peso"]
    expected = [
        bn.n(abs(cp["full"]["coef"]["d_copper"]), 2),
        bn.n(cp["full"]["coef"]["d_dollar"], 2),
        bn.n(100 * cp["full"]["r_squared"], 0) + "%",
        bn.pct(pol["policy_rate"], 2),
        bn.pct(pol["cpi_yoy"], 2),
        bn.pct(pol["real_policy_rate"], 2),
        bn.pct(pol["taylor_rate"], 2),
        bn.n(fx["base"]["usdclp_end"], 0),
        bn.n(fx["copper_down"]["usdclp_end"], 0),
        bn.n(fx["copper_up"]["usdclp_end"], 0),
        bn.n(bt["usdclp_cum_h12"]["ratio_model_to_naive"], 2),
        bn.n(bt["inflation_cum_h1"]["rmse_model"], 2),
        bn.n(res["levels"]["usdclp_last"], 1),
    ]
    for e in expected:
        assert e in text, e


def test_weo_table_values_in_note(res, text):
    for r in res["comparison"]["rows"]:
        for v in r["values"].values():
            assert bn.n(v) in text


def test_no_em_dashes_or_garbled_characters(text):
    assert chr(0x2014) not in text and chr(0x2013) not in text and "--" not in text
    assert chr(0xFFFD) not in text
    assert not re.search(r"[^\x00-\x7f]", text)


def test_metadata_and_heading_style_colors():
    doc = Document(bn.NOTE_FILE)
    assert doc.core_properties.author == "Yazad Madan"
    assert doc.core_properties.last_modified_by == "Yazad Madan"
    styles = zipfile.ZipFile(bn.NOTE_FILE).read("word/styles.xml").decode()
    for sid in ("Heading1", "Heading2"):
        block = re.search(rf'<w:style [^>]*w:styleId="{sid}".*?</w:style>', styles, re.S).group(0)
        assert "<w:color" not in block


def test_note_has_charts_and_expected_sections():
    doc = Document(bn.NOTE_FILE)
    assert len(doc.inline_shapes) == 4
    heads = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    for h in ("Key views", "What changed", "Policy path view", "Risks", "Southern Cone comparison"):
        assert h in heads


def test_note_is_rebuilt_from_json_identically(res, tmp_path):
    out = tmp_path / "rebuilt.docx"
    bn.build(res).save(out)
    a = [p.text for p in Document(out).paragraphs]
    b = [p.text for p in Document(bn.NOTE_FILE).paragraphs]
    assert a == b
