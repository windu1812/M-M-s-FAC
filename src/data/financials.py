"""Turn SEC "companyfacts" JSON into a clean table of annual 10-K values.

Main entry point: :func:`get_financials`.

Classic pitfalls of companyfacts, and how they are handled here:

1. The ``fy`` field of a fact is the fiscal year of the FILING, not of the
   number. A 10-K for 2023 also contains the 2022 and 2021 figures, all with
   ``fy = 2023``. So ``fy`` is never used: the fiscal year of a number comes
   from its ``end`` date.
2. A 10-K can also contain quarterly or multi-year periods. For flow items
   (income statement, cash flow) only periods of about one year are kept:
   350 to 380 days between ``start`` and ``end``.
3. The same period appears in several 10-Ks (as a comparison column). The
   value from the most recent filing is kept, so restatements are taken into
   account.
4. A missing value is never guessed: the row is kept with an empty value and
   the status "not available".

Only the pure functions below read the JSON; the download itself is done by
:mod:`src.data.sec_client`. This makes everything testable without internet.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

from src.data import sec_client
from src.data.xbrl_tags import FLOW, ITEMS

TAXONOMY = "us-gaap"
UNIT = "USD"
ANNUAL_FORMS = {"10-K"}
ANNUAL_MIN_DAYS = 350
ANNUAL_MAX_DAYS = 380
DEFAULT_YEARS = 5

STATUS_OK = "ok"
STATUS_MISSING = "not available"

COLUMNS = [
    "company",
    "ticker",
    "fiscal_year",
    "period_end",
    "item",
    "value",
    "unit",
    "xbrl_tag",
    "form",
    "filed",
    "accession",
    "status",
]


class NoAnnualDataError(ValueError):
    """Raised when a company has no annual 10-K data in companyfacts."""


def is_annual_period(start: str, end: str) -> bool:
    """Return True if the period from ``start`` to ``end`` lasts about one year.

    "About one year" means 350 to 380 days, which accepts 52- and 53-week
    fiscal years (364 or 371 days) and rejects quarters and multi-year totals.
    Dates are ISO strings such as ``"2023-12-31"``.
    """
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    return ANNUAL_MIN_DAYS <= days <= ANNUAL_MAX_DAYS


def fiscal_year_from_end(end: str) -> int:
    """Return the fiscal year of a period, based on its ``end`` date.

    The fiscal year is the calendar year of the end date. One exception: a
    52/53-week year that ends in the first 7 days of January (for example on
    2021-01-02) belongs to the previous year (2020).
    """
    end_date = date.fromisoformat(end)
    if end_date.month == 1 and end_date.day <= 7:
        return end_date.year - 1
    return end_date.year


def _annual_report_facts(facts: dict, tag: str) -> list[dict]:
    """Return the USD facts of one us-gaap ``tag`` that come from a 10-K."""
    units = facts.get("facts", {}).get(TAXONOMY, {}).get(tag, {}).get("units", {})
    return [f for f in units.get(UNIT, []) if f.get("form") in ANNUAL_FORMS]


def _has_expected_period(fact: dict, kind: str) -> bool:
    """Flow items need a one-year period; balance-sheet items are a single date."""
    if kind == FLOW:
        return "start" in fact and is_annual_period(fact["start"], fact["end"])
    return "start" not in fact


def find_fiscal_year_ends(facts: dict) -> list[str]:
    """Return the fiscal year end dates of the company, most recent first.

    Each 10-K covers one fiscal year. Its closing date is the end of the most
    recent one-year period it reports (older periods in the same 10-K are
    comparison columns). Collecting this date for every 10-K gives the list
    of fiscal year ends. Quarterly dates or 10-Q filings never create a year.
    """
    latest_end_by_filing: dict[str, str] = {}
    for tag_data in facts.get("facts", {}).get(TAXONOMY, {}).values():
        for unit_facts in tag_data.get("units", {}).values():
            for fact in unit_facts:
                if fact.get("form") not in ANNUAL_FORMS or "start" not in fact:
                    continue
                if not is_annual_period(fact["start"], fact["end"]):
                    continue
                accession = fact["accn"]
                if fact["end"] > latest_end_by_filing.get(accession, ""):
                    latest_end_by_filing[accession] = fact["end"]
    return sorted(set(latest_end_by_filing.values()), reverse=True)


def _missing_row(item: str, end: str) -> dict:
    """Row for an item that has no value for this fiscal year."""
    return {
        "fiscal_year": fiscal_year_from_end(end),
        "period_end": end,
        "item": item,
        "value": math.nan,
        "unit": None,
        "xbrl_tag": None,
        "form": None,
        "filed": None,
        "accession": None,
        "status": STATUS_MISSING,
    }


def extract_item(facts: dict, item: str, year_ends: list[str]) -> list[dict]:
    """Return one row per fiscal year end for one item (in ``year_ends`` order).

    For each year, the tags of the item are tried in priority order (see
    :mod:`src.data.xbrl_tags`). Among the matching facts of the first tag that
    has a value, the one from the most recent filing wins (the accession
    number breaks ties). If no tag has a value, a "not available" row is
    returned.
    """
    spec = ITEMS[item]
    facts_by_tag = {tag: _annual_report_facts(facts, tag) for tag in spec["tags"]}

    rows = []
    for end in year_ends:
        row = _missing_row(item, end)
        for tag in spec["tags"]:
            candidates = [
                f
                for f in facts_by_tag[tag]
                if f["end"] == end and _has_expected_period(f, spec["kind"])
            ]
            if candidates:
                best = max(candidates, key=lambda f: (f["filed"], f["accn"]))
                row = {
                    "fiscal_year": fiscal_year_from_end(end),
                    "period_end": end,
                    "item": item,
                    "value": float(best["val"]),
                    "unit": UNIT,
                    "xbrl_tag": tag,
                    "form": best["form"],
                    "filed": best["filed"],
                    "accession": best["accn"],
                    "status": STATUS_OK,
                }
                break
        rows.append(row)
    return rows


def build_financials(facts: dict, ticker: str, n_years: int = DEFAULT_YEARS) -> pd.DataFrame:
    """Build the table of the last ``n_years`` fiscal years from companyfacts JSON.

    The result has one row per (fiscal year, item), with the columns listed
    in ``COLUMNS``. Rows are ordered by fiscal year (most recent first), then
    in the item order of :data:`src.data.xbrl_tags.ITEMS`.

    Raises:
        NoAnnualDataError: if no 10-K annual data is found.
    """
    year_ends = find_fiscal_year_ends(facts)[:n_years]
    if not year_ends:
        raise NoAnnualDataError(f"No annual 10-K data found for ticker '{ticker}'.")

    rows_by_item = {item: extract_item(facts, item, year_ends) for item in ITEMS}
    rows = [rows_by_item[item][i] for i in range(len(year_ends)) for item in ITEMS]

    df = pd.DataFrame(rows)
    df.insert(0, "company", facts.get("entityName"))
    df.insert(1, "ticker", ticker.strip().upper())
    df["period_end"] = pd.to_datetime(df["period_end"])
    df["filed"] = pd.to_datetime(df["filed"])
    return df[COLUMNS]


def get_financials(
    ticker: str, n_years: int = DEFAULT_YEARS, refresh: bool = False
) -> pd.DataFrame:
    """Return the annual 10-K financial data of a company as a DataFrame.

    Steps: ticker -> CIK -> companyfacts JSON (downloaded once, then read from
    ``data/cache/``) -> clean table of the last ``n_years`` fiscal years.

    Args:
        ticker: stock ticker, for example ``"AAPL"``.
        n_years: number of fiscal years to return (default 5).
        refresh: True to download the data again instead of using the cache.

    Returns:
        A DataFrame with the columns of ``COLUMNS``. Missing values have
        ``value`` = NaN and ``status`` = "not available".
    """
    cik = sec_client.get_cik(ticker, refresh=refresh)
    facts = sec_client.get_company_facts(cik, refresh=refresh)
    return build_financials(facts, ticker, n_years)
