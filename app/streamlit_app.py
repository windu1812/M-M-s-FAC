"""CreditLens dashboard: the Streamlit entry point (slice 5, issue #8).

Run it from the app/ folder:
    .venv/bin/python -m streamlit run streamlit_app.py

This file only draws the page. Data access, ratios, flags and display-ready
values live in the creditlens package (see docs/architecture.md); this file
never computes, rounds or fills in a financial number: it shows the values of
creditlens/display.py.

Journey (docs/product.md): type 1 to 5 tickers, click Run, read the summary
cards, the ratio table and the underlying data. The debt definition selector
switches every debt-based number without downloading again.

The charts and the "Download Excel" button (slice 6, François) are in the part
marked "Slice 6" below; they read ``display_tbl``, ``underlying``, ``alerts``
and ``thresholds``.
"""

from __future__ import annotations

from datetime import date

from pathlib import Path

import pandas as pd
import streamlit as st

from creditlens import charts, display, export, flags
from creditlens.data import financials as fin
from creditlens.data import sec_client
from creditlens.ratios import compute_ratios

# One title per error of the data part; the message of the error follows it (V3, AC3, E8-E10).
ERROR_TITLES = {
    sec_client.TickerNotFoundError: "Ticker not found",
    sec_client.SecUnavailableError: "SEC EDGAR unreachable",
    sec_client.SecConfigError: "Settings missing",
    sec_client.NoFinancialDataError: "No financial data on SEC EDGAR",
    sec_client.CacheFileError: "Damaged cache file",
    fin.NoAnnualDataError: "No annual 10-K data",
}
DATA_ERRORS = tuple(ERROR_TITLES)

# Colours of the alert line and of the table cells: colour is used only for the flags.
ALERT_COLOURS = {"green": "green", "orange": "orange", "red": "red", "": "gray"}

TABLE_ROW_HEIGHT = 35  # pixels, so the whole table shows without its own scroll bar
SCROLLBAR_ROOM = 16  # pixels under the last row: the wide Notes column scrolls sideways (bar shown on Windows)
STYLE_FILE = Path(__file__).with_name("style.css")  # the look of the page (fonts, cards, hidden Streamlit controls)
EXAMPLE_TICKERS = "AAPL, MSFT, NKE"  # the demo companies, kept in the local cache
# Section headings and their anchors; the links of the top bar (short words, so they fit on a phone) jump to them.
SECTIONS = {"summary": "Summary", "charts": "Charts", "ratios": "Credit ratios, last 5 fiscal years"}
NAV_LINKS = {"summary": "Summary", "charts": "Charts", "ratios": "Ratios"}
PLOTLY_CONFIG = {"displayModeBar": False}  # no Plotly toolbar over the charts
EMPTY_CELL = "–"  # a cell left empty on purpose (no XBRL tag for an item that is not reported)


def escape(text: str) -> str:
    """Show a text as it is, even if it holds Markdown signs (a company name with '*', for example)."""
    for sign in "\\`*_[]<>#|~$":
        text = text.replace(sign, "\\" + sign)
    return text


# --- Fetching -------------------------------------------------------------------------------


def plural(count: int, word: str) -> str:
    """ "1 error", "2 errors", "1 company", "2 companies"."""
    if count == 1:
        return f"1 {word}"
    return f"{count} {word[:-1]}ies" if word.endswith("y") else f"{count} {word}s"


def fetch(tickers: list[str]) -> dict:
    """Get the 10-K data of each ticker; an error stops only its own ticker (V3)."""
    data, errors = {}, {}
    box = st.empty()  # the progress box: removed after a clean run, kept when something failed
    with box.status(f"Loading {plural(len(tickers), 'company')} from SEC EDGAR or the local cache...",
                    expanded=True) as status:
        for ticker in tickers:
            st.write(f"Fetching {ticker} from SEC EDGAR...")
            try:
                company = fin.get_financials(ticker)
                compute_ratios(company)  # a data problem (an amount not in USD) stops this ticker only
            except DATA_ERRORS as error:
                errors[ticker] = (ERROR_TITLES[type(error)], str(error))
                continue
            except ValueError as error:
                errors[ticker] = ("Data problem", str(error))
                continue
            except Exception as error:  # noqa: BLE001 - broad on purpose: one ticker must never stop the page (V3)
                errors[ticker] = ("Unexpected problem", f"{type(error).__name__}: {error}")
                continue
            data[ticker] = company
        label = f"Loaded {len(data)} of {plural(len(tickers), 'company')}"
        if errors:
            label += f"; {plural(len(errors), 'error')} (see below)"
        status.update(label=label, state="complete" if data else "error", expanded=False)
    if not errors:
        box.empty()  # every company loaded: the "Results for" line says it, and the cards move up
    return {"tickers": tickers, "financials": data, "errors": errors, "cache_dates": cache_dates(list(data))}



