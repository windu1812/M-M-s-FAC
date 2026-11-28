"""SAMPLE DATA: synthetic companies in the SEC companyfacts format, for the dashboard tests.

The companies are fictional. Their figures are chosen by hand (in USD m) so that
the expected values of test_display.py and test_app.py can be worked out on
paper, independently of the app's code (AGENTS.md, rule 5).

* ALFA: the example company of docs/acceptance.md in FY2026 (CALC1 to CALC12),
  with FY2025 and FY2024 for the changes and a missing D&A in FY2024.
* BETA: a company that tags no D&A and no interest expense (like NKE), with a
  May year end and only 2 fiscal years.
* FRGN: a foreign filer that files only 20-F reports (no 10-K).
* SEPT and DECM: two companies whose year ends differ (September and December).
  SEPT already has FY2026 (FY2022 to FY2026); DECM ends at FY2025 (FY2021 to
  FY2025). Together they cover 6 fiscal years, but the ratio table shows 5.
* GAMA: green with financial debt only, orange including leases (its alert
  changes with the debt definition).
* NEGA: EBITDA <= 0 and negative equity in FY2026 ("not meaningful").
* RCVR: the NEGA year in FY2025, then the example company in FY2026.
* GAPY (FY2024 and FY2026, no FY2025) and ONEY (FY2026 only): no prior year.
* DUPY: two year ends in 2025 (January and December), the same fiscal year
  twice: a "Data problem" for this ticker only.

The hand working of every expected value is in docs/acceptance.md
("Known answers of the SAMPLE DATA companies").

:func:`write_cache` saves them as the SEC files of the local cache, so the page
reads them exactly as it would read real downloaded files.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from creditlens.data.xbrl_tags import FLOW, ITEMS

# The example company of docs/acceptance.md ("Calculations (known answers)"), USD m.
EXAMPLE_FY2026 = {
    "revenue": 6000,
    "operating_income": 1000,
    "net_income": 600,
    "depreciation_amortization": 200,
    "interest_expense": 125,
    "total_assets": 9000,
    "total_liabilities": 7500,
    "long_term_debt": 2000,
    "long_term_debt_current": 300,
    "short_term_borrowings": 200,
    "operating_lease_liabilities": 400,
    "finance_lease_liabilities": 100,
    "cash": 600,
    "stockholders_equity": 1500,
    "current_assets": 1800,
    "current_liabilities": 1200,
    "operating_cash_flow": 1500,
    "capex": 400,
}

# FY2025: operating income 900, interest 150, cash 500, current assets 1,500.
ALFA_FY2025 = {**EXAMPLE_FY2026, "operating_income": 900, "interest_expense": 150, "cash": 500,
               "current_assets": 1500}
# FY2024: as FY2025, but D&A not reported.
ALFA_FY2024 = {k: v for k, v in ALFA_FY2025.items() if k != "depreciation_amortization"}

# BETA: no D&A, no interest expense, no short-term borrowings, no finance leases.
BETA_FY2026 = {
    "revenue": 4000,
    "operating_income": 500,
    "net_income": 350,
    "total_assets": 5000,
    "total_liabilities": 2000,
    "long_term_debt": 1000,
    "long_term_debt_current": 0,
    "operating_lease_liabilities": 300,
    "cash": 1500,
    "stockholders_equity": 3000,
    "current_assets": 2400,
    "current_liabilities": 3000,
    "operating_cash_flow": 300,
    "capex": 450,
}
BETA_FY2025 = {**BETA_FY2026, "current_assets": 2700}

# SEPT: the example company in each of its 5 years (current ratio 1,800 / 1,200 = 1.50x, green).
# DECM: the same, but current assets 900 (current ratio 900 / 1,200 = 0.75x, red).
DECM_YEAR = {**EXAMPLE_FY2026, "current_assets": 900}

# GAMA: EBITDA 800 + 200 = 1,000; debt 1,500 (no current portion, no cash); operating leases 1,000.
GAMA_FY2026 = {
    "revenue": 4000,
    "operating_income": 800,
    "net_income": 500,
    "depreciation_amortization": 200,
    "interest_expense": 100,
    "total_assets": 5000,
    "total_liabilities": 3000,
    "long_term_debt": 1500,
    "long_term_debt_current": 0,
    "operating_lease_liabilities": 1000,
    "cash": 0,
    "stockholders_equity": 2000,
    "current_assets": 1500,
    "current_liabilities": 1000,
    "operating_cash_flow": 500,
    "capex": 200,
}

# NEGA: the example company with an operating loss of 300 (EBITDA -300 + 200 = -100) and equity -100.
NEGA_FY2026 = {**EXAMPLE_FY2026, "operating_income": -300, "stockholders_equity": -100}

COMPANIES = {
    "ALFA": {
        "cik": 1111111,
        "name": "Alfa Corp (SAMPLE DATA)",
        "years": {"2026-12-31": EXAMPLE_FY2026, "2025-12-31": ALFA_FY2025, "2024-12-31": ALFA_FY2024},
        "form": "10-K",
    },
    "BETA": {
        "cik": 2222222,
        "name": "Beta Inc (SAMPLE DATA)",
        "years": {"2026-05-31": BETA_FY2026, "2025-05-31": BETA_FY2025},
        "form": "10-K",
    },
    "FRGN": {
        "cik": 3333333,
        "name": "Foreign Filer plc (SAMPLE DATA)",
        "years": {"2026-12-31": {"revenue": 100, "total_assets": 200}},
        "form": "20-F",
    },
    "SEPT": {
        "cik": 5555555,
        "name": "September Year End Inc (SAMPLE DATA)",
        "years": {f"{year}-09-30": EXAMPLE_FY2026 for year in range(2022, 2027)},
        "form": "10-K",
    },
    "DECM": {
        "cik": 6666666,
        "name": "December Year End Inc (SAMPLE DATA)",
        "years": {f"{year}-12-31": DECM_YEAR for year in range(2021, 2026)},
        "form": "10-K",
    },
    "GAMA": {
        "cik": 7777777,
        "name": "Gama Leases Inc (SAMPLE DATA)",
        "years": {"2026-12-31": GAMA_FY2026},
        "form": "10-K",
    },
    "NEGA": {
        "cik": 8888888,
        "name": "Nega Loss Inc (SAMPLE DATA)",
        "years": {"2026-12-31": NEGA_FY2026, "2025-12-31": EXAMPLE_FY2026},
        "form": "10-K",
    },
    "RCVR": {
        "cik": 9999999,
        "name": "Recovery Inc (SAMPLE DATA)",
        "years": {"2026-12-31": EXAMPLE_FY2026, "2025-12-31": NEGA_FY2026},
        "form": "10-K",
    },
    "GAPY": {
        "cik": 1212121,
        "name": "Gap Year Inc (SAMPLE DATA)",
        "years": {"2026-12-31": EXAMPLE_FY2026, "2024-12-31": EXAMPLE_FY2026},
        "form": "10-K",
    },
    "ONEY": {
        "cik": 1313131,
        "name": "One Year Inc (SAMPLE DATA)",
        "years": {"2026-12-31": EXAMPLE_FY2026},
        "form": "10-K",
    },
    "DUPY": {
        "cik": 1414141,
        "name": "Duplicate Year Inc (SAMPLE DATA)",
        "years": {"2025-12-31": EXAMPLE_FY2026, "2025-01-10": EXAMPLE_FY2026},
        "form": "10-K",
    },
}

# A ticker in the SEC list whose companyfacts file is not in the cache.
NOT_CACHED = {"ticker": "NCCH", "cik": 4444444, "name": "Not Cached Corp (SAMPLE DATA)"}


def companyfacts(ticker: str) -> dict:
    """The synthetic companyfacts JSON of one company (first XBRL tag of each item)."""
    company = COMPANIES[ticker]
    facts: dict[str, dict] = {}
    for n, (end, values) in enumerate(sorted(company["years"].items())):
        end_date = date.fromisoformat(end)
        accession = f"{company['cik']:010d}-{end_date.year % 100:02d}-{n + 1:06d}"
        filed = (end_date + timedelta(days=40)).isoformat()
        for item, value in values.items():
            spec = ITEMS[item]
            fact = {"end": end, "val": value * 1_000_000, "accn": accession, "fy": end_date.year,
                    "fp": "FY", "form": company["form"], "filed": filed}
            if spec["kind"] == FLOW:
                fact["start"] = (end_date - timedelta(days=364)).isoformat()
            tag = spec["tags"][0]
            facts.setdefault(tag, {"units": {"USD": []}})["units"]["USD"].append(fact)
    return {
        "_comment": "SAMPLE DATA: synthetic company for the CreditLens tests, not a real filing.",
        "cik": company["cik"],
        "entityName": company["name"],
        "facts": {"us-gaap": facts},
    }


def write_cache(cache_dir: Path) -> None:
    """Write the SEC ticker list and the companyfacts of the synthetic companies to ``cache_dir``."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    entries = [{"cik_str": c["cik"], "ticker": t, "title": c["name"]} for t, c in COMPANIES.items()]
    entries.append({"cik_str": NOT_CACHED["cik"], "ticker": NOT_CACHED["ticker"], "title": NOT_CACHED["name"]})
    tickers = {str(i): entry for i, entry in enumerate(entries)}
    (cache_dir / "company_tickers.json").write_text(json.dumps(tickers), encoding="utf-8")
    for ticker, company in COMPANIES.items():
        path = cache_dir / f"CIK{company['cik']:010d}.json"
        path.write_text(json.dumps(companyfacts(ticker)), encoding="utf-8")
