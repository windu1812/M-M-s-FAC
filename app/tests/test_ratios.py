"""Tests for creditlens/ratios.py (slice 3, issue #6).

The expected values are the hand-worked results of docs/acceptance.md
(CALC1 to CALC13, E1 to E11). They were never taken from the code's output.

The example company is app/tests/fixtures/ratios_sample.csv: SAMPLE DATA,
synthetic, in the format of data.financials.get_financials (values in USD).
Each test changes one input of that company to create its edge case.
"""

import json
import math

import pandas as pd
import pytest

from creditlens import ratios
from creditlens.data import financials as fin

FY = 2026  # the fiscal year of the sample company
TOLERANCE_RATIO = 0.005  # "x" ratios, docs/acceptance.md
TOLERANCE_MARGIN = 0.05  # EBITDA margin, in percentage points
EXACT = 1e-9  # USD m amounts are exact; this only absorbs float noise

# The contract of docs/architecture.md, written out here on purpose (not
# imported from ratios.py), so a change in the code cannot change the test.
CONTRACT_COLUMNS = ["ticker", "fiscal_year", "period_end", "metric", "value", "unit", "status", "reason"]
UNITS = {
    "ebitda": "USD m",
    "total_debt": "USD m",
    "net_debt": "USD m",
    "net_debt_to_ebitda": "x",
    "debt_to_equity": "x",
    "interest_coverage": "x",
    "current_ratio": "x",
    "ebitda_margin": "%",
    "free_cash_flow": "USD m",
    "total_debt_incl_leases": "USD m",
    "net_debt_incl_leases": "USD m",
    "net_debt_to_ebitda_incl_leases": "x",
    "debt_to_equity_incl_leases": "x",
}
DEBT_BASED = ["total_debt", "net_debt", "net_debt_to_ebitda", "debt_to_equity"]
BOTH_VERSIONS = DEBT_BASED + [m + "_incl_leases" for m in DEBT_BASED]


# --- Helpers -------------------------------------------------------------------


@pytest.fixture
def sample(fixtures_dir) -> pd.DataFrame:
    """The example company of docs/acceptance.md, as get_financials returns it."""
    return pd.read_csv(
        fixtures_dir / "ratios_sample.csv",
        comment="#",
        parse_dates=["period_end", "filed"],
        dtype={"value": "float64"},  # like get_financials: floats, NaN when missing
    )


def set_usd_m(financials, item, usd_m):
    """Return a copy where ``item`` has the value ``usd_m`` (given in USD m)."""
    df = financials.copy()
    df.loc[df["item"] == item, "value"] = usd_m * 1_000_000
    return df


def not_reported(financials, item):
    """Return a copy where ``item`` is missing, as the data layer marks it."""
    df = financials.copy()
    mask = df["item"] == item
    df.loc[mask, ["value", "unit", "xbrl_tag", "status"]] = [math.nan, None, None, fin.STATUS_MISSING]
    return df


def row(result, metric, fiscal_year=FY, ticker="SMPL"):
    """Return the single row of ``metric`` for one company and fiscal year."""
    rows = result[
        (result["metric"] == metric)
        & (result["fiscal_year"] == fiscal_year)
        & (result["ticker"] == ticker)
    ]
    assert len(rows) == 1, f"expected one row for {ticker} {metric} {fiscal_year}, got {len(rows)}"
    return rows.iloc[0]


def assert_ok(result, metric, expected, tolerance, ticker="SMPL"):
    r = row(result, metric, ticker=ticker)
    assert r["status"] == "ok", f"{metric}: {r['status']} ({r['reason']})"
    assert r["value"] == pytest.approx(expected, abs=tolerance)


def assert_without_value(result, metric, status, reason):
    r = row(result, metric)
    assert r["status"] == status
    assert r["reason"] == reason
    assert math.isnan(r["value"]), f"{metric} must have no value, never 0 or a guess"


# --- Contract (docs/architecture.md) and AC5 ------------------------------------------


def test_output_follows_the_contract(sample):
    result = ratios.compute_ratios(sample)

    assert list(result.columns) == CONTRACT_COLUMNS
    assert len(result) == 13  # 9 numbers, 4 of them in two debt versions
    assert dict(zip(result["metric"], result["unit"])) == UNITS
    assert set(result["ticker"]) == {"SMPL"}
    assert set(result["fiscal_year"]) == {FY}
    assert set(result["period_end"]) == {pd.Timestamp("2026-12-31")}


