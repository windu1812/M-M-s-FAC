"""Journey tests of the dashboard page (slice 5), with Streamlit's AppTest.

AppTest runs the page without a browser. Every test is offline (conftest.py):
the SEC files are SAMPLE DATA written to a temporary cache by
tests/synthetic_company.py. Expected values are worked out by hand in
test_display.py and docs/acceptance.md (example company = ALFA FY2026).
"""

from pathlib import Path

import pandas as pd
import pytest
import requests
from streamlit.testing.v1 import AppTest

from creditlens.data import financials as fin
from creditlens.data import sec_client

import synthetic_company as sc

APP_FILE = Path(__file__).resolve().parents[1] / "streamlit_app.py"
TIMEOUT = 30  # seconds


@pytest.fixture
def cache():
    """The SAMPLE DATA companies, saved in the (temporary) SEC cache of the test."""
    sc.write_cache(sec_client.CACHE_DIR)
    return sec_client.CACHE_DIR


def start() -> AppTest:
    return AppTest.from_file(str(APP_FILE), default_timeout=TIMEOUT).run()


def run(tickers: str, at: AppTest | None = None, allow_unexpected: bool = False) -> AppTest:
    """Type the tickers and click Run. The field is in a form: as in the browser, what is typed is
    sent only when the form is submitted (Run or Enter), so both happen in the same run.

    The page turns any unexpected error into an "Unexpected problem" box for its ticker; a test would
    then pass silently (even the "no internet in tests" block). So it is refused unless allowed.
    """
    at = at or start()
    at.text_input(key="tickers").input(tickers)
    at.button(key="run").click().run()
    assert not at.exception, at.exception
    if not allow_unexpected:
        assert not any("Unexpected problem" in e for e in errors(at)), errors(at)
    return at


