# Acceptance criteria

Each criterion is checkable: a starting state, an action and an expected result. Status: `open`,
`passing (test: <test name>)`, `checked by hand on <date>`, or `failing`.

## Main user journey

| Id | Feature | Given | When | Then | Status |
|---|---|---|---|---|---|
| AC1 | F1 | The app is running and the SEC files of AAPL, MSFT and NKE are in the cache | The user types `AAPL, MSFT, NKE` and clicks Run | Within 60 seconds, 3 summary cards appear, each with the company name, the latest fiscal year and its end date | page passing on SAMPLE DATA (test: `test_run_shows_one_card_per_company_with_name_year_and_end_date`); the real run on AAPL, MSFT, NKE: slice 7 |
| AC2 | F1 | The app is running | The user types 6 tickers and clicks Run | The message "Enter 1 to 5 tickers" is shown and nothing is downloaded | passing (tests: `test_six_tickers_show_the_message_and_download_nothing`, `test_six_tickers_are_refused`) |
| AC3 | F1 | The app is running | The user types `AAPL, ZZZZ` and clicks Run | ZZZZ shows "Ticker not found"; AAPL is shown normally | passing with a SAMPLE DATA company instead of AAPL (test: `test_unknown_ticker_shows_an_error_and_the_other_company_is_shown`) |
| AC4 | F1 | The reconciliation table below is filled from the 10-K filings | The test or the reconciler compares the app's figures | Revenue, total assets and net income (USD m) of the last 2 fiscal years equal the 10-K values for AAPL, MSFT and NKE, with the page cited | passing (test: `test_reconciliation_10k.py`, 18 checks); pages checked by Arthur on 2026-11-20 |
| AC5 | F2 | A run with 1 to 5 companies | The user looks at the ratio table | Each company has 9 rows for the selected debt definition (EBITDA, total debt, net debt and the 6 ratios), 5 fiscal-year columns and a unit on every row | ratios part passing (test: `test_each_debt_version_has_the_9_numbers_with_a_unit`); the table on the page passing (tests: `test_ratio_table_has_9_rows_per_company_and_one_column_per_year`, `test_ratio_table_has_9_rows_per_company_with_units_and_flag_words`) |
| AC5b | F2 | A run with 3 companies, "Financial debt only" selected | The user selects "Including leases and short-term borrowings" | Total debt, net debt, Net debt / EBITDA and Debt / equity change in the cards, charts, flags and table; the other ratios do not change. The Excel Ratios sheet holds both versions | cards and table passing (tests: `test_debt_selector_switches_cards_and_table_without_downloading_again`, `test_ratio_table_switches_only_the_debt_based_rows`, `test_card_switches_with_the_debt_definition`); charts and Excel passing (tests: `test_debt_selector_switches_the_charts_and_keeps_the_chosen_ratio`, `test_excel_summary_follows_the_debt_selector`) |
| AC6 | F3 | The app shows AAPL with a red flag on current ratio | The team changes the current ratio limits in `thresholds.toml` and runs again | The flag changes, without any code change | flags part passing (test: `test_ac6_changing_the_file_changes_the_flag`); the run on the page: slice 5 |
| AC7 | F3 | A run with 3 companies | The user looks at the cards | Each card shows the overall alert as a word and a colour, and counts the "not available" ratios | alert part passing (tests: `test_calc12_overall_alert_is_orange`, `test_overall_alert_red_counts_not_available_and_not_meaningful`); the card on the page passing (tests: `test_cards_show_the_ratios_changes_and_overall_alert`, `test_card_with_missing_ratios_counts_them`) |
| AC8 | F4 | A run with 3 companies | The user picks "Interest coverage" in the ratio selector | Both charts switch to interest coverage; a missing value is shown as "n/a", never as 0 | passing (test: `test_picking_interest_coverage_switches_both_charts_and_missing_is_never_zero`); page run on the cached SEC files of AAPL, MSFT and NKE (2026-11-28): every ratio, both debt definitions, missing values n/a, never 0. Look at the page: pending |
| AC9 | F5 | A run with 3 companies | The user clicks "Download Excel" | An `.xlsx` file downloads with the sheets Summary, Ratios, Financials and Notes; its values equal those on the screen | passing (tests: `test_download_excel_button_gives_the_four_sheets_with_the_screen_values`, `test_excel_summary_follows_the_debt_selector`, `test_export.py`); file built from the page for AAPL, MSFT and NKE (2026-11-28): 4 sheets, 39 ratio rows. Downloaded file opened in Excel: pending |

