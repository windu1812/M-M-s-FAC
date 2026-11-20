"""Reconciliation of key figures with the 10-K filings (acceptance criterion AC4).

The expected values below were typed from the 10-K documents themselves (the
HTML filed with the SEC), NOT from the app's output. Each value cites its page.
The app reads small extracts of the real SEC companyfacts JSON, saved in
app/tests/fixtures/companyfacts_<TICKER>_extract.json (no internet).

Amounts are in USD millions, as printed in the 10-K statements.
See docs/acceptance.md (R1 to R3) for the document links.
"""

import json

import pytest

from creditlens.data import financials as fin

TEN_K = {
    # Apple 10-K, fiscal year ended 2026-09-26, accession 0000320193-26-000026
    # Consolidated Statements of Operations: page 32. Consolidated Balance Sheets: page 34.
    "AAPL": {
        2026: {"revenue": 478_834, "net_income": 132_175, "total_assets": 404_548},
        2025: {"revenue": 416_161, "net_income": 112_010, "total_assets": 359_241},
    },
    # Microsoft 10-K, fiscal year ended 2026-06-30, accession 0001193125-26-323660
    # Income Statements: page 50. Balance Sheets: page 52.
    "MSFT": {
        2026: {"revenue": 331_839, "net_income": 133_749, "total_assets": 758_376},
        2025: {"revenue": 281_724, "net_income": 101_832, "total_assets": 619_003},
    },
    # Nike 10-K, fiscal year ended 2026-05-31, accession 0000320187-26-000088
    # Consolidated Statements of Income: page 55. Consolidated Balance Sheets: page 57.
    "NKE": {
        2026: {"revenue": 46_398, "net_income": 3_108, "total_assets": 38_410},
        2025: {"revenue": 46_309, "net_income": 3_219, "total_assets": 36_579},
    },
}

CASES = [
    (ticker, year, item, expected)
    for ticker, years in TEN_K.items()
    for year, items in years.items()
    for item, expected in items.items()
]


def load_extract(fixtures_dir, ticker):
    path = fixtures_dir / f"companyfacts_{ticker}_extract.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("ticker, fiscal_year, item, expected_usd_m", CASES)
def test_key_figure_matches_the_10k(fixtures_dir, ticker, fiscal_year, item, expected_usd_m):
    df = fin.build_financials(load_extract(fixtures_dir, ticker), ticker, n_years=2)
    row = df[(df["item"] == item) & (df["fiscal_year"] == fiscal_year)].iloc[0]

    assert row["status"] == fin.STATUS_OK
    assert row["form"] == "10-K"
    # Exact match: the 10-K prints USD millions, the SEC data is in USD.
    assert row["value"] == expected_usd_m * 1_000_000
