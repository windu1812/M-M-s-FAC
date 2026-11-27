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

# --- Names shared with ratios.py and flags.py ------------------------------------

STATUS_OK = "ok"
STATUS_NOT_AVAILABLE = "not available"
STATUS_NOT_MEANINGFUL = "not meaningful"

USD_M = "USD m"
TIMES = "x"
PERCENT = "%"

INCL_LEASES = "_incl_leases"
DEBT_BASED_METRICS = ["total_debt", "net_debt", "net_debt_to_ebitda", "debt_to_equity"]

MAX_TICKERS = 5

# Decimals shown on screen, per unit (docs/product.md, "Rules").
DECIMALS = {USD_M: 0, TIMES: 2, PERCENT: 1}

DEBT_DEFINITIONS = {False: "Financial debt only", True: "Including leases and short-term borrowings"}

# The 9 numbers of the ratio table, in the order of docs/product.md. The
# debt-based ones get the INCL_LEASES suffix for the second debt definition.
TABLE_METRICS = [
    "ebitda",
    "total_debt",
    "net_debt",
    "net_debt_to_ebitda",
    "debt_to_equity",
    "interest_coverage",
    "current_ratio",
    "ebitda_margin",
    "free_cash_flow",
]

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
INCL_LEASES_LABEL = " (incl. leases)"

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

# Words of the "Latest flag" column and of the cards: the meaning never depends on colour alone.
NO_FLAG_TEXT = "no flag"
NO_YEAR_TEXT = "no data"

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


# --- Numbers and texts ---------------------------------------------------------------


def round_value(value: float, unit: str) -> float:
    """Round a value as it is shown on screen; the same rule as flags.flag_for.

    A value that rounds to zero is written 0, never -0.
    """
    rounded = round(float(value), DECIMALS[unit])
    return 0.0 if rounded == 0 else rounded


def format_number(value: float, unit: str) -> str:
    """The screen text of a number that is already rounded: "1.42x", "20.0 %", "-1,200 USD m"."""
    if unit == TIMES:
        return f"{value:,.2f}x"
    if unit == PERCENT:
        return f"{value:,.1f} %"
    return f"{value:,.0f} {USD_M}"


def missing_text(status: str, reason: str) -> str:
    """The screen text of a value that is not there: "not available: D&A not reported"."""
    return f"{status}: {reason}" if reason else status


def metric_label(metric: str) -> str:
    """The label of a metric: "Net debt / EBITDA" or "Net debt / EBITDA (incl. leases)"."""
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
    only once each (in the order typed).

    Returns:
        ``(tickers, error)``: the list of tickers and an empty error, or an
        empty list and the message to show. Nothing must be downloaded when
        there is an error (AC2).
    """
    tickers: list[str] = []
    for part in re.split(r"[,;\s]+", raw or ""):
        ticker = part.strip().upper()
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
    alert_level: str  # "green", "orange", "red" or "" (no flag)
    alert_text: str
    headlines: list[Headline]


def change_text(current: pd.Series, previous: pd.Series | None, previous_year: int) -> str:
    """The change of a value vs the prior fiscal year, computed on the rounded values shown.

    Examples: "+0.17x vs FY2025", "-1.5 pt vs FY2025", "+200 USD m vs FY2025".
    No change is computed when either year has no number; the text then says why.
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
    return f"{number} vs FY{previous_year}"


def summary_card(display: pd.DataFrame, ticker: str, alert, incl_leases: bool = False) -> Card:
    """The summary card of one company.

    Args:
        display: the table of :func:`display_table`.
        ticker: the company.
        alert: its ``flags.overall_alert(...)`` for the same debt definition.
        incl_leases: the selected debt definition.
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
            change=change_text(row, prior, latest_year - 1),
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
        headlines=headlines,
    )


# --- Table "Credit ratios, last 5 fiscal years" --------------------------------------------


def _year_column(year: int) -> str:
    return f"FY{year}"


def ratio_table(display: pd.DataFrame, incl_leases: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The wide ratio table: one row per company and metric, one column per fiscal year.

    Only the 9 numbers of the selected debt definition are kept. A cell shows
    the number ("1.42x") or its status ("not available"); the reasons are
    written in the "Notes" column with their years, so the cells stay short.
    A fiscal year that a company does not have shows "no data" (never a filler).

    Returns:
        ``(table, flags)``: the table to show, with the columns "Ticker",
        "Company", "Metric", "Unit", one "FY<year>" column per fiscal year
        (oldest first), "Latest flag" and "Notes"; and a table of the same
        shape that holds the flag of each fiscal-year cell ("green", "orange",
        "red" or ""), used to colour the cells.
    """
    metrics = [selected_metric(m, incl_leases) for m in TABLE_METRICS]
    rows = display[display["metric"].isin(metrics)]
    years = sorted(int(y) for y in rows["fiscal_year"].unique())
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
                    row[column] = cell["text"]
                    note = cell["reason"]
                else:
                    row[column] = cell["status"]
                    note = cell["text"]
                flags[column] = cell["flag"]
                if note:
                    notes.setdefault(note, []).append(year)
            latest_flag = metric_rows.loc[metric_rows.index.max(), "flag"]
            row["Latest flag"] = latest_flag or NO_FLAG_TEXT
            row["Notes"] = "; ".join(
                f"{', '.join(_year_column(y) for y in note_years)}: {note}" for note, note_years in notes.items()
            )
            flags["Latest flag"], flags["Notes"] = "", ""
            table_rows.append(row)
            flag_rows.append(flags)

    columns = ["Ticker", "Company", "Metric", "Unit", *year_columns, "Latest flag", "Notes"]
    return pd.DataFrame(table_rows, columns=columns), pd.DataFrame(flag_rows, columns=columns)
