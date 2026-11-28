"""Tests for creditlens/flags.py and app/config/thresholds.toml (slice 4, issue #7).

The expected flags are worked by hand from the thresholds table of
docs/acceptance.md (agreed on 2026-11-20) and the hand working of CALC12.
They were never taken from the code's output.

The input is app/tests/fixtures/flags_sample.csv: SAMPLE DATA, synthetic, in
the format of ratios.compute_ratios (docs/architecture.md, "Contracts between
parts"), so these tests do not depend on another member's code.
"""

import math

import pandas as pd
import pytest

from creditlens import flags

# The thresholds of docs/acceptance.md, written out here on purpose (not read
# from the code), so a change in thresholds.toml cannot change the test.
AGREED_THRESHOLDS = {
    "net_debt_to_ebitda": ("lower_is_better", 2.0, 3.5),
    "debt_to_equity": ("lower_is_better", 1.0, 2.0),
    "interest_coverage": ("higher_is_better", 6.0, 3.0),
    "current_ratio": ("higher_is_better", 1.5, 1.0),
    "ebitda_margin": ("higher_is_better", 20.0, 10.0),
    "free_cash_flow": ("higher_is_better", 0.0, None),
}

CONTRACT_COLUMNS = ["ticker", "fiscal_year", "period_end", "metric", "value", "unit", "status", "reason"]
AMOUNTS = ["ebitda", "total_debt", "net_debt", "total_debt_incl_leases", "net_debt_incl_leases"]

# A valid thresholds file, used as the base of the AC6 and error tests.
VALID_TOML = """
[net_debt_to_ebitda]
direction = "lower_is_better"
green = 2.0
orange = 3.5

[debt_to_equity]
direction = "lower_is_better"
green = 1.0
orange = 2.0

[interest_coverage]
direction = "higher_is_better"
green = 6.0
orange = 3.0

[current_ratio]
direction = "higher_is_better"
green = 1.5
orange = 1.0

[ebitda_margin]
direction = "higher_is_better"
green = 20.0
orange = 10.0

[free_cash_flow]
direction = "higher_is_better"
green = 0.0
"""


# --- Helpers -------------------------------------------------------------------


@pytest.fixture
def sample(fixtures_dir) -> pd.DataFrame:
    """The SAMPLE DATA ratios table, as compute_ratios returns it."""
    df = pd.read_csv(fixtures_dir / "flags_sample.csv", comment="#", parse_dates=["period_end"])
    df["reason"] = df["reason"].fillna("")  # compute_ratios gives "" when there is nothing to say
    return df


@pytest.fixture
def thresholds():
    """The thresholds of the real app/config/thresholds.toml."""
    return flags.load_thresholds()


def write_toml(tmp_path, text):
    path = tmp_path / "thresholds.toml"
    path.write_text(text, encoding="utf-8")
    return path


def flag_of(flagged, metric, ticker="SMPL", fiscal_year=2026):
    rows = flagged[
        (flagged["ticker"] == ticker) & (flagged["fiscal_year"] == fiscal_year) & (flagged["metric"] == metric)
    ]
    assert len(rows) == 1, f"expected one row for {ticker} {fiscal_year} {metric}"
    return rows["flag"].iloc[0]


def one_row(metric, value, unit="x", status="ok"):
    """A ratios table with a single row."""
    return pd.DataFrame(
        [
            {
                "ticker": "ONE",
                "fiscal_year": 2026,
                "period_end": pd.Timestamp("2026-12-31"),
                "metric": metric,
                "value": value,
                "unit": unit,
                "status": status,
                "reason": "",
            }
        ]
    )


def with_value(df, metric, value, ticker="SMPL", fiscal_year=2026):
    """Return a copy where one metric has a new value."""
    df = df.copy()
    mask = (df["ticker"] == ticker) & (df["fiscal_year"] == fiscal_year) & (df["metric"] == metric)
    df.loc[mask, "value"] = value
    return df


# --- The thresholds file ---------------------------------------------------------


def test_thresholds_file_has_the_agreed_values(thresholds):
    assert set(thresholds) == set(AGREED_THRESHOLDS)
    for ratio, (direction, green, orange) in AGREED_THRESHOLDS.items():
        rule = thresholds[ratio]
        assert rule["direction"] == direction, ratio
        assert rule["green"] == green, ratio
        assert rule["orange"] == orange, ratio


def test_each_ratio_has_a_label_for_the_page(thresholds):
    for ratio, rule in thresholds.items():
        assert rule["label"], ratio


# --- CALC12: the example company ---------------------------------------------------


