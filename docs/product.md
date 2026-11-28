# Product: CreditLens

Status: agreed on 2026-11-20 (Arthur, for the team)

## Problem and customers

- **Customer:** credit analysts and relationship managers in corporate banking at small and mid-sized banks and
  private debt funds.
- **Problem today:** they copy figures from 10-K filings into Excel by hand to compute credit ratios. This takes
  several hours per company and causes typing errors.
- **Success looks like:** a credit screen of 5 US companies in under one minute, with key figures reconciled to the
  10-K.

## Main user journey

1. The user opens the app on a laptop and sees a ticker field and a **Run** button.
2. They type 1 to 5 US tickers (for example `AAPL, MSFT, NKE`) and click **Run**.
3. The app gets the annual 10-K data from SEC EDGAR (or from the local cache). It computes the ratios for the last
   5 fiscal years and applies the green / orange / red flags.
4. The user reads the summary cards, the comparison charts and the 5-year ratio table, then downloads an Excel file.

## Screens and visuals

Look: one dashboard page with summary cards, charts and a table. Made for a laptop; on a phone (390 px) the page
adapts (one card per row, inputs one under the other), and the wide table scrolls inside its own box.
Layout (agreed on 2026-11-28): the ticker field, Run and the debt definition (two buttons) on one aligned row;
"Results for" and the cache date in small text under it; then the summary cards, visible without scrolling on a
1280 × 800 laptop screen. Modern look (agreed on 2026-11-28, Arthur): a fixed frosted top bar with links to the
sections, a hero title that gets small once there are results, the inputs in one white panel, cards with a line of
their alert colour on top (the alert word is always written), the charts and the table in white panels, small
rise-in and hover effects (off when the computer asks for less motion), and on the first visit three tiles saying
what the screen gives and a "Try AAPL, MSFT, NKE" link.
Visual reference: a bank credit sheet. It is sober, with a white background and a dense table; colour carries meaning
only for the flags (the blue of the title, logo and buttons is decorative, one accent).

| Screen | Purpose | The user sees first | Cards / charts / tables | The user can | Loading / empty / error |
|---|---|---|---|---|---|
| Dashboard | Screen 1 to 5 companies | Ticker field and Run button, then one summary card per company | Visuals 1 to 5 below | Type tickers, click Run, choose the debt definition (see "Total debt" below), choose the ratio shown in the charts, open the underlying data, download the Excel file | **Empty:** a one-line instruction with example tickers. **Loading:** progress per company ("Fetching AAPL from SEC EDGAR..."). **Error:** a message per ticker (unknown ticker, no 10-K data, SEC unreachable); the other companies are still shown |

Agreed visuals:

1. **Summary card per company** (up to 5 cards in one row). Each card shows:
   - the company name, the ticker, the latest fiscal year and its end date;
   - Net debt / EBITDA (x), interest coverage (x) and current ratio (x), each with its change vs the prior fiscal
     year;
   - the overall alert as a word and a colour (for example "Red: 2 red flags").

   A ratio that cannot be computed shows "not available" and the reason.
2. **Chart "How do the companies compare in the latest fiscal year?"**
   - Horizontal bars, one per company, sorted, for one ratio chosen in a selector (default: Net debt / EBITDA).
   - The unit is on the axis, the zero line is visible, and the flag thresholds are drawn as reference lines.
   - A company without a value is listed as "n/a", without a bar.
3. **Chart "How did this ratio change over 5 years?"**
   - One line with markers per company, for the same selected ratio.
   - Missing years are left as gaps; the line is not joined across them.
   - The x axis shows fiscal years, with a note that the year-end dates differ by company.
4. **Table "Credit ratios, last 5 fiscal years"**
   - One row per company and ratio, one column per fiscal year.
   - Each cell has its flag colour, and a "Latest flag" column gives the flag as a word, so the meaning does not
     depend on colour alone.
   - Below the table, a "View underlying data" section shows the input figures in USD m, with the XBRL tag and the
     10-K accession number.
5. **Button "Download Excel"**, giving the sheets Summary, Ratios, Financials and Notes. The Ratios sheet holds both
   debt definitions.
6. **Debt definition selector** with two choices: "Financial debt only" (the default) and "Including leases and
   short-term borrowings". It switches the debt-based numbers in the cards, charts, flags and table.

## MVP features (must have)

| Id | Feature | Why the customer needs it |
|---|---|---|
| F1 | SEC EDGAR data: ticker → CIK → annual 10-K values for 5 fiscal years, cached | No more manual copying from the 10-K |
| F2 | Ratio calculation (the 9 numbers in the table below) | The core of a credit screen |
| F3 | Green / orange / red flags, with thresholds in a configuration file | Spot problems at a glance; thresholds can change without code |
| F4 | Comparison charts | Compare peers and trends faster than in a table |
| F5 | Excel export | Analysts continue their work in Excel |

## Explicitly not in the MVP

