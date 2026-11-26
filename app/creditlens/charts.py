"""The two Plotly charts of the CreditLens dashboard (slice 6, issue #9).

* :func:`comparison_bar_chart`: "How do the companies compare in the latest
  fiscal year?" (visual 2 of docs/product.md);
* :func:`trend_line_chart`: "How did this ratio change over 5 years?" (visual 3).

Input: the display table of creditlens/display.py (one row per ticker, fiscal
year and metric; columns ``ticker, company, fiscal_year, period_end, metric,
label, unit, value, text, status, flag``). ``value`` is already rounded as on
screen and empty when there is no number; ``text`` is what the screen shows.
A sample is in app/tests/fixtures/charts_sample.csv.

This module only draws (docs/architecture.md): it never computes, rounds or
decides that a value is missing. Honesty rules
(.claude/skills/design-interface/financial-visuals.md):

* a missing value has no bar or point and is labelled "n/a" with its reason;
  a real 0 is drawn;
* lines are not joined across missing years, and only real years are shown;
* the unit is on every value axis, and the zero line is visible;
* the flag thresholds are drawn as reference lines on the bar chart.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

COMPARISON_TITLE = "How do the companies compare in the latest fiscal year?"
TREND_TITLE = "How did this ratio change over 5 years?"

INCL_LEASES = "_incl_leases"

# The ratios offered in the chart selector, in the order of the ratio table.
# The two debt-based ones switch with the debt definition selector.
CHART_RATIOS = [
    "net_debt_to_ebitda",
    "debt_to_equity",
    "interest_coverage",
    "current_ratio",
    "ebitda_margin",
    "free_cash_flow",
]
DEBT_BASED_RATIOS = ["net_debt_to_ebitda", "debt_to_equity"]

# Colour is used only for the flags (docs/product.md, "Visual reference").
FLAG_COLOURS = {"green": "#2e7d32", "orange": "#ef6c00", "red": "#c62828"}
NO_FLAG_COLOUR = "#9e9e9e"

# Company lines: neutral blues and greys, told apart by dash and marker too,
# so they are never confused with a flag colour.
LINE_STYLES = [
    ("#1f4e79", "solid", "circle"),
    ("#5b9bd5", "dash", "square"),
    ("#595959", "dot", "diamond"),
    ("#8faadc", "dashdot", "triangle-up"),
    ("#a5a5a5", "longdash", "x"),
]

# How a threshold is written on its reference line, per unit.
THRESHOLD_FORMATS = {"x": "{:.1f}x", "%": "{:.1f} %", "USD m": "{:,.0f} USD m"}


def chart_metrics(incl_leases: bool = False) -> list[str]:
    """The metric names offered in the chart selector, for one debt definition."""
    suffix = INCL_LEASES if incl_leases else ""
    return [ratio + suffix if ratio in DEBT_BASED_RATIOS else ratio for ratio in CHART_RATIOS]


def _rows_for(display: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = display[display["metric"] == metric]
    if rows.empty:
        raise ValueError(f"The display table has no rows for the metric '{metric}'.")
    return rows


def _number(value) -> float | None:
    """The value to draw, or None when there is no number (never 0)."""
    return None if pd.isna(value) else float(value)


def _axis_title(rows: pd.DataFrame) -> str:
    first = rows.iloc[0]
    return f"{first['label']} ({first['unit']})"


def _flag_colour(flag) -> str:
    return FLAG_COLOURS.get(flag, NO_FLAG_COLOUR) if isinstance(flag, str) else NO_FLAG_COLOUR


def _add_sample_mark(fig: go.Figure) -> None:
    fig.add_annotation(
        text="SAMPLE DATA",
        xref="paper", yref="paper", x=1, y=1.12,
        xanchor="right", showarrow=False,
        font={"size": 16, "color": "#c62828"},
    )


def _add_note(fig: go.Figure, text: str, y: float) -> None:
    fig.add_annotation(
        text=text,
        xref="paper", yref="paper", x=0, y=y,
        xanchor="left", yanchor="top", align="left", showarrow=False,
        font={"size": 11, "color": "#595959"},
    )


def _add_thresholds(fig: go.Figure, metric: str, unit: str, thresholds: dict | None) -> None:
    """Draw the green and orange limits of the metric as dashed vertical lines."""
    rule = (thresholds or {}).get(metric.removesuffix(INCL_LEASES))
    if rule is None:
        return
    sign = "≤" if rule["direction"] == "lower_is_better" else "≥"
    number_format = THRESHOLD_FORMATS.get(unit, "{}")
    for colour in ("green", "orange"):
        limit = rule.get(colour)
        if limit is None:
            continue
        fig.add_vline(
            x=limit,
            line={"color": FLAG_COLOURS[colour], "dash": "dash", "width": 1.5},
            annotation_text=f"{colour} {sign} {number_format.format(limit)}",
            annotation_position="top",
            annotation_font={"color": FLAG_COLOURS[colour], "size": 11},
        )


def comparison_bar_chart(
    display: pd.DataFrame,
    metric: str,
    thresholds: dict | None = None,
    sample: bool = False,
) -> go.Figure:
    """Horizontal bars, one per company, for its latest fiscal year.

    Args:
        display: the display table (see the module docstring).
        metric: the metric to show, for example ``"net_debt_to_ebitda"``.
        thresholds: the rules of flags.load_thresholds(); the green and orange
            limits are drawn as reference lines. None draws no line.
        sample: True adds a "SAMPLE DATA" mark (synthetic data).

    Bars are sorted by value; a company without a value comes last, with no bar
    and an "n/a" label giving the reason.
    """
    rows = _rows_for(display, metric)
    latest = rows.loc[rows.groupby("ticker", sort=False)["fiscal_year"].idxmax()]
    has_value = latest["value"].notna()
    ordered = pd.concat([latest[has_value].sort_values("value", kind="stable"), latest[~has_value]])

    labels = [f"{r.ticker} (FY{r.fiscal_year})" for r in ordered.itertuples()]
    fig = go.Figure(
        go.Bar(
            orientation="h",
            x=[_number(v) for v in ordered["value"]],
            y=labels,
            text=[r.text if pd.notna(r.value) else "" for r in ordered.itertuples()],
            textposition="outside",
            marker={"color": [_flag_colour(f) for f in ordered["flag"]]},
            hovertext=[
                f"{r.company}<br>FY{r.fiscal_year}, year ended {r.period_end}<br>{r.text}"
                for r in ordered.itertuples()
            ],
            hoverinfo="text",
            showlegend=False,
        )
    )
    for label, r in zip(labels, ordered.itertuples()):
        if pd.isna(r.value):
            fig.add_annotation(
                x=0, y=label, text=f"n/a ({r.text})",
                xanchor="left", showarrow=False, font={"color": "#595959"},
            )

    unit = rows.iloc[0]["unit"]
    _add_thresholds(fig, metric, unit, thresholds)
    fig.update_layout(
        title={"text": COMPARISON_TITLE},
        template="plotly_white",
        height=180 + 60 * len(labels),
        margin={"l": 10, "r": 30, "t": 80, "b": 50},
        xaxis={
            "title": {"text": _axis_title(rows)},
            "zeroline": True, "zerolinewidth": 2, "zerolinecolor": "#404040",
            "rangemode": "tozero",
        },
        yaxis={"autorange": "reversed"},
    )
    if sample:
        _add_sample_mark(fig)
    return fig


def _missing_note(missing: list[tuple[str, int, str]]) -> str | None:
    """One "n/a" note for the points not drawn: ticker, years and reason."""
    if not missing:
        return None
    groups: dict[tuple[str, str], list[int]] = {}
    for ticker, year, reason in missing:
        groups.setdefault((ticker, reason), []).append(year)
    parts = [
        f"{ticker} {', '.join(f'FY{y}' for y in years)} ({reason})"
        for (ticker, reason), years in groups.items()
    ]
    return "n/a (not drawn): " + "; ".join(parts)


def trend_line_chart(display: pd.DataFrame, metric: str, sample: bool = False) -> go.Figure:
    """One line with markers per company, over its fiscal years.

    Args:
        display: the display table (see the module docstring).
        metric: the metric to show, for example ``"net_debt_to_ebitda"``.
        sample: True adds a "SAMPLE DATA" mark (synthetic data).

    Each company covers only its own years, from its first to its last one in
    the table. A year without a value, or missing from the table, is a gap:
    the line is not joined across it, and a note lists it as "n/a".
    """
    rows = _rows_for(display, metric)
    fig = go.Figure()
    missing: list[tuple[str, int, str]] = []
    year_ends = []

    for i, (ticker, company_rows) in enumerate(rows.groupby("ticker", sort=False)):
        by_year = company_rows.set_index("fiscal_year")
        years = list(range(int(by_year.index.min()), int(by_year.index.max()) + 1))
        values, hover = [], []
        for year in years:
            if year not in by_year.index:
                values.append(None)
                hover.append(f"{ticker} FY{year}: no data")
                missing.append((ticker, year, "no data"))
                continue
            row = by_year.loc[year]
            values.append(_number(row["value"]))
            hover.append(f"{ticker} FY{year}, year ended {row['period_end']}: {row['text']}")
            if pd.isna(row["value"]):
                missing.append((ticker, year, row["text"]))
        year_ends.append(f"{ticker} {by_year.loc[years[-1], 'period_end']}")

        colour, dash, symbol = LINE_STYLES[i % len(LINE_STYLES)]
        fig.add_trace(
            go.Scatter(
                x=years, y=values, name=ticker,
                mode="lines+markers", connectgaps=False,
                line={"color": colour, "dash": dash, "width": 2},
                marker={"symbol": symbol, "size": 9},
                hovertext=hover, hoverinfo="text",
            )
        )

    _add_note(fig, f"Fiscal year-end dates differ by company (latest: {', '.join(year_ends)})", y=-0.18)
    note = _missing_note(missing)
    if note:
        _add_note(fig, note, y=-0.26)
    fig.update_layout(
        title={"text": TREND_TITLE},
        template="plotly_white",
        height=460,
        margin={"l": 10, "r": 30, "t": 80, "b": 120},
        xaxis={"title": {"text": "Fiscal year"}, "dtick": 1, "tickformat": "d"},
        yaxis={
            "title": {"text": _axis_title(rows)},
            "zeroline": True, "zerolinewidth": 2, "zerolinecolor": "#404040",
            "rangemode": "tozero",
        },
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0},
    )
    if sample:
        _add_sample_mark(fig)
    return fig
