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
    with st.status(f"Loading {plural(len(tickers), 'company')} from SEC EDGAR or the local cache...",
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


def draw_card(card: display.Card) -> None:
    with st.container(border=True):
        # :small[] keeps the normal text colour (a caption is grey and too pale for required content)
        st.markdown(f"**{escape(card.company)}**  \n"
                    f":small[{card.ticker} · FY{card.fiscal_year}, year ended {card.period_end}]")
        colour = ALERT_COLOURS.get(card.alert_level, "gray")
        st.markdown(f":{colour}-background[:{colour}[**{escape(card.alert_text)}**]]  \n"  # wraps, never cut
                    f":small[{escape(card.alert_note)}]")
        for h in card.headlines:
            flag = f" · :{h.flag}[{h.flag}]" if h.flag else ""
            st.markdown(f"{escape(h.label)} ({escape(h.unit)})  \n**{escape(h.shown)}**{flag}")  # V1: a unit
            details = [escape(part) for part in (h.note, h.change) if part]
            if details:
                st.markdown(f":small[{' · '.join(details)}]")


def coloured_table(table: pd.DataFrame, colours: pd.DataFrame):
    """The ratio table with each fiscal-year cell in its flag colour (the word is in "Latest flag")."""
    return table.style.apply(lambda _: colours.map(display.cell_style), axis=None)


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

st.title("CreditLens")
st.caption("5-year credit screen of US companies, from their 10-K filings on SEC EDGAR.")

input_column, debt_column = st.columns([3, 2], vertical_alignment="bottom")
with input_column:
    # A form, so that Enter in the field runs the screen like the Run button does.
    with st.form("ticker_form", border=False):
        st.text_input(
            "Tickers (1 to 5 US companies, separated by commas)",
            placeholder="AAPL, MSFT, NKE",
            key="tickers",
        )
        run_clicked = st.form_submit_button("Run", type="primary", key="run")
with debt_column:  # outside the form: switching it redraws at once, without Run
    incl_leases = st.radio(
        "Debt definition",
        options=[False, True],
        format_func=display.DEBT_DEFINITIONS.get,
        horizontal=True,
        key="incl_leases",
        help="Including leases and short-term borrowings adds commercial paper and lease liabilities to debt.",
    )

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
        st.markdown("Enter 1 to 5 US tickers, for example **AAPL, MSFT, NKE**, then click **Run** "
                    "(or press Enter).")
else:
    st.markdown(f"Results for: **{escape(', '.join(result['tickers']))}** "
                "(change the tickers and click Run to update)")
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

        # Summary cards: up to 5 in one row (visual 1).
        st.header("Summary")
        for column, ticker in zip(st.columns(display.MAX_TICKERS), alerts):  # same card width for 1 to 5
            with column:
                draw_card(display.summary_card(display_tbl, ticker, alerts[ticker], incl_leases, thresholds))

        for saved, cached in result["cache_dates"].items():
            st.caption(f"Data from SEC EDGAR, saved in the local cache on {saved} ({', '.join(cached)}).")

        # Slice 6 (François): the two charts and the "Download Excel" button (visuals 2, 3 and 5).
        # charts.py draws and export.py writes the values of display_tbl; nothing is computed here.
        st.header("Charts")
        chart_ratio = st.selectbox(
            "Ratio shown in the charts",
            options=charts.CHART_RATIOS,
            format_func=display.metric_label,
            key="chart_ratio",
        )
        chart_metric = display.selected_metric(chart_ratio, incl_leases)  # follows the debt definition
        st.plotly_chart(charts.comparison_bar_chart(display_tbl, chart_metric, thresholds),
                        width="stretch", key="comparison_chart")
        st.plotly_chart(charts.trend_line_chart(display_tbl, chart_metric), width="stretch", key="trend_chart")

        today = date.today().isoformat()
        st.download_button(
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
        )

        # Table "Credit ratios, last 5 fiscal years" (visual 4).
        st.header("Credit ratios, last 5 fiscal years")
        st.caption(display.table_caption(display_tbl, incl_leases))
        table, colours = display.ratio_table(display_tbl, incl_leases)
        st.dataframe(
            coloured_table(table, colours),
            hide_index=True,
            width="stretch",
            height=TABLE_ROW_HEIGHT * (len(table) + 1) + 3,
            column_order=[c for c in table.columns if c != "Company"],  # the cards give the names
            column_config={"Notes": st.column_config.TextColumn(width="large")},
            key="ratio_table",
        )

        with st.expander("View underlying data"):
            st.caption("Input figures from the 10-K, in USD m, with the XBRL tag and the 10-K accession number.")
            draw_underlying(underlying)

st.caption("Source: SEC EDGAR XBRL company facts (free public data).")
