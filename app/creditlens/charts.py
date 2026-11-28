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

# The words agreed in docs/product.md. A Plotly title never wraps, so the long one has its own line break (it fits on
# a phone).
COMPARISON_TITLE = "How do the companies compare<br>in the latest fiscal year?"
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

# Colour carries meaning only for the flags (docs/product.md, "Visual reference"); the same tones as the cards
# (app/style.css). A bar also writes its flag as a word, so colour is never the only sign.
FLAG_COLOURS = {"green": "#1e8e3e", "orange": "#c25e00", "red": "#d70015"}
NO_FLAG_COLOUR = "#8e8e93"

# Company lines: one hue per company, in a fixed order, with no green, orange or red (reserved for the flags).
# The order was checked with a colour-blindness validator (adjacent pairs: CVD ΔE ≥ 11.8, normal vision ≥ 23.8).
# Dashes and markers differ too, and each line ends with its ticker, so a line is never told apart by colour alone.
LINE_STYLES = [
    ("#257de0", "solid", "circle"),
    ("#ee7fac", "dash", "square"),
    ("#6a4ce2", "dot", "diamond"),
    ("#00b894", "dashdot", "triangle-up"),
    ("#f2a600", "longdash", "x"),
]
MAX_DIRECT_LABELS = 4  # with 5 companies the end labels would crowd: the legend names them

# The look shared by both charts: the page's system font, quiet grid and axes, text in text colours.
FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif'
TEXT_COLOUR = "#1d1d1f"
MUTED_COLOUR = "#6e6e73"
GRID_COLOUR = "#eceef2"
ZERO_LINE_COLOUR = "#8e8e93"
BAR_CORNER_RADIUS = 6  # pixels: rounded bar ends

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


def no_value_text(display: pd.DataFrame, metric: str) -> str:
    """A sentence for the page when no company has a number for ``metric``: both charts would be empty
    (for example NKE alone with Net debt / EBITDA, as NKE reports no operating income). "" otherwise."""
    rows = _rows_for(display, metric)
    if rows["value"].notna().any():
        return ""
    return (f"No company shown has a value for {rows.iloc[0]['label']}, so there is no bar or point to draw: "
            "the reasons are written under each chart. To compare the companies, choose another ratio.")


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
        xref="paper", yref="paper", x=1, y=1.2,  # in the title margin, clear of the threshold labels
        xanchor="right", yanchor="bottom", showarrow=False,
        font={"size": 16, "color": "#c62828"},
    )


NOTE_LINE_HEIGHT = 15  # pixels per line of a note under the trend chart


def _add_note(fig: go.Figure, text: str, below_plot: int) -> None:
    """A grey note under the plot, ``below_plot`` pixels under its bottom edge (pixels, so it never overlaps the
    axis title, whatever the height of the chart)."""
    fig.add_annotation(
        text=text,
        xref="paper", yref="paper", x=0, y=0, yshift=-below_plot,
        xanchor="left", yanchor="top", align="left", showarrow=False,
        font={"size": 11, "color": MUTED_COLOUR},
    )


def _add_thresholds(fig: go.Figure, metric: str, unit: str, thresholds: dict | None, vertical: bool = True,
                    within: tuple[float, float] | None = None) -> None:
    """Draw the green and orange limits of the metric as dotted reference lines in their flag colour: vertical on
    the bar chart (values along x), horizontal on the trend chart (values along y). The label is in text colour.
    ``within`` (low, high): draw only the limits inside it, so a far limit does not flatten the data."""
    rule = (thresholds or {}).get(metric.removesuffix(INCL_LEASES))
    if rule is None:
        return
    sign = "≤" if rule["direction"] == "lower_is_better" else "≥"
    number_format = THRESHOLD_FORMATS.get(unit, "{}")
    limits = [rule.get(c) for c in ("green", "orange") if rule.get(c) is not None]
    for colour in ("green", "orange"):
        limit = rule.get(colour)
        if limit is None or (within and not within[0] <= limit <= within[1]):
            continue
        # the two labels lean away from each other (the lower limit's to the left), so they never overlap
        side = "left" if len(limits) == 2 and limit == min(limits) else "right"
        line = {"color": FLAG_COLOURS[colour], "dash": "dot", "width": 1.5}
        label = {"annotation_text": f"{colour} {sign} {number_format.format(limit)}",
                 "annotation_font": {"color": MUTED_COLOUR, "size": 11}}
        if vertical:
            fig.add_vline(x=limit, line=line, annotation_position=f"top {side}", layer="below", **label)
        else:
            fig.add_hline(y=limit, line=line, annotation_position="top left", layer="below", **label)


