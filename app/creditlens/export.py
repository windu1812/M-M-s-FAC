"""The "Download Excel" file of CreditLens (slice 6, issue #9; visual 5 of docs/product.md).

:func:`build_excel` returns an ``.xlsx`` file, in memory, with four sheets:

* **Summary**: one row per company, latest fiscal year, overall alert and the
  three headline ratios for the selected debt definition;
* **Ratios**: one row per company and metric, one column per fiscal year, with
  both debt definitions;
* **Financials**: the input figures in USD m, with the XBRL tag and the 10-K
  accession number ("View underlying data");
* **Notes**: source, date, definitions, rules and known limitations.

Input: the display tables of creditlens/display.py (format in
docs/architecture.md, samples in app/tests/fixtures/). This module computes
nothing (docs/architecture.md): it writes the values as they are shown on screen.
A number stays a number, with an Excel format that shows the screen rounding;
a missing value is written as its text ("not available: D&A not reported"),
never as 0 or an empty cell.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from creditlens.flags import FLAGGED_RATIOS

SHEETS = ["Summary", "Ratios", "Financials", "Notes"]
TITLE_ROW = 1
SOURCE_ROW = 2
HEADER_ROW = 4  # the data starts on the next row

INCL_LEASES = "_incl_leases"
DEBT_BASED_METRICS = ["total_debt", "net_debt", "net_debt_to_ebitda", "debt_to_equity"]
DEBT_DEFINITIONS = {False: "Financial debt only", True: "Including leases and short-term borrowings"}
SAME_FOR_BOTH = "same for both"

# The three ratios of the summary cards (visual 1 of docs/product.md).
HEADLINE_METRICS = [
    ("net_debt_to_ebitda", "Net debt / EBITDA"),
    ("interest_coverage", "Interest coverage"),
    ("current_ratio", "Current ratio"),
]

NOT_AVAILABLE_TEXT = "not available"
NO_YEAR_TEXT = "no data for this fiscal year"
NO_FLAG_TEXT = "n/a"  # a flagged ratio with no value to flag: the same word as the screen
NOT_FLAGGED_TEXT = "–"  # an amount (EBITDA, total debt, net debt): never flagged, as on the screen

# Excel formats that show the screen rounding (ratios 2 decimals, margin 1, amounts 0).
NUMBER_FORMATS = {"x": '0.00"x"', "%": '0.0" %"', "USD m": "#,##0"}
FLAG_FILLS = {
    "green": PatternFill("solid", fgColor="C8E6C9"),
    "orange": PatternFill("solid", fgColor="FFE0B2"),
    "red": PatternFill("solid", fgColor="FFCDD2"),
}

DISPLAY_COLUMNS = ["ticker", "company", "fiscal_year", "period_end", "metric", "label", "unit", "value", "text", "flag"]
FINANCIALS_COLUMNS = ["ticker", "company", "fiscal_year", "period_end", "label", "value", "text", "xbrl_tag",
                      "accession", "status"]

SOURCE_TEXT = "Source: SEC EDGAR XBRL company facts, annual 10-K filings (free public data)."


def excel_filename(tickers: list[str], on: date | str) -> str:
    """The name of the downloaded file, for example ``CreditLens_AAPL_MSFT_2026-11-26.xlsx``."""
    return f"CreditLens_{'_'.join(tickers)}_{on}.xlsx"


def _check_columns(table: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [c for c in columns if c not in table.columns]
    if missing:
        raise ValueError(f"The {name} table has no column(s) {missing}.")


def _optional(value):
    """A text cell, or None (an empty cell) for a missing tag or accession number."""
    return None if pd.isna(value) else str(value)


def _screen_value(value, text):
    """The number shown on screen, or its text when there is no number (never 0)."""
    return text if pd.isna(value) else float(value)


def _debt_definition(metric: str) -> str:
    if metric.endswith(INCL_LEASES):
        return DEBT_DEFINITIONS[True]
    if metric in DEBT_BASED_METRICS:
        return DEBT_DEFINITIONS[False]
    return SAME_FOR_BOTH


def _start_sheet(sheet, title: str, header: list[str], sample: bool) -> None:
    """Title, source line and header row, the same on every sheet."""
    if sample:
        title += " - SAMPLE DATA (synthetic companies, not real filings)"
    sheet.cell(TITLE_ROW, 1, title).font = Font(bold=True, size=14)
    sheet.cell(SOURCE_ROW, 1, SOURCE_TEXT).font = Font(italic=True, color="595959")
    for col, name in enumerate(header, start=1):
        sheet.cell(HEADER_ROW, col, name).font = Font(bold=True)
        sheet.column_dimensions[get_column_letter(col)].width = max(12, len(name) + 2)
    sheet.freeze_panes = sheet.cell(HEADER_ROW + 1, 1)


def _write_value(sheet, row: int, col: int, value, text, unit: str, flag=None) -> None:
    cell = sheet.cell(row, col, _screen_value(value, text))
    if not pd.isna(value):
        cell.number_format = NUMBER_FORMATS.get(unit, "General")
    if isinstance(flag, str) and flag in FLAG_FILLS:
        cell.fill = FLAG_FILLS[flag]


def _write_summary(sheet, display: pd.DataFrame, alerts: dict, incl_leases: bool, sample: bool) -> None:
    header = ["Ticker", "Company", "Latest fiscal year", "Fiscal year end", "Overall alert", "Debt definition"]
    header += [label for _, label in HEADLINE_METRICS]
    _start_sheet(sheet, "CreditLens - Summary, latest fiscal year", header, sample)
    sheet.column_dimensions["B"].width = 30
    sheet.column_dimensions["E"].width = 36
    sheet.column_dimensions["F"].width = 40

    row = HEADER_ROW + 1
    for ticker, rows in display.groupby("ticker", sort=False):
        latest_year = int(rows["fiscal_year"].max())
        latest = rows[rows["fiscal_year"] == latest_year]
        values = [ticker, rows.iloc[0]["company"], latest_year, str(latest.iloc[0]["period_end"]),
                  alerts.get(ticker, NOT_AVAILABLE_TEXT), DEBT_DEFINITIONS[incl_leases]]
        for col, value in enumerate(values, start=1):
            sheet.cell(row, col, value)
        for i, (metric, _) in enumerate(HEADLINE_METRICS, start=len(values) + 1):
            if metric in DEBT_BASED_METRICS and incl_leases:
                metric += INCL_LEASES
            match = latest[latest["metric"] == metric]
            if match.empty:
                sheet.cell(row, i, NOT_AVAILABLE_TEXT)
                continue
            r = match.iloc[0]
            _write_value(sheet, row, i, r["value"], r["text"], r["unit"], r["flag"])
        row += 1


def _write_ratios(sheet, display: pd.DataFrame, sample: bool) -> None:
    years = sorted(int(y) for y in display["fiscal_year"].unique())
    header = ["Ticker", "Company", "Metric", "Metric id", "Debt definition", "Unit"]
    header += [f"FY{y}" for y in years] + ["Latest flag"]
    _start_sheet(sheet, "CreditLens - Credit ratios, last 5 fiscal years", header, sample)
    sheet.column_dimensions["B"].width = 30
    sheet.column_dimensions["C"].width = 34
    sheet.column_dimensions["D"].width = 32
    sheet.column_dimensions["E"].width = 40

    row = HEADER_ROW + 1
    for (ticker, metric), rows in display.groupby(["ticker", "metric"], sort=False):
        first = rows.iloc[0]
        values = [ticker, first["company"], first["label"], metric, _debt_definition(metric), first["unit"]]
        for col, value in enumerate(values, start=1):
            sheet.cell(row, col, value)
        by_year = rows.set_index("fiscal_year")
        for col, year in enumerate(years, start=len(values) + 1):
            if year not in by_year.index:
                sheet.cell(row, col, NO_YEAR_TEXT)
                continue
            r = by_year.loc[year]
            _write_value(sheet, row, col, r["value"], r["text"], r["unit"], r["flag"])
        latest_flag = by_year.loc[by_year.index.max(), "flag"]
        if metric.removesuffix(INCL_LEASES) not in FLAGGED_RATIOS:
            flag_text = NOT_FLAGGED_TEXT
        else:
            flag_text = latest_flag if isinstance(latest_flag, str) and latest_flag else NO_FLAG_TEXT
        sheet.cell(row, len(header), flag_text)
        row += 1


def _write_financials(sheet, financials: pd.DataFrame, sample: bool) -> None:
    header = ["Ticker", "Company", "Fiscal year", "Fiscal year end", "Item", "Value (USD m)", "XBRL tag",
              "10-K accession", "Status"]
    _start_sheet(sheet, "CreditLens - Underlying data from the 10-K (USD m)", header, sample)
    sheet.column_dimensions["B"].width = 30
    sheet.column_dimensions["E"].width = 34
    sheet.column_dimensions["G"].width = 50
    sheet.column_dimensions["H"].width = 24

    for row, r in enumerate(financials.itertuples(), start=HEADER_ROW + 1):
        values = [r.ticker, r.company, int(r.fiscal_year), str(r.period_end), r.label]
        for col, value in enumerate(values, start=1):
            sheet.cell(row, col, value)
        _write_value(sheet, row, 6, r.value, r.text, "USD m")
        sheet.cell(row, 7, _optional(r.xbrl_tag))
        sheet.cell(row, 8, _optional(r.accession))
        sheet.cell(row, 9, r.status)


def _threshold_lines(thresholds: dict) -> list[tuple[str, str]]:
    lines = []
    for rule in thresholds.values():
        lower = rule["direction"] == "lower_is_better"
        sign = "≤" if lower else "≥"
        text = f"{rule['label']}: {'lower' if lower else 'higher'} is better, green {sign} {rule['green']:.1f}, "
        text += f"orange {sign} {rule['orange']:.1f}" if rule["orange"] is not None else "no orange zone"
        lines.append(("Threshold", text))
    return lines


def _write_notes(sheet, generated_on, thresholds: dict | None, sample: bool) -> None:
    _start_sheet(sheet, "CreditLens - Notes", ["Topic", "Note"], sample)
    sheet.column_dimensions["A"].width = 22
    sheet.column_dimensions["B"].width = 110
    notes = [
        ("Generated on", str(generated_on)),
        ("Source", SOURCE_TEXT + " The fiscal year is identified by the period end date of each figure."),
        ("Units", "Amounts in USD millions (0 decimals); ratios in times, x (2 decimals); "
                  "EBITDA margin in percent (1 decimal). Values are rounded as on the CreditLens screen."),
        ("Debt definitions", f"{DEBT_DEFINITIONS[False]}: long-term debt (noncurrent) + current portion of "
                             f"long-term debt. {DEBT_DEFINITIONS[True]}: the same + short-term borrowings "
                             "(commercial paper) + operating and finance lease liabilities. "
                             "The Ratios sheet holds both."),
        ("Missing values", "\"not available\" means an input is not reported or a denominator is zero; "
                           "\"not meaningful\" means a negative denominator (EBITDA ≤ 0, negative equity). "
                           "No missing value is estimated or replaced by 0."),
        ("Fiscal years", "Fiscal year-end dates differ by company; see the \"Fiscal year end\" column."),
        ("Known limitation", "With leases, Net debt / EBITDA is slightly conservative: lease liabilities are "
                             "added to debt, but the operating lease cost is not added back to EBITDA."),
        ("Flags", "Green / orange / red from app/config/thresholds.toml; a value exactly on a limit takes "
                  "the better colour."),
    ]
    notes += _threshold_lines(thresholds or {})
    for row, (topic, text) in enumerate(notes, start=HEADER_ROW + 1):
        sheet.cell(row, 1, topic).font = Font(bold=True)
        sheet.cell(row, 2, text)


def build_excel(
    display: pd.DataFrame,
    financials: pd.DataFrame,
    alerts: dict[str, str],
    *,
    generated_on: date | str,
    incl_leases: bool = False,
    thresholds: dict | None = None,
    sample: bool = False,
) -> bytes:
    """Build the Excel file and return its content, ready for ``st.download_button``.

    Args:
        display: the display table of the ratios, with all metrics of both
            debt definitions (format in docs/architecture.md).
        financials: the "View underlying data" table (USD m).
        alerts: ticker -> overall alert text (``flags.overall_alert(...).text``).
        generated_on: the date written in the Notes sheet.
        incl_leases: the debt definition selected on screen, used in Summary.
        thresholds: the rules of flags.load_thresholds(), listed in Notes.
        sample: True marks every sheet "SAMPLE DATA" (synthetic data).

    Raises:
        ValueError: if a table lacks a column this module needs.
    """
    _check_columns(display, DISPLAY_COLUMNS, "display")
    _check_columns(financials, FINANCIALS_COLUMNS, "financials")

    workbook = Workbook()
    workbook.active.title = SHEETS[0]
    for name in SHEETS[1:]:
        workbook.create_sheet(name)
    _write_summary(workbook["Summary"], display, alerts, incl_leases, sample)
    _write_ratios(workbook["Ratios"], display, sample)
    _write_financials(workbook["Financials"], financials, sample)
    _write_notes(workbook["Notes"], generated_on, thresholds, sample)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
