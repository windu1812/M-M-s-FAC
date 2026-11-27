"""Tests of creditlens/display.py: display-ready values of the dashboard (slice 5).

Expected values are worked out by hand in the comments (AGENTS.md, rule 5),
from the example company of docs/acceptance.md and the SAMPLE DATA companies of
tests/synthetic_company.py. They are never copied from the app's output.
"""

import math

import pandas as pd
import pytest

from creditlens import display, flags
from creditlens.data.financials import build_financials
from creditlens.ratios import compute_ratios

import synthetic_company as sc


# --- Helpers ---------------------------------------------------------------------------


def pipeline(*tickers):
    """financials -> ratios -> flags -> display, as the page does it."""
    financials = pd.concat([build_financials(sc.companyfacts(t), t) for t in tickers], ignore_index=True)
    flagged = flags.apply_flags(compute_ratios(financials))
    return financials, flagged, display.display_table(flagged, financials)


@pytest.fixture(scope="module")
def alfa_beta():
    return pipeline("ALFA", "BETA")


def cell(table, ticker, year, metric):
    rows = table[(table["ticker"] == ticker) & (table["fiscal_year"] == year) & (table["metric"] == metric)]
    assert len(rows) == 1, (ticker, year, metric)
    return rows.iloc[0]


# --- Rounding and texts --------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, unit, expected",
    [
        (1.41666, "x", "1.42x"),  # CALC4a: 1,700 / 1,200
        (2.0, "x", "2.00x"),  # CALC4b
        (-0.5, "x", "-0.50x"),  # CALC11: net cash
        (20.0, "%", "20.0 %"),  # CALC8
        (18.3333, "%", "18.3 %"),  # 1,100 / 6,000
        (1100.0, "USD m", "1,100 USD m"),  # CALC9
        (416161.0, "USD m", "416,161 USD m"),  # CALC10
        (-1234.6, "USD m", "-1,235 USD m"),
        (0.0, "USD m", "0 USD m"),  # a real zero is shown
        (-0.0004, "x", "0.00x"),  # never "-0.00x"
    ],
)
def test_screen_text_of_a_number(value, unit, expected):
    assert display.format_number(display.round_value(value, unit), unit) == expected


def test_rounding_is_the_same_as_the_flags():
    # flags.flag_for compares round(value, 2) for "x": the display must show that same number.
    for value in [1.995, 2.004999, 2.005, 3.4949, 0.125]:
        assert display.round_value(value, "x") == round(value, flags.DISPLAY_DECIMALS["x"])


def test_missing_text_says_why():
    assert display.missing_text("not available", "D&A not reported") == "not available: D&A not reported"
    assert display.missing_text("not meaningful", "EBITDA ≤ 0") == "not meaningful: EBITDA ≤ 0"
    assert display.missing_text("not available", "") == "not available"


def test_labels_of_both_debt_definitions():
    assert display.metric_label("net_debt_to_ebitda") == "Net debt / EBITDA"
    assert display.metric_label("net_debt_to_ebitda_incl_leases") == "Net debt / EBITDA (incl. leases)"
    assert display.selected_metric("debt_to_equity", True) == "debt_to_equity_incl_leases"
    assert display.selected_metric("interest_coverage", True) == "interest_coverage"  # not debt-based


# --- Ticker field (AC2) ------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("AAPL, MSFT, NKE", ["AAPL", "MSFT", "NKE"]),
        (" aapl,msft  nke ", ["AAPL", "MSFT", "NKE"]),
        ("AAPL, AAPL, msft", ["AAPL", "MSFT"]),  # each ticker once
        ("BRK-B", ["BRK-B"]),
    ],
)
def test_tickers_are_read_in_capitals_once_each(raw, expected):
    assert display.parse_tickers(raw) == (expected, "")


def test_six_tickers_are_refused():
    tickers, error = display.parse_tickers("A, B, C, D, E, F")
    assert tickers == []
    assert error.startswith("Enter 1 to 5 tickers")


def test_empty_field_asks_for_tickers():
    tickers, error = display.parse_tickers("  , ")
    assert tickers == [] and "Enter 1 to 5 tickers" in error


def test_invalid_ticker_is_refused():
    tickers, error = display.parse_tickers("AAPL, 1X$")
    assert tickers == [] and "1X$" in error


# --- The display table (contract shared with charts.py and export.py) ------------------------------


