"""Tests of creditlens/export.py (slice 6, issue #9): the Excel download.

The file is built in memory from the display tables (SAMPLE DATA in
app/tests/fixtures/charts_sample.csv and export_financials_sample.csv), then
read back with openpyxl. AC9: the sheets are Summary, Ratios, Financials and
Notes, and every value equals the display table (the screen). No internet.
"""

from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from creditlens import export

ALERTS = {"ALFA": "Orange: 1 orange flag", "BETA": "Red: 1 red flag, 1 not available"}
THRESHOLDS = {
    "net_debt_to_ebitda": {"label": "Net debt / EBITDA", "direction": "lower_is_better", "green": 2.0, "orange": 3.5},
    "free_cash_flow": {"label": "Free cash flow", "direction": "higher_is_better", "green": 0.0, "orange": None},
}


@pytest.fixture
def display(fixtures_dir) -> pd.DataFrame:
    return pd.read_csv(fixtures_dir / "charts_sample.csv", comment="#")


@pytest.fixture
def financials(fixtures_dir) -> pd.DataFrame:
    return pd.read_csv(fixtures_dir / "export_financials_sample.csv", comment="#")


def build(display, financials, **kwargs):
    kwargs.setdefault("generated_on", "2026-11-26")
    content = export.build_excel(display, financials, ALERTS, **kwargs)
    assert isinstance(content, bytes)
    return load_workbook(BytesIO(content))


def records(sheet) -> list[dict]:
    """The rows of a sheet under its header row, as dicts."""
    rows = list(sheet.iter_rows(min_row=export.HEADER_ROW, values_only=True))
    header = rows[0]
    return [dict(zip(header, row)) for row in rows[1:]]


def expected_cell(row) -> object:
    """What the screen shows: the rounded number, or the text when there is no number."""
    return float(row.value) if pd.notna(row.value) else row.text


# --- Workbook --------------------------------------------------------------------------


def test_ac9_workbook_has_the_four_sheets_in_order(display, financials):
    assert build(display, financials).sheetnames == ["Summary", "Ratios", "Financials", "Notes"]


def test_file_name_lists_the_tickers_and_the_date():
    assert export.excel_filename(["AAPL", "MSFT", "NKE"], "2026-11-26") == "CreditLens_AAPL_MSFT_NKE_2026-11-26.xlsx"


def test_missing_column_is_refused(display, financials):
    with pytest.raises(ValueError, match="text"):
        export.build_excel(display.drop(columns="text"), financials, ALERTS, generated_on="2026-11-26")


# --- Ratios sheet ----------------------------------------------------------------------


def test_ac9_every_ratio_cell_equals_the_display_table(display, financials):
    sheet = build(display, financials)["Ratios"]
    by_key = {(r["Ticker"], r["Metric id"]): r for r in records(sheet)}
    assert len(by_key) == display[["ticker", "metric"]].drop_duplicates().shape[0]
    for row in display.itertuples():
        assert by_key[(row.ticker, row.metric)][f"FY{row.fiscal_year}"] == expected_cell(row), row


def test_missing_value_is_written_as_its_reason_never_zero(display, financials):
    sheet = build(display, financials)["Ratios"]
    beta = {r["Metric id"]: r for r in records(sheet) if r["Ticker"] == "BETA"}
    assert beta["net_debt_to_ebitda"]["FY2024"] == "not available: D&A not reported"
    assert beta["interest_coverage"]["FY2026"] == "not available: interest expense not reported"
    gama = {r["Metric id"]: r for r in records(sheet) if r["Ticker"] == "GAMA"}
    assert gama["net_debt_to_ebitda"]["FY2026"] == "not meaningful: EBITDA ≤ 0"
    assert gama["free_cash_flow"]["FY2026"] == 0  # a real zero stays a number


def test_a_fiscal_year_the_company_does_not_have_is_said_not_filled(display, financials):
    sheet = build(display, financials)["Ratios"]
    gama = {r["Metric id"]: r for r in records(sheet) if r["Ticker"] == "GAMA"}
    assert gama["net_debt_to_ebitda"]["FY2022"] == export.NO_YEAR_TEXT


def test_ratios_sheet_holds_both_debt_definitions(display, financials):
    sheet = build(display, financials)["Ratios"]
    alfa = {r["Metric id"]: r for r in records(sheet) if r["Ticker"] == "ALFA"}
    assert alfa["net_debt_to_ebitda"]["Debt definition"] == export.DEBT_DEFINITIONS[False]
    assert alfa["net_debt_to_ebitda_incl_leases"]["Debt definition"] == export.DEBT_DEFINITIONS[True]
    assert alfa["interest_coverage"]["Debt definition"] == export.SAME_FOR_BOTH
    assert alfa["net_debt_to_ebitda_incl_leases"]["FY2026"] == 2.90


