"""Tests for creditlens/data/financials.py.

All tests use the synthetic file app/tests/fixtures/companyfacts_sample.json
(fictional company, fiscal year = calendar year, 10-Ks for 2018 to 2023).
The expected numbers below are the ones written in that file.
"""

import json
import math
import shutil
from datetime import date, timedelta

import pandas as pd
import pytest

from creditlens.data import financials as fin
from creditlens.data import sec_client
from creditlens.data.financials import STATUS_MISSING, STATUS_OK
from creditlens.data.xbrl_tags import ITEMS

FY2022_10K = "0001234567-23-000010"
FY2023_10K = "0001234567-24-000010"
FY2020_10K = "0001234567-21-000010"


@pytest.fixture
def df(sample_facts):
    return fin.build_financials(sample_facts, "test")


def row_for(df, item, fiscal_year):
    """Return the single row of ``item`` for ``fiscal_year``."""
    rows = df[(df["item"] == item) & (df["fiscal_year"] == fiscal_year)]
    assert len(rows) == 1, f"expected one row for {item} {fiscal_year}, got {len(rows)}"
    return rows.iloc[0]


# --- Period rules ------------------------------------------------------------


@pytest.mark.parametrize(
    "days, expected",
    [
        (91, False),    # quarter
        (349, False),
        (350, True),    # lower bound
        (364, True),    # 52-week year
        (371, True),    # 53-week year
        (380, True),    # upper bound
        (381, False),
        (1095, False),  # 3-year total
    ],
)
def test_is_annual_period_keeps_only_about_one_year(days, expected):
    start = date(2023, 1, 1)
    end = start + timedelta(days=days)
    assert fin.is_annual_period(start.isoformat(), end.isoformat()) is expected


@pytest.mark.parametrize(
    "end, expected",
    [
        ("2023-12-31", 2023),
        ("2024-09-28", 2024),  # Apple-style 52/53-week year
        ("2025-05-31", 2025),  # Nike-style year end
        ("2021-01-02", 2020),  # 52/53-week year ending in early January
        ("2021-01-08", 2021),
    ],
)
def test_fiscal_year_comes_from_end_date(end, expected):
    assert fin.fiscal_year_from_end(end) == expected


def test_fiscal_year_ends_come_from_10k_annual_periods_only(sample_facts):
    # 2023-09-30 and 2024-03-31 are 10-Q dates; 2017-12-31 only appears as a
    # comparison column inside the FY2018 10-K. None of them is a year end here.
    assert fin.find_fiscal_year_ends(sample_facts) == [
        "2023-12-31",
        "2022-12-31",
        "2021-12-31",
        "2020-12-31",
        "2019-12-31",
        "2018-12-31",
    ]


# --- Pitfall: "fy" is the filing year, not the year of the number -------------


def test_fy_field_is_ignored_comparatives_get_their_own_year(df):
    # The FY2023 10-K (fy = 2023) also reports 2022 revenue. That number must
    # be filed under fiscal year 2022 (its end date), not 2023.
    row_2022 = row_for(df, "revenue", 2022)
    assert row_2022["period_end"] == pd.Timestamp("2022-12-31")
    assert row_2022["accession"] == FY2023_10K
    assert row_2022["value"] == 1250

    row_2023 = row_for(df, "revenue", 2023)
    assert row_2023["period_end"] == pd.Timestamp("2023-12-31")
    assert row_2023["value"] == 1400


def test_one_row_per_item_and_fiscal_year(df):
    assert df.groupby(["fiscal_year", "item"]).size().max() == 1
    assert (df["fiscal_year"] == df["period_end"].dt.year).all()


# --- Pitfall: same period in several filings ---------------------------------


def test_most_recent_filing_wins_for_restated_values(df):
    # Revenue 2022: 1200 in the FY2022 10-K, restated to 1250 in the FY2023 10-K.
    assert row_for(df, "revenue", 2022)["value"] == 1250
    # Total assets 2022: 5000 in the FY2022 10-K, restated to 5100 in the FY2023 10-K.
    assert row_for(df, "total_assets", 2022)["value"] == 5100
    # Revenue 2021 is in the FY2021 and FY2022 10-Ks: the later one is kept.
    row_2021 = row_for(df, "revenue", 2021)
    assert row_2021["accession"] == FY2022_10K
    assert row_2021["filed"] == pd.Timestamp("2023-02-15")


