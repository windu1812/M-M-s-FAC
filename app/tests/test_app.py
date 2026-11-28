"""Journey tests of the dashboard page (slice 5), with Streamlit's AppTest.

AppTest runs the page without a browser. Every test is offline (conftest.py):
the SEC files are SAMPLE DATA written to a temporary cache by
tests/synthetic_company.py. Expected values are worked out by hand in
test_display.py and docs/acceptance.md (example company = ALFA FY2026).
"""

from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

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


def run(tickers: str, at: AppTest | None = None) -> AppTest:
    at = at or start()
    at.text_input(key="tickers").input(tickers).run()
    at.button(key="run").click().run()
    assert not at.exception, at.exception
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
    assert "AAPL, MSFT, NKE" in at.markdown[0].value
    assert at.radio(key="incl_leases").value is False  # "Financial debt only" is the default
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
    assert ":red-background[:red[**Red: 2 red flags, 3 not available**]]" in text
    assert "Interest coverage (x)  \n**not available**" in text
    assert "interest expense not reported" in text  # the reason, under the value


def test_ratio_table_has_9_rows_per_company_with_units_and_flag_words(cache):
    at = run("ALFA, BETA")

    ratios = table(at, "ratio_table")
    assert len(ratios) == 2 * 9  # AC5
    assert list(ratios.columns[4:7]) == ["FY2024", "FY2025", "FY2026"]  # only real years (E11)
    alfa = ratios[ratios["Ticker"] == "ALFA"].set_index("Metric")
    assert alfa.loc["Debt / equity", "FY2026"] == "1.53x"
    assert alfa.loc["Debt / equity", "Latest flag"] == "orange"
    assert ratios["Unit"].isin(["USD m", "x", "%"]).all()


def test_underlying_data_shows_tags_and_accession_numbers(cache):
    at = run("ALFA")

    underlying = table(at, "underlying_table")
    revenue = underlying[(underlying["Fiscal year"] == 2026) & (underlying["Item"] == "Revenue")].iloc[0]
    assert revenue["Value (USD m)"] == "6,000 USD m"
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
    at.radio(key="incl_leases").set_value(True).run()
    assert not at.exception

    after = table(at, "ratio_table").set_index("Metric")
    # 2,000 + 300 + 200 + 400 + 100 = 3,000 (CALC2b); 2,400 / 1,200 = 2.00 (CALC4b); 3,000 / 1,500 = 2.00 (CALC5b)
    assert after.loc["Total debt (incl. leases)", "FY2026"] == "3,000 USD m"
    assert after.loc["Net debt / EBITDA (incl. leases)", "FY2026"] == "2.00x"
    assert after.loc["Debt / equity (incl. leases)", "FY2026"] == "2.00x"
    # the other ratios do not change
    for metric in ["EBITDA", "Interest coverage", "Current ratio", "EBITDA margin", "Free cash flow"]:
        assert after.loc[metric, "FY2026"] == before.loc[metric, "FY2026"]
    text = page_text(at)
    assert "Net debt / EBITDA (incl. leases) (x)  \n**2.00x**" in text  # the card switched too
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

    assert "FRGN: No annual 10-K data for FRGN." in at.error[0].value  # E10
    assert len(table(at, "ratio_table")) == 9


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
