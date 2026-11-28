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

The charts and the "Download Excel" button (slice 6, François) go in the place
marked "Slice 6" below; they read ``display_tbl``, ``underlying``, ``alerts``
and ``thresholds``.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from creditlens import display, flags
from creditlens.data import financials as fin
from creditlens.data import sec_client
from creditlens.ratios import compute_ratios

# One title per error of the data part; the message of the error follows it (V3, AC3, E8-E10).
ERROR_TITLES = {
    sec_client.TickerNotFoundError: "Ticker not found",
    sec_client.SecUnavailableError: "SEC EDGAR unreachable",
    sec_client.SecConfigError: "Settings missing",
    fin.NoAnnualDataError: "No annual 10-K data for {ticker}",
}
DATA_ERRORS = tuple(ERROR_TITLES)

# Colours of the alert line and of the table cells: colour is used only for the flags.
ALERT_COLOURS = {"green": "green", "orange": "orange", "red": "red", "": "gray"}
CELL_COLOURS = {"green": "#C8E6C9", "orange": "#FFE0B2", "red": "#FFCDD2"}  # the same as the Excel file

TABLE_ROW_HEIGHT = 35  # pixels, so the whole table shows without its own scroll bar


def escape(text: str) -> str:
    """Show a text as it is, even if it holds Markdown signs (a company name with '*', for example)."""
    for sign in "\\`*_[]<>#|~$":
        text = text.replace(sign, "\\" + sign)
    return text


# --- Fetching -------------------------------------------------------------------------------


def fetch(tickers: list[str]) -> dict:
    """Get the 10-K data of each ticker; an error stops only its own ticker (V3)."""
    data, errors = {}, {}
    with st.status(f"Fetching {len(tickers)} compan{'y' if len(tickers) == 1 else 'ies'} "
                   "from SEC EDGAR...", expanded=True) as status:
        for ticker in tickers:
            st.write(f"Fetching {ticker} from SEC EDGAR...")
            try:
                company = fin.get_financials(ticker)
                compute_ratios(company)  # a data problem (an amount not in USD) stops this ticker only
            except DATA_ERRORS as error:
                errors[ticker] = (ERROR_TITLES[type(error)].format(ticker=ticker), str(error))
                continue
            except ValueError as error:
                errors[ticker] = ("Data problem", str(error))
                continue
            data[ticker] = company
        status.update(label=f"Fetched {len(data)} of {len(tickers)} from SEC EDGAR", state="complete",
                      expanded=False)
    return {"tickers": tickers, "financials": data, "errors": errors, "cache_dates": cache_dates(list(data))}


def cache_dates(tickers: list[str]) -> dict[str, list[str]]:
    """Date each company file was saved in the local cache -> tickers (E7)."""
    dates: dict[str, list[str]] = {}
    for ticker in tickers:
        try:
            path = sec_client.CACHE_DIR / f"CIK{sec_client.get_cik(ticker)}.json"
            saved = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        except (OSError, *DATA_ERRORS):
            continue
        dates.setdefault(saved, []).append(ticker)
    return dates


# --- Drawing --------------------------------------------------------------------------------


def draw_card(card: display.Card) -> None:
    with st.container(border=True):
        st.markdown(f"**{escape(card.company)}**")
        st.caption(f"{card.ticker} · FY{card.fiscal_year}, year ended {card.period_end}")
        colour = ALERT_COLOURS.get(card.alert_level, "gray")
        st.markdown(f":{colour}-background[:{colour}[**{escape(card.alert_text)}**]]")  # wraps, never cut
        for h in card.headlines:
            flag = f" · :{h.flag}[{h.flag}]" if h.flag else ""
            st.markdown(f"{escape(h.label)} ({escape(h.unit)})  \n**{escape(h.shown)}**{flag}")
            details = [escape(part) for part in (h.note, h.change) if part]
            if details:
                st.caption(" · ".join(details))


def coloured_table(table: pd.DataFrame, colours: pd.DataFrame):
    """The ratio table with each fiscal-year cell in its flag colour (the word is in "Latest flag")."""

    def css(flag: str) -> str:
        colour = CELL_COLOURS.get(flag)
        return f"background-color: {colour}; color: #1a1a1a" if colour else ""

    return table.style.apply(lambda _: colours.map(css), axis=None)


def draw_underlying(underlying: pd.DataFrame) -> None:
    shown = underlying.rename(columns={
        "ticker": "Ticker", "fiscal_year": "Fiscal year", "period_end": "Year end", "label": "Item",
        "text": "Value (USD m)", "xbrl_tag": "XBRL tag", "accession": "10-K accession",
    })[["Ticker", "Fiscal year", "Year end", "Item", "Value (USD m)", "XBRL tag", "10-K accession"]]
    st.dataframe(shown, hide_index=True, width="stretch", key="underlying_table")


# --- The page ------------------------------------------------------------------------------

st.set_page_config(page_title="CreditLens", layout="wide")

st.title("CreditLens")
st.caption("5-year credit screen of US companies, from their 10-K filings on SEC EDGAR.")

input_column, debt_column = st.columns([3, 2], vertical_alignment="bottom")
with input_column:
    st.text_input(
        "Tickers (1 to 5 US companies, separated by commas)",
        placeholder="AAPL, MSFT, NKE",
        key="tickers",
    )
with debt_column:
    incl_leases = st.radio(
        "Debt definition",
        options=[False, True],
        format_func=display.DEBT_DEFINITIONS.get,
        horizontal=True,
        key="incl_leases",
        help="Including leases and short-term borrowings adds commercial paper and lease liabilities to debt.",
    )
run_clicked = st.button("Run", type="primary", key="run")

if run_clicked:
    tickers, input_error = display.parse_tickers(st.session_state["tickers"])
    if input_error:
        st.session_state.pop("result", None)
        st.error(input_error)  # nothing is downloaded (AC2)
    else:
        st.session_state["result"] = fetch(tickers)

result = st.session_state.get("result")

if result is None:
    if not run_clicked:
        st.markdown("Enter 1 to 5 US tickers, for example **AAPL, MSFT, NKE**, then click **Run**.")
else:
    for ticker, (title, message) in result["errors"].items():
        st.error(f"**{escape(ticker)}: {escape(title)}.** {escape(message)}")

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
        for column, ticker in zip(st.columns(display.MAX_TICKERS), alerts):  # same card width for 1 to 5
            with column:
                draw_card(display.summary_card(display_tbl, ticker, alerts[ticker], incl_leases))

        for saved, cached in result["cache_dates"].items():
            st.caption(f"Data from SEC EDGAR, saved in the local cache on {saved} ({', '.join(cached)}).")

        # Slice 6 (François): the two charts and the "Download Excel" button go here.

        # Table "Credit ratios, last 5 fiscal years" (visual 4).
        st.subheader("Credit ratios, last 5 fiscal years")
        st.caption(f"Debt definition: {display.DEBT_DEFINITIONS[incl_leases]}. Cell colours are the flags; "
                   "\"Latest flag\" gives the flag of each company's latest fiscal year as a word, with the year "
                   "when it is not the last column. Fiscal year-end dates differ by company. "
                   + display.left_out_years_text(display_tbl))
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