def _style(fig: go.Figure, title: str) -> None:
    """The shared look: system font, title on the left, transparent background (the page's white panel shows),
    light grid, axis text in muted grey, white tooltips."""
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 16, "color": TEXT_COLOUR}},
        template="plotly_white",
        font={"family": FONT_FAMILY, "color": TEXT_COLOUR, "size": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "#ffffff", "bordercolor": "#d2d2d7",
                    "font": {"family": FONT_FAMILY, "color": TEXT_COLOUR, "size": 12}},
    )
    axis = {"gridcolor": GRID_COLOUR, "linecolor": GRID_COLOUR, "tickfont": {"color": MUTED_COLOUR},
            "title": {"font": {"color": MUTED_COLOUR, "size": 12}}, "zerolinecolor": ZERO_LINE_COLOUR}
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)


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
            # the value and its flag as a word ("2.40x · orange"); no text for a missing value (its "n/a" note says why)
            text=[(f"{r.text} · {r.flag}" if isinstance(r.flag, str) and r.flag else r.text)
                  if pd.notna(r.value) else "" for r in ordered.itertuples()],
            textposition="outside",
            textfont={"color": TEXT_COLOUR, "size": 12},
            cliponaxis=False,  # keep the minus sign of a negative value visible
            marker={"color": [_flag_colour(f) for f in ordered["flag"]], "cornerradius": BAR_CORNER_RADIUS,
                    "line": {"width": 0}},
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
                xanchor="left", showarrow=False, font={"color": MUTED_COLOUR, "size": 11},
            )

    unit = rows.iloc[0]["unit"]
    _add_thresholds(fig, metric, unit, thresholds)
    _style(fig, COMPARISON_TITLE)
    fig.update_layout(
        height=180 + 60 * len(labels),
        margin={"l": 10, "r": 30, "t": 80, "b": 50},
        bargap=0.45,  # slim bars, room to read
        xaxis={
            "title": {"text": _axis_title(rows)},
            "zeroline": True, "zerolinewidth": 1.5,
            "rangemode": "tozero",
        },
        yaxis={"autorange": "reversed", "showgrid": False, "tickfont": {"color": TEXT_COLOUR}},
    )
    if sample:
        _add_sample_mark(fig)
    return fig


def _missing_note(missing: list[tuple[str, int, str]]) -> str | None:
    """One "n/a" note for the points not drawn: one line per ticker and reason, with the years."""
    if not missing:
        return None
    groups: dict[tuple[str, str], list[int]] = {}
    for ticker, year, reason in missing:
        groups.setdefault((ticker, reason), []).append(year)
    parts = [
        f"{ticker} {', '.join(f'FY{y}' for y in years)} ({reason})"
        for (ticker, reason), years in groups.items()
    ]
    return "n/a (not drawn):<br>" + "<br>".join(parts)


