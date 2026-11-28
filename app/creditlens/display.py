"""Display-ready values of the CreditLens dashboard (slice 5, issue #8).

The page (``streamlit_app.py``), the charts (``charts.py``) and the Excel file
(``export.py``) all show the numbers prepared here, so the card, the chart, the
table and the Excel cell always agree (docs/architecture.md, "Display layer").

This module does not call any API and does not read any file. It only:

* rounds once, with the rule of docs/product.md (amounts 0 decimals, ratios
  2 decimals, EBITDA margin 1 decimal), the same way as ``flags.py``;
* writes the screen text of every value ("1.42x", "20.0 %", "1,100 USD m",
  "not available: D&A not reported");
* gives every metric and input item its label;
* builds the summary cards, the wide "Credit ratios, last 5 fiscal years"
  table and the "View underlying data" table;
* checks the tickers typed by the user.

Main entry points:

* :func:`parse_tickers`
* :func:`display_table` -> the display table read by charts.py and export.py
  (one row per ticker, fiscal year and metric; sample in
  app/tests/fixtures/charts_sample.csv);
* :func:`underlying_table` -> the "View underlying data" table, also the
  Financials sheet of the Excel file;
* :func:`summary_card`, :func:`ratio_table`.

A missing value is never 0: its ``value`` is empty (NaN) and its ``text``
says why.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd

# Names shared with ratios.py and flags.py: imported, never copied, so they cannot drift apart.
from creditlens.flags import DISPLAY_DECIMALS, FLAGGED_RATIOS, LOWER_IS_BETTER, shown_value
from creditlens.ratios import (  # noqa: F401 - re-exported for the page, charts.py and export.py
    DEBT_BASED_METRICS,
    INCL_LEASES,
    METRICS,
    PERCENT,
    STATUS_NOT_AVAILABLE,
    STATUS_NOT_MEANINGFUL,
    STATUS_OK,
    TIMES,
    USD_M,
)

MAX_TICKERS = 5

# Fiscal-year columns of the table "Credit ratios, last 5 fiscal years" (AC5).
TABLE_YEARS = 5

# Decimals shown on screen, per unit (docs/product.md, "Rules"): the same table as flags.py.
DECIMALS = DISPLAY_DECIMALS

DEBT_DEFINITIONS = {False: "Financial debt only", True: "Including leases and short-term borrowings"}

# The 9 numbers of the ratio table, in the order of ratios.METRICS (docs/product.md). The
# debt-based ones get the INCL_LEASES suffix for the second debt definition.
TABLE_METRICS = [metric for metric in METRICS if not metric.endswith(INCL_LEASES)]

# The three ratios of each summary card (visual 1 of docs/product.md).
CARD_METRICS = ["net_debt_to_ebitda", "interest_coverage", "current_ratio"]

METRIC_LABELS = {
    "ebitda": "EBITDA",
    "total_debt": "Total debt",
    "net_debt": "Net debt",
    "net_debt_to_ebitda": "Net debt / EBITDA",
    "debt_to_equity": "Debt / equity",
    "interest_coverage": "Interest coverage",
    "current_ratio": "Current ratio",
    "ebitda_margin": "EBITDA margin",
    "free_cash_flow": "Free cash flow",
}
INCL_LEASES_LABEL = ", incl. leases"  # "Net debt / EBITDA, incl. leases (x)": no double brackets

# The input items of data/xbrl_tags.py, in the order of the 10-K statements.
ITEM_LABELS = {
    "revenue": "Revenue",
    "operating_income": "Operating income",
    "net_income": "Net income",
    "depreciation_amortization": "D&A",
    "interest_expense": "Interest expense",
    "total_assets": "Total assets",
    "total_liabilities": "Total liabilities",
    "stockholders_equity": "Equity",
    "current_assets": "Current assets",
    "current_liabilities": "Current liabilities",
    "cash": "Cash",
    "long_term_debt": "Long-term debt (noncurrent)",
    "long_term_debt_current": "Current portion of long-term debt",
    "short_term_borrowings": "Short-term borrowings",
    "operating_lease_liabilities": "Operating lease liabilities",
    "finance_lease_liabilities": "Finance lease liabilities",
    "operating_cash_flow": "Operating cash flow",
    "capex": "Capex",
}
NOT_REPORTED_TEXT = "not reported"

# Columns of the two tables read by charts.py and export.py (docs/architecture.md).
DISPLAY_COLUMNS = ["ticker", "company", "fiscal_year", "period_end", "metric", "label", "unit", "value", "text",
                   "status", "flag", "reason"]
UNDERLYING_COLUMNS = ["ticker", "company", "fiscal_year", "period_end", "item", "label", "value", "text",
                      "xbrl_tag", "accession", "status"]

# Words of the "Latest flag" column: the meaning never depends on colour alone.
NO_FLAG_TEXT = "n/a"  # a flagged ratio with no value to flag ("not available" or "not meaningful")
NOT_FLAGGED_TEXT = "–"  # an amount (EBITDA, total debt, net debt): never flagged
NO_YEAR_TEXT = "no data"  # the company has no 10-K figures for that fiscal year
# Cell colours of the ratio table: light, so the dark text stays readable; the same as the Excel file.
CELL_COLOURS = {"green": "#C8E6C9", "orange": "#FFE0B2", "red": "#FFCDD2"}
NOTES_SEPARATOR = " | "  # between the year groups of the "Notes" column ("; " stays inside one reason)

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


# --- Numbers and texts ---------------------------------------------------------------


def round_value(value: float, unit: str) -> float:
    """Round a value as it is shown on screen: flags.shown_value, the rule of the flags (halves up).

    A value that rounds to zero is written 0, never -0.
    """
    rounded = shown_value(value, unit)
    return 0.0 if rounded == 0 else rounded


def format_number(value: float, unit: str, with_unit: bool = True) -> str:
    """The screen text of a number that is already rounded: "1.42x", "20.0 %", "-1,200 USD m".

    ``with_unit=False`` gives the number alone ("1.42", "20.0", "-1,200"), for the
    ratio table, whose "Unit" column already gives the unit.
    """
    if unit == TIMES:
        return f"{value:,.2f}" + ("x" if with_unit else "")
    if unit == PERCENT:
        return f"{value:,.1f}" + (" %" if with_unit else "")
    return f"{value:,.0f}" + (f" {USD_M}" if with_unit else "")


def missing_text(status: str, reason: str) -> str:
    """The screen text of a value that is not there: "not available: D&A not reported"."""
    return f"{status}: {reason}" if reason else status


def metric_label(metric: str) -> str:
    """The label of a metric: "Net debt / EBITDA" or "Net debt / EBITDA, incl. leases"."""
    base = metric.removesuffix(INCL_LEASES)
    label = METRIC_LABELS[base]
    return label + INCL_LEASES_LABEL if metric != base else label


def selected_metric(metric: str, incl_leases: bool) -> str:
    """The metric name for the selected debt definition (debt-based metrics get the suffix)."""
    return metric + INCL_LEASES if incl_leases and metric in DEBT_BASED_METRICS else metric


def _date_text(value) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _clean_reason(reason) -> str:
    return reason if isinstance(reason, str) else ""


# --- Ticker input --------------------------------------------------------------------


def parse_tickers(raw: str) -> tuple[list[str], str]:
    """Read the ticker field.

    Tickers are separated by commas or spaces, written in capitals, and given
    only once each (in the order typed). A dot is read as a dash, as in the
    SEC list: "BRK.B" and "BRK-B" are the same company.

    Returns:
        ``(tickers, error)``: the list of tickers and an empty error, or an
        empty list and the message to show. Nothing must be downloaded when
        there is an error (AC2).
    """
    tickers: list[str] = []
    for part in re.split(r"[,;\s]+", raw or ""):
        ticker = part.strip().upper().replace(".", "-")
        if ticker and ticker not in tickers:
            tickers.append(ticker)

    if not tickers:
        return [], "Enter 1 to 5 tickers, for example AAPL, MSFT, NKE."
    if len(tickers) > MAX_TICKERS:
        return [], f"Enter 1 to 5 tickers: you entered {len(tickers)} ({', '.join(tickers)})."
    wrong = [t for t in tickers if not TICKER_PATTERN.match(t)]
    if wrong:
        return [], (
            f"Not a valid ticker: {', '.join(wrong)}. A ticker starts with a letter and holds only "
            "letters, digits, '.' or '-' (for example AAPL or BRK-B)."
        )
    return tickers, ""


# --- The display table (read by the page, charts.py and export.py) ------------------------


def company_names(financials: pd.DataFrame) -> dict[str, str]:
    """ticker -> company name, from the table of get_financials."""
    return {str(t): str(c) for t, c in financials.groupby("ticker", sort=False)["company"].first().items()}


def display_table(flagged: pd.DataFrame, financials: pd.DataFrame) -> pd.DataFrame:
    """The ratios ready to show: one row per ticker, fiscal year and metric.

    Args:
        flagged: the table of flags.apply_flags (all 13 metrics, both debt definitions).
        financials: the table(s) of get_financials, for the company names.

    Returns:
        The columns of ``DISPLAY_COLUMNS``. ``value`` is rounded as on screen
        (NaN when there is no number); ``text`` is what the screen shows;
        ``reason`` keeps the note of an "ok" value (for example
        "short-term borrowings not reported"); ``period_end`` is a
        "YYYY-MM-DD" text. Rows keep the order of ``flagged``.

    Raises:
        ValueError: if an "ok" row has no value (a missing value must say why).
    """
    names = company_names(financials)
    rows = []
    for r in flagged.itertuples(index=False):
        reason = _clean_reason(r.reason)
        if r.status == STATUS_OK:
            if pd.isna(r.value):
                raise ValueError(f"display_table: {r.ticker} FY{r.fiscal_year} {r.metric} is \"ok\" but has no value.")
            value = round_value(r.value, r.unit)
            text = format_number(value, r.unit)
        else:
            value = math.nan
            text = missing_text(r.status, reason)
        rows.append({
            "ticker": r.ticker,
            "company": names.get(r.ticker, r.ticker),
            "fiscal_year": int(r.fiscal_year),
            "period_end": _date_text(r.period_end),
            "metric": r.metric,
            "label": metric_label(r.metric),
            "unit": r.unit,
            "value": value,
            "text": text,
            "status": r.status,
            "flag": r.flag if isinstance(r.flag, str) else "",
            "reason": reason,
        })
    return pd.DataFrame(rows, columns=DISPLAY_COLUMNS)


def underlying_table(financials: pd.DataFrame) -> pd.DataFrame:
    """The input figures ready to show ("View underlying data", Excel Financials sheet).

    One row per ticker, fiscal year (most recent first) and item (in the order
    of ``ITEM_LABELS``). ``value`` is in USD m, rounded to 0 decimals, NaN when
    the item is not reported; ``text`` is "1,100 USD m" or "not reported".
    """
    order = {item: i for i, item in enumerate(ITEM_LABELS)}
    table = financials.assign(_order=financials["item"].map(order).fillna(len(order)))
    table = table.sort_values(["fiscal_year", "_order"], ascending=[False, True], kind="stable")
    ticker_order = {t: i for i, t in enumerate(dict.fromkeys(financials["ticker"]))}
    table = table.sort_values("ticker", key=lambda s: s.map(ticker_order), kind="stable")

    rows = []
    for r in table.itertuples(index=False):
        reported = r.status == STATUS_OK and not pd.isna(r.value)
        value = round_value(float(r.value) / 1_000_000, USD_M) if reported else math.nan
        rows.append({
            "ticker": r.ticker,
            "company": r.company,
            "fiscal_year": int(r.fiscal_year),
            "period_end": _date_text(r.period_end),
            "item": r.item,
            "label": ITEM_LABELS.get(r.item, r.item),
            "value": value,
            "text": format_number(value, USD_M) if reported else NOT_REPORTED_TEXT,
            "xbrl_tag": r.xbrl_tag if reported else None,
            "accession": r.accession if reported else None,
            "status": r.status,
        })
    return pd.DataFrame(rows, columns=UNDERLYING_COLUMNS)


# --- Summary cards --------------------------------------------------------------------


@dataclass(frozen=True)
class Headline:
    """One ratio of a summary card."""

    label: str
    unit: str
    text: str  # the full text: "1.42x" or "not available: D&A not reported"
    shown: str  # the short text in bold on the card: "1.42x" or "not available"
    flag: str  # "green", "orange", "red" or "" (no flag)
    change: str  # "+0.17x vs FY2025", why no change is shown, or "" when there is no value
    note: str  # the reason of a missing value, or the note of an "ok" one ("short-term borrowings not reported")


@dataclass(frozen=True)
class Card:
    """The summary card of one company, for its latest fiscal year."""

    ticker: str
    company: str
    fiscal_year: int
    period_end: str
    alert_level: str  # "green", "orange", "red" or "" for "N/A" (not rated)
    alert_text: str
    alert_note: str  # what the alert covers: the 6 flagged ratios, of which the card shows 3
    headlines: list[Headline]


def change_text(current: pd.Series, previous: pd.Series | None, previous_year: int,
                direction: str | None = None) -> str:
    """The change of a value vs the prior fiscal year, computed on the rounded values shown.

    Examples: "+0.17x vs FY2025", "-1.5 pt vs FY2025", "+200 USD m vs FY2025".
    No change is computed when either year has no number; the text then says why.
    With the ``direction`` of the ratio's thresholds ("lower_is_better" or
    "higher_is_better"), a change that is not zero ends with "(better)" or
    "(worse)": a fall of Net debt / EBITDA is good, a fall of the current ratio is not.
    """
    if pd.isna(current["value"]):
        return ""  # the card already says why there is no value
    if previous is None:
        return f"no change shown: no FY{previous_year} data"
    if pd.isna(previous["value"]):
        return f"no change shown: FY{previous_year} {previous['status']}"
    unit = current["unit"]
    change = round_value(current["value"] - previous["value"], unit)
    sign = "+" if change > 0 else ""  # a negative number already has its minus sign
    if unit == PERCENT:
        number = f"{sign}{change:,.1f} pt"  # a change of a margin is in percentage points
    else:
        number = sign + format_number(change, unit)
    text = f"{number} vs FY{previous_year}"
    if direction and change != 0:
        better = change < 0 if direction == LOWER_IS_BETTER else change > 0
        text += " (better)" if better else " (worse)"
    return text


def summary_card(display: pd.DataFrame, ticker: str, alert, incl_leases: bool = False,
                 thresholds: dict | None = None) -> Card:
    """The summary card of one company.

    Args:
        display: the table of :func:`display_table`.
        ticker: the company.
        alert: its ``flags.overall_alert(...)`` for the same debt definition.
        incl_leases: the selected debt definition.
        thresholds: the rules of ``flags.load_thresholds()``; with them, each
            change says "(better)" or "(worse)". None leaves that out.
    """
    company = display[display["ticker"] == ticker]
    if company.empty:
        raise ValueError(f"summary_card: no rows for {ticker}.")
    latest_year = int(company["fiscal_year"].max())
    latest = company[company["fiscal_year"] == latest_year].set_index("metric")
    previous = company[company["fiscal_year"] == latest_year - 1].set_index("metric")

    headlines = []
    for base in CARD_METRICS:
        metric = selected_metric(base, incl_leases)
        row = latest.loc[metric]
        prior = previous.loc[metric] if metric in previous.index else None
        headlines.append(Headline(
            label=row["label"],
            unit=row["unit"],
            text=row["text"],
            shown=row["text"] if row["status"] == STATUS_OK else row["status"],
            flag=row["flag"],
            change=change_text(row, prior, latest_year - 1, (thresholds or {}).get(base, {}).get("direction")),
            note=row["reason"],
        ))
    first = latest.iloc[0]
    return Card(
        ticker=ticker,
        company=first["company"],
        fiscal_year=latest_year,
        period_end=first["period_end"],
        alert_level=alert.level,
        alert_text=alert.text,
        alert_note=(f"Alert on all {len(FLAGGED_RATIOS)} flagged ratios of FY{latest_year} (see the table)."
                    if alert.level else  # "N/A": say why the company is not rated
                    f"Not rated: too few of the {len(FLAGGED_RATIOS)} flagged ratios of FY{latest_year} have a value "
                    "(see the table)."),
        headlines=headlines,
    )


# --- Table "Credit ratios, last 5 fiscal years" --------------------------------------------


def _year_column(year: int) -> str:
    return f"FY{year}"


def years_text(years: list[int]) -> str:
    """Fiscal years in a short form, consecutive years as a range.

    [2022, 2023, 2024, 2025] gives "FY2022–FY2025"; [2022, 2024] gives "FY2022, FY2024".
    """
    parts, run = [], []
    for year in sorted(years):
        if run and year != run[-1] + 1:
            parts.append(run)
            run = []
        run.append(year)
    if run:
        parts.append(run)
    return ", ".join(_year_column(r[0]) if len(r) == 1 else f"{_year_column(r[0])}–{_year_column(r[-1])}"
                     for r in parts)


def table_years(display: pd.DataFrame) -> tuple[list[int], list[int]]:
    """The fiscal years of the ratio table, and the older years left out of it.

    Year ends differ by company: a September company may already have FY2026
    while a December one ends at FY2025, so together they cover 6 fiscal
    years. The table keeps the 5 most recent fiscal years present (AC5); a
    year that no company has is skipped, never filled (E11).

    Returns:
        ``(shown, left_out)``, both oldest first.
    """
    years = sorted(int(y) for y in display["fiscal_year"].unique())
    if not years:
        return [], []
    return years[-TABLE_YEARS:], years[:-TABLE_YEARS]


def left_out_years_text(display: pd.DataFrame) -> str:
    """The sentence under the table title when older years are left out, else ""."""
    shown, left_out = table_years(display)
    if not left_out:
        return ""
    text = f"Only the {TABLE_YEARS} most recent fiscal years are shown; left out: {years_text(left_out)}."
    latest = display.groupby("ticker", sort=False)["fiscal_year"].max()
    for ticker, year in latest.items():
        if int(year) < shown[0]:  # all its rows would read "no data": say why
            text += f" {ticker} has no fiscal year in this table (latest: {_year_column(int(year))})."
    return text


def _latest_flag_word(metric: str, metric_rows: pd.DataFrame, last_column_year: int) -> str:
    """The "Latest flag" word of one row: "orange", "n/a" or "–", with the year when it is not the last column."""
    if metric.removesuffix(INCL_LEASES) not in FLAGGED_RATIOS:
        return NOT_FLAGGED_TEXT  # amounts are never flagged, so no year either
    latest_year = int(metric_rows.index.max())
    word = metric_rows.loc[latest_year, "flag"] or NO_FLAG_TEXT
    if latest_year != last_column_year:  # this company has no figure in the last column yet
        word += f" ({_year_column(latest_year)})"
    return word


def grouped_errors(errors: dict[str, tuple[str, str]]) -> list[tuple[list[str], str, str]]:
    """The error boxes to show: tickers with the same title and the same message share one box (for example
    "Settings missing" for every ticker); a different message gets its own box. The order is kept."""
    groups: dict[tuple[str, str], list[str]] = {}
    for ticker, (title, message) in errors.items():
        groups.setdefault((title, message), []).append(ticker)
    return [(tickers, title, message) for (title, message), tickers in groups.items()]


def cell_style(flag: str) -> str:
    """The CSS of a ratio-table cell with this flag: its colour, or "" for no flag."""
    colour = CELL_COLOURS.get(flag)
    return f"background-color: {colour}; color: #1a1a1a" if colour else ""


def table_caption(display: pd.DataFrame, incl_leases: bool = False) -> str:
    """The text under the title of the ratio table: what its words and colours mean."""
    caption = (
        f"Debt definition: {DEBT_DEFINITIONS[incl_leases]}. Values are in the unit of the Unit column; "
        "cell colours are the flags. \"no data\": no 10-K figures for that fiscal year. "
        "\"Latest flag\": the flag of the company's latest fiscal year as a word, with the year when it is "
        "not the last column; \"n/a\": no value to flag; \"–\": amounts are not flagged. "
        "\"Notes\": why a value is missing, or a part counted as zero. Fiscal year-end dates differ by company."
    )
    left_out = left_out_years_text(display)
    return f"{caption} {left_out}" if left_out else caption


def ratio_table(display: pd.DataFrame, incl_leases: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The wide ratio table: one row per company and metric, one column per fiscal year.

    Only the 9 numbers of the selected debt definition are kept. A cell shows
    the number without its unit ("1.42"; the "Unit" column gives it) or its
    status ("not available"). The reasons are written once in the "Notes"
    column with their years ("FY2022–FY2025: D&A not reported"), so the cells
    stay short. A fiscal year that a company does not have shows "no data"
    (never a filler). The columns are the 5 most recent fiscal years
    (:func:`table_years`). "Latest flag" is the flag of the company's latest
    fiscal year as a word, "n/a" for a ratio with no value and "–" for an
    amount (never flagged); when that year is not the last column, it is
    named: "red (FY2025)".

    Returns:
        ``(table, flags)``: the table to show, with the columns "Ticker",
        "Company", "Metric", "Unit", one "FY<year>" column per shown fiscal
        year (oldest first), "Latest flag" and "Notes"; and a table of the same
        shape that holds the flag of each fiscal-year cell ("green", "orange",
        "red" or ""), used to colour the cells.
    """
    metrics = [selected_metric(m, incl_leases) for m in TABLE_METRICS]
    rows = display[display["metric"].isin(metrics)]
    years, _ = table_years(rows)
    year_columns = [_year_column(y) for y in years]

    table_rows, flag_rows = [], []
    for ticker in dict.fromkeys(rows["ticker"]):
        company = rows[rows["ticker"] == ticker]
        for metric in metrics:
            metric_rows = company[company["metric"] == metric].set_index("fiscal_year")
            if metric_rows.empty:
                continue
            first = metric_rows.iloc[0]
            row = {"Ticker": ticker, "Company": first["company"], "Metric": first["label"], "Unit": first["unit"]}
            flags = {column: "" for column in row}
            notes: dict[str, list[int]] = {}
            for year, column in zip(years, year_columns):
                if year not in metric_rows.index:
                    row[column], flags[column] = NO_YEAR_TEXT, ""
                    continue
                cell = metric_rows.loc[year]
                if cell["status"] == STATUS_OK:
                    row[column] = format_number(cell["value"], cell["unit"], with_unit=False)
                else:
                    row[column] = cell["status"]  # the reason goes to "Notes", not repeated in the cell
                flags[column] = cell["flag"]
                if cell["reason"]:
                    notes.setdefault(cell["reason"], []).append(year)
            row["Latest flag"] = _latest_flag_word(metric, metric_rows, years[-1])
            row["Notes"] = NOTES_SEPARATOR.join(
                f"{years_text(note_years)}: {note}" for note, note_years in notes.items()
            )
            flags["Latest flag"], flags["Notes"] = "", ""
            table_rows.append(row)
            flag_rows.append(flags)

    columns = ["Ticker", "Company", "Metric", "Unit", *year_columns, "Latest flag", "Notes"]
    return pd.DataFrame(table_rows, columns=columns), pd.DataFrame(flag_rows, columns=columns)
