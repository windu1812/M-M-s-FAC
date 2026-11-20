"""Walking-skeleton tests: the dashboard page starts and shows its first states.

Streamlit's AppTest runs the page without a browser and without internet.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_FILE = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_page_starts_and_shows_the_empty_state():
    at = AppTest.from_file(str(APP_FILE)).run()

    assert not at.exception
    assert at.title[0].value == "CreditLens"
    assert at.text_input(key="tickers").value == ""
    assert at.button(key="run").label == "Run"
    assert "AAPL, MSFT, NKE" in at.markdown[0].value


def test_run_button_answers_without_error():
    at = AppTest.from_file(str(APP_FILE)).run()

    at.text_input(key="tickers").input("AAPL").run()
    at.button(key="run").click().run()

    assert not at.exception
    assert "not built yet" in at.info[0].value