def test_display_table_has_the_agreed_columns_and_all_13_metrics(alfa_beta):
    _, flagged, table = alfa_beta
    assert list(table.columns) == display.DISPLAY_COLUMNS
    assert len(table) == len(flagged)
    # ALFA 3 years + BETA 2 years, 13 metrics each (both debt definitions).
    assert len(table) == (3 + 2) * 13
    assert table["period_end"].map(type).eq(str).all()


def test_display_values_are_the_hand_worked_answers(alfa_beta):
    _, _, table = alfa_beta
    expected = {
        # ALFA FY2026 = the example company of acceptance.md
        ("ALFA", 2026, "net_debt_to_ebitda"): (1.42, "1.42x", "green"),  # CALC4a
        ("ALFA", 2026, "net_debt_to_ebitda_incl_leases"): (2.00, "2.00x", "green"),  # CALC4b
        ("ALFA", 2026, "debt_to_equity"): (1.53, "1.53x", "orange"),  # CALC5a, CALC12
        ("ALFA", 2026, "debt_to_equity_incl_leases"): (2.00, "2.00x", "orange"),  # CALC5b, CALC12
        ("ALFA", 2026, "interest_coverage"): (8.00, "8.00x", "green"),  # CALC6
        ("ALFA", 2026, "current_ratio"): (1.50, "1.50x", "green"),  # CALC7
        ("ALFA", 2026, "ebitda_margin"): (20.0, "20.0 %", "green"),  # CALC8
        ("ALFA", 2026, "free_cash_flow"): (1100, "1,100 USD m", "green"),  # CALC9
        ("ALFA", 2026, "ebitda"): (1200, "1,200 USD m", ""),  # CALC1, amounts get no flag
        ("ALFA", 2026, "total_debt_incl_leases"): (3000, "3,000 USD m", ""),  # CALC2b
        # ALFA FY2025: EBITDA 900 + 200 = 1,100; net debt 2,300 - 500 = 1,800; 1,800 / 1,100 = 1.636
        ("ALFA", 2025, "net_debt_to_ebitda"): (1.64, "1.64x", "green"),
        # 1,100 / 6,000 = 18.33 %
        ("ALFA", 2025, "ebitda_margin"): (18.3, "18.3 %", "orange"),
        # BETA FY2026: net debt 1,000 - 1,500 = -500 (net cash); current ratio 2,400 / 3,000 = 0.80
        ("BETA", 2026, "net_debt"): (-500, "-500 USD m", ""),
        ("BETA", 2026, "current_ratio"): (0.80, "0.80x", "red"),
        # FCF 300 - 450 = -150
        ("BETA", 2026, "free_cash_flow"): (-150, "-150 USD m", "red"),
        # incl. leases: 1,000 + 0 + 300 = 1,300; 1,300 / 3,000 = 0.433
        ("BETA", 2026, "debt_to_equity_incl_leases"): (0.43, "0.43x", "green"),
    }
    for (ticker, year, metric), (value, text, flag) in expected.items():
        row = cell(table, ticker, year, metric)
        assert row["value"] == pytest.approx(value), (ticker, year, metric)
        assert (row["text"], row["flag"]) == (text, flag), (ticker, year, metric)


def test_missing_value_is_empty_with_its_reason_never_zero(alfa_beta):
    _, _, table = alfa_beta
    row = cell(table, "BETA", 2026, "interest_coverage")
    assert math.isnan(row["value"])
    assert row["text"] == "not available: interest expense not reported"
    assert row["flag"] == ""
    row = cell(table, "ALFA", 2024, "ebitda")  # D&A not reported in FY2024
    assert math.isnan(row["value"]) and row["text"] == "not available: D&A not reported"


def test_note_of_an_ok_value_is_kept(alfa_beta):
    _, _, table = alfa_beta
    row = cell(table, "BETA", 2026, "total_debt_incl_leases")
    assert row["status"] == "ok" and row["text"] == "1,300 USD m"
    assert "short-term borrowings not reported" in row["reason"]
    assert "finance lease liabilities not reported" in row["reason"]


def test_company_name_and_year_end_come_from_the_data(alfa_beta):
    _, _, table = alfa_beta
    row = cell(table, "BETA", 2026, "ebitda")
    assert row["company"] == "Beta Inc (SAMPLE DATA)"
    assert row["period_end"] == "2026-05-31"