# --- Pitfall: quarterly / multi-year periods and 10-Q filings -----------------


def test_quarterly_and_multi_year_periods_are_ignored(df):
    # The FY2023 10-K also has a Q4 figure (380) and a 3-year total (3850)
    # ending on 2023-12-31 under the same tag. Only the 1-year value is kept.
    assert row_for(df, "revenue", 2023)["value"] == 1400


def test_10q_values_are_ignored_even_if_more_recent(df):
    # A later 10-Q repeats total assets at 2023-12-31 with 5650.
    row = row_for(df, "total_assets", 2023)
    assert row["value"] == 5600
    assert row["form"] == "10-K"
    assert (df["form"].dropna() == "10-K").all()


# --- Alternative XBRL tags ---------------------------------------------------


def test_highest_priority_tag_wins_when_several_exist(df):
    # 2023 revenue exists under "Revenues" and under the newer contract tag.
    assert row_for(df, "revenue", 2023)["xbrl_tag"] == "Revenues"


def test_tag_is_chosen_year_by_year_when_company_changes_tag(df):
    new_tag = "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert row_for(df, "revenue", 2022)["xbrl_tag"] == new_tag
    assert row_for(df, "revenue", 2021)["xbrl_tag"] == new_tag
    # 2020 exists under both the old and the new tag: the new one has priority.
    assert row_for(df, "revenue", 2020)["xbrl_tag"] == new_tag
    # 2019 only exists under the old tag, so the old tag is used.
    row_2019 = row_for(df, "revenue", 2019)
    assert row_2019["xbrl_tag"] == "SalesRevenueNet"
    assert row_2019["value"] == 1000
    assert row_2019["accession"] == FY2020_10K


# --- Missing data ------------------------------------------------------------


def test_item_missing_for_one_year_is_marked_not_available(df):
    # Interest expense is not reported in the FY2023 10-K.
    row = row_for(df, "interest_expense", 2023)
    assert math.isnan(row["value"])
    assert row["status"] == STATUS_MISSING
    assert pd.isna(row["xbrl_tag"])
    assert pd.isna(row["accession"])
    # The other years are still there.
    assert row_for(df, "interest_expense", 2022)["value"] == 40
    assert row_for(df, "interest_expense", 2019)["value"] == 30


def test_item_never_reported_is_not_available_every_year(df):
    rows = df[df["item"] == "operating_income"]
    assert len(rows) == 5
    assert rows["value"].isna().all()
    assert (rows["status"] == STATUS_MISSING).all()


def test_every_row_is_a_real_value_or_marked_missing(df):
    ok = df["status"] == STATUS_OK
    assert set(df["status"]) <= {STATUS_OK, STATUS_MISSING}
    assert df.loc[ok, "value"].notna().all()
    assert df.loc[~ok, "value"].isna().all()


# --- Output format -----------------------------------------------------------


