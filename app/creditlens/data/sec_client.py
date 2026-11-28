"""Small client for the free SEC EDGAR APIs.

This module is the only place in CreditLens that talks to the internet.
It applies the SEC access rules of AGENTS.md (course rules):

* every request sends the User-Agent read from ``SEC_USER_AGENT`` in ``.env``;
* at most 10 requests per second;
* every download is cached as a JSON file in ``app/cache/``.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

# This file is app/creditlens/data/sec_client.py, so parents[2] is the app/ folder.
APP_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = APP_DIR / ".env"
CACHE_DIR = APP_DIR / "cache"

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# The SEC allows 10 requests per second. 0.11 s between requests keeps a margin.
MIN_SECONDS_BETWEEN_REQUESTS = 0.11
REQUEST_TIMEOUT_SECONDS = 30


class SecConfigError(RuntimeError):
    """Raised when the local configuration (the .env file) is incomplete."""


class TickerNotFoundError(ValueError):
    """Raised when a ticker is not in the SEC ticker list."""


class SecUnavailableError(RuntimeError):
    """Raised when a file is not in the cache and the SEC cannot provide it.

    Causes: no internet connection, no answer in time, an error status from the
    SEC (for example 503 or 429), or an answer that is not JSON. The message
    can be shown to the user as it is.
    """


class NoFinancialDataError(LookupError):
    """Raised when the SEC answers 404: it has no such file (no XBRL financial data).

    This is not an outage, so it is not a :class:`SecUnavailableError`.
    """


class CacheFileError(RuntimeError):
    """Raised when a file of the local cache cannot be read (cut or damaged).

    The message names the file to delete; the next run downloads it again.
    """


class RateLimiter:
    """Make sure two requests are never closer than ``min_interval`` seconds.

    ``clock`` and ``sleep`` can be replaced by fakes in tests, so the tests
    do not really wait.
    """

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last_request = None

    def wait(self) -> None:
        """Sleep if needed, then record the time of the new request."""
        now = self._clock()
        if self._last_request is not None:
            remaining = self.min_interval - (now - self._last_request)
            if remaining > 0:
                self._sleep(remaining)
                now = self._clock()
        self._last_request = now


_rate_limiter = RateLimiter(MIN_SECONDS_BETWEEN_REQUESTS)


def get_user_agent(env_file: Path | None = None) -> str:
    """Return the SEC User-Agent read from the ``SEC_USER_AGENT`` setting.

    The value is loaded from ``env_file`` (default: ``app/.env``) with
    python-dotenv; an environment variable that is already set wins. The SEC requires a name and an email, for example
    ``"First Last first.last@example.com"``.

    Raises:
        SecConfigError: if the setting is missing or empty.
    """
    load_dotenv(env_file or ENV_FILE)
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise SecConfigError(
            "SEC_USER_AGENT is not set. In the app/ folder, run: cp .env.example .env, "
            "then write your name and email in it, for example: "
            "SEC_USER_AGENT=First Last first.last@example.com"
        )
    return user_agent


def fetch_json(url: str, cache_file: Path, refresh: bool = False) -> dict:
    """Return the JSON at ``url``, using ``cache_file`` as a local cache.

    If ``cache_file`` exists and ``refresh`` is False, the file is read and no
    request is sent. Otherwise the URL is downloaded (with the User-Agent and
    the rate limit) and the result is saved to ``cache_file``.

    Raises:
        SecConfigError: if the User-Agent is not configured.
        SecUnavailableError: if the download fails (see that class). Nothing
            is written to the cache in that case.
    """
    if cache_file.exists() and not refresh:
        try:
            with cache_file.open(encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CacheFileError(
                f"The saved SEC file {cache_file.name} in the app/cache folder is damaged. "
                "Delete it and click Run again (the internet is needed to download it again)."
            ) from error

    headers = {"User-Agent": get_user_agent(), "Accept-Encoding": "gzip, deflate"}
    _rate_limiter.wait()
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        if isinstance(error, requests.HTTPError) and error.response is not None \
                and error.response.status_code == 404:
            raise NoFinancialDataError(
                f"SEC EDGAR has no XBRL financial data for this company ({urlparse(url).netloc} answered "
                "HTTP 404). It may be a fund, or a company that files no financial statements in XBRL."
            ) from error
        raise SecUnavailableError(_explain_download_error(url, error)) from error

    # Write to a temporary file first so an interrupted run never leaves a
    # half-written file in the cache.
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    tmp_file.replace(cache_file)
    return data


def _explain_download_error(url: str, error: requests.RequestException) -> str:
    """Turn a failed download into a message a user can read.

    The order of the checks matters: a connection timeout is both a
    ``Timeout`` and a ``ConnectionError`` in requests.
    """
    host = urlparse(url).netloc
    if isinstance(error, requests.Timeout):
        reason = f"no answer within {REQUEST_TIMEOUT_SECONDS} seconds"
        advice = "Check the internet connection and try again."
    elif isinstance(error, requests.ConnectionError):
        reason = "no internet connection"
        advice = "Check the internet connection and try again."
    elif isinstance(error, requests.HTTPError) and error.response is not None:
        reason = f"the SEC answered with HTTP status {error.response.status_code}"
        advice = "Try again in a few minutes."
    elif isinstance(error, requests.exceptions.JSONDecodeError):
        reason = "the answer was not valid JSON"
        advice = "Try again in a few minutes."
    else:
        reason = "the request failed"
        advice = "Try again in a few minutes."
    return (
        f"Could not get data from the SEC ({host}): {reason}. "
        f"No copy is saved in the cache yet, so there is no data to show. {advice}"
    )


def get_cik(ticker: str, refresh: bool = False) -> str:
    """Return the 10-digit CIK of a ticker, for example ``"AAPL"`` -> ``"0000320193"``.

    The ticker is case-insensitive and ``"BRK.B"`` is accepted for ``"BRK-B"``
    (the SEC list uses a dash).

    Raises:
        TickerNotFoundError: if the ticker is not in the SEC list.
    """
    tickers = fetch_json(TICKERS_URL, CACHE_DIR / "company_tickers.json", refresh)
    wanted = ticker.strip().upper().replace(".", "-")
    for entry in tickers.values():
        if entry["ticker"].upper() == wanted:
            return f"{int(entry['cik_str']):010d}"
    raise TickerNotFoundError(
        f"'{ticker}' is not in the SEC ticker list. Check the spelling: only companies that file reports "
        "with the SEC are covered (for example BRK-B for Berkshire Hathaway class B)."
    )


def get_company_facts(cik: str, refresh: bool = False) -> dict:
    """Return the SEC "companyfacts" JSON (all XBRL facts) of a company.

    Args:
        cik: the 10-digit CIK, as returned by :func:`get_cik`.
    """
    if not (len(cik) == 10 and cik.isdigit()):
        raise ValueError(f"CIK must have exactly 10 digits, got '{cik}'.")
    url = COMPANY_FACTS_URL.format(cik=cik)
    return fetch_json(url, CACHE_DIR / f"CIK{cik}.json", refresh)