@pytest.mark.parametrize("suffix", ["", "_incl_leases"])
def test_each_debt_version_has_the_9_numbers_with_a_unit(sample, suffix):
    # AC5: 9 rows per company for the selected debt definition.
    result = ratios.compute_ratios(sample)
    nine = ["ebitda", "interest_coverage", "current_ratio", "ebitda_margin", "free_cash_flow"]
    nine += [m + suffix for m in DEBT_BASED]

    rows = result[result["metric"].isin(nine)]
    assert len(rows) == 9
    assert rows["unit"].isin(["USD m", "x", "%"]).all()


def test_the_example_company_has_no_missing_value(sample):
    result = ratios.compute_ratios(sample)
    assert (result["status"] == "ok").all()
    assert (result["reason"] == "").all()


# --- Known answers CALC1 to CALC9 (docs/acceptance.md) --------------------------------


@pytest.mark.parametrize(
    "calc, metric, expected, tolerance",
    [
        ("CALC1", "ebitda", 1_200, EXACT),
        ("CALC2a", "total_debt", 2_300, EXACT),
        ("CALC2b", "total_debt_incl_leases", 3_000, EXACT),
        ("CALC3a", "net_debt", 1_700, EXACT),
        ("CALC3b", "net_debt_incl_leases", 2_400, EXACT),
        ("CALC4a", "net_debt_to_ebitda", 1.42, TOLERANCE_RATIO),
        ("CALC4b", "net_debt_to_ebitda_incl_leases", 2.00, TOLERANCE_RATIO),
        ("CALC5a", "debt_to_equity", 1.53, TOLERANCE_RATIO),
        ("CALC5b", "debt_to_equity_incl_leases", 2.00, TOLERANCE_RATIO),
        ("CALC6", "interest_coverage", 8.00, TOLERANCE_RATIO),
        ("CALC7", "current_ratio", 1.50, TOLERANCE_RATIO),
        ("CALC8", "ebitda_margin", 20.0, TOLERANCE_MARGIN),
        ("CALC9", "free_cash_flow", 1_100, EXACT),
    ],
)
def test_known_answer(sample, calc, metric, expected, tolerance):
    assert_ok(ratios.compute_ratios(sample), metric, expected, tolerance)


def test_calc10_usd_to_usd_millions():
    assert ratios.usd_to_usd_m(416_161_000_000) == 416_161


def test_ebitda_margin_is_in_percent_not_a_fraction(sample):
    # 20 %, written 20.0 (not 0.20), because the unit is "%".
    margin = row(ratios.compute_ratios(sample), "ebitda_margin")["value"]
    assert margin > 1


# --- Net cash: CALC11 and E5 ----------------------------------------------------------


def test_calc11_net_cash_gives_negative_net_debt(sample):
    result = ratios.compute_ratios(set_usd_m(sample, "cash", 3_600))

    assert_ok(result, "net_debt_incl_leases", -600, EXACT)
    assert_ok(result, "net_debt_to_ebitda_incl_leases", -0.50, TOLERANCE_RATIO)
    # Financial debt only: 2,300 - 3,600 = -1,300, also net cash.
    assert_ok(result, "net_debt", -1_300, EXACT)
    assert row(result, "net_debt_to_ebitda")["value"] < 0


# --- Parts of total debt not reported: CALC13, E6, E6b --------------------------------


def test_calc13_parts_not_reported_count_as_zero_with_a_note(sample):
    df = not_reported(sample, "short_term_borrowings")
    df = not_reported(df, "finance_lease_liabilities")
    result = ratios.compute_ratios(df)

    total = row(result, "total_debt_incl_leases")
    assert total["status"] == "ok"
    assert total["value"] == pytest.approx(2_700, abs=EXACT)
    assert "short-term borrowings not reported" in total["reason"]
    assert "finance lease liabilities not reported" in total["reason"]
    # The note follows the numbers built on this total.
    for metric in ["net_debt_incl_leases", "net_debt_to_ebitda_incl_leases", "debt_to_equity_incl_leases"]:
        assert row(result, metric)["status"] == "ok"
        assert "short-term borrowings not reported" in row(result, metric)["reason"]
    # These two parts are not in the "financial debt only" version.
    assert_ok(result, "total_debt", 2_300, EXACT)
    assert row(result, "total_debt")["reason"] == ""


