"""Pure-Python US equity market-hours/holiday check — no external dependency, no live network
call, works for any year without needing yearly updates. Used by the CLAUDE.md Execution Mode's
market-hours gate (Step 0, before anything else): if the market is fully closed (a weekend, an
NYSE holiday, or outside the 7:00 AM-8:00 PM ET extended-trading window CLAUDE.md's "Extended
Hours Execution" rule already uses), the cycle aborts before touching Robinhood or Drive at all.

Scope: this models full-day closures and the fixed daily open/close clock only. It does NOT model
NYSE's early-close (1:00 PM ET) half-days (day before Independence Day, the day after
Thanksgiving, and Christmas Eve when it falls on a weekday) — CLAUDE.md's existing Extended Hours
Execution rule has no early-close concept either, so this doesn't add one a level down from what
the rest of the document already assumes.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Dict, Tuple

MARKET_OPEN_TIME = time(7, 0)   # pre-market open, ET
MARKET_CLOSE_TIME = time(20, 0)  # after-hours close, ET


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th occurrence (1-indexed) of `weekday` (Mon=0..Sun=6) in `year`/`month`."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """The last occurrence of `weekday` in `year`/`month` (e.g. Memorial Day = last Monday of May)."""
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    d = next_month_first - timedelta(days=1)
    offset = (d.weekday() - weekday) % 7
    return d - timedelta(days=offset)


def _easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher) — Easter Sunday for `year`."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed(d: date) -> date:
    """NYSE's weekend-observance shift for a fixed-calendar-date holiday: a Saturday holiday is
    observed the preceding Friday, a Sunday holiday the following Monday."""
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    if d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def nyse_holidays(year: int) -> Dict[date, str]:
    """Every NYSE full-market-closure holiday in `year`, computed from the standard rules (not a
    hardcoded per-year date list) so this stays correct for any year without maintenance."""
    holidays: Dict[date, str] = {
        _nth_weekday_of_month(year, 1, 0, 3): "Martin Luther King Jr. Day",
        _nth_weekday_of_month(year, 2, 0, 3): "Washington's Birthday (Presidents Day)",
        _easter_sunday(year) - timedelta(days=2): "Good Friday",
        _last_weekday_of_month(year, 5, 0): "Memorial Day",
        _nth_weekday_of_month(year, 9, 0, 1): "Labor Day",
        _nth_weekday_of_month(year, 11, 3, 4): "Thanksgiving Day",
        _observed(date(year, 7, 4)): "Independence Day",
        _observed(date(year, 12, 25)): "Christmas Day",
    }
    # NYSE Rule 7.2 exception: every other fixed-date holiday shifts to the preceding Friday when
    # it falls on a Saturday, but New Year's Day does NOT — December 31 is the critical
    # month/quarter/year-end accounting date, so the market stays open that Friday. A Sunday
    # New Year's Day still shifts to the following Monday as usual (_observed handles that half).
    new_years = date(year, 1, 1)
    if new_years.weekday() != 5:
        holidays[_observed(new_years)] = "New Year's Day"
    if year >= 2022:  # NYSE added Juneteenth as a market holiday starting 2022
        holidays[_observed(date(year, 6, 19))] = "Juneteenth National Independence Day"
    return holidays


def is_market_open(dt_et: datetime) -> Tuple[bool, str]:
    """Whether the US equity market is open (including CLAUDE.md's extended-hours window) at
    `dt_et` — a naive or aware datetime already in US/Eastern local time. Returns
    (is_open, reason): reason names why it's closed, or which session is active when open."""
    if dt_et.weekday() >= 5:
        return False, f"weekend ({dt_et.strftime('%A')})"

    holidays = nyse_holidays(dt_et.year)
    d = dt_et.date()
    if d in holidays:
        return False, f"NYSE holiday ({holidays[d]})"

    t = dt_et.time()
    if not (MARKET_OPEN_TIME <= t <= MARKET_CLOSE_TIME):
        return False, "outside extended trading hours (7:00 AM-8:00 PM ET)"

    if time(9, 30) <= t <= time(16, 0):
        return True, "regular hours"
    if t < time(9, 30):
        return True, "pre-market extended hours"
    return True, "after-hours extended hours"
