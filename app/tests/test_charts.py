"""Tests of creditlens/charts.py (slice 6, issue #9): the two Plotly charts.

The charts only draw the display-ready values they receive (docs/architecture.md),
so every test compares the figure with the sample display table
(app/tests/fixtures/charts_sample.csv, SAMPLE DATA). The honesty rules come from
.claude/skills/design-interface/financial-visuals.md: missing is never drawn as 0,
a real 0 is drawn, the unit is on every axis, the zero line is visible, lines do
not join across gaps, only real years are shown.
"""

import pandas as pd
import pytest

from creditlens import charts

# Same shape as flags.load_thresholds() returns (the agreed limits of docs/acceptance.md).
THRESHOLDS = {
    "net_debt_to_ebitda": {"label": "Net debt / EBITDA", "direction": "lower_is_better", "green": 2.0, "orange": 3.5},
    "interest_coverage": {"label": "Interest coverage", "direction": "higher_is_better", "green": 6.0, "orange": 3.0},
    "free_cash_flow": {"label": "Free cash flow", "direction": "higher_is_better", "green": 0.0, "orange": None},
}


@pytest.fixture
def display(fixtures_dir) -> pd.DataFrame:
    return pd.read_csv(fixtures_dir / "charts_sample.csv", comment="#")


def bar_values(fig) -> dict:
    """Company label -> drawn bar value (None when there is no bar)."""
    bar = fig.data[0]
    return dict(zip(bar.y, bar.x))


def annotation_texts(fig) -> list[str]:
    return [a.text for a in fig.layout.annotations]


def vertical_lines(fig) -> list[float]:
    return sorted(s.x0 for s in fig.layout.shapes if s.type == "line" and s.x0 == s.x1)


def line_by_ticker(fig) -> dict:
    return {trace.name: trace for trace in fig.data}


# --- Selector options ----------------------------------------------------------------


def test_chart_metrics_follow_the_debt_definition():
    assert charts.chart_metrics() == [
        "net_debt_to_ebitda",
        "debt_to_equity",
        "interest_coverage",
        "current_ratio",
        "ebitda_margin",
        "free_cash_flow",
    ]
    assert charts.chart_metrics(incl_leases=True)[:2] == [
        "net_debt_to_ebitda_incl_leases",
        "debt_to_equity_incl_leases",
    ]
    assert charts.chart_metrics(incl_leases=True)[2:] == charts.chart_metrics()[2:]


def test_unknown_metric_is_refused(display):
    with pytest.raises(ValueError, match="no_such_ratio"):
        charts.comparison_bar_chart(display, "no_such_ratio")
    with pytest.raises(ValueError, match="no_such_ratio"):
        charts.trend_line_chart(display, "no_such_ratio")


# --- Chart "How do the companies compare in the latest fiscal year?" ------------------