def test_ratios_sheet_has_units_labels_and_latest_flag_as_a_word(display, financials):
    sheet = build(display, financials)["Ratios"]
    alfa = {r["Metric id"]: r for r in records(sheet) if r["Ticker"] == "ALFA"}
    row = alfa["net_debt_to_ebitda"]
    assert (row["Company"], row["Metric"], row["Unit"]) == ("Alpha Corp (SAMPLE DATA)", "Net debt / EBITDA", "x")
    assert row["Latest flag"] == "orange"
    gama = {r["Metric id"]: r for r in records(sheet) if r["Ticker"] == "GAMA"}
    assert gama["net_debt_to_ebitda"]["Latest flag"] == export.NO_FLAG_TEXT


def test_numbers_keep_the_screen_rounding_as_excel_formats(display, financials):
    sheet = build(display, financials)["Ratios"]
    header = [c.value for c in sheet[export.HEADER_ROW]]
    fy2026 = header.index("FY2026") + 1
    formats = {}
    for row in sheet.iter_rows(min_row=export.HEADER_ROW + 1):
        cell = row[fy2026 - 1]
        if isinstance(cell.value, (int, float)):
            formats[row[header.index("Unit")].value] = cell.number_format
    assert formats == {"x": export.NUMBER_FORMATS["x"], "USD m": export.NUMBER_FORMATS["USD m"]}


# --- Summary sheet ---------------------------------------------------------------------


def test_summary_one_row_per_company_with_latest_year_and_alert(display, financials):
    rows = records(build(display, financials)["Summary"])
    assert [r["Ticker"] for r in rows] == ["ALFA", "BETA", "GAMA"]
    alfa = rows[0]
    assert alfa["Latest fiscal year"] == 2026
    assert alfa["Fiscal year end"] == "2026-12-31"
    assert alfa["Overall alert"] == "Orange: 1 orange flag"
    assert alfa["Debt definition"] == export.DEBT_DEFINITIONS[False]
    assert (alfa["Net debt / EBITDA"], alfa["Interest coverage"], alfa["Current ratio"]) == (2.40, 6.00, 1.50)
    gama = rows[2]
    assert gama["Overall alert"] == "not available"
    assert gama["Net debt / EBITDA"] == "not meaningful: EBITDA ≤ 0"
    assert gama["Current ratio"] == "not available: current liabilities not reported"


def test_summary_follows_the_selected_debt_definition(display, financials):
    rows = records(build(display, financials, incl_leases=True)["Summary"])
    assert rows[0]["Net debt / EBITDA"] == 2.90
    assert rows[0]["Debt definition"] == export.DEBT_DEFINITIONS[True]


# --- Financials sheet ------------------------------------------------------------------


def test_financials_sheet_equals_the_underlying_data(financials, display):
    rows = records(build(display, financials)["Financials"])
    assert len(rows) == len(financials)
    for got, row in zip(rows, financials.itertuples()):
        assert got["Ticker"] == row.ticker
        assert got["Fiscal year"] == row.fiscal_year
        assert got["Item"] == row.label
        assert got["Value (USD m)"] == expected_cell(row)
        assert got["XBRL tag"] == (row.xbrl_tag if pd.notna(row.xbrl_tag) else None)
        assert got["10-K accession"] == (row.accession if pd.notna(row.accession) else None)
    assert rows[2]["Value (USD m)"] == "not reported"


# --- Notes sheet -----------------------------------------------------------------------


def notes_text(workbook) -> str:
    return "\n".join(str(v) for row in workbook["Notes"].iter_rows(values_only=True) for v in row if v is not None)


def test_notes_give_source_date_rules_and_limits(display, financials):
    text = notes_text(build(display, financials))
    assert "SEC EDGAR" in text
    assert "2026-11-26" in text
    assert export.DEBT_DEFINITIONS[False] in text and export.DEBT_DEFINITIONS[True] in text
    assert "not available" in text and "not meaningful" in text
    assert "slightly conservative" in text  # known limitation of the lease version


def test_notes_list_the_thresholds_when_given(display, financials):
    text = notes_text(build(display, financials, thresholds=THRESHOLDS))
    assert "Net debt / EBITDA: lower is better, green ≤ 2.0, orange ≤ 3.5" in text
    assert "Free cash flow: higher is better, green ≥ 0.0, no orange zone" in text


def test_sample_data_is_marked_on_every_sheet(display, financials):
    workbook = build(display, financials, sample=True)
    for sheet in workbook:
        assert "SAMPLE DATA" in sheet["A1"].value, sheet.title
    assert all("SAMPLE DATA" not in sheet["A1"].value for sheet in build(display, financials))