def cache_dates(tickers: list[str]) -> dict[str, list[str]]:
    """Date each company file was saved in the local cache -> tickers (E7); read by the data part."""
    dates: dict[str, list[str]] = {}
    for ticker in tickers:
        saved = sec_client.cache_saved_on(ticker)
        if saved:
            dates.setdefault(saved, []).append(ticker)
    return dates


# --- Drawing --------------------------------------------------------------------------------


def top_bar(with_links: bool) -> str:
    """The fixed bar at the top of the page (fixed text of the project, no user input in it)."""
    if with_links:
        right = "".join(f'<a href="#{anchor}" target="_self">{word}</a>' for anchor, word in NAV_LINKS.items())
    else:
        right = '<span class="cl-tag">SEC EDGAR · 10-K data</span>'
    return ('<nav class="cl-nav" aria-label="CreditLens"><div class="cl-brand"><span class="cl-logo" aria-hidden="true">'
            f'C</span>CreditLens</div><div class="cl-links">{right}</div></nav>')


EMPTY_STATE_TILES = (  # what the screen gives, shown before the first run (fixed text, no user input)
    '<div class="cl-features">'
    '<div class="cl-feature"><div class="cl-dots" aria-hidden="true"><i style="background:#1e8e3e"></i>'
    '<i style="background:#c25e00"></i><i style="background:#d70015"></i></div>'
    "<b>Six credit ratios, flagged</b><span>Leverage, coverage, liquidity, margin and free cash flow, each green, "
    "orange or red against the agreed limits.</span></div>"
    '<div class="cl-feature"><div class="cl-dots" aria-hidden="true"><i style="background:#0071e3"></i>'
    '<i style="background:#5e5ce6"></i></div>'
    "<b>Five fiscal years, side by side</b><span>Compare up to 5 companies and see how each ratio moved, from the "
    "10-K filings on SEC EDGAR.</span></div>"
    '<div class="cl-feature"><div class="cl-dots" aria-hidden="true"><i style="background:#8e8e93"></i></div>'
    "<b>Every number traceable</b><span>XBRL tag and 10-K accession for each input, and an Excel file with the "
    "values on screen.</span></div>"
    "</div>"
)


def use_example() -> None:
    """The "Try AAPL, MSFT, NKE" button: fill in the tickers and run, before the page is drawn again."""
    st.session_state["tickers"] = EXAMPLE_TICKERS
    st.session_state["run_example"] = True


def draw_card(card: display.Card) -> None:
    # A keyed container: style.css draws it as a grey tile with a line of the alert colour on top
    # (class st-key-card_<level>_<ticker>; the alert word is written on the card too).
    with st.container(key=f"card_{card.alert_level or 'na'}_{card.ticker}", gap="xsmall"):
        # :small[] keeps the normal text colour (a caption is grey and too pale for required content)
        st.markdown(f"**{escape(card.company)}**  \n"
                    f":small[{card.ticker} · FY{card.fiscal_year}, year ended {card.period_end}]")
        colour = ALERT_COLOURS.get(card.alert_level, "gray")
        st.markdown(f":{colour}-background[:{colour}[**{escape(card.alert_text)}**]]  \n"  # wraps, never cut
                    f":small[{escape(card.alert_note)}]")
        for h in card.headlines:
            flag = f" · :{h.flag}[{h.flag}]" if h.flag else ""
            line = f"{escape(h.label)} ({escape(h.unit)}): **{escape(h.shown)}**{flag}"  # one line; V1: a unit
            details = [escape(part) for part in (h.note, h.change) if part]
            if details:
                line += f"  \n:small[{' · '.join(details)}]"  # the note and the change, just under it
            st.markdown(line)


def coloured_table(table: pd.DataFrame, colours: pd.DataFrame):
    """The ratio table with each fiscal-year cell in its flag colour (the word is in "Latest flag")."""
    return table.style.apply(lambda _: colours.map(display.cell_style), axis=None)


YEAR_COLUMN_WIDTH = 112  # pixels: "not available" fits in a fiscal-year column
NOTE_CHAR_WIDTH = 7  # pixels per character of a note, about, at the table's font size


def ratio_table_columns(table: pd.DataFrame) -> dict:
    """Column sizes of the ratio table: every fiscal-year cell readable, every note shown in full (the table then
    scrolls sideways inside its own box), and the ticker and metric kept in view while it scrolls."""
    lengths = table["Notes"].fillna("").str.len() if "Notes" in table else pd.Series(dtype=int)
    longest_note = int(lengths.max()) if len(lengths) else 0  # an empty table has no longest note
    columns = {year: st.column_config.Column(width=YEAR_COLUMN_WIDTH) for year in table.columns
               if str(year).startswith("FY")}
    columns["Ticker"] = st.column_config.Column(pinned=True)
    columns["Metric"] = st.column_config.Column(pinned=True)
    columns["Notes"] = st.column_config.TextColumn(width=max(400, NOTE_CHAR_WIDTH * longest_note + 32))
    return columns