## Screens (how each was checked)

| Id | Screen / state | Expected | Test | Browser check | Looked at by |
|---|---|---|---|---|---|
| V1 | Dashboard, 5 companies, 1280 px laptop width | 5 cards in one row, no sideways scrolling, table readable, every axis and card shows its unit | – | not run (project check not installed) | screenshots at 1280 px with 5 SAMPLE DATA companies looked at by Claude on 2026-11-27 (cards and table; charts: slice 6); Marc's look pending |
| V2 | Dashboard, empty (first visit) | Instruction and example tickers, no error | passing (test: `test_page_starts_and_shows_the_empty_state`) | not run | screenshot looked at by Claude on 2026-11-27; Marc's look pending |
| V3 | Dashboard, one ticker in error | Error message for that ticker only, the other companies still shown | passing (tests: `test_unknown_ticker_shows_an_error_and_the_other_company_is_shown`, `test_company_without_10k_shows_its_message`, `test_sec_unreachable_without_cache_shows_a_message_for_that_ticker`) | not run | screenshot looked at by Claude on 2026-11-27; Marc's look pending |

## Calculations (known answers)

**Example company** (synthetic, in USD m):

| Item | Value |
|---|---|
| Revenue | 6,000 |
| Operating income | 1,000 |
| D&A | 200 |
| Interest expense | 125 |
| Long-term debt, noncurrent | 2,000 |
| Current portion of long-term debt | 300 |
| Short-term borrowings | 200 |
| Operating lease liabilities | 400 |
| Finance lease liabilities | 100 |
| Cash | 600 |
| Equity | 1,500 |
| Current assets | 1,800 |
| Current liabilities | 1,200 |
| Operating cash flow | 1,500 |
| Capex | 400 |