def test_ok_row_without_value_is_refused(alfa_beta):
    financials, flagged, _ = alfa_beta
    broken = flagged.copy()
    broken.loc[broken.index[0], ["value", "status"]] = [math.nan, "ok"]
    with pytest.raises(ValueError, match="has no value"):
        display.display_table(broken, financials)


# --- "View underlying data" ---------------------------------------------------------------


def test_underlying_data_in_usd_m_with_tag_and_accession(alfa_beta):
    financials, _, _ = alfa_beta
    table = display.underlying_table(financials)
    assert list(table.columns) == display.UNDERLYING_COLUMNS
    revenue = table[(table["ticker"] == "ALFA") & (table["fiscal_year"] == 2026) & (table["item"] == "revenue")]
    r = revenue.iloc[0]
    # 6,000,000,000 USD / 1,000,000 = 6,000 USD m
    assert (r["value"], r["text"], r["label"], r["xbrl_tag"]) == (6000, "6,000 USD m", "Revenue", "Revenues")
    assert r["accession"] == "0001111111-26-000003"
    # BETA reports no D&A: shown as "not reported", never 0
    da = table[(table["ticker"] == "BETA") & (table["fiscal_year"] == 2026)
               & (table["item"] == "depreciation_amortization")].iloc[0]
    assert math.isnan(da["value"]) and da["text"] == "not reported" and pd.isna(da["xbrl_tag"])
    # companies in the order typed, most recent year first, every item of each year
    assert list(dict.fromkeys(table["ticker"])) == ["ALFA", "BETA"]
    assert list(table[table["ticker"] == "ALFA"]["fiscal_year"].unique()) == [2026, 2025, 2024]
    assert len(table) == (3 + 2) * len(display.ITEM_LABELS)


# --- Summary cards (AC1, AC7) ---------------------------------------------------------------


def test_card_of_the_example_company(alfa_beta):
    _, flagged, table = alfa_beta
    card = display.summary_card(table, "ALFA", flags.overall_alert(flagged, "ALFA"))
    assert (card.company, card.fiscal_year, card.period_end) == ("Alfa Corp (SAMPLE DATA)", 2026, "2026-12-31")
    # CALC12, financial debt only: D/E 1.53 orange, the other 5 green
    assert (card.alert_level, card.alert_text) == ("orange", "Orange: 1 orange flag")
    ndebitda, coverage, current = card.headlines
    assert (ndebitda.label, ndebitda.text, ndebitda.shown, ndebitda.flag) == (
        "Net debt / EBITDA", "1.42x", "1.42x", "green")
    assert ndebitda.note == ""
    assert ndebitda.change == "-0.22x vs FY2025"  # 1.42 - 1.64
    assert (coverage.text, coverage.change) == ("8.00x", "+2.00x vs FY2025")  # 1,000/125 - 900/150 = 8 - 6
    assert (current.text, current.change) == ("1.50x", "+0.25x vs FY2025")  # 1,800/1,200 - 1,500/1,200


def test_card_switches_with_the_debt_definition(alfa_beta):
    _, flagged, table = alfa_beta
    card = display.summary_card(table, "ALFA", flags.overall_alert(flagged, "ALFA", incl_leases=True), True)
    ndebitda, coverage, _ = card.headlines
    # 2,400 / 1,200 = 2.00; FY2025: (3,000 - 500) / 1,100 = 2.27; 2.00 - 2.27 = -0.27
    assert (ndebitda.label, ndebitda.text, ndebitda.change) == (
        "Net debt / EBITDA (incl. leases)", "2.00x", "-0.27x vs FY2025")
    assert coverage.text == "8.00x"  # not debt-based: unchanged (AC5b)
    assert card.alert_text == "Orange: 1 orange flag"  # CALC12, including leases


def test_card_with_missing_ratios_counts_them(alfa_beta):
    _, flagged, table = alfa_beta
    card = display.summary_card(table, "BETA", flags.overall_alert(flagged, "BETA"))
    # red: current ratio 0.80 and FCF -150; not available: ND/EBITDA, coverage, margin
    assert (card.alert_level, card.alert_text) == ("red", "Red: 2 red flags, 3 not available")
    ndebitda, coverage, current = card.headlines
    assert ndebitda.text == "not available: D&A not reported" and ndebitda.flag == ""
    assert (ndebitda.shown, ndebitda.note, ndebitda.change) == ("not available", "D&A not reported", "")
    assert coverage.text == "not available: interest expense not reported"
    assert current.change == "-0.10x vs FY2025"  # 0.80 - 2,700/3,000 = 0.80 - 0.90