def test_output_columns_and_shape(df):
    assert list(df.columns) == [
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
    assert len(df) == 5 * len(ITEMS)
    assert sorted(df["fiscal_year"].unique()) == [2019, 2020, 2021, 2022, 2023]
    assert set(df["item"]) == set(ITEMS)
    assert (df["company"] == "SAMPLE TEST CORP").all()
    assert (df["ticker"] == "TEST").all()
    assert (df.loc[df["status"] == STATUS_OK, "unit"] == "USD").all()


def test_rows_are_sorted_by_year_then_item(df):
    assert df["fiscal_year"].iloc[0] == 2023
    assert df["fiscal_year"].iloc[-1] == 2019
    assert list(df["item"].iloc[: len(ITEMS)]) == list(ITEMS)


def test_n_years_limits_the_history(sample_facts):
    two = fin.build_financials(sample_facts, "TEST", n_years=2)
    assert sorted(two["fiscal_year"].unique()) == [2022, 2023]
    # Only 6 fiscal years exist in the sample: asking for 10 returns 6.
    ten = fin.build_financials(sample_facts, "TEST", n_years=10)
    assert ten["fiscal_year"].nunique() == 6


def test_no_annual_data_raises_clear_error():
    with pytest.raises(fin.NoAnnualDataError, match="NONE"):
        fin.build_financials({"entityName": "EMPTY", "facts": {}}, "NONE")


# --- Main function, end to end from the cache ---------------------------------


def test_get_financials_end_to_end_from_cache(fixtures_dir):
    cache = sec_client.CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    tickers = {"0": {"cik_str": 1234567, "ticker": "TEST", "title": "SAMPLE TEST CORP"}}
    (cache / "company_tickers.json").write_text(json.dumps(tickers))
    shutil.copy(fixtures_dir / "companyfacts_sample.json", cache / "CIK0001234567.json")

    # requests.get is blocked by conftest: everything must come from the cache.
    df = fin.get_financials("test")

    assert len(df) == 5 * len(ITEMS)
    assert row_for(df, "revenue", 2023)["value"] == 1400
    assert row_for(df, "total_assets", 2023)["value"] == 5600


# --- Items added in slice 2 (net income, debt parts, leases) -----------------


def test_contract_lists_every_item_the_ratios_need(df):
    # Contract with the ratios slice (issue #6): these item names must exist.
    needed = {
        "revenue", "operating_income", "net_income", "depreciation_amortization",
        "interest_expense", "total_assets", "total_liabilities", "stockholders_equity",
        "current_assets", "current_liabilities", "cash", "long_term_debt",
        "long_term_debt_current", "short_term_borrowings", "operating_lease_liabilities",
        "finance_lease_liabilities", "operating_cash_flow", "capex",
    }
    assert set(df["item"]) == needed


def test_net_income_is_the_parent_figure_not_profit_loss(df):
    # ProfitLoss (155) includes noncontrolling interests: it must not be used.
    row = row_for(df, "net_income", 2023)
    assert row["value"] == 150
    assert row["xbrl_tag"] == "NetIncomeLoss"
    assert row_for(df, "net_income", 2021)["value"] == 100


def test_current_portion_of_long_term_debt(df):
    assert row_for(df, "long_term_debt_current", 2023)["value"] == 300
    assert row_for(df, "long_term_debt_current", 2022)["value"] == 250
    assert row_for(df, "long_term_debt_current", 2021)["status"] == STATUS_MISSING


def test_short_term_borrowings_total_wins_over_commercial_paper(df):
    # 2023: total short-term borrowings (200) already include commercial paper (150):
    # taking the total avoids counting commercial paper twice.
    row_2023 = row_for(df, "short_term_borrowings", 2023)
    assert row_2023["value"] == 200
    assert row_2023["xbrl_tag"] == "ShortTermBorrowings"
    # 2022: only commercial paper is reported, so it is used.
    row_2022 = row_for(df, "short_term_borrowings", 2022)
    assert row_2022["value"] == 80
    assert row_2022["xbrl_tag"] == "CommercialPaper"
    assert row_for(df, "short_term_borrowings", 2021)["status"] == STATUS_MISSING


def test_operating_and_finance_lease_liabilities(df):
    assert row_for(df, "operating_lease_liabilities", 2023)["value"] == 400
    assert row_for(df, "operating_lease_liabilities", 2022)["value"] == 380
    assert row_for(df, "finance_lease_liabilities", 2023)["value"] == 100
    # Not reported for 2022: marked missing, never set to zero here.
    row = row_for(df, "finance_lease_liabilities", 2022)
    assert row["status"] == STATUS_MISSING
    assert math.isnan(row["value"])


def test_long_term_debt_never_comes_from_a_tag_that_includes_leases(df):
    # 2020 is only reported under LongTermDebtAndCapitalLeaseObligations (debt + finance
    # leases). Using it would count finance leases twice in the "including leases" total.
    assert row_for(df, "long_term_debt", 2020)["status"] == STATUS_MISSING
    row_2023 = row_for(df, "long_term_debt", 2023)
    assert row_2023["value"] == 2000
    assert row_2023["xbrl_tag"] == "LongTermDebtNoncurrent"