def test_bars_use_each_company_latest_fiscal_year_values_unchanged(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda", THRESHOLDS)
    assert fig.layout.title.text == charts.COMPARISON_TITLE
    assert bar_values(fig) == {"BETA (FY2026)": -0.20, "ALFA (FY2026)": 2.40, "GAMA (FY2026)": None}


def test_missing_value_has_no_bar_and_is_labelled_na_with_its_reason(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda", THRESHOLDS)
    assert bar_values(fig)["GAMA (FY2026)"] is None  # no bar, never 0
    na = [t for t in annotation_texts(fig) if t.startswith("n/a")]
    assert na == ["n/a (not meaningful: EBITDA ≤ 0)"]


def test_real_zero_is_drawn_as_a_bar(display):
    fig = charts.comparison_bar_chart(display, "free_cash_flow", THRESHOLDS)
    assert bar_values(fig)["GAMA (FY2026)"] == 0
    assert not [t for t in annotation_texts(fig) if t.startswith("n/a")]


def test_bars_are_sorted_with_na_last(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda", THRESHOLDS)
    assert list(fig.data[0].y) == ["BETA (FY2026)", "ALFA (FY2026)", "GAMA (FY2026)"]
    assert fig.layout.yaxis.autorange == "reversed"  # first company at the top


def test_bars_show_the_screen_text_and_flag_colour(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda", THRESHOLDS)
    bar = fig.data[0]
    assert list(bar.text) == ["-0.20x · green", "2.40x · orange", ""]  # the flag as a word too, never colour alone
    assert bar.cliponaxis is False  # seen on screen: the minus sign of -0.20x was cut off
    assert list(bar.marker.color) == [
        charts.FLAG_COLOURS["green"],
        charts.FLAG_COLOURS["orange"],
        charts.NO_FLAG_COLOUR,
    ]


def test_bar_axis_has_the_unit_and_a_visible_zero_line(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda", THRESHOLDS)
    assert fig.layout.xaxis.title.text == "Net debt / EBITDA (x)"
    assert fig.layout.xaxis.zeroline is True
    assert fig.layout.xaxis.rangemode == "tozero"
    fcf = charts.comparison_bar_chart(display, "free_cash_flow", THRESHOLDS)
    assert fcf.layout.xaxis.title.text == "Free cash flow (USD m)"


def test_thresholds_are_drawn_as_reference_lines(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda", THRESHOLDS)
    assert vertical_lines(fig) == [2.0, 3.5]
    texts = annotation_texts(fig)
    assert "green ≤ 2.0x" in texts and "orange ≤ 3.5x" in texts


def test_thresholds_of_the_incl_leases_version_are_the_same(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda_incl_leases", THRESHOLDS)
    assert vertical_lines(fig) == [2.0, 3.5]
    assert fig.layout.xaxis.title.text == "Net debt / EBITDA (incl. leases) (x)"
    assert bar_values(fig) == {"BETA (FY2026)": 0.30, "ALFA (FY2026)": 2.90, "GAMA (FY2026)": None}


def test_ratio_without_orange_zone_has_one_reference_line(display):
    fig = charts.comparison_bar_chart(display, "free_cash_flow", THRESHOLDS)
    assert vertical_lines(fig) == [0.0]
    assert "green ≥ 0 USD m" in annotation_texts(fig)


def test_no_thresholds_given_means_no_reference_lines(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda")
    assert vertical_lines(fig) == []


def test_ac8_interest_coverage_bars(display):
    """AC8: picking interest coverage switches the chart; a missing value is n/a, never 0."""
    fig = charts.comparison_bar_chart(display, "interest_coverage", THRESHOLDS)
    assert bar_values(fig) == {"GAMA (FY2026)": 2.50, "ALFA (FY2026)": 6.00, "BETA (FY2026)": None}
    assert "n/a (not available: interest expense not reported)" in annotation_texts(fig)
    assert vertical_lines(fig) == [3.0, 6.0]


# --- Chart "How did this ratio change over 5 years?" -----------------------------------


def test_lines_one_per_company_with_gaps_not_joined(display):
    fig = charts.trend_line_chart(display, "net_debt_to_ebitda")
    assert fig.layout.title.text == charts.TREND_TITLE
    lines = line_by_ticker(fig)
    assert list(lines) == ["ALFA", "BETA", "GAMA"]
    beta = lines["BETA"]
    assert list(beta.x) == [2022, 2023, 2024, 2025, 2026]
    assert list(beta.y) == [0.50, 0.40, None, None, -0.20]
    assert all(trace.connectgaps is False for trace in fig.data)
    assert all(trace.mode == "lines+markers" for trace in fig.data)


def test_lines_show_only_real_years(display):
    fig = charts.trend_line_chart(display, "net_debt_to_ebitda")
    gama = line_by_ticker(fig)["GAMA"]
    assert list(gama.x) == [2024, 2025, 2026]  # no filler years before FY2024
    assert list(gama.y) == [3.10, 3.60, None]


def test_a_year_missing_from_the_table_is_a_gap_not_a_joined_line(display):
    without_2024 = display[~((display["ticker"] == "ALFA") & (display["fiscal_year"] == 2024))]
    fig = charts.trend_line_chart(without_2024, "net_debt_to_ebitda")
    alfa = line_by_ticker(fig)["ALFA"]
    assert list(alfa.x) == [2022, 2023, 2024, 2025, 2026]
    assert list(alfa.y) == [1.10, 1.25, None, 1.80, 2.40]


def test_line_axes_have_units_zero_line_and_year_end_note(display):
    fig = charts.trend_line_chart(display, "net_debt_to_ebitda")
    assert fig.layout.yaxis.title.text == "Net debt / EBITDA (x)"
    assert fig.layout.yaxis.zeroline is True
    assert fig.layout.yaxis.rangemode == "tozero"
    assert fig.layout.xaxis.title.text == "Fiscal year"
    assert fig.layout.xaxis.dtick == 1
    note = [t for t in annotation_texts(fig) if "year-end" in t]
    assert note == [
        "Fiscal year-end dates differ by company (latest: ALFA 2026-12-31, BETA 2026-06-30, GAMA 2026-05-31)"
    ]


def test_lines_list_missing_points_as_na_with_reason(display):
    fig = charts.trend_line_chart(display, "net_debt_to_ebitda")
    na = [t for t in annotation_texts(fig) if t.startswith("n/a")]
    assert na == [  # one line per company and reason, so a long reason is never cut at the chart's edge
        "n/a (not drawn):<br>BETA FY2024, FY2025 (not available: D&A not reported)<br>"
        "GAMA FY2026 (not meaningful: EBITDA ≤ 0)"
    ]


def test_ac8_interest_coverage_lines(display):
    """AC8: the line chart switches too; BETA has no value, so no point is drawn at 0."""
    fig = charts.trend_line_chart(display, "interest_coverage")
    lines = line_by_ticker(fig)
    assert list(lines["BETA"].y) == [None] * 5
    assert list(lines["GAMA"].y) == [4.20, 3.10, 2.50]
    na = [t for t in annotation_texts(fig) if t.startswith("n/a")]
    assert na == ["n/a (not drawn):<br>BETA FY2022, FY2023, FY2024, FY2025, FY2026 "
                  "(not available: interest expense not reported)"]


def test_real_zero_is_drawn_as_a_point(display):
    fig = charts.trend_line_chart(display, "free_cash_flow")
    assert list(line_by_ticker(fig)["GAMA"].y) == [120, -50, 0]


# --- SAMPLE DATA mark ------------------------------------------------------------------


@pytest.mark.parametrize("build", [charts.comparison_bar_chart, charts.trend_line_chart])
def test_sample_data_mark_only_when_asked(display, build):
    assert "SAMPLE DATA" in annotation_texts(build(display, "net_debt_to_ebitda", sample=True))
    assert "SAMPLE DATA" not in annotation_texts(build(display, "net_debt_to_ebitda"))


# --- An empty chart says why (seen in the browser on 2026-11-28: NKE alone, Net debt / EBITDA) ------------


def test_empty_charts_get_a_sentence_saying_why(display):
    only_beta = display[display["ticker"] == "BETA"]  # BETA reports no interest expense in any year
    text = charts.no_value_text(only_beta, "interest_coverage")
    assert text.startswith("No company shown has a value for Interest coverage")
    assert "choose another ratio" in text


def test_no_sentence_when_one_company_has_a_value(display):
    assert charts.no_value_text(display, "interest_coverage") == ""  # ALFA has interest coverage


# --- Look (design of 2026-11-28, with François's agreement): rounded bars, thresholds and labels on the lines ------


def horizontal_lines(fig) -> list[float]:
    return sorted(s.y0 for s in fig.layout.shapes if s.type == "line" and s.y0 == s.y1)


def test_bars_have_rounded_ends(display):
    fig = charts.comparison_bar_chart(display, "net_debt_to_ebitda", THRESHOLDS)
    assert fig.data[0].marker.cornerradius == charts.BAR_CORNER_RADIUS


def test_trend_chart_draws_the_flag_limits_when_given(display):
    """Net debt / EBITDA: green up to 2.0x, orange up to 3.5x (thresholds.toml) -> two horizontal lines."""
    with_limits = charts.trend_line_chart(display, "net_debt_to_ebitda", thresholds=THRESHOLDS)
    without = charts.trend_line_chart(display, "net_debt_to_ebitda")
    assert horizontal_lines(with_limits) == [2.0, 3.5]
    assert horizontal_lines(without) == []


def test_trend_chart_leaves_out_a_limit_far_above_the_data(display):
    """BETA alone: values 0.50, 0.40, -0.20x. Limits 2.0x and 3.5x are above 1.25 x 0.50 = 0.625: drawing them would
    stretch the axis and flatten the line, so they are left out (the bar chart keeps them)."""
    beta = display[display["ticker"] == "BETA"]
    fig = charts.trend_line_chart(beta, "net_debt_to_ebitda", thresholds=THRESHOLDS)
    assert horizontal_lines(fig) == []


def test_each_line_ends_with_its_ticker_and_last_value(display):
    """Direct labels: each company's last drawn point, with the screen text (GAMA FY2026 is not meaningful, so its
    last drawn point is FY2025, 3.60x)."""
    fig = charts.trend_line_chart(display, "net_debt_to_ebitda")
    labels = [t for t in annotation_texts(fig) if t.split(" ")[0] in {"ALFA", "BETA", "GAMA"}]
    assert sorted(labels) == ["ALFA 2.40x", "BETA -0.20x", "GAMA 3.60x"]
    assert list(fig.layout.xaxis.range) == [2021.75, 2026.25]  # the real years: the labels never widen the axis


def test_company_lines_never_use_a_flag_colour(display):
    """Colour carries meaning only for the flags (docs/product.md): a company line must not look like a flag."""
    fig = charts.trend_line_chart(display, "net_debt_to_ebitda")
    flag_colours = {c.lower() for c in charts.FLAG_COLOURS.values()}
    assert all(trace.line.color.lower() not in flag_colours for trace in fig.data)
    assert len({trace.line.color for trace in fig.data}) == len(fig.data)  # one colour per company