- Non-US companies (they file no 10-K).
- Share prices and valuation.
- User accounts, payments, file uploads.
- Any paid service. This includes the LLM credit comment first proposed as an option: an LLM API is paid, and the
  team must not pay anything (decision of 2026-11-20).
- Quarterly data and forecasts.

## Data and calculations

| Data | Source | Freshness | Licence / terms checked? |
|---|---|---|---|
| Ticker → CIK list | `https://www.sec.gov/files/company_tickers.json` | Downloaded once, then cached; refreshed on demand | Free public SEC data; User-Agent required, max 10 requests/s (checked by Arthur on 2026-11-20) |
| Annual 10-K values (XBRL) | `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` | Latest 10-K filed; cached | Same as above |

**Items extracted:**
- income statement: revenue, operating income, net income, depreciation and amortization (D&A), interest expense;
- balance sheet: total assets, total liabilities, equity, current assets, current liabilities, cash, long-term debt
  (noncurrent) and its current portion, short-term borrowings (including commercial paper), operating lease
  liabilities, finance lease liabilities;
- cash flow statement: operating cash flow, capex.

Each item has alternative XBRL tags in priority order. The fiscal year comes from the `end` date, never from `fy`.
Income statement and cash flow items keep only periods of 350 to 380 days. When the same period appears in several
10-Ks, the most recent filing wins.

| Number the app shows | Formula | Units |
|---|---|---|
| EBITDA | operating income + D&A | USD m |
| Total debt, financial debt only (default) | long-term debt (noncurrent) + current portion of long-term debt | USD m |
| Total debt, including leases and short-term borrowings | financial debt only + short-term borrowings (commercial paper) + operating lease liabilities + finance lease liabilities | USD m |
| Net debt (both versions) | total debt − cash | USD m |
| Net debt / EBITDA (both versions) | net debt ÷ EBITDA | x |
| Debt / equity (both versions) | total debt ÷ equity | x |
| Interest coverage | operating income ÷ interest expense | x |
| Current ratio | current assets ÷ current liabilities | x |
| EBITDA margin | EBITDA ÷ revenue | % |
| Free cash flow | operating cash flow − capex | USD m |

Rules:
- Amounts are shown in USD millions.
- A missing input or a zero denominator gives "not available", with the reason.
- A negative denominator (EBITDA ≤ 0 for Net debt / EBITDA, negative equity for Debt / equity) gives
  "not meaningful".
- Display rounding: amounts 0 decimals, ratios 2 decimals, margin 1 decimal. Halves are rounded up, away from
  zero, as Excel's ROUND does (2.005 → 2.01; −2.5 → −3). The flags compare the rounded value shown (decision of
  2026-11-28).
- No value is derived from other lines to fill a gap (decision of 2026-11-20). For example, a company that tags no
  D&A total gets "not available" for EBITDA, with the reason.
- Revenue, total assets and net income are reconciled with the 10-K of AAPL, MSFT and NKE, with the 10-K page cited.

**Total debt, in two versions** (decision of 2026-11-20, replacing an earlier "leases always included" choice).
The app computes both versions. The analyst picks one with the selector, and the Excel file holds both.

- **Financial debt only (default):** the loans and bonds on the balance sheet. This is the debt that companies
  usually report as "total debt".
- **Including leases and short-term borrowings:** credit analysts and rating agencies also treat commercial paper and
  lease obligations as debt, because a company must pay them like a loan. This version shows leverage closer to
  how an agency sees it. For companies with large leases, the difference is big (Microsoft's data-center leases,
  for example).

Rules for both versions:

- Long-term debt (noncurrent) is required. If it is missing, both versions of total debt, and every ratio that uses
  them, are "not available".
- The other parts are added when the 10-K reports them. A part that is not reported counts as zero, and the app
  shows the note "<part> not reported". Many companies have no commercial paper, for example.
- Each part is shown separately in "View underlying data" and in the Excel file.
- Known limitation, for the version with leases: under US GAAP, the operating lease cost is already deducted before
  EBITDA. Rating agencies add part of it back when they add lease debt; CreditLens does not. With leases, Net debt /
  EBITDA is therefore slightly conservative (a little higher).

## Capabilities

| Capability | Needed? | Notes |
|---|---|---|
| Accounts / sign-in | no | |
| Per-user saved data | no | Only the local cache of downloaded SEC files is kept between two runs |
| File uploads | no | |
| Payments | no | |
| Must be online for others | no | A live demo on a laptop is enough |

## Team and constraints

- **Experience:** 5 M2 finance students, little programming experience.
- **Time available:** about 15 hours each, about 75 hours in total.
- **Deadline:** Tuesday 1 December 2026, 23:59.
- **Budget:** 0 EUR. Only the AI coding assistant is paid.
- **Rules to respect:** the FIN_8546 course rules at the end of `AGENTS.md`:
  - one issue and one branch per member;
  - only free public data;
  - SEC User-Agent and rate limit;
  - the fy/end trap;
  - never invent a number;
  - offline tests;
  - 10-K reconciliation;
  - AI log per branch.
