"""Green / orange / red flags of CreditLens (slice 4, issue #7).

Main entry points:

* :func:`load_thresholds` reads ``app/config/thresholds.toml``;
* :func:`apply_flags` gives each ratio of a year a flag;
* :func:`overall_alert` gives one company its overall alert, for the latest
  fiscal year and the selected debt version.

Input: the table of :func:`creditlens.ratios.compute_ratios` (contract of
docs/architecture.md): one row per (ticker, fiscal year, metric), ratios in
times (x), the EBITDA margin in percent (20.0 = 20 %), amounts in USD m.

Rules (docs/acceptance.md, agreed on 2026-11-20):

* The thresholds live in the TOML file only, never in this code (AC6).
* A value exactly on a limit takes the better colour.
* The value is compared as it is shown on screen (ratios 2 decimals, margin
  1 decimal, amounts 0 decimals), so a cell that reads "2.00x" is never orange
  when the limit is 2.0.
* The same thresholds apply to both debt versions: ``net_debt_to_ebitda`` and
  ``net_debt_to_ebitda_incl_leases`` use the ``[net_debt_to_ebitda]`` section.
* A row that is "not available" or "not meaningful" has no value, so no flag
  (empty text). Amounts (EBITDA, total debt, net debt) get no flag either.
* Overall alert: red if at least one ratio is red, otherwise orange if at least
  one is orange, otherwise green. "Not available" ratios do not count as red,
  but the alert text says how many there are.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DEFAULT_THRESHOLDS_PATH = Path(__file__).resolve().parent.parent / "config" / "thresholds.toml"

GREEN = "green"
ORANGE = "orange"
RED = "red"
NO_FLAG = ""

LOWER_IS_BETTER = "lower_is_better"
HIGHER_IS_BETTER = "higher_is_better"
DIRECTIONS = (LOWER_IS_BETTER, HIGHER_IS_BETTER)

STATUS_OK = "ok"
STATUS_NOT_AVAILABLE = "not available"
STATUS_NOT_MEANINGFUL = "not meaningful"

INCL_LEASES = "_incl_leases"

# The 6 ratios that get a flag, in the order of the table. The first two
# exist in two debt versions (add INCL_LEASES for the second one).
FLAGGED_RATIOS = [
    "net_debt_to_ebitda",
    "debt_to_equity",
    "interest_coverage",
    "current_ratio",
    "ebitda_margin",
    "free_cash_flow",
]
DEBT_BASED_RATIOS = ["net_debt_to_ebitda", "debt_to_equity"]

# Decimals shown on screen for each unit (docs/product.md, "Display rounding").
DISPLAY_DECIMALS = {"x": 2, "%": 1, "USD m": 0}

REQUIRED_COLUMNS = ["ticker", "fiscal_year", "metric", "value", "unit", "status"]
ALLOWED_KEYS = {"label", "direction", "green", "orange"}


# --- Thresholds file -------------------------------------------------------------


def _number(section: str, key: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"thresholds.toml, [{section}]: '{key}' must be a number, got {value!r}.")
    return float(value)


def _check_rule(section: str, raw: dict) -> dict:
    """Check one section of the file and return it as a clean dict."""
    unknown = set(raw) - ALLOWED_KEYS
    if unknown:
        raise ValueError(
            f"thresholds.toml, [{section}]: unknown key(s) {sorted(unknown)}. "
            f"Allowed keys: {sorted(ALLOWED_KEYS)}."
        )
    direction = raw.get("direction")
    if direction not in DIRECTIONS:
        raise ValueError(
            f"thresholds.toml, [{section}]: direction must be \"{LOWER_IS_BETTER}\" or "
            f"\"{HIGHER_IS_BETTER}\", got {direction!r}."
        )
    if "green" not in raw:
        raise ValueError(f"thresholds.toml, [{section}]: the 'green' limit is missing.")
    green = _number(section, "green", raw["green"])
    orange = None
    if "orange" in raw:
        orange = _number(section, "orange", raw["orange"])
        if direction == LOWER_IS_BETTER and orange < green:
            raise ValueError(
                f"thresholds.toml, [{section}]: lower is better, so the orange limit ({orange}) "
                f"must be at least the green limit ({green})."
            )
        if direction == HIGHER_IS_BETTER and orange > green:
            raise ValueError(
                f"thresholds.toml, [{section}]: higher is better, so the orange limit ({orange}) "
                f"must be at most the green limit ({green})."
            )
    label = str(raw.get("label", section.replace("_", " ").capitalize()))
    return {"label": label, "direction": direction, "green": green, "orange": orange}


def load_thresholds(path: str | Path | None = None) -> dict[str, dict]:
    """Read and check the thresholds file.

    Args:
        path: the TOML file; by default ``app/config/thresholds.toml``.

    Returns:
        ratio name -> {"label", "direction", "green", "orange"}; "orange" is
        None when the ratio has no orange zone (free cash flow).

    Raises:
        ValueError: with a readable message if the file is not valid TOML, a
            ratio is missing, or a limit is wrong. A wrong flag is worse than
            no flag, so the app stops instead of guessing.
    """
    path = Path(path) if path is not None else DEFAULT_THRESHOLDS_PATH
    try:
        with path.open("rb") as f:
            raw = tomllib.load(f)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"thresholds.toml ({path}) is not valid TOML: {error}") from error

    missing = [ratio for ratio in FLAGGED_RATIOS if ratio not in raw]
    if missing:
        raise ValueError(f"thresholds.toml ({path}): no section for {missing}.")
    return {ratio: _check_rule(ratio, raw[ratio]) for ratio in FLAGGED_RATIOS}


# --- Flags -----------------------------------------------------------------------


def flagged_metrics(incl_leases: bool = False) -> list[str]:
    """The 6 metric names that get a flag, for one debt version."""
    suffix = INCL_LEASES if incl_leases else ""
    return [ratio + suffix if ratio in DEBT_BASED_RATIOS else ratio for ratio in FLAGGED_RATIOS]


def _ratio_of(metric: str) -> str | None:
    """The thresholds section of a metric, or None if the metric gets no flag."""
    base = metric.removesuffix(INCL_LEASES)
    if base in FLAGGED_RATIOS and (metric == base or base in DEBT_BASED_RATIOS):
        return base
    return None


def flag_for(value: float, unit: str, rule: dict) -> str:
    """The colour of one value, compared as it is shown on screen."""
    shown = round(value, DISPLAY_DECIMALS.get(unit, 2))
    green, orange = rule["green"], rule["orange"]
    if rule["direction"] == LOWER_IS_BETTER:
        if shown <= green:
            return GREEN
        if orange is not None and shown <= orange:
            return ORANGE
        return RED
    if shown >= green:
        return GREEN
    if orange is not None and shown >= orange:
        return ORANGE
    return RED


def apply_flags(ratios: pd.DataFrame, thresholds: dict | None = None) -> pd.DataFrame:
    """Add a ``flag`` column to the ratios table.

    Args:
        ratios: the table of ratios.compute_ratios (one or several companies).
        thresholds: the result of :func:`load_thresholds`; by default the
            real file is read.

    Returns:
        A copy of ``ratios`` with the same rows, plus ``flag``: "green",
        "orange", "red", or "" when the row has no value or is an amount.

    Raises:
        ValueError: if a column is missing, or an "ok" ratio has no value.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in ratios.columns]
    if missing:
        raise ValueError(f"apply_flags: the ratios table has no column {missing}.")
    if thresholds is None:
        thresholds = load_thresholds()

    result = ratios.copy()
    colours = []
    for _, row in result.iterrows():
        ratio = _ratio_of(row["metric"])
        if ratio is None or row["status"] != STATUS_OK:
            colours.append(NO_FLAG)
            continue
        if pd.isna(row["value"]):
            raise ValueError(
                f"apply_flags: {row['ticker']} {row['fiscal_year']} {row['metric']} is \"ok\" "
                "but has no value. A missing value must be \"not available\"."
            )
        colours.append(flag_for(float(row["value"]), row["unit"], thresholds[ratio]))
    result["flag"] = colours
    return result