def trend_line_chart(display: pd.DataFrame, metric: str, sample: bool = False,
                     thresholds: dict | None = None) -> go.Figure:
    """One line with markers per company, over its fiscal years.

    Args:
        display: the display table (see the module docstring).
        metric: the metric to show, for example ``"net_debt_to_ebitda"``.
        sample: True adds a "SAMPLE DATA" mark (synthetic data).
        thresholds: the rules of flags.load_thresholds(); the green and orange
            limits are drawn as horizontal reference lines. None draws no line.

    Each company covers only its own years, from its first to its last one in
    the table. A year without a value, or missing from the table, is a gap:
    the line is not joined across it, and a note lists it as "n/a".
    """
    rows = _rows_for(display, metric)
    fig = go.Figure()
    missing: list[tuple[str, int, str]] = []
    year_ends = []
    end_labels = []  # (ticker, year, value, text) of each company's last drawn point
    all_years: list[int] = []

    for i, (ticker, company_rows) in enumerate(rows.groupby("ticker", sort=False)):
        by_year = company_rows.set_index("fiscal_year")
        years = list(range(int(by_year.index.min()), int(by_year.index.max()) + 1))
        all_years += years
        values, hover = [], []
        last_drawn = None
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
            else:
                last_drawn = (ticker, year, float(row["value"]), row["text"])
        year_ends.append(f"{ticker} {by_year.loc[years[-1], 'period_end']}")
        if last_drawn:
            end_labels.append(last_drawn)

        colour, dash, symbol = LINE_STYLES[i % len(LINE_STYLES)]
        fig.add_trace(
            go.Scatter(
                x=years, y=values, name=ticker,
                mode="lines+markers", connectgaps=False,
                line={"color": colour, "dash": dash, "width": 2.5},
                marker={"symbol": symbol, "size": 9, "line": {"color": "#ffffff", "width": 2}},  # white ring
                hovertext=hover, hoverinfo="text",
            )
        )

    if len(fig.data) <= MAX_DIRECT_LABELS:  # each line ends with its ticker and value, in text colour
        for ticker, year, value, text in end_labels:
            fig.add_annotation(x=year, y=value, text=f"{ticker} {text}", xanchor="left", xshift=10,
                               showarrow=False, font={"color": TEXT_COLOUR, "size": 12})

    # Limits are drawn only near the data (from 0 or the lowest value to 1.25 x the highest): a far limit would
    # stretch the axis and flatten the lines, hiding how the ratio moved. The bar chart always shows them.
    drawn = rows["value"].dropna()
    if not drawn.empty:
        low, high = min(0.0, float(drawn.min())), float(drawn.max())
        within = (low - 0.25 * abs(low), high + 0.25 * abs(high))
        _add_thresholds(fig, metric, rows.iloc[0]["unit"], thresholds, vertical=False, within=within)

    _add_note(fig, f"Fiscal year-end dates differ by company (latest: {', '.join(year_ends)})", below_plot=50)
    note = _missing_note(missing)
    note_lines = note.count("<br>") + 1 if note else 0
    if note:
        _add_note(fig, note, below_plot=50 + NOTE_LINE_HEIGHT + 6)
    bottom = 50 + NOTE_LINE_HEIGHT * (1 + note_lines) + 16  # axis title, then the notes, each on its own line
    _style(fig, TREND_TITLE)
    fig.update_layout(
        height=100 + 300 + bottom,  # title and legend, a 300 px plot, the notes
        margin={"l": 10, "r": 90, "t": 100, "b": bottom},  # top: a legend on two lines (phone) stays under the title  # room on the right for the end labels
        # the real years only: without a fixed range Plotly widens the axis to fit the end labels (to FY2032 on a
        # phone), which squeezed the lines
        xaxis={"title": {"text": "Fiscal year"}, "dtick": 1, "tickformat": "d", "showgrid": False,
               "range": [min(all_years) - 0.25, max(all_years) + 0.25]},
        yaxis={
            "title": {"text": _axis_title(rows)},
            "zeroline": True, "zerolinewidth": 1.5,
            "rangemode": "tozero",
        },
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0, "font": {"color": TEXT_COLOUR}},
        hovermode="x unified",  # one tooltip per fiscal year with every company
    )
    if sample:
        _add_sample_mark(fig)
    return fig
