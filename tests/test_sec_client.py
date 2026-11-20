"""Tests for src/data/sec_client.py (no internet: see conftest.py)."""

import json
import shutil

import pytest

from src.data import sec_client


class FakeClock:
    """Fake time: ``sleep`` moves the clock forward instead of waiting."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def tickers_in_cache(fixtures_dir):
    """Put the sample ticker list in the (temporary) cache."""
    sec_client.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        fixtures_dir / "company_tickers_sample.json",
        sec_client.CACHE_DIR / "company_tickers.json",
    )


# --- User-Agent ------------------------------------------------------------


def test_user_agent_is_read_from_environment(test_user_agent):
    assert sec_client.get_user_agent() == test_user_agent


def test_user_agent_is_read_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("SEC_USER_AGENT")
    env_file = tmp_path / ".env"
    env_file.write_text("SEC_USER_AGENT=From File file@example.com\n")
    assert sec_client.get_user_agent(env_file) == "From File file@example.com"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_user_agent_raises_clear_error(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("SEC_USER_AGENT")
    else:
        monkeypatch.setenv("SEC_USER_AGENT", value)
    with pytest.raises(sec_client.SecConfigError, match="SEC_USER_AGENT"):
        sec_client.get_user_agent()


# --- Rate limit --------------------------------------------------------------


def test_rate_limiter_first_request_does_not_wait():
    fake = FakeClock()
    limiter = sec_client.RateLimiter(0.11, fake.clock, fake.sleep)
    limiter.wait()
    assert fake.sleeps == []


def test_rate_limiter_waits_when_requests_are_too_close():
    fake = FakeClock()
    limiter = sec_client.RateLimiter(0.11, fake.clock, fake.sleep)
    limiter.wait()
    fake.now += 0.05
    limiter.wait()
    assert fake.sleeps == [pytest.approx(0.06)]


def test_rate_limiter_never_exceeds_10_requests_per_second():
    fake = FakeClock()
    limiter = sec_client.RateLimiter(
        sec_client.MIN_SECONDS_BETWEEN_REQUESTS, fake.clock, fake.sleep
    )
    request_times = []
    for _ in range(50):  # 50 requests sent back to back
        limiter.wait()
        request_times.append(fake.now)
    for t in request_times:
        in_one_second = [u for u in request_times if t <= u < t + 1.0]
        assert len(in_one_second) <= 10


# --- Download and cache ------------------------------------------------------


def test_fetch_json_uses_cache_without_calling_internet(tmp_path):
    cache_file = tmp_path / "cached.json"
    cache_file.write_text('{"from": "cache"}')
    # requests.get is blocked by conftest: this would fail if it was called.
    assert sec_client.fetch_json("https://data.sec.gov/x.json", cache_file) == {"from": "cache"}


def test_fetch_json_downloads_with_user_agent_then_caches(monkeypatch, tmp_path, test_user_agent):
    calls = []

    def fake_get(url, headers, timeout):
        calls.append({"url": url, "headers": headers})
        return FakeResponse({"hello": "world"})

    fake = FakeClock()
    monkeypatch.setattr(sec_client.requests, "get", fake_get)
    monkeypatch.setattr(
        sec_client, "_rate_limiter", sec_client.RateLimiter(0.11, fake.clock, fake.sleep)
    )
    cache_file = tmp_path / "sub" / "data.json"

    data = sec_client.fetch_json("https://data.sec.gov/x.json", cache_file)

    assert data == {"hello": "world"}
    assert calls[0]["headers"]["User-Agent"] == test_user_agent
    assert json.loads(cache_file.read_text()) == {"hello": "world"}

    sec_client.fetch_json("https://data.sec.gov/x.json", cache_file)
    assert len(calls) == 1  # second call served from the cache

    sec_client.fetch_json("https://data.sec.gov/x.json", cache_file, refresh=True)
    assert len(calls) == 2  # refresh=True downloads again


def test_fetch_json_without_user_agent_sends_nothing(monkeypatch, tmp_path):
    monkeypatch.delenv("SEC_USER_AGENT")
    with pytest.raises(sec_client.SecConfigError):
        sec_client.fetch_json("https://data.sec.gov/x.json", tmp_path / "x.json")


# --- Ticker -> CIK -----------------------------------------------------------


def test_get_cik_returns_10_digits(tickers_in_cache):
    assert sec_client.get_cik("AAPL") == "0000320193"
    assert sec_client.get_cik("MSFT") == "0000789019"


def test_get_cik_ignores_case_spaces_and_dot(tickers_in_cache):
    assert sec_client.get_cik(" nke ") == "0000320187"
    assert sec_client.get_cik("BRK.B") == "0001067983"


def test_get_cik_unknown_ticker_raises(tickers_in_cache):
    with pytest.raises(sec_client.TickerNotFoundError, match="ZZZZ"):
        sec_client.get_cik("ZZZZ")


# --- companyfacts ------------------------------------------------------------


def test_get_company_facts_builds_url_and_cache_name(monkeypatch):
    captured = {}

    def fake_fetch_json(url, cache_file, refresh=False):
        captured.update(url=url, cache_file=cache_file)
        return {}

    monkeypatch.setattr(sec_client, "fetch_json", fake_fetch_json)
    sec_client.get_company_facts("0000320193")

    assert captured["url"] == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
    assert captured["cache_file"] == sec_client.CACHE_DIR / "CIK0000320193.json"


@pytest.mark.parametrize("bad_cik", ["320193", "AAPL000000", "00003201930"])
def test_get_company_facts_rejects_bad_cik(bad_cik):
    with pytest.raises(ValueError, match="10 digits"):
        sec_client.get_company_facts(bad_cik)