def test_no_change_when_the_prior_year_has_no_value():
    current = pd.Series({"value": 1.42, "unit": "x", "status": "ok"})
    prior = pd.Series({"value": math.nan, "unit": "x", "status": "not available"})
    assert display.change_text(current, prior, 2025) == "no change shown: FY2025 not available"
    assert display.change_text(current, None, 2025) == "no change shown: no FY2025 data"
    margin_now = pd.Series({"value": 20.0, "unit": "%", "status": "ok"})
    margin_before = pd.Series({"value": 18.3, "unit": "%", "status": "ok"})
    assert display.change_text(margin_now, margin_before, 2025) == "+1.7 pt vs FY2025"


# --- Table "Credit ratios, last 5 fiscal years" (AC5, AC5b, E11) ---------------------------------


def test_ratio_table_has_9_rows_per_company_and_one_column_per_year(alfa_beta):
    _, _, table = alfa_beta
    wide, colours = display.ratio_table(table)
    assert list(wide.columns) == ["Ticker", "Company", "Metric", "Unit", "FY2024", "FY2025", "FY2026",
                                  "Latest flag", "Notes"]
    assert wide.shape == colours.shape
    assert list(wide["Ticker"]).count("ALFA") == 9 and list(wide["Ticker"]).count("BETA") == 9
    assert wide["Unit"].isin(["USD m", "x", "%"]).all()  # a unit on every row
    alfa = wide[wide["Ticker"] == "ALFA"].set_index("Metric")
    assert list(alfa.loc["Debt / equity", ["FY2024", "FY2025", "FY2026"]]) == ["1.53x", "1.53x", "1.53x"]
    assert alfa.loc["Debt / equity", "Latest flag"] == "orange"
    assert alfa.loc["EBITDA", "Latest flag"] == "no flag"
    # FY2024: D&A not reported -> short status in the cell, reason in Notes
    assert alfa.loc["EBITDA", "FY2024"] == "not available"
    assert alfa.loc["EBITDA", "Notes"] == "FY2024: not available: D&A not reported"


def test_ratio_table_shows_no_filler_year(alfa_beta):
    _, _, table = alfa_beta
    wide, colours = display.ratio_table(table)
    beta = wide[wide["Ticker"] == "BETA"].set_index("Metric")
    assert beta.loc["Current ratio", "FY2024"] == "no data"  # BETA has only FY2025 and FY2026
    assert beta.loc["Current ratio", "FY2026"] == "0.80x"
    beta_colours = colours[wide["Ticker"] == "BETA"].set_index(wide[wide["Ticker"] == "BETA"]["Metric"])
    assert beta_colours.loc["Current ratio", "FY2026"] == "red"
    assert beta_colours.loc["Current ratio", "FY2024"] == ""


def test_ratio_table_switches_only_the_debt_based_rows(alfa_beta):
    _, _, table = alfa_beta
    financial, _ = display.ratio_table(table, incl_leases=False)
    leases, _ = display.ratio_table(table, incl_leases=True)
    financial = financial[financial["Ticker"] == "ALFA"].reset_index(drop=True)
    leases = leases[leases["Ticker"] == "ALFA"].reset_index(drop=True)
    changed = [m for m, a, b in zip(financial["Metric"], financial["FY2026"], leases["FY2026"]) if a != b]
    # AC5b: total debt, net debt, ND/EBITDA and D/E change; the others do not
    assert changed == ["Total debt", "Net debt", "Net debt / EBITDA", "Debt / equity"]
    assert list(leases["Metric"][1:5]) == ["Total debt (incl. leases)", "Net debt (incl. leases)",
                                           "Net debt / EBITDA (incl. leases)", "Debt / equity (incl. leases)"]
    # 2,000 + 300 + 200 + 400 + 100 = 3,000 (CALC2b); 3,000 - 600 = 2,400 (CALC3b)
    assert list(leases["FY2026"][1:3]) == ["3,000 USD m", "2,400 USD m"]


def test_ratio_table_notes_keep_the_reason_of_an_ok_value(alfa_beta):
    _, _, table = alfa_beta
    wide, _ = display.ratio_table(table, incl_leases=True)
    beta = wide[wide["Ticker"] == "BETA"].set_index("Metric")
    assert beta.loc["Total debt (incl. leases)", "FY2026"] == "1,300 USD m"
    assert "short-term borrowings not reported" in beta.loc["Total debt (incl. leases)", "Notes"]