def draw_underlying(underlying: pd.DataFrame) -> None:
    """The input figures: the value is a number (it sorts and aligns as one); an item that is not
    reported has an empty value, the status "not reported" and "–" for its tag and accession."""
    shown = underlying.assign(
        status=underlying["status"].map(lambda s: "reported" if s == display.STATUS_OK else "not reported"),
        xbrl_tag=underlying["xbrl_tag"].fillna(EMPTY_CELL),
        accession=underlying["accession"].fillna(EMPTY_CELL),
    ).rename(columns={
        "ticker": "Ticker", "fiscal_year": "Fiscal year", "period_end": "Year end", "label": "Item",
        "value": "Value (USD m)", "status": "Status", "xbrl_tag": "XBRL tag", "accession": "10-K accession",
    })[["Ticker", "Fiscal year", "Year end", "Item", "Value (USD m)", "Status", "XBRL tag", "10-K accession"]]
    st.dataframe(
        shown,
        hide_index=True,
        width="stretch",
        column_config={
            "Value (USD m)": st.column_config.NumberColumn(format="%,d"),  # "1,234", as in the 10-K
            "Fiscal year": st.column_config.NumberColumn(format="%d"),  # "2026", not "2,026"
        },
        key="underlying_table",
    )


# --- The page ------------------------------------------------------------------------------

