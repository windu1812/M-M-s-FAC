"""Shared pytest setup.

Every test runs offline and isolated (AGENTS.md course rules):

* ``requests.get`` is replaced by a function that fails, so a test that
  tries to reach the internet fails loudly;
* the SEC cache points to a temporary folder, never to ``app/cache/``;
* the real ``.env`` is never read; a fake User-Agent is set instead.
"""

import json
from pathlib import Path

import pytest
import requests

from creditlens.data import sec_client

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_USER_AGENT = "CreditLens tests tests@example.com"


@pytest.fixture(autouse=True)
def offline_and_isolated(monkeypatch, tmp_path):
    """Block the internet, isolate the cache and the .env file for every test."""

    def blocked_get(*args, **kwargs):
        raise RuntimeError("Tests must not call the internet (AGENTS.md course rules).")

    monkeypatch.setattr(requests, "get", blocked_get)
    monkeypatch.setattr(sec_client, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(sec_client, "ENV_FILE", tmp_path / "no-such.env")
    monkeypatch.setenv("SEC_USER_AGENT", TEST_USER_AGENT)


@pytest.fixture
def test_user_agent() -> str:
    """The fake User-Agent set for every test."""
    return TEST_USER_AGENT


@pytest.fixture
def fixtures_dir() -> Path:
    """Folder with the saved sample files."""
    return FIXTURES_DIR


@pytest.fixture
def sample_facts() -> dict:
    """Synthetic companyfacts JSON (see app/tests/fixtures/companyfacts_sample.json)."""
    with (FIXTURES_DIR / "companyfacts_sample.json").open(encoding="utf-8") as f:
        return json.load(f)
