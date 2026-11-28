# M-M-s-FAC - CreditLens

CreditLens turns public SEC EDGAR filings into a 5-year credit screen (leverage, coverage, liquidity, cash flow) with
green / orange / red flags and an Excel export, for corporate bankers and credit analysts.

EDHEC Business School - Programming and AI for Corporate Finance (FIN_8546), final project 2026-2027.
Team: Arthur, Corentin, Maiwenn, Marc, François.

## What it does

1. Type 1 to 5 US tickers (for example `AAPL, MSFT, NKE`) and click **Run**.
2. The app gets the annual 10-K figures of the last 5 fiscal years from SEC EDGAR (or from the local cache).
3. It shows, for each company:
   - a summary card: Net debt / EBITDA, interest coverage and current ratio with their change vs the prior year,
     and an overall alert;
   - a 5-year ratio table, each cell coloured by its flag, with a "Latest flag" column in words;
   - "View underlying data": the input figures in USD m, with their XBRL tag and 10-K accession number.
4. Two charts compare the companies on one ratio: the latest fiscal year (bars) and 5 years (lines).
5. **Download Excel** gives a file with 4 sheets: Summary, Ratios (both debt definitions), Financials and Notes.

A selector switches total debt between **Financial debt only** (default) and **Including leases and short-term
borrowings**. Only the debt-based numbers change (total debt, net debt, Net debt / EBITDA, Debt / equity).

Formulas, rules and design decisions: `docs/product.md` and `docs/architecture.md`.

## Install

You need Python 3.12 and an internet connection for the first run. All commands are run from the `app/` folder.

macOS / Linux:

```bash
cd app
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Windows: see `app/README.md` (same steps with `py -3.12` and `.venv\Scripts\python`).

Then open `app/.env` and write your name and email after `SEC_USER_AGENT=`, for example
`SEC_USER_AGENT=First Last first.last@edhec.com`. The SEC refuses requests without it. Never commit `.env`.

## Run

```bash
cd app
.venv/bin/python -m streamlit run streamlit_app.py
```

Open http://localhost:8501. Stop the app with `Ctrl+C`. The app only accepts connections from this computer.

## Test

```bash
cd app
.venv/bin/python -m pytest
```

The tests never call the internet and do not need `.env` (390 tests passed on 2026-11-28). Revenue, total assets
and net income of the last 2 fiscal years are reconciled with the 10-K of AAPL, MSFT and NKE, page cited
(`app/tests/test_reconciliation_10k.py`).

Troubleshooting (damaged cache file, port already in use, wrong Python): `app/README.md`.

## Data

| Data | Source | Terms |
|---|---|---|
| Ticker → CIK list | `https://www.sec.gov/files/company_tickers.json` | Free public SEC data |
| Annual 10-K figures (XBRL) | `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` | Free public SEC data |

- The SEC requires a User-Agent with a name and an email, and at most 10 requests per second. The app respects both.
- Every downloaded file is saved in `app/cache/` (not committed). The next runs read the cache and work offline.
  The page shows the date each company file was saved.
- To get a newer 10-K, delete that company's file `app/cache/CIK##########.json` and click Run again.
- The fiscal year of a figure comes from its period `end` date, never from the `fy` field of the filing. Income
  statement and cash flow figures keep only periods of 350 to 380 days. When a period appears in several 10-Ks,
  the most recent filing wins.
- No number is invented or derived to fill a gap: a missing value is shown as "not available", with the reason.

## Flags

The thresholds are in `app/config/thresholds.toml` and can be changed without touching the code: save the file
and click Run again. The same thresholds apply to both debt definitions.

| Ratio | Green | Orange | Red |
|---|---|---|---|
| Net debt / EBITDA | ≤ 2.0x | ≤ 3.5x | above 3.5x |
| Debt / equity | ≤ 1.0x | ≤ 2.0x | above 2.0x |
| Interest coverage | ≥ 6.0x | ≥ 3.0x | below 3.0x |
| Current ratio | ≥ 1.5x | ≥ 1.0x | below 1.0x |
| EBITDA margin | ≥ 20 % | ≥ 10 % | below 10 % |
| Free cash flow | ≥ 0 | – | below 0 |

A value is compared as it is shown on screen (2 decimals for ratios, 1 for the margin); a value exactly on a limit
takes the better colour. The overall alert of a company is red if one ratio of its latest fiscal year
is red; otherwise "N/A" (not rated) if 3 or more of its 6 flagged ratios are "not available"; otherwise orange if one
is orange, otherwise green. Its text counts the ratios that are "not available" or "not meaningful".

## Known limitations

- **Several ratios are "not available" for the demo companies,** because the company does not tag the input in
  standard XBRL:
  - MSFT tags no total D&A: EBITDA, Net debt / EBITDA and EBITDA margin are not available;
  - NKE tags no operating income and no gross interest expense: EBITDA, Net debt / EBITDA, interest coverage and
    EBITDA margin are not available;
  - AAPL tags no interest expense after FY2023: interest coverage is not available for FY2024 to FY2026.

  The app shows the reason and does not estimate the value (team decision of 2026-11-20).
- **Net debt / EBITDA "including leases" is slightly conservative.** Lease liabilities are added to debt, but the
  operating lease cost, already deducted before EBITDA under US GAAP, is not added back as rating agencies do. The
  ratio is therefore a little higher than an agency's.
- **A part of debt that is not reported counts as zero** (for example no commercial paper), with the note
  "<part> not reported". Long-term debt (noncurrent) is required; without it every debt-based ratio is
  "not available".
- **The overall alert is rated with up to 2 missing ratios.** With 1 or 2 of the 6 "not available", the alert uses
  the others (MSFT: "Orange: 1 orange flag, 2 not available"); read the counts in the alert text. With 3 or more,
  the alert is "N/A" (NKE: "N/A: 3 not available, 3 green flags"), unless a red flag is known: red is always shown.
- **US companies with a 10-K only.** No quarterly data, no share prices, no forecasts.
- **Fiscal years are not calendar years.** Year-end dates differ by company (Apple ends in September, Microsoft in
  June, Nike in May). When they differ, the table keeps the 5 most recent fiscal years and says which older years
  are left out.
- **The first run needs the internet.** Without it and without a cached copy, the page shows "SEC EDGAR unreachable"
  for that ticker. Warm the cache before a demo by running the demo tickers once.
- **Best on a laptop.** The page adapts to the window width (cards wrap: 3 per row on a laptop, 1 on a phone),
  but the wide ratio table and the charts are easier to read on a screen of 1280 px or more. The ratio table shows
  every note in full: scroll it sideways inside its box (Ticker and Metric stay in view).

## Repository

- `app/`: the application (Streamlit page, `creditlens/` package, tests, `config/thresholds.toml`).
- `docs/`: product, architecture, acceptance criteria, plan and AI logs per branch (`docs/ai-log/`).
- `docs/guide-equipe.md`: team guide in French (who does what, branches, pull requests).
- `AI-USAGE.md`: how AI tools were used, checked and corrected.
