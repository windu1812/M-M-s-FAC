"""Journey tests of the charts and the "Download Excel" button on the page (slice 6, step 6c).

AppTest runs the page without a browser, offline (conftest.py), on the SAMPLE DATA
companies of tests/synthetic_company.py. The expected numbers are worked out by
hand, never taken from the app:

* ALFA FY2026 is the example company of docs/acceptance.md: Net debt / EBITDA
  1.42x with financial debt only (CALC4a), 2.00x including leases (CALC4b);
  interest coverage 1,000 / 125 = 8.00x (CALC6).
* ALFA FY2025 and FY2024: interest coverage 900 / 150 = 6.00x.
* BETA tags no interest expense and no D&A, so its interest coverage and its
  Net debt / EBITDA are "not available": no bar, no point, never 0.
"""

import json
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from creditlens import charts, export
from creditlens.data import sec_client

import synthetic_company as sc

APP_FILE = Path(__file__).resolve().parents[1] / "streamlit_app.py"
TIMEOUT = 30  # seconds
RATIO_SELECTOR = "chart_ratio"
DEBT_SELECTOR = "incl_leases"


@pytest.fixture
def cache():
    """The SAMPLE DATA companies, saved in the (temporary) SEC cache of the test."""
    sc.write_cache(sec_client.CACHE_DIR)


@pytest.fixture
def excel_files(monkeypatch):
    """Record every Excel file the page builds (the bytes given to the download button)."""
    built = []

    def recording_build_excel(*args, **kwargs):
        content = real_build_excel(*args, **kwargs)
        built.append(content)
        return content

    real_build_excel = export.build_excel
    monkeypatch.setattr(export, "build_excel", recording_build_excel)
    return built


def run(tickers: str) -> AppTest:
    at = AppTest.from_file(str(APP_FILE), default_timeout=TIMEOUT).run()
    at.text_input(key="tickers").input(tickers)  # the field is in a form: typed and sent with Run
    at.button(key="run").click().run()
    assert not at.exception, at.exception
    return at


def figures(at: AppTest) -> list[dict]:
    """The Plotly figures on the page, in their order: comparison bars, then 5-year lines."""
    return [json.loads(chart.proto.spec) for chart in at.get("plotly_chart")]


def bars(at: AppTest) -> dict:
    """Company label -> bar value (None when there is no bar), and the axis title."""
    figure = figures(at)[0]
    bar = figure["data"][0]
    return {"values": dict(zip(bar["y"], bar["x"])), "axis": figure["layout"]["xaxis"]["title"]["text"]}


def lines(at: AppTest) -> dict:
    """Company -> its points by fiscal year (None when there is no point), and the axis title."""
    figure = figures(at)[1]
    points = {trace["name"]: dict(zip(trace["x"], trace["y"])) for trace in figure["data"]}
    return {"points": points, "axis": figure["layout"]["yaxis"]["title"]["text"]}


def annotations(at: AppTest, index: int) -> list[str]:
    return [a["text"] for a in figures(at)[index]["layout"].get("annotations", [])]


# --- The charts (visuals 2 and 3) ---------------------------------------------------------------


def test_no_chart_and_no_excel_button_before_a_run():
    at = AppTest.from_file(str(APP_FILE), default_timeout=TIMEOUT).run()

    assert not at.get("plotly_chart")
    assert not at.get("download_button")


def test_run_shows_both_charts_for_net_debt_to_ebitda_by_default(cache):
    at = run("ALFA, BETA")

    assert at.selectbox(key=RATIO_SELECTOR).value == "net_debt_to_ebitda"
    titles = [f["layout"]["title"]["text"] for f in figures(at)]
    assert titles == [charts.COMPARISON_TITLE, charts.TREND_TITLE]
    assert bars(at)["axis"] == "Net debt / EBITDA (x)"
    assert bars(at)["values"]["ALFA (FY2026)"] == pytest.approx(1.42)  # CALC4a


def test_ratio_selector_offers_the_six_chart_ratios_with_their_labels(cache):
    at = run("ALFA, BETA")

    assert at.selectbox(key=RATIO_SELECTOR).options == [
        "Net debt / EBITDA", "Debt / equity", "Interest coverage", "Current ratio", "EBITDA margin",
        "Free cash flow",
    ]


def test_picking_interest_coverage_switches_both_charts_and_missing_is_never_zero(cache):
    """AC8."""
    at = run("ALFA, BETA")

    at.selectbox(key=RATIO_SELECTOR).select("interest_coverage").run()

    assert not at.exception
    assert bars(at)["axis"] == "Interest coverage (x)"
    assert lines(at)["axis"] == "Interest coverage (x)"
    assert bars(at)["values"]["ALFA (FY2026)"] == pytest.approx(8.00)  # CALC6
    assert lines(at)["points"]["ALFA"] == {2024: pytest.approx(6.00), 2025: pytest.approx(6.00),
                                           2026: pytest.approx(8.00)}
    # BETA: interest expense not reported -> no bar and no point (None, never 0), labelled "n/a".
    assert bars(at)["values"]["BETA (FY2026)"] is None
    assert set(lines(at)["points"]["BETA"].values()) == {None}
    assert any(text.startswith("n/a (not available") and "interest expense" in text
               for text in annotations(at, 0))