# --- Overall alert -----------------------------------------------------------------


@dataclass(frozen=True)
class Alert:
    """The overall alert of one company, for its latest fiscal year."""

    level: str  # "green", "orange", "red", or "" when no ratio has a flag
    text: str  # for example "Red: 2 red flags, 1 not available"
    fiscal_year: int
    green: int
    orange: int
    red: int
    not_available: int
    not_meaningful: int


def _count(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def overall_alert(flagged: pd.DataFrame, ticker: str, incl_leases: bool = False) -> Alert:
    """The overall alert of one company.

    Args:
        flagged: the table returned by :func:`apply_flags`.
        ticker: the company.
        incl_leases: False for "Financial debt only" (the default), True for
            "Including leases and short-term borrowings".

    Returns:
        An :class:`Alert` for the latest fiscal year of ``ticker``, built on
        the 6 flagged ratios of the selected debt version.

    Raises:
        ValueError: if ``flagged`` has no ``flag`` column or no row for ``ticker``.
    """
    if "flag" not in flagged.columns:
        raise ValueError("overall_alert: the table has no 'flag' column; call apply_flags first.")
    company = flagged[flagged["ticker"] == ticker]
    if company.empty:
        raise ValueError(f"overall_alert: no ratios for {ticker}.")

    fiscal_year = int(company["fiscal_year"].max())
    year = company[(company["fiscal_year"] == fiscal_year) & company["metric"].isin(flagged_metrics(incl_leases))]

    counts = {
        GREEN: int((year["flag"] == GREEN).sum()),
        ORANGE: int((year["flag"] == ORANGE).sum()),
        RED: int((year["flag"] == RED).sum()),
    }
    not_available = int((year["status"] == STATUS_NOT_AVAILABLE).sum())
    not_meaningful = int((year["status"] == STATUS_NOT_MEANINGFUL).sum())

    if counts[RED]:
        level = RED
    elif counts[ORANGE]:
        level = ORANGE
    elif counts[GREEN]:
        level = GREEN
    else:
        level = NO_FLAG  # nothing could be flagged: never say "green" in that case

    parts = [_count(counts[level], f"{level} flag")] if level else []
    if not_available:
        parts.append(f"{not_available} not available")
    if not_meaningful:
        parts.append(f"{not_meaningful} not meaningful")
    title = level.capitalize() if level else "No flag"
    text = f"{title}: {', '.join(parts)}" if parts else title

    return Alert(
        level=level,
        text=text,
        fiscal_year=fiscal_year,
        green=counts[GREEN],
        orange=counts[ORANGE],
        red=counts[RED],
        not_available=not_available,
        not_meaningful=not_meaningful,
    )