st.set_page_config(page_title="CreditLens", layout="wide")
# The page's own style sheet (a file of the project, no user text in it, so HTML is safe here).
st.markdown(f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

nav = st.empty()  # the top bar: its links are added once there are results (below)
nav.markdown(top_bar(with_links=False), unsafe_allow_html=True)

with st.container(key="hero", gap="xxsmall"):
    st.markdown('<span class="cl-eyebrow">Credit screen</span>', unsafe_allow_html=True)
    st.title("CreditLens", anchor=False)
    st.caption("5-year credit screen of US companies, from their 10-K filings on SEC EDGAR.")

# The search panel, one row: the tickers, Run and the debt definition, aligned, so the cards fit on the first
# screen. In a narrow window (phone) the columns go one under the other.
# A row that wraps, not fixed columns: when the window is too narrow for both groups, the debt definition goes under
# the field instead of squeezing it (fixed columns cut "Run" to "R..." at about 700 px). style.css sets the widths.
search = st.container(key="search", horizontal=True, wrap=True, gap="medium", vertical_alignment="top")
with search.container(key="search_tickers"):
    # A form, so that Enter in the field runs the screen like the Run button does.
    with st.form("ticker_form", border=False):
        with st.container(horizontal=True, vertical_alignment="bottom", gap="small", key="field_row"):
            st.text_input(
                "Tickers (1 to 5 US companies, separated by commas)",
                placeholder=f"e.g. {EXAMPLE_TICKERS}",  # "e.g.": the empty field must not look filled in
                key="tickers",
            )
            run_clicked = st.form_submit_button("Run", type="primary", key="run", width="content")  # never cut
with search.container(key="search_debt", width="content"):  # outside the form: redraws at once, without Run
    incl_leases = st.segmented_control(  # both choices visible, the same height as the ticker field
        "Debt definition",
        options=[False, True],
        format_func=display.DEBT_DEFINITIONS.get,
        default=False,
        required=True,  # one definition is always selected
        wrap=True,  # in a narrow window the second choice goes under the first, never cut off
        key="incl_leases",
        help="Including leases and short-term borrowings adds commercial paper and lease liabilities to debt.",
    )

run_clicked = run_clicked or st.session_state.pop("run_example", False)  # the example button
if run_clicked:
    tickers, input_error = display.parse_tickers(st.session_state["tickers"])
    if input_error:
        st.session_state.pop("result", None)
        st.error(escape(input_error))  # nothing is downloaded (AC2); shown as typed
    else:
        st.session_state["result"] = fetch(tickers)

result = st.session_state.get("result")

if result is None:
    if not run_clicked:
        with st.container(horizontal=True, vertical_alignment="center", gap="small", key="empty_state"):
            st.markdown("Enter 1 to 5 US tickers, for example **AAPL, MSFT, NKE**, then click **Run** "
                        "(or press Enter).", width="content")
            st.button(f"Try {EXAMPLE_TICKERS}", on_click=use_example, key="example", type="tertiary",
                      icon=":material/arrow_forward:")
        st.markdown(EMPTY_STATE_TILES, unsafe_allow_html=True)
else:
    # Two small lines under the inputs: what the results are, and where the data comes from (E7).
    with st.container(gap="xxsmall"):
        st.caption(f"Results for: **{escape(', '.join(result['tickers']))}** "
                   "(change the tickers and click Run to update)")
        for saved, cached in result["cache_dates"].items():
            st.caption(f"Data from SEC EDGAR, saved in the local cache on {saved} ({', '.join(cached)}).")
    for tickers, title, message in display.grouped_errors(result["errors"]):
        st.error(f"**{escape(', '.join(tickers))}: {escape(title)}.** {escape(message)}")

    if result["financials"]:
        try:
            thresholds = flags.load_thresholds()
        except ValueError as error:
            st.error(f"**The flag thresholds cannot be read.** {escape(str(error))}")
            st.stop()

        financials = pd.concat(result["financials"].values(), ignore_index=True)
        flagged = flags.apply_flags(compute_ratios(financials), thresholds)
        display_tbl = display.display_table(flagged, financials)
        underlying = display.underlying_table(financials)
        alerts = {t: flags.overall_alert(flagged, t, incl_leases) for t in result["financials"]}

        nav.markdown(top_bar(with_links=True), unsafe_allow_html=True)

        # Summary cards: up to 5 in one row (visual 1).
        st.header(SECTIONS["summary"], anchor="summary")
        # The cards share the row and wrap in a narrower window (style.css: about 16 rem each).
        with st.container(horizontal=True, wrap=True, gap="small", key="cards"):
            for ticker in alerts:
                draw_card(display.summary_card(display_tbl, ticker, alerts[ticker], incl_leases, thresholds))

        # Slice 6 (François): the two charts and the "Download Excel" button (visuals 2, 3 and 5).
        # charts.py draws and export.py writes the values of display_tbl; nothing is computed here.
        st.header(SECTIONS["charts"], anchor="charts")
        panel = st.container(key="panel_charts")
        tools = panel.container(horizontal=True, wrap=True, gap="small", key="chart_tools")  # selector and Excel
        chart_ratio = tools.selectbox(
            "Ratio shown in the charts",
            options=charts.CHART_RATIOS,
            format_func=display.metric_label,
            key="chart_ratio",
            width=320,
        )
        chart_metric = display.selected_metric(chart_ratio, incl_leases)  # follows the debt definition
        empty_charts = charts.no_value_text(display_tbl, chart_metric)
        if empty_charts:
            panel.info(empty_charts)  # an empty chart would look like a bug: say why
        # One under the other, full width: side by side, the "n/a (not drawn)" notes under the charts were cut off.
        panel.plotly_chart(charts.comparison_bar_chart(display_tbl, chart_metric, thresholds),
                           width="stretch", config=PLOTLY_CONFIG, key="comparison_chart")
        panel.plotly_chart(charts.trend_line_chart(display_tbl, chart_metric), width="stretch", config=PLOTLY_CONFIG,
                           key="trend_chart")

        today = date.today().isoformat()
        tools.download_button(
            "Download Excel",
            data=export.build_excel(
                display_tbl,
                underlying,
                {ticker: alert.text for ticker, alert in alerts.items()},
                generated_on=today,
                incl_leases=incl_leases,
                thresholds=thresholds,
            ),
            file_name=export.excel_filename(list(alerts), today),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            on_click="ignore",  # downloading does not redraw the page
            key="download_excel",
            help="Sheets Summary, Ratios (both debt definitions), Financials and Notes, with the values on screen.",
            icon=":material/download:",
        )

        # Table "Credit ratios, last 5 fiscal years" (visual 4).
        st.header(SECTIONS["ratios"], anchor="ratios")
        table_panel = st.container(key="panel_table")
        table_panel.caption(display.table_caption(display_tbl, incl_leases))
        table, colours = display.ratio_table(display_tbl, incl_leases)
        table_panel.dataframe(
            coloured_table(table, colours),
            hide_index=True,
            width="stretch",
            height=TABLE_ROW_HEIGHT * (len(table) + 1) + 3 + SCROLLBAR_ROOM,
            column_order=[c for c in table.columns if c != "Company"],  # the cards give the names
            column_config=ratio_table_columns(table),
            key="ratio_table",
        )

        with table_panel.expander("View underlying data", icon=":material/table_view:"):
            st.caption("Input figures from the 10-K, in USD m, with the XBRL tag and the 10-K accession number.")
            draw_underlying(underlying)

with st.container(key="footer"):
    st.markdown('<div class="cl-footer"></div>', unsafe_allow_html=True)
    st.caption("Source: SEC EDGAR XBRL company facts (free public data).")