def test_calc12_flags_including_leases(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    # Hand working of CALC12 (docs/acceptance.md)
    assert flag_of(flagged, "net_debt_to_ebitda_incl_leases") == "green"  # 2.00 <= 2.0
    assert flag_of(flagged, "debt_to_equity_incl_leases") == "orange"  # 1.0 < 2.00 <= 2.0
    assert flag_of(flagged, "interest_coverage") == "green"  # 8.00 >= 6.0
    assert flag_of(flagged, "current_ratio") == "green"  # 1.50 >= 1.5
    assert flag_of(flagged, "ebitda_margin") == "green"  # 20.0 >= 20
    assert flag_of(flagged, "free_cash_flow") == "green"  # 1,100 >= 0


def test_calc12_flags_financial_debt_only(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    assert flag_of(flagged, "net_debt_to_ebitda") == "green"  # 1.42 <= 2.0
    assert flag_of(flagged, "debt_to_equity") == "orange"  # 1.0 < 1.53 <= 2.0


@pytest.mark.parametrize("incl_leases", [False, True], ids=["financial-debt-only", "including-leases"])
def test_calc12_overall_alert_is_orange(sample, thresholds, incl_leases):
    flagged = flags.apply_flags(sample, thresholds)
    alert = flags.overall_alert(flagged, "SMPL", incl_leases=incl_leases)
    assert alert.level == "orange"
    assert alert.text == "Orange: 1 orange flag"
    assert (alert.green, alert.orange, alert.red) == (5, 1, 0)
    assert (alert.not_available, alert.not_meaningful) == (0, 0)


# --- apply_flags: shape of the output ---------------------------------------------


def test_apply_flags_keeps_every_row_and_adds_the_flag_column(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    assert list(flagged.columns) == CONTRACT_COLUMNS + ["flag"]
    assert len(flagged) == len(sample)
    pd.testing.assert_frame_equal(flagged[CONTRACT_COLUMNS], sample[CONTRACT_COLUMNS])
    assert set(flagged["flag"]) <= {"green", "orange", "red", ""}


def test_apply_flags_does_not_change_its_input(sample, thresholds):
    before = sample.copy()
    flags.apply_flags(sample, thresholds)
    pd.testing.assert_frame_equal(sample, before)


def test_apply_flags_reads_the_real_file_by_default(sample):
    flagged = flags.apply_flags(sample)
    assert flag_of(flagged, "debt_to_equity") == "orange"


def test_amounts_get_no_flag(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    for metric in AMOUNTS:
        assert flag_of(flagged, metric) == "", metric


def test_e1_not_available_and_not_meaningful_get_no_flag(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    gaps = flagged[(flagged["ticker"] == "GAPS") & (flagged["status"] != "ok")]
    assert len(gaps) == 7
    assert (gaps["flag"] == "").all()
    # the "ok" ratios of the same company are still flagged
    assert flag_of(flagged, "current_ratio", ticker="GAPS") == "red"  # 0.80 < 1.0
    assert flag_of(flagged, "free_cash_flow", ticker="GAPS") == "red"  # -50 < 0


def test_ok_row_without_value_is_refused(thresholds):
    with pytest.raises(ValueError, match="no value"):
        flags.apply_flags(one_row("current_ratio", math.nan), thresholds)


def test_missing_column_is_refused(sample, thresholds):
    with pytest.raises(ValueError, match="status"):
        flags.apply_flags(sample.drop(columns=["status"]), thresholds)


# --- Limits: "a value exactly on a limit takes the better colour" -------------------


@pytest.mark.parametrize(
    "metric, value, unit, expected",
    [
        ("net_debt_to_ebitda", 2.0, "x", "green"),
        ("net_debt_to_ebitda", 2.01, "x", "orange"),
        ("net_debt_to_ebitda", 3.5, "x", "orange"),
        ("net_debt_to_ebitda", 3.51, "x", "red"),
        ("net_debt_to_ebitda", -0.5, "x", "green"),  # net cash (CALC11)
        ("net_debt_to_ebitda_incl_leases", 3.51, "x", "red"),  # same thresholds for both versions
        ("debt_to_equity", 1.0, "x", "green"),
        ("debt_to_equity", 1.01, "x", "orange"),
        ("debt_to_equity", 2.0, "x", "orange"),
        ("debt_to_equity", 2.01, "x", "red"),
        ("debt_to_equity_incl_leases", 2.01, "x", "red"),
        ("interest_coverage", 6.0, "x", "green"),
        ("interest_coverage", 5.99, "x", "orange"),
        ("interest_coverage", 3.0, "x", "orange"),
        ("interest_coverage", 2.99, "x", "red"),
        ("current_ratio", 1.5, "x", "green"),
        ("current_ratio", 1.49, "x", "orange"),
        ("current_ratio", 1.0, "x", "orange"),
        ("current_ratio", 0.99, "x", "red"),
        ("ebitda_margin", 20.0, "%", "green"),
        ("ebitda_margin", 19.9, "%", "orange"),
        ("ebitda_margin", 10.0, "%", "orange"),
        ("ebitda_margin", 9.9, "%", "red"),
        ("free_cash_flow", 0.0, "USD m", "green"),
        ("free_cash_flow", -1.0, "USD m", "red"),  # no orange zone
        ("free_cash_flow", 1100.0, "USD m", "green"),
    ],
)
def test_limits(thresholds, metric, value, unit, expected):
    flagged = flags.apply_flags(one_row(metric, value, unit), thresholds)
    assert flagged["flag"].iloc[0] == expected


@pytest.mark.parametrize(
    "metric, value, unit, shown, expected",
    [
        ("net_debt_to_ebitda", 2.004, "x", "2.00x", "green"),
        ("net_debt_to_ebitda", 2.006, "x", "2.01x", "orange"),
        ("current_ratio", 1.496, "x", "1.50x", "green"),
        ("ebitda_margin", 19.96, "%", "20.0 %", "green"),
        ("ebitda_margin", 19.94, "%", "19.9 %", "orange"),
        # exact halves are rounded up, as Excel's ROUND (2,406 / 1,200 = 2.005)
        ("net_debt_to_ebitda", 2406 / 1200, "x", "2.01x", "orange"),
        ("current_ratio", 1.495, "x", "1.50x", "green"),
        ("ebitda_margin", 19.95, "%", "20.0 %", "green"),
    ],
)
def test_flag_matches_the_rounded_value_shown_on_screen(thresholds, metric, value, unit, shown, expected):
    # The page shows ratios with 2 decimals and the margin with 1 (product.md).
    # A cell that reads "2.00x" must not be orange when the limit is 2.0.
    flagged = flags.apply_flags(one_row(metric, value, unit), thresholds)
    assert flagged["flag"].iloc[0] == expected, f"shown as {shown}"


@pytest.mark.parametrize(
    "value, unit, expected",
    [
        (2406 / 1200, "x", 2.01),  # 2.005: half up (Python's round gives 2.0)
        (2.675, "x", 2.68),
        (0.125, "x", 0.13),
        (2.004, "x", 2.0),
        (18.25, "%", 18.3),
        (1234.5, "USD m", 1235.0),
        (-2.5, "USD m", -3.0),  # away from zero, as Excel's ROUND
    ],
)
def test_shown_value_rounds_half_up_like_excel(value, unit, expected):
    assert flags.shown_value(value, unit) == expected


# --- AC6: thresholds change without code ---------------------------------------------


def test_ac6_changing_the_file_changes_the_flag(sample, tmp_path):
    # Current ratio 1.50: green with the agreed limits (>= 1.5).
    stricter = VALID_TOML.replace(
        '[current_ratio]\ndirection = "higher_is_better"\ngreen = 1.5\norange = 1.0',
        '[current_ratio]\ndirection = "higher_is_better"\ngreen = 2.0\norange = 1.6',
    )
    assert stricter != VALID_TOML
    before = flags.apply_flags(sample, flags.load_thresholds(write_toml(tmp_path, VALID_TOML)))
    after = flags.apply_flags(sample, flags.load_thresholds(write_toml(tmp_path, stricter)))
    assert flag_of(before, "current_ratio") == "green"
    assert flag_of(after, "current_ratio") == "red"  # 1.50 < 1.6


# --- Errors in the thresholds file ---------------------------------------------------


@pytest.mark.parametrize(
    "old, new, message",
    [
        ('direction = "lower_is_better"\ngreen = 2.0', 'direction = "lower"\ngreen = 2.0', "direction"),
        ("green = 2.0\norange = 3.5", "orange = 3.5", "green"),
        ("green = 2.0\norange = 3.5", 'green = "two"\norange = 3.5', "number"),
        ("green = 2.0\norange = 3.5", "green = 4.0\norange = 3.5", "orange"),  # lower is better: orange must be >= green
        ("green = 6.0\norange = 3.0", "green = 6.0\norange = 7.0", "orange"),  # higher is better: orange must be <= green
        ("green = 2.0\norange = 3.5", "green = 2.0\norange = 3.5\nred = 5.0", "red"),  # unknown key
    ],
    ids=["bad-direction", "no-green", "not-a-number", "lower-order", "higher-order", "unknown-key"],
)
def test_bad_thresholds_file_gives_a_clear_error(tmp_path, old, new, message):
    text = VALID_TOML.replace(old, new, 1)
    assert text != VALID_TOML
    with pytest.raises(ValueError, match=message):
        flags.load_thresholds(write_toml(tmp_path, text))


def test_missing_ratio_in_the_file_gives_a_clear_error(tmp_path):
    text = VALID_TOML.split("[free_cash_flow]")[0]
    with pytest.raises(ValueError, match="free_cash_flow"):
        flags.load_thresholds(write_toml(tmp_path, text))


def test_file_that_is_not_toml_gives_a_clear_error(tmp_path):
    with pytest.raises(ValueError, match="thresholds.toml"):
        flags.load_thresholds(write_toml(tmp_path, "[current_ratio\ngreen = "))


# --- overall_alert -------------------------------------------------------------------


def test_overall_alert_red_counts_not_available_and_not_meaningful(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    alert = flags.overall_alert(flagged, "GAPS")
    # ND/EBITDA, coverage, margin not available; D/E not meaningful; current ratio and FCF red
    assert alert.level == "red"
    assert alert.text == "Red: 2 red flags, 3 not available, 1 not meaningful"
    assert (alert.red, alert.not_available, alert.not_meaningful) == (2, 3, 1)


def test_overall_alert_uses_the_latest_fiscal_year(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    assert flag_of(flagged, "net_debt_to_ebitda", fiscal_year=2025) == "red"  # 4.00 > 3.5
    alert = flags.overall_alert(flagged, "SMPL")
    assert alert.fiscal_year == 2026
    assert alert.level == "orange"  # FY2025 is red, but it is not the latest year


def test_overall_alert_green(sample, thresholds):
    flagged = flags.apply_flags(with_value(sample, "debt_to_equity", 0.9), thresholds)
    alert = flags.overall_alert(flagged, "SMPL")
    assert alert.level == "green"
    assert alert.text == "Green: 6 green flags"


def test_overall_alert_red_wins_over_orange(sample, thresholds):
    flagged = flags.apply_flags(with_value(sample, "current_ratio", 0.5), thresholds)
    alert = flags.overall_alert(flagged, "SMPL")
    assert alert.level == "red"
    assert alert.text == "Red: 1 red flag"
    assert (alert.green, alert.orange, alert.red) == (4, 1, 1)


def test_overall_alert_follows_the_debt_version(sample, thresholds):
    # Only the lease version is red: the alert depends on the selector.
    flagged = flags.apply_flags(with_value(sample, "net_debt_to_ebitda_incl_leases", 4.0), thresholds)
    assert flags.overall_alert(flagged, "SMPL", incl_leases=False).level == "orange"
    assert flags.overall_alert(flagged, "SMPL", incl_leases=True).level == "red"


def test_overall_alert_without_any_flag_is_not_green(thresholds):
    rows = pd.concat(
        [one_row(metric, math.nan, status="not available") for metric in flags.flagged_metrics()],
        ignore_index=True,
    )
    alert = flags.overall_alert(flags.apply_flags(rows, thresholds), "ONE")
    assert alert.level == ""
    assert alert.text == "No flag: 6 not available"


def test_overall_alert_unknown_ticker(sample, thresholds):
    flagged = flags.apply_flags(sample, thresholds)
    with pytest.raises(ValueError, match="ZZZZ"):
        flags.overall_alert(flagged, "ZZZZ")


def test_overall_alert_needs_apply_flags_first(sample):
    with pytest.raises(ValueError, match="apply_flags"):
        flags.overall_alert(sample, "SMPL")


def test_flagged_metrics_for_each_debt_version():
    assert flags.flagged_metrics() == [
        "net_debt_to_ebitda",
        "debt_to_equity",
        "interest_coverage",
        "current_ratio",
        "ebitda_margin",
        "free_cash_flow",
    ]
    assert flags.flagged_metrics(incl_leases=True)[:2] == [
        "net_debt_to_ebitda_incl_leases",
        "debt_to_equity_incl_leases",
    ]


# --- With the real ratios module (runs once PR #13 of Coco is merged) -------------------


def test_calc12_end_to_end_with_compute_ratios(fixtures_dir, thresholds):
    ratios = pytest.importorskip("creditlens.ratios", reason="ratios.py arrives with PR #13 (slice 3)")
    path = fixtures_dir / "ratios_sample.csv"
    if not path.exists():
        pytest.skip("ratios_sample.csv arrives with PR #13 (slice 3)")
    financials = pd.read_csv(path, comment="#", parse_dates=["period_end", "filed"], dtype={"value": "float64"})
    flagged = flags.apply_flags(ratios.compute_ratios(financials), thresholds)
    assert flags.overall_alert(flagged, "SMPL", incl_leases=True).text == "Orange: 1 orange flag"
    assert flags.overall_alert(flagged, "SMPL", incl_leases=False).text == "Orange: 1 orange flag"