def test_e6_current_portion_not_reported_counts_as_zero(sample):
    # 2,000 + 0 = 2,000 (financial debt only); 2,000 + 0 + 200 + 400 + 100 = 2,700 (including leases).
    result = ratios.compute_ratios(not_reported(sample, "long_term_debt_current"))

    assert_ok(result, "total_debt", 2_000, EXACT)
    assert_ok(result, "total_debt_incl_leases", 2_700, EXACT)
    assert row(result, "total_debt")["reason"] == "current portion of long-term debt not reported"


def test_e6b_long_term_debt_not_reported_makes_both_debt_versions_unavailable(sample):
    result = ratios.compute_ratios(not_reported(sample, "long_term_debt"))

    for metric in BOTH_VERSIONS:
        assert_without_value(result, metric, "not available", "long-term debt not reported")
    for metric in ["ebitda", "interest_coverage", "current_ratio", "ebitda_margin", "free_cash_flow"]:
        assert row(result, metric)["status"] == "ok"


# --- Missing inputs and zero denominators: E1, E2 -------------------------------------


def test_e1_missing_d_and_a(sample):
    result = ratios.compute_ratios(not_reported(sample, "depreciation_amortization"))

    for metric in ["ebitda", "net_debt_to_ebitda", "net_debt_to_ebitda_incl_leases", "ebitda_margin"]:
        assert_without_value(result, metric, "not available", "D&A not reported")
    others = result[~result["metric"].str.contains("ebitda")]
    assert (others["status"] == "ok").all()


@pytest.mark.parametrize(
    "item, metric, reason",
    [
        ("operating_income", "interest_coverage", "operating income not reported"),
        ("interest_expense", "interest_coverage", "interest expense not reported"),
        ("current_assets", "current_ratio", "current assets not reported"),
        ("current_liabilities", "current_ratio", "current liabilities not reported"),
        ("revenue", "ebitda_margin", "revenue not reported"),
        ("operating_cash_flow", "free_cash_flow", "operating cash flow not reported"),
        ("capex", "free_cash_flow", "capex not reported"),
        ("cash", "net_debt", "cash not reported"),
        ("cash", "net_debt_incl_leases", "cash not reported"),
        ("stockholders_equity", "debt_to_equity", "equity not reported"),
        ("stockholders_equity", "debt_to_equity_incl_leases", "equity not reported"),
    ],
)
def test_missing_input_gives_not_available_with_the_reason(sample, item, metric, reason):
    result = ratios.compute_ratios(not_reported(sample, item))
    assert_without_value(result, metric, "not available", reason)


def test_reasons_of_several_missing_inputs_are_all_given(sample):
    df = not_reported(sample, "operating_income")
    df = not_reported(df, "depreciation_amortization")
    result = ratios.compute_ratios(df)

    assert_without_value(
        result, "ebitda", "not available", "operating income not reported; D&A not reported"
    )


@pytest.mark.parametrize(
    "item, metrics, reason",
    [
        ("interest_expense", ["interest_coverage"], "interest expense is zero"),
        ("current_liabilities", ["current_ratio"], "current liabilities are zero"),
        ("revenue", ["ebitda_margin"], "revenue is zero"),
        ("stockholders_equity", ["debt_to_equity", "debt_to_equity_incl_leases"], "equity is zero"),
    ],
)
def test_e2_zero_denominator_gives_not_available(sample, item, metrics, reason):
    result = ratios.compute_ratios(set_usd_m(sample, item, 0))
    for metric in metrics:
        assert_without_value(result, metric, "not available", reason)


# --- Negative denominators: E3, E4 -----------------------------------------------------