def page_text(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [e.value for e in at.error]
    return "\n".join(parts)


def errors(at: AppTest) -> list[str]:
    return [e.value for e in at.error]


TABLE_ORDER = ["ratio_table", "underlying_table"]  # their order on the page (AppTest gives no key)


def table(at: AppTest, key: str):
    assert len(at.dataframe) == len(TABLE_ORDER)
    return at.dataframe[TABLE_ORDER.index(key)].value


# --- Empty state (V2) -------------------------------------------------------------------------


def test_page_starts_and_shows_the_empty_state():
    at = start()

    assert not at.exception
    assert at.title[0].value == "CreditLens"
    assert at.text_input(key="tickers").value == ""
    assert at.button(key="run").label == "Run"
    assert any("AAPL, MSFT, NKE" in m.value and "Run" in m.value for m in at.markdown)
    assert at.segmented_control(key="incl_leases").value is False  # "Financial debt only" is the default
    assert not at.error


# --- Ticker checks (AC2) ----------------------------------------------------------------------


def test_six_tickers_show_the_message_and_download_nothing(cache, monkeypatch):
    calls = []
    monkeypatch.setattr(sec_client, "fetch_json", lambda *a, **k: calls.append(a))

    at = run("AAPL, MSFT, NKE, GOOG, AMZN, META")

    assert any("Enter 1 to 5 tickers" in e for e in errors(at))
    assert calls == []  # nothing downloaded, not even read from the cache
    assert not at.dataframe


# --- Main journey (AC1, AC5, AC7) ------------------------------------------------------------------


def test_run_shows_one_card_per_company_with_name_year_and_end_date(cache):
    at = run("alfa, BETA")

    text = page_text(at)
    assert not at.error
    assert "Alfa Corp (SAMPLE DATA)" in text and "Beta Inc (SAMPLE DATA)" in text
    assert "ALFA · FY2026, year ended 2026-12-31" in text
    assert "BETA · FY2026, year ended 2026-05-31" in text


def test_cards_show_the_ratios_changes_and_overall_alert(cache):
    at = run("ALFA, BETA")

    text = page_text(at)
    # ALFA = example company: ND/EBITDA 1.42x (CALC4a), coverage 8.00x, current ratio 1.50x; CALC12 orange
    assert "**1.42x** · :green[green]" in text
    assert "-0.22x vs FY2025" in text  # 1.42 - 1.64
    assert "**8.00x**" in text and "+2.00x vs FY2025" in text
    assert ":orange-background[:orange[**Orange: 1 orange flag**]]" in text  # word and colour (AC7)
    # BETA: current ratio 0.80 and FCF -150 red; ND/EBITDA, coverage, margin not available (AC7)
    assert ":gray-background[:gray[**N/A: 3 not available, 2 red flags, 1 green flag**]]" in text  # not rated
    assert "Interest coverage (x): **not available**" in text
    assert "interest expense not reported" in text  # the reason, under the value


def test_ratio_table_has_9_rows_per_company_with_units_and_flag_words(cache):
    at = run("ALFA, BETA")

    ratios = table(at, "ratio_table")
    assert len(ratios) == 2 * 9  # AC5
    assert list(ratios.columns[4:7]) == ["FY2024", "FY2025", "FY2026"]  # only real years (E11)
    alfa = ratios[ratios["Ticker"] == "ALFA"].set_index("Metric")
    assert alfa.loc["Debt / equity", "FY2026"] == "1.53"
    assert alfa.loc["Debt / equity", "Latest flag"] == "orange"
    assert ratios["Unit"].isin(["USD m", "x", "%"]).all()


def test_ratio_table_shows_5_years_when_year_ends_differ_and_says_which_are_left_out(cache):
    """AC5: SEPT (FY2022-FY2026) and DECM (FY2021-FY2025) cover 6 fiscal years; the table shows 5."""
    at = run("SEPT, DECM")

    ratios = table(at, "ratio_table")
    year_columns = [c for c in ratios.columns if c.startswith("FY")]
    assert year_columns == ["FY2022", "FY2023", "FY2024", "FY2025", "FY2026"]
    decm = ratios[ratios["Ticker"] == "DECM"].set_index("Metric")
    assert decm.loc["Current ratio", "Latest flag"] == "red (FY2025)"  # 900 / 1,200 = 0.75x < 1.0
    assert "Only the 5 most recent fiscal years are shown; left out: FY2021." in page_text(at)


def test_underlying_data_shows_tags_and_accession_numbers(cache):
    at = run("ALFA")

    underlying = table(at, "underlying_table")
    revenue = underlying[(underlying["Fiscal year"] == 2026) & (underlying["Item"] == "Revenue")].iloc[0]
    assert revenue["Value (USD m)"] == 6000  # a number: the column sorts and aligns as numbers
    assert revenue["Status"] == "reported"
    assert revenue["XBRL tag"] == "Revenues"
    assert revenue["10-K accession"] == "0001111111-26-000003"
    assert "View underlying data" in [e.label for e in at.expander]


def test_cache_date_is_shown(cache):
    at = run("ALFA")

    assert any("saved in the local cache on" in c.value and "(ALFA)" in c.value for c in at.caption)  # E7


# --- Debt definition selector (AC5b) ----------------------------------------------------------------


def test_debt_selector_switches_cards_and_table_without_downloading_again(cache, monkeypatch):
    at = run("ALFA")
    before = table(at, "ratio_table").set_index("Metric")

    calls = []
    original = sec_client.fetch_json
    monkeypatch.setattr(sec_client, "fetch_json", lambda *a, **k: calls.append(a) or original(*a, **k))
    at.segmented_control(key="incl_leases").set_value(True).run()
    assert not at.exception

    after = table(at, "ratio_table").set_index("Metric")
    # 2,000 + 300 + 200 + 400 + 100 = 3,000 (CALC2b); 2,400 / 1,200 = 2.00 (CALC4b); 3,000 / 1,500 = 2.00 (CALC5b)
    assert after.loc["Total debt, incl. leases", "FY2026"] == "3,000"
    assert after.loc["Net debt / EBITDA, incl. leases", "FY2026"] == "2.00"
    assert after.loc["Debt / equity, incl. leases", "FY2026"] == "2.00"
    # the other ratios do not change
    for metric in ["EBITDA", "Interest coverage", "Current ratio", "EBITDA margin", "Free cash flow"]:
        assert after.loc[metric, "FY2026"] == before.loc[metric, "FY2026"]
    text = page_text(at)
    assert "Net debt / EBITDA, incl. leases (x): **2.00x**" in text  # the card switched too, with its unit
    assert "Including leases and short-term borrowings" in text
    assert calls == []  # only the stored result is redrawn


# --- Errors for one ticker only (AC3, V3, E8, E9, E10) ---------------------------------------------------


def test_unknown_ticker_shows_an_error_and_the_other_company_is_shown(cache):
    at = run("ALFA, ZZZZ")  # AC3 with a SAMPLE DATA company instead of AAPL

    assert len(at.error) == 1
    assert "ZZZZ: Ticker not found." in at.error[0].value
    assert "Alfa Corp (SAMPLE DATA)" in page_text(at)
    assert len(table(at, "ratio_table")) == 9


def test_company_without_10k_shows_its_message(cache):
    at = run("FRGN, ALFA")

    assert "FRGN: No annual 10-K data." in at.error[0].value  # E10
    assert "20-F" in at.error[0].value  # says why, without repeating the title
    assert len(table(at, "ratio_table")) == 9


def test_several_failing_tickers_each_get_their_message_and_the_others_are_shown(cache):
    at = run("ZZZZ, FRGN, ALFA")

    assert len(at.error) == 2
    assert "ZZZZ: Ticker not found." in at.error[0].value and "Check the spelling" in at.error[0].value
    assert "FRGN: No annual 10-K data." in at.error[1].value
    assert "Alfa Corp (SAMPLE DATA)" in page_text(at)


def test_an_unexpected_problem_stops_only_its_own_ticker(cache, monkeypatch):
    real_get_financials = fin.get_financials

    def broken_for_beta(ticker, *args, **kwargs):
        if ticker == "BETA":
            raise KeyError("accn")  # for example a cached file with an unexpected shape
        return real_get_financials(ticker, *args, **kwargs)

    monkeypatch.setattr(fin, "get_financials", broken_for_beta)
    at = run("ALFA, BETA", allow_unexpected=True)

    assert len(at.error) == 1
    assert "BETA: Unexpected problem." in at.error[0].value and "KeyError" in at.error[0].value
    assert "Alfa Corp (SAMPLE DATA)" in page_text(at)  # V3


def test_damaged_cache_file_says_which_file_to_delete(cache):
    cik_file = sec_client.CACHE_DIR / f"CIK{sc.COMPANIES['BETA']['cik']:010d}.json"
    cik_file.write_text('{"facts": ', encoding="utf-8")
    at = run("ALFA, BETA")

    assert "BETA: Damaged cache file." in at.error[0].value
    assert "CIK0002222222.json" in at.error[0].value
    assert "Alfa Corp (SAMPLE DATA)" in page_text(at)


def test_the_same_error_for_several_tickers_is_shown_once(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT")
    at = run("ALFA, BETA")  # empty cache: both would have to download

    assert len(at.error) == 1
    assert at.error[0].value.startswith("**ALFA, BETA: Settings missing.**")


def test_progress_box_shows_an_error_when_no_company_could_be_loaded(cache):
    at = run("ZZZZ, FRGN")

    assert at.status[0].label == "Loaded 0 of 2 companies; 2 errors (see below)"
    assert at.status[0].state == "error"  # not a green tick


def test_progress_box_counts_the_companies_loaded(cache):
    at = run("ALFA, ZZZZ")

    assert at.status[0].label == "Loaded 1 of 2 companies; 1 error (see below)"
    assert at.status[0].state == "complete"


def test_results_say_which_tickers_they_belong_to(cache):
    at = run("ALFA")
    assert "Results for: **ALFA**" in page_text(at)

    at.text_input(key="tickers").input("BETA").run()  # typed, but Run not clicked (nor Enter)

    assert at.session_state["tickers"] == "ALFA"  # the form sends what is typed only on Run or Enter
    assert "Results for: **ALFA**" in page_text(at)  # the shown results still say what they are
    assert "Alfa Corp (SAMPLE DATA)" in page_text(at)


def test_input_error_is_shown_as_typed(cache):
    at = run("AB$C, D$E")  # "$...$" would be read as a formula by Markdown

    assert "AB\\$C" in at.error[0].value and "D\\$E" in at.error[0].value


def test_sec_unreachable_without_cache_shows_a_message_for_that_ticker(cache, monkeypatch):
    def no_internet(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(requests, "get", no_internet)
    at = run("ALFA, NCCH")  # NCCH is in the ticker list but its file is not in the cache

    assert len(at.error) == 1
    assert "NCCH: SEC EDGAR unreachable." in at.error[0].value  # E8
    assert "Alfa Corp (SAMPLE DATA)" in page_text(at)


def test_missing_user_agent_explains_how_to_create_the_env_file(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT")
    at = run("ALFA")  # empty cache: the page would have to download

    assert "ALFA: Settings missing." in at.error[0].value  # E9
    assert ".env" in at.error[0].value
    assert not at.dataframe


def test_wrong_thresholds_file_stops_with_a_readable_message(cache, monkeypatch, tmp_path):
    from creditlens import flags

    broken = tmp_path / "thresholds.toml"
    broken.write_text("[net_debt_to_ebitda]\ndirection = \"sideways\"\n", encoding="utf-8")
    monkeypatch.setattr(flags, "DEFAULT_THRESHOLDS_PATH", broken)
    at = run("ALFA")

    assert any("The flag thresholds cannot be read." in e for e in errors(at))
    assert not at.dataframe


# --- Readability (review of PR #16) -----------------------------------------------------------------


def test_cards_explain_the_alert_and_say_better_or_worse(cache):
    at = run("ALFA")

    text = page_text(at)
    assert "Alert on all 6 flagged ratios of FY2026 (see the table)." in text
    assert "-0.22x vs FY2025 (better)" in text  # Net debt / EBITDA 1.42 - 1.64, lower is better


def test_page_has_section_headings(cache):
    at = run("ALFA")

    assert [h.value for h in at.header] == ["Summary", "Charts", "Credit ratios, last 5 fiscal years"]


def test_underlying_data_marks_items_not_reported(cache):
    at = run("ALFA")

    underlying = table(at, "underlying_table")
    da_2024 = underlying[(underlying["Fiscal year"] == 2024) & (underlying["Item"] == "D&A")]
    row = da_2024.iloc[0]  # ALFA does not report D&A in FY2024
    assert row["Status"] == "not reported" and pd.isna(row["Value (USD m)"])  # empty, never 0
    assert row["XBRL tag"] == "–" and row["10-K accession"] == "–"


def test_ac6_changing_the_thresholds_file_changes_the_flag_on_the_page(cache, monkeypatch, tmp_path):
    from creditlens import flags

    before = run("BETA")  # current ratio 2,400 / 3,000 = 0.80x: red with the agreed limits (< 1.0)
    beta = table(before, "ratio_table").set_index("Metric")
    assert beta.loc["Current ratio", "Latest flag"] == "red"

    agreed = flags.DEFAULT_THRESHOLDS_PATH.read_text(encoding="utf-8")
    old = 'label = "Current ratio"\ndirection = "higher_is_better"\ngreen = 1.5\norange = 1.0'
    assert old in agreed
    looser = tmp_path / "thresholds.toml"
    looser.write_text(agreed.replace(old, old.replace("green = 1.5", "green = 0.8").replace(
        "orange = 1.0", "orange = 0.5")), encoding="utf-8")
    monkeypatch.setattr(flags, "DEFAULT_THRESHOLDS_PATH", looser)  # the file changed, not the code

    after = run("BETA")
    beta = table(after, "ratio_table").set_index("Metric")
    assert beta.loc["Current ratio", "Latest flag"] == "green"  # 0.80 >= 0.8


# --- Tests asked by the test review of PR #16 -------------------------------------------------------


def card_lines(at: AppTest) -> list[str]:
    """The "TICKER · FY…, year ended …" line of each card on the page."""
    lines = [m.value for m in at.markdown if " · FY" in m.value and ":small[" in m.value]
    return [line.split(":small[")[1].rstrip("]") for line in lines]


def test_three_companies_give_exactly_three_cards(cache):
    """AC1 with 3 companies."""
    at = run("ALFA, BETA, SEPT")

    assert card_lines(at) == ["ALFA · FY2026, year ended 2026-12-31", "BETA · FY2026, year ended 2026-05-31",
                              "SEPT · FY2026, year ended 2026-09-30"]


def test_five_tickers_are_run_and_each_failure_is_shown(cache, monkeypatch):
    """AC2 upper limit: 5 tickers are accepted; V3: 2 cards and 3 errors, one per failing ticker."""
    def no_internet(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(requests, "get", no_internet)
    at = run("ALFA, BETA, FRGN, ZZZZ, NCCH")

    assert not any("Enter 1 to 5 tickers" in e for e in errors(at))
    assert len(card_lines(at)) == 2
    assert [e.split(":")[0] for e in errors(at)] == ["**FRGN", "**ZZZZ", "**NCCH"]


def test_data_problem_stops_only_its_ticker(cache):
    """DUPY files two 10-K year ends in 2025: the same fiscal year twice."""
    at = run("DUPY, ALFA")

    assert "DUPY: Data problem." in at.error[0].value and "given twice" in at.error[0].value
    assert card_lines(at) == ["ALFA · FY2026, year ended 2026-12-31"]


def test_alert_on_the_card_switches_with_the_debt_definition(cache):
    """AC5b: the flags and the alert change in the cards."""
    at = run("GAMA")
    assert ":green-background[:green[**Green: 6 green flags**]]" in page_text(at)

    at.segmented_control(key="incl_leases").set_value(True).run()

    assert ":orange-background[:orange[**Orange: 2 orange flags**]]" in page_text(at)
    assert "**2.50x** · :orange[orange]" in page_text(at)  # (1,500 + 1,000) / 1,000


def test_not_meaningful_is_shown_on_the_card_and_in_the_table(cache):
    at = run("NEGA")

    assert ":red-background[:red[**Red: 2 red flags, 2 not meaningful**]]" in page_text(at)
    assert "Net debt / EBITDA (x): **not meaningful**" in page_text(at)
    nega = table(at, "ratio_table").set_index("Metric")
    assert nega.loc["Debt / equity", "FY2026"] == "not meaningful"



# --- Second review round of PR #16 ---------------------------------------------------------------


class FakeNotFound:
    """The SEC's answer when it has no such file (HTTP 404)."""

    status_code = 404

    def raise_for_status(self):
        raise requests.HTTPError("404 Not Found", response=self)


def test_table_cells_are_coloured_on_the_page(cache):
    at = run("BETA")  # current ratio 0.80x and free cash flow -150: red

    assert "#FFCDD2" in str(at.dataframe[0].proto)  # the red of display.CELL_COLOURS


def test_company_without_xbrl_data_gets_its_own_title(cache, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeNotFound())
    at = run("NCCH, ALFA")  # NCCH is in the ticker list; its file is not cached and the SEC answers 404

    assert "NCCH: No financial data on SEC EDGAR." in at.error[0].value
    assert card_lines(at) == ["ALFA · FY2026, year ended 2026-12-31"]


def test_cache_date_lists_only_the_companies_shown(cache):
    at = run("FRGN, ALFA")  # FRGN's file is cached, but FRGN files no 10-K

    saved = [c.value for c in at.caption if "saved in the local cache" in c.value]
    assert saved and all(line.endswith("(ALFA).") for line in saved)



# --- Compact layout (design of 2026-11-28) -------------------------------------------------------------


def test_inputs_are_on_one_row_that_wraps_instead_of_cutting_text(cache):
    """The ticker field, Run and the debt definition sit side by side when there is room, so the cards are visible
    without scrolling; in a narrower window the row wraps (the debt definition goes under the field) instead of
    squeezing fixed columns, which cut "Run" to "R..." and the leases option at about 700 px (bug of 2026-11-28)."""
    at = start()

    def blocks(node):  # every block of the page, at any depth
        for child in getattr(node, "children", {}).values():
            yield child
            yield from blocks(child)

    search = [b for b in at.main.get("flex_container") if getattr(b.proto.flex_container, "wrap", False)
              and b.get("text_input") and b.get("button_group")]
    assert search, "the inputs are not in a row that wraps"
    keys = [w.key for w in search[0].get("text_input") + search[0].get("button") + search[0].get("button_group")]
    assert keys == ["tickers", "run", "incl_leases"]
    assert not [b for b in blocks(search[0]) if type(b).__name__ == "Column"]  # no fixed-ratio columns

def test_results_line_and_cache_date_come_before_the_cards(cache):
    at = run("ALFA")

    captions = [c.value for c in at.caption]
    results = next(i for i, c in enumerate(captions) if c.startswith("Results for: **ALFA**"))
    saved = next(i for i, c in enumerate(captions) if "saved in the local cache" in c)
    assert saved == results + 1  # the two small lines together, under the inputs
    assert at.header[0].value == "Summary"


def test_progress_box_is_removed_when_every_company_loaded(cache):
    """The box is useful while loading and when something failed; after a clean run the "Results for" line
    says the same, so the box goes and the cards move up."""
    at = run("ALFA, BETA")

    assert not at.status
    assert "Results for: **ALFA, BETA**" in page_text(at)


# --- Responsive, sober "product page" style without Streamlit's own controls (design of 2026-11-28) ------


def test_streamlit_toolbar_and_menu_are_hidden():
    """No Deploy button and no menu (so no "Record a screencast"): toolbarMode "minimal"."""
    import tomllib

    config = tomllib.loads((APP_FILE.parent / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["client"]["toolbarMode"] == "minimal"


def test_page_loads_its_style_sheet():
    at = start()

    styles = [m.value for m in at.markdown if m.value.startswith("<style>")]
    assert any('[data-testid="stHeader"]' in s and "display: none" in s for s in styles)  # the top bar
    assert any('[data-testid="stElementToolbar"]' in s for s in styles)  # the toolbars over tables


def test_cards_flow_in_a_wrapping_row(cache):
    """Responsive: the cards have a fixed width inside a row that wraps, so a narrow window shows fewer per row."""
    at = run("ALFA, BETA")

    cards = [b for b in at.main.get("flex_container") if getattr(b.proto.flex_container, "wrap", False)]
    assert cards, "no wrapping row of cards"
    assert len(card_lines(at)) == 2


# --- Modern, responsive page (design of 2026-11-28, branch design/modern-ui) ---------------------------


def test_example_button_fills_in_the_demo_tickers_and_runs(monkeypatch):
    """Empty state: one click runs the demo companies (offline here, so they end as "SEC EDGAR unreachable")."""

    def no_network(*args, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(requests, "get", no_network)
    at = start()

    at.button(key="example").click().run()

    assert not at.exception
    assert at.text_input(key="tickers").value == "AAPL, MSFT, NKE"
    assert "Results for: **AAPL, MSFT, NKE**" in page_text(at)
    assert any("SEC EDGAR unreachable" in e for e in errors(at))  # it ran: one error line for the 3 tickers


def test_top_bar_links_to_the_sections_once_there_are_results(cache):
    def bar(at):
        return next(m.value for m in at.markdown if 'class="cl-nav"' in m.value)

    assert "href=" not in bar(start())  # nothing to jump to yet
    at = run("ALFA")
    links = bar(at)
    for anchor in ("#summary", "#charts", "#ratios"):
        assert f'href="{anchor}"' in links
    assert [h.proto.anchor for h in at.header] == ["summary", "charts", "ratios"]


def test_ratio_table_shows_every_note_and_year_cell_in_full(cache, monkeypatch):
    """Fiscal-year columns fit "not available"; the Notes column is as wide as its longest note (the table then
    scrolls sideways inside its box) and Ticker and Metric stay in view (review of PR #16, ux-reviewer #3)."""
    import json

    from creditlens import display

    long_note = "FY2022: operating income not reported; D&A not reported | FY2023–FY2026: operating income not reported"

    def with_a_long_note(*args, **kwargs):  # NKE's real notes are this long (138 characters at most)
        table, colours = real_ratio_table(*args, **kwargs)
        table.loc[table.index[0], "Notes"] = long_note
        return table, colours

    real_ratio_table = display.ratio_table
    monkeypatch.setattr(display, "ratio_table", with_a_long_note)
    at = run("ALFA, BETA")

    config = json.loads(at.dataframe[0].proto.columns)
    assert config["Notes"]["width"] >= 7 * len(long_note)  # about 7 pixels per character
    assert all(config[year]["width"] >= 100 for year in config if year.startswith("FY"))
    assert config["Ticker"]["pinned"] and config["Metric"]["pinned"]
