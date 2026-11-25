"""Credit ratios of CreditLens: the 9 numbers of docs/product.md.

Main entry point: :func:`compute_ratios`.

Input: the table of :func:`creditlens.data.financials.get_financials`, one row
per (fiscal year, item), amounts in USD.

Output: one row per (company, fiscal year, metric), with the columns of
``COLUMNS`` (the contract of docs/architecture.md):

* amounts are in USD millions (``unit`` = "USD m"), not rounded;
* ratios are in times (``unit`` = "x");
* the EBITDA margin is in percent (``unit`` = "%"): 20.0 means 20 %.

Rounding for display is done later, in ``display.py``.

The four debt-based metrics exist in two versions (decision of 2026-11-20):

* ``total_debt``, ``net_debt``, ``net_debt_to_ebitda``, ``debt_to_equity``:
  financial debt only (long-term debt + its current portion), the default;
* the same names ending in ``_incl_leases``: financial debt + short-term
  borrowings + operating lease liabilities + finance lease liabilities.

Rules (docs/product.md, "Data and calculations"):

* A missing input or a zero denominator gives "not available", with the
  reason, for example "D&A not reported" or "interest expense is zero".
* EBITDA <= 0 (for Net debt / EBITDA) and negative equity (for Debt / equity)
  give "not meaningful".
* A value that is not "ok" is always empty (NaN), never 0 or a guess.
* No value is derived from other lines to fill a gap.
* Long-term debt (noncurrent) is required for total debt. The other parts of
  total debt count as zero when they are not reported; the row stays "ok" and
  its ``reason`` holds the note "<part> not reported". The note is carried to
  the numbers built on that total (net debt, Net debt / EBITDA, Debt / equity).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

STATUS_OK = "ok"
STATUS_NOT_AVAILABLE = "not available"
STATUS_NOT_MEANINGFUL = "not meaningful"

USD_M = "USD m"
TIMES = "x"
PERCENT = "%"

INCL_LEASES = "_incl_leases"

COLUMNS = ["ticker", "fiscal_year", "period_end", "metric", "value", "unit", "status", "reason"]

# Every metric and its unit, in display order: the 9 numbers with financial
# debt only first, then the 4 debt-based numbers including leases.
METRICS = {
    "ebitda": USD_M,
    "total_debt": USD_M,
    "net_debt": USD_M,
    "net_debt_to_ebitda": TIMES,
    "debt_to_equity": TIMES,
    "interest_coverage": TIMES,
    "current_ratio": TIMES,
    "ebitda_margin": PERCENT,
    "free_cash_flow": USD_M,
    "total_debt_incl_leases": USD_M,
    "net_debt_incl_leases": USD_M,
    "net_debt_to_ebitda_incl_leases": TIMES,
    "debt_to_equity_incl_leases": TIMES,
}

# The metrics that exist in two versions (add INCL_LEASES for the second one).
DEBT_BASED_METRICS = ["total_debt", "net_debt", "net_debt_to_ebitda", "debt_to_equity"]

# How each input is named in a reason ("D&A not reported").
ITEM_LABELS = {
    "revenue": "revenue",
    "operating_income": "operating income",
    "depreciation_amortization": "D&A",
    "interest_expense": "interest expense",
    "stockholders_equity": "equity",
    "current_assets": "current assets",
    "current_liabilities": "current liabilities",
    "cash": "cash",
    "long_term_debt": "long-term debt",
    "long_term_debt_current": "current portion of long-term debt",
    "short_term_borrowings": "short-term borrowings",
    "operating_lease_liabilities": "operating lease liabilities",
    "finance_lease_liabilities": "finance lease liabilities",
    "operating_cash_flow": "operating cash flow",
    "capex": "capex",
}

# Parts added to long-term debt (noncurrent), for each version of total debt.
FINANCIAL_DEBT_PARTS = ["long_term_debt_current"]
LEASE_AND_SHORT_TERM_PARTS = [
    "short_term_borrowings",
    "operating_lease_liabilities",
    "finance_lease_liabilities",
]

REASON_SEPARATOR = "; "


@dataclass(frozen=True)
class Result:
    """One computed number: its value (NaN when there is none), status and reason."""

    value: float
    status: str = STATUS_OK
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK


def usd_to_usd_m(value: float) -> float:
    """Convert an amount from USD to USD millions (416,161,000,000 -> 416,161)."""
    return value / 1_000_000


def _not_available(*reasons: str) -> Result:
    return Result(math.nan, STATUS_NOT_AVAILABLE, REASON_SEPARATOR.join(r for r in reasons if r))


def _not_meaningful(reason: str) -> Result:
    return Result(math.nan, STATUS_NOT_MEANINGFUL, reason)


def _not_reported(item: str) -> str:
    return f"{ITEM_LABELS[item]} not reported"


def _zero(item: str) -> str:
    verb = "are" if ITEM_LABELS[item].endswith("liabilities") else "is"
    return f"{ITEM_LABELS[item]} {verb} zero"


def _missing_inputs(values: dict, *items: str) -> list[str]:
    """Return the reasons "<item> not reported" for the items without a value."""
    return [_not_reported(item) for item in items if values.get(item) is None]


def _ebitda(v: dict) -> Result:
    """EBITDA = operating income + D&A."""
    missing = _missing_inputs(v, "operating_income", "depreciation_amortization")
    if missing:
        return _not_available(*missing)
    return Result(v["operating_income"] + v["depreciation_amortization"])


def _total_debt(v: dict, parts: list[str]) -> Result:
    """Total debt = long-term debt (noncurrent) + the parts that are reported.

    Long-term debt is required. A part that is not reported counts as zero
    and leaves the note "<part> not reported".
    """
    if v.get("long_term_debt") is None:
        return _not_available(_not_reported("long_term_debt"))
    total = v["long_term_debt"]
    notes = []
    for part in parts:
        if v.get(part) is None:
            notes.append(_not_reported(part))
        else:
            total += v[part]
    return Result(total, reason=REASON_SEPARATOR.join(notes))


def _net_debt(total_debt: Result, v: dict) -> Result:
    """Net debt = total debt - cash. Negative when the company has net cash."""
    missing = [] if total_debt.ok else [total_debt.reason]
    missing += _missing_inputs(v, "cash")
    if missing:
        return _not_available(*missing)
    return Result(total_debt.value - v["cash"], reason=total_debt.reason)


def _net_debt_to_ebitda(net_debt: Result, ebitda: Result) -> Result:
    """Net debt / EBITDA, "not meaningful" when EBITDA <= 0."""
    missing = [r.reason for r in (net_debt, ebitda) if not r.ok]
    if missing:
        return _not_available(*missing)
    if ebitda.value <= 0:
        return _not_meaningful("EBITDA ≤ 0")
    return Result(net_debt.value / ebitda.value, reason=net_debt.reason)


def _debt_to_equity(total_debt: Result, v: dict) -> Result:
    """Debt / equity, "not meaningful" when equity is negative."""
    missing = [] if total_debt.ok else [total_debt.reason]
    missing += _missing_inputs(v, "stockholders_equity")
    if missing:
        return _not_available(*missing)
    equity = v["stockholders_equity"]
    if equity == 0:
        return _not_available(_zero("stockholders_equity"))
    if equity < 0:
        return _not_meaningful("negative equity")
    return Result(total_debt.value / equity, reason=total_debt.reason)


def _ratio(v: dict, numerator: str, denominator: str) -> Result:
    """numerator / denominator, "not available" if the denominator is zero."""
    missing = _missing_inputs(v, numerator, denominator)
    if missing:
        return _not_available(*missing)
    if v[denominator] == 0:
        return _not_available(_zero(denominator))
    return Result(v[numerator] / v[denominator])


def _ebitda_margin(ebitda: Result, v: dict) -> Result:
    """EBITDA margin = EBITDA / revenue, in percent."""
    missing = [] if ebitda.ok else [ebitda.reason]
    missing += _missing_inputs(v, "revenue")
    if missing:
        return _not_available(*missing)
    if v["revenue"] == 0:
        return _not_available(_zero("revenue"))
    return Result(ebitda.value / v["revenue"] * 100)


def _free_cash_flow(v: dict) -> Result:
    """Free cash flow = operating cash flow - capex (capex is reported as a positive payment)."""
    missing = _missing_inputs(v, "operating_cash_flow", "capex")
    if missing:
        return _not_available(*missing)
    return Result(v["operating_cash_flow"] - v["capex"])


def ratios_for_year(values: dict) -> dict[str, Result]:
    """Compute every metric of ``METRICS`` for one company and one fiscal year.

    Args:
        values: item name -> amount in USD m, or None when the item is not
            reported (item names of data.xbrl_tags.ITEMS).

    Returns:
        metric name -> :class:`Result`, in the order of ``METRICS``.
    """
    ebitda = _ebitda(values)
    results = {"ebitda": ebitda}
    for suffix, parts in [
        ("", FINANCIAL_DEBT_PARTS),
        (INCL_LEASES, FINANCIAL_DEBT_PARTS + LEASE_AND_SHORT_TERM_PARTS),
    ]:
        total_debt = _total_debt(values, parts)
        net_debt = _net_debt(total_debt, values)
        results["total_debt" + suffix] = total_debt
        results["net_debt" + suffix] = net_debt
        results["net_debt_to_ebitda" + suffix] = _net_debt_to_ebitda(net_debt, ebitda)
        results["debt_to_equity" + suffix] = _debt_to_equity(total_debt, values)
    results["interest_coverage"] = _ratio(values, "operating_income", "interest_expense")
    results["current_ratio"] = _ratio(values, "current_assets", "current_liabilities")
    results["ebitda_margin"] = _ebitda_margin(ebitda, values)
    results["free_cash_flow"] = _free_cash_flow(values)
    return {metric: results[metric] for metric in METRICS}


def _inputs_in_usd_m(year: pd.DataFrame, ticker: str, fiscal_year: int) -> dict:
    """Read one fiscal year of financials: item -> amount in USD m, or None if missing.

    Raises:
        ValueError: if an item appears twice, or if an "ok" amount is not in USD.
            A wrong number in a credit ratio is worse than no number.
    """
    values = {}
    for _, line in year.iterrows():
        item = line["item"]
        if item in values:
            raise ValueError(f"{ticker} {fiscal_year}: item '{item}' is given twice.")
        missing = line["status"] != STATUS_OK or pd.isna(line["value"])
        if not missing and line["unit"] != "USD":
            raise ValueError(
                f"{ticker} {fiscal_year}: item '{item}' is in '{line['unit']}', expected USD."
            )
        values[item] = None if missing else usd_to_usd_m(float(line["value"]))
    return values


def compute_ratios(financials: pd.DataFrame) -> pd.DataFrame:
    """Compute the credit ratios of every company and fiscal year in ``financials``.

    Args:
        financials: the table of data.financials.get_financials (one company),
            or several of them put together with ``pd.concat``.

    Returns:
        One row per (ticker, fiscal year, metric) with the columns of
        ``COLUMNS``. Companies and years keep their order in ``financials``
        (most recent year first); only the years present are returned. Each
        year has the 13 metrics of ``METRICS``, in that order.

    Raises:
        ValueError: if an item is given twice for one year, or an amount is not in USD.
    """
    rows = []
    for (ticker, fiscal_year), year in financials.groupby(["ticker", "fiscal_year"], sort=False):
        values = _inputs_in_usd_m(year, ticker, fiscal_year)
        period_end = year["period_end"].iloc[0]
        for metric, result in ratios_for_year(values).items():
            rows.append(
                {
                    "ticker": ticker,
                    "fiscal_year": fiscal_year,
                    "period_end": period_end,
                    "metric": metric,
                    "value": result.value,
                    "unit": METRICS[metric],
                    "status": result.status,
                    "reason": result.reason,
                }
            )
    return pd.DataFrame(rows, columns=COLUMNS)