@pytest.mark.parametrize(
    "operating_income, ebitda",
    [
        (-200, 0),  # -200 + 200 = 0: EBITDA exactly zero
        (-500, -300),  # -500 + 200 = -300: negative EBITDA
    ],
)
def test_e3_ebitda_zero_or_negative_gives_not_meaningful(sample, operating_income, ebitda):
    result = ratios.compute_ratios(set_usd_m(sample, "operating_income", operating_income))

    assert_ok(result, "ebitda", ebitda, EXACT)  # EBITDA itself is still shown
    for metric in ["net_debt_to_ebitda", "net_debt_to_ebitda_incl_leases"]:
        assert_without_value(result, metric, "not meaningful", "EBITDA ≤ 0")


def test_e4_negative_equity_gives_not_meaningful(sample):
    result = ratios.compute_ratios(set_usd_m(sample, "stockholders_equity", -500))
    for metric in ["debt_to_equity", "debt_to_equity_incl_leases"]:
        assert_without_value(result, metric, "not meaningful", "negative equity")


def test_a_loss_still_gives_a_ratio(sample):
    # A negative numerator is a real result: -500 / 125 = -4.00x; FCF 1,500 - 1,700 = -200.
    df = set_usd_m(sample, "operating_income", -500)
    df = set_usd_m(df, "capex", 1_700)
    result = ratios.compute_ratios(df)

    assert_ok(result, "interest_coverage", -4.00, TOLERANCE_RATIO)
    assert_ok(result, "free_cash_flow", -200, EXACT)


# --- Several years and companies: E11 ----------------------------------------------------


def test_e11_only_the_real_years_are_returned(sample):
    years = []
    for fiscal_year in [2026, 2025, 2024]:
        year = sample.copy()
        year["fiscal_year"] = fiscal_year
        year["period_end"] = pd.Timestamp(f"{fiscal_year}-12-31")
        years.append(year)
    result = ratios.compute_ratios(pd.concat(years, ignore_index=True))

    assert list(result["fiscal_year"].unique()) == [2026, 2025, 2024]  # no filler year, same order
    assert len(result) == 3 * 13
    assert row(result, "ebitda", fiscal_year=2024)["period_end"] == pd.Timestamp("2024-12-31")


def test_each_company_keeps_its_own_numbers(sample):
    other = set_usd_m(sample, "cash", 3_600)
    other["ticker"] = "OTHR"
    result = ratios.compute_ratios(pd.concat([sample, other], ignore_index=True))

    assert_ok(result, "net_debt", 1_700, EXACT)  # 2,300 - 600
    assert_ok(result, "net_debt", -1_300, EXACT, ticker="OTHR")  # 2,300 - 3,600


def test_empty_input_gives_an_empty_table_with_the_contract_columns():
    empty = pd.DataFrame(columns=fin.COLUMNS)
    result = ratios.compute_ratios(empty)
    assert result.empty
    assert list(result.columns) == CONTRACT_COLUMNS


# --- Real output of the data layer -------------------------------------------------------


def test_works_on_the_real_output_of_the_data_layer(fixtures_dir):
    # The MSFT extract only holds revenue, net income and total assets
    # (enough for the 10-K reconciliation). Every other input is "not
    # available", so every ratio must say so, with a reason, and never show 0.
    with (fixtures_dir / "companyfacts_MSFT_extract.json").open(encoding="utf-8") as f:
        financials = fin.build_financials(json.load(f), "MSFT", n_years=2)
    result = ratios.compute_ratios(financials)

    assert list(result["fiscal_year"].unique()) == [2026, 2025]
    assert len(result) == 2 * 13
    assert (result["status"] == "not available").all()
    assert result["value"].isna().all()
    assert (result["reason"].str.len() > 0).all()
    assert row(result, "ebitda", ticker="MSFT")["reason"] == (
        "operating income not reported; D&A not reported"
    )


# --- Bad input is refused, never silently used ------------------------------------------


def test_an_amount_not_in_usd_is_refused(sample):
    df = sample.copy()
    df.loc[df["item"] == "revenue", "unit"] = "EUR"
    with pytest.raises(ValueError, match="revenue"):
        ratios.compute_ratios(df)


def test_an_item_given_twice_for_one_year_is_refused(sample):
    df = pd.concat([sample, sample[sample["item"] == "cash"]], ignore_index=True)
    with pytest.raises(ValueError, match="cash"):
        ratios.compute_ratios(df)
