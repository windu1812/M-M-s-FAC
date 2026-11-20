"""CreditLens dashboard: the Streamlit entry point.

Run it from the app/ folder:
    .venv/bin/python -m streamlit run streamlit_app.py

This file only draws the page. Data access, ratios, flags and display-ready
values live in the creditlens package (see docs/architecture.md); this file
must never compute, round or fill in a financial number.

Walking skeleton (slice 1): the page, the ticker field and the Run button.
The credit screen itself arrives with slices 2 to 6 (docs/plan.md).
"""

import streamlit as st

st.set_page_config(page_title="CreditLens", layout="wide")

st.title("CreditLens")
st.caption("5-year credit screen of US companies, from their 10-K filings on SEC EDGAR.")

st.text_input(
    "Tickers (1 to 5 US companies, separated by commas)",
    placeholder="AAPL, MSFT, NKE",
    key="tickers",
)
run_clicked = st.button("Run", type="primary", key="run")

if run_clicked:
    st.info("The credit screen is not built yet. It arrives with slices 2 to 6 of docs/plan.md.")
else:
    st.markdown("Enter 1 to 5 US tickers, for example **AAPL, MSFT, NKE**, then click **Run**.")

st.caption("Source: SEC EDGAR XBRL company facts (free public data).")