def test_debt_selector_switches_the_charts_and_keeps_the_chosen_ratio(cache):
    """AC5b, charts part."""
    at = run("ALFA, BETA")
    assert bars(at)["values"]["ALFA (FY2026)"] == pytest.approx(1.42)  # CALC4a

    at.radio(key=DEBT_SELECTOR).set_value(True).run()

    assert at.selectbox(key=RATIO_SELECTOR).value == "net_debt_to_ebitda"
    assert bars(at)["axis"] == "Net debt / EBITDA, incl. leases (x)"
    assert bars(at)["values"]["ALFA (FY2026)"] == pytest.approx(2.00)  # CALC4b


def test_a_ratio_without_debt_does_not_change_with_the_debt_selector(cache):
    at = run("ALFA, BETA")
    at.selectbox(key=RATIO_SELECTOR).select("interest_coverage").run()

    at.radio(key=DEBT_SELECTOR).set_value(True).run()

    assert at.selectbox(key=RATIO_SELECTOR).value == "interest_coverage"
    assert bars(at)["axis"] == "Interest coverage (x)"
    assert bars(at)["values"]["ALFA (FY2026)"] == pytest.approx(8.00)


# --- The "Download Excel" button (visual 5) -------------------------------------------------------


def test_download_excel_button_gives_the_four_sheets_with_the_screen_values(cache, excel_files):
    """AC9: the file has Summary, Ratios, Financials and Notes, with the numbers shown on screen."""
    at = run("ALFA, BETA")

    buttons = at.get("download_button")
    assert [b.proto.label for b in buttons] == ["Download Excel"]
    assert excel_files, "the page built no Excel file"

    workbook = load_workbook(BytesIO(excel_files[-1]))
    assert workbook.sheetnames == ["Summary", "Ratios", "Financials", "Notes"]
    summary = workbook["Summary"]
    header = [cell.value for cell in summary[export.HEADER_ROW]]
    alfa = next(row for row in summary.iter_rows(min_row=export.HEADER_ROW + 1, values_only=True)
                if row[0] == "ALFA")
    assert alfa[header.index("Net debt / EBITDA")] == pytest.approx(1.42)  # CALC4a, as on the card
    assert alfa[header.index("Interest coverage")] == pytest.approx(8.00)  # CALC6
    assert alfa[header.index("Debt definition")] == "Financial debt only"
    card_texts = [m.value for m in at.markdown]
    assert any(alfa[header.index("Overall alert")] in text for text in card_texts)  # same alert as the card


def test_excel_summary_follows_the_debt_selector(cache, excel_files):
    """AC5b: the Summary sheet uses the selected debt definition; the Ratios sheet always has both."""
    at = run("ALFA, BETA")

    at.radio(key=DEBT_SELECTOR).set_value(True).run()

    workbook = load_workbook(BytesIO(excel_files[-1]))
    summary = workbook["Summary"]
    header = [cell.value for cell in summary[export.HEADER_ROW]]
    alfa = next(row for row in summary.iter_rows(min_row=export.HEADER_ROW + 1, values_only=True)
                if row[0] == "ALFA")
    assert alfa[header.index("Net debt / EBITDA")] == pytest.approx(2.00)  # CALC4b
    assert alfa[header.index("Debt definition")] == "Including leases and short-term borrowings"
    metric_ids = {row[3] for row in workbook["Ratios"].iter_rows(min_row=export.HEADER_ROW + 1,
                                                                   values_only=True)}
    assert {"net_debt_to_ebitda", "net_debt_to_ebitda_incl_leases"} <= metric_ids


def test_excel_latest_flag_uses_the_words_of_the_screen(cache, excel_files):
    """AC9: "Latest flag" in the Ratios sheet reads like the ratio table on the page."""
    at = run("ALFA, BETA")

    ratios = load_workbook(BytesIO(excel_files[-1]))["Ratios"]
    header = [cell.value for cell in ratios[export.HEADER_ROW]]
    latest = {(row[0], row[3]): row[header.index("Latest flag")]
              for row in ratios.iter_rows(min_row=export.HEADER_ROW + 1, values_only=True)}
    screen = at.dataframe[0].value.set_index(["Ticker", "Metric"])["Latest flag"]
    assert latest[("ALFA", "ebitda")] == "–" == screen[("ALFA", "EBITDA")]  # amounts get no flag
    assert latest[("BETA", "net_debt_to_ebitda")] == "n/a" == screen[("BETA", "Net debt / EBITDA")]  # no D&A
    assert latest[("ALFA", "debt_to_equity")] == "orange" == screen[("ALFA", "Debt / equity")]  # 1.53x, CALC12


def test_excel_file_name_lists_the_companies_shown_and_the_date(cache, monkeypatch):
    names = []

    def recording_filename(*args, **kwargs):
        names.append(real_filename(*args, **kwargs))
        return names[-1]

    real_filename = export.excel_filename
    monkeypatch.setattr(export, "excel_filename", recording_filename)

    run("ALFA, NOPE, BETA")  # NOPE is not a known ticker: it is not in the file

    assert names[-1] == f"CreditLens_ALFA_BETA_{date.today().isoformat()}.xlsx"