| Id | Number | Hand working | Expected result | Tolerance | Status |
|---|---|---|---|---|---|
| CALC1 | EBITDA | 1,000 + 200 = 1,200 | 1,200 USD m | exact | passing (test: `test_known_answer[CALC1]`) |
| CALC2a | Total debt, financial debt only | 2,000 + 300 = 2,300 | 2,300 USD m | exact | passing (test: `test_known_answer[CALC2a]`) |
| CALC2b | Total debt, including leases and short-term borrowings | 2,300 + 200 = 2,500; + 400 = 2,900; + 100 = 3,000 | 3,000 USD m | exact | passing (test: `test_known_answer[CALC2b]`) |
| CALC3a | Net debt, financial debt only | 2,300 − 600 = 1,700 | 1,700 USD m | exact | passing (test: `test_known_answer[CALC3a]`) |
| CALC3b | Net debt, including leases | 3,000 − 600 = 2,400 | 2,400 USD m | exact | passing (test: `test_known_answer[CALC3b]`) |
| CALC4a | Net debt / EBITDA, financial debt only | 1,700 ÷ 1,200: 1,200 × 1.4 = 1,680, remainder 20; 20 ÷ 1,200 = 0.0167; total 1.4167 | 1.42x | 0.005 | passing (test: `test_known_answer[CALC4a]`) |
| CALC4b | Net debt / EBITDA, including leases | 2,400 ÷ 1,200: 1,200 × 2 = 2,400 | 2.00x | 0.005 | passing (test: `test_known_answer[CALC4b]`) |
| CALC5a | Debt / equity, financial debt only | 2,300 ÷ 1,500: 1,500 × 1.5 = 2,250, remainder 50; 50 ÷ 1,500 = 0.0333; total 1.5333 | 1.53x | 0.005 | passing (test: `test_known_answer[CALC5a]`) |
| CALC5b | Debt / equity, including leases | 3,000 ÷ 1,500: 1,500 × 2 = 3,000 | 2.00x | 0.005 | passing (test: `test_known_answer[CALC5b]`) |
| CALC6 | Interest coverage | 1,000 ÷ 125: 125 × 8 = 1,000 | 8.00x | 0.005 | passing (test: `test_known_answer[CALC6]`) |
| CALC7 | Current ratio | 1,800 ÷ 1,200: 1,200 × 1.5 = 1,800 | 1.50x | 0.005 | passing (test: `test_known_answer[CALC7]`) |
| CALC8 | EBITDA margin | 1,200 ÷ 6,000: 6,000 × 0.2 = 1,200 | 20.0 % | 0.05 pt | passing (test: `test_known_answer[CALC8]`) |
| CALC9 | Free cash flow | 1,500 − 400 = 1,100 | 1,100 USD m | exact | passing (test: `test_known_answer[CALC9]`) |
| CALC10 | USD → USD m | 416,161,000,000 ÷ 1,000,000 = 416,161 | 416,161 USD m | exact | passing (test: `test_calc10_usd_to_usd_millions`) |
| CALC11 | Net cash (including leases) | Cash 3,600: 3,000 − 3,600 = −600; −600 ÷ 1,200 = −0.5 | Net debt −600 USD m; Net debt / EBITDA −0.50x | 0.005 | passing (test: `test_calc11_net_cash_gives_negative_net_debt`) |
| CALC12 | Flags for the example company, with the thresholds below (including leases) | ND/EBITDA 2.00 ≤ 2.0 → green; D/E 2.00 is > 1.0 and ≤ 2.0 → orange; coverage 8.00 ≥ 6.0 → green; current ratio 1.50 ≥ 1.5 → green; margin 20.0 ≥ 20 → green; FCF 1,100 ≥ 0 → green | 5 green, 1 orange → overall **orange**. Financial debt only: ND/EBITDA 1.42 → green, D/E 1.53 → orange, overall **orange** | exact | passing (tests: `test_calc12_flags_including_leases`, `test_calc12_flags_financial_debt_only`, `test_calc12_overall_alert_is_orange`; with `compute_ratios`: `test_calc12_end_to_end_with_compute_ratios`, runs once PR #13 is merged) |
| CALC13 | Total debt including leases, when two parts are not reported | Short-term borrowings and finance leases not reported: 2,000 + 300 + 400 = 2,700 | 2,700 USD m, with the notes "short-term borrowings not reported" and "finance lease liabilities not reported" | exact | passing (test: `test_calc13_parts_not_reported_count_as_zero_with_a_note`) |

**Thresholds (agreed on 2026-11-20).** These are the starting values for `thresholds.toml`. A value exactly on a
limit takes the better colour.

| Ratio | Direction | Green | Orange | Red |
|---|---|---|---|---|
| Net debt / EBITDA | lower is better | ≤ 2.0x | ≤ 3.5x | > 3.5x |
| Debt / equity | lower is better | ≤ 1.0x | ≤ 2.0x | > 2.0x |
| Interest coverage | higher is better | ≥ 6.0x | ≥ 3.0x | < 3.0x |
| Current ratio | higher is better | ≥ 1.5x | ≥ 1.0x | < 1.0x |
| EBITDA margin | higher is better | ≥ 20 % | ≥ 10 % | < 10 % |
| Free cash flow | higher is better | ≥ 0 | – | < 0 |

**Overall alert (agreed on 2026-11-20):**
- red if at least one ratio is red;
- otherwise orange if at least one is orange;
- otherwise green.

"Not available" ratios do not count as red, but the card shows how many there are.

**Reconciliation with the 10-K.** The "10-K value" and "page" columns are filled by a team member from the filing
itself, never from the app's output.

| Id | Ticker | Fiscal years | Items | 10-K value (USD m) and page | App value | Status |
|---|---|---|---|---|---|---|
| R1 | AAPL | FY2026 / FY2025 | revenue, total assets, net income | Total net sales 478,834 / 416,161 and net income 132,175 / 112,010 (Consolidated Statements of Operations, p. 32); total assets 404,548 / 359,241 (Consolidated Balance Sheets, p. 34). [10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019326000026/aapl-20260926.htm) | equal, exact | passing (test: `test_reconciliation_10k.py`); 10-K values read by Claude from the filed document, checked by Arthur on 2026-11-20 |
| R2 | MSFT | FY2026 / FY2025 | revenue, total assets, net income | Total revenue 331,839 / 281,724 and net income 133,749 / 101,832 (Income Statements, p. 50); total assets 758,376 / 619,003 (Balance Sheets, p. 52). [10-K](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm) | equal, exact | passing (test: `test_reconciliation_10k.py`); 10-K values read by Claude from the filed document, checked by Arthur on 2026-11-20 |
| R3 | NKE | FY2026 / FY2025 | revenue, total assets, net income | Revenues 46,398 / 46,309 and net income 3,108 / 3,219 (Consolidated Statements of Income, p. 55); total assets 38,410 / 36,579 (Consolidated Balance Sheets, p. 57). [10-K](https://www.sec.gov/Archives/edgar/data/320187/000032018726000088/nke-20260531.htm) | equal, exact | passing (test: `test_reconciliation_10k.py`); 10-K values read by Claude from the filed document, checked by Arthur on 2026-11-20 |

## Edge cases and errors

| Id | Situation | Expected behaviour | Status |
|---|---|---|---|
| E1 | An input is missing (for example MSFT tags no D&A total) | EBITDA, Net debt / EBITDA and EBITDA margin show "not available: D&A not reported"; no flag | ratios part passing (test: `test_e1_missing_d_and_a`); "no flag": slice 4 |
| E2 | Zero denominator (for example interest expense = 0) | "not available: interest expense is zero" | passing (test: `test_e2_zero_denominator_gives_not_available`; same rule for zero current liabilities, revenue and equity) |
| E3 | EBITDA ≤ 0 | Net debt / EBITDA shows "not meaningful: EBITDA ≤ 0" | passing (test: `test_e3_ebitda_zero_or_negative_gives_not_meaningful`, EBITDA = 0 and EBITDA = −300) |
| E4 | Negative equity | Debt / equity shows "not meaningful: negative equity" | passing (test: `test_e4_negative_equity_gives_not_meaningful`) |
| E5 | Net cash (cash > total debt) | Net debt and Net debt / EBITDA shown with a minus sign (see CALC11) | passing (test: `test_calc11_net_cash_gives_negative_net_debt`) |
| E6 | A part of total debt other than noncurrent long-term debt is not reported (for example no commercial paper) | That part counts as zero, with the note "<part> not reported" (see CALC13) | passing (tests: `test_calc13_parts_not_reported_count_as_zero_with_a_note`, `test_e6_current_portion_not_reported_counts_as_zero`: current portion not reported, 2,000 + 0 = 2,000) |
| E6b | Noncurrent long-term debt not reported | Both versions of total debt, net debt, Net debt / EBITDA and Debt / equity show "not available: long-term debt not reported" | passing (test: `test_e6b_long_term_debt_not_reported_makes_both_debt_versions_unavailable`) |
| E7 | SEC unreachable, cache present | Cached data used; "Data from cache, downloaded on <date>" shown | data part passing (test: `test_fetch_json_uses_cache_without_calling_internet`); the note on the page passing (test: `test_cache_date_is_shown`; it says "saved in the local cache on <date>") |
| E8 | SEC unreachable, no cache | Error message for that ticker, no crash | data part passing (tests: `test_fetch_json_sec_unreachable_without_cache_raises_clear_error`, `test_get_financials_sec_unreachable_without_cache_raises_clear_error`); the message on the page passing (test: `test_sec_unreachable_without_cache_shows_a_message_for_that_ticker`) |
| E9 | `SEC_USER_AGENT` not set | Message explaining how to create `app/.env`; no request is sent | data part passing (test: `test_fetch_json_without_user_agent_sends_nothing`); the message on the page passing (test: `test_missing_user_agent_explains_how_to_create_the_env_file`) |
| E10 | Company with no 10-K (for example a foreign filer that files a 20-F) | "No annual 10-K data for <ticker>" | data part passing (test: `test_no_annual_data_raises_clear_error`); the message on the page passing (test: `test_company_without_10k_shows_its_message`) |
| E11 | Fewer than 5 fiscal years available | Only the real years are shown, with no filler years | ratios part passing (test: `test_e11_only_the_real_years_are_returned`); the table on the page passing (test: `test_ratio_table_shows_no_filler_year`: a missing year shows "no data") |
