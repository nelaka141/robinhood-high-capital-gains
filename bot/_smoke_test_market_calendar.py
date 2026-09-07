"""Smoke test for bot/market_calendar.py (v2.88.0 market-hours gate) — not part of the package's
public surface. Run: python3 -m bot._smoke_test_market_calendar
"""
from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path

from bot import journal, market_calendar


def main() -> None:
    # --- Easter algorithm self-check against known reference dates ---
    assert market_calendar._easter_sunday(2024) == date(2024, 3, 31)
    assert market_calendar._easter_sunday(2025) == date(2025, 4, 20)
    assert market_calendar._easter_sunday(2026) == date(2026, 4, 5)
    print("[easter] matches known reference dates for 2024/2025/2026")

    # --- Weekend ---
    is_open, reason = market_calendar.is_market_open(datetime(2026, 9, 5, 10, 0))  # Saturday
    assert not is_open and "weekend" in reason, reason
    print(f"[weekend] Sat 2026-09-05 10:00 -> closed ({reason})")

    # --- Fixed-formula Monday holiday: Labor Day 2026 = Sept 7 (the real holiday this feature
    # was built in response to) ---
    is_open, reason = market_calendar.is_market_open(datetime(2026, 9, 7, 10, 30))
    assert not is_open and "Labor Day" in reason, reason
    print(f"[labor day] Mon 2026-09-07 10:30 -> closed ({reason})")

    # --- Good Friday 2026 = April 3 (2 days before Easter Sunday April 5) ---
    is_open, reason = market_calendar.is_market_open(datetime(2026, 4, 3, 10, 0))
    assert not is_open and "Good Friday" in reason, reason
    print(f"[good friday] 2026-04-03 10:00 -> closed ({reason})")

    # --- Fixed-date holiday landing on Sunday, observed the following Monday: July 4, 2027 is a
    # Sunday -> observed Monday July 5, 2027 is the actual closure, not the Sunday itself
    # (weekend already covers the Sunday). ---
    holidays_2027 = market_calendar.nyse_holidays(2027)
    assert date(2027, 7, 5) in holidays_2027, holidays_2027
    assert date(2027, 7, 4) not in holidays_2027  # the Sunday itself isn't a separate entry
    is_open, reason = market_calendar.is_market_open(datetime(2027, 7, 5, 10, 0))
    assert not is_open and "Independence Day" in reason, reason
    print(f"[observed holiday] Mon 2027-07-05 (July 4 observed) 10:00 -> closed ({reason})")

    # --- Juneteenth only from 2022 onward ---
    assert date(2021, 6, 19) not in market_calendar.nyse_holidays(2021)
    assert any("Juneteenth" in v for v in market_calendar.nyse_holidays(2022).values())
    print("[juneteenth] absent pre-2022, present 2022+")

    # --- Daily time-window boundaries on a genuine trading day (Tuesday 2026-09-08) ---
    cases = [
        (datetime(2026, 9, 8, 6, 59), False, "before pre-market"),
        (datetime(2026, 9, 8, 7, 0), True, "pre-market open boundary"),
        (datetime(2026, 9, 8, 9, 30), True, "regular open boundary"),
        (datetime(2026, 9, 8, 12, 0), True, "midday regular hours"),
        (datetime(2026, 9, 8, 16, 0), True, "regular close boundary"),
        (datetime(2026, 9, 8, 19, 59), True, "after-hours"),
        (datetime(2026, 9, 8, 20, 0), True, "after-hours close boundary"),
        (datetime(2026, 9, 8, 20, 1), False, "after the after-hours close"),
        (datetime(2026, 9, 8, 2, 0), False, "overnight"),
    ]
    for dt, expected_open, label in cases:
        is_open, reason = market_calendar.is_market_open(dt)
        assert is_open == expected_open, f"{label}: expected open={expected_open}, got {is_open} ({reason})"
    print("[time windows] all boundary cases match on a genuine trading day")

    # --- Regular trading day, well inside hours ---
    is_open, reason = market_calendar.is_market_open(datetime(2026, 9, 8, 10, 30))
    assert is_open and reason == "regular hours", reason
    print(f"[open] Tue 2026-09-08 10:30 -> open ({reason})")

    # --- journal.render_market_closed_entry + prepend_entry round-trip ---
    with tempfile.TemporaryDirectory() as tmp:
        logs_dir = Path(tmp) / "logs"
        entry_md = journal.render_market_closed_entry(datetime(2026, 9, 7, 8, 15), "NYSE holiday (Labor Day)")
        assert entry_md.startswith("# 2026-09-07")
        assert "MARKET CLOSED" in entry_md
        journal.prepend_entry(entry_md, logs_dir)
        live_text = (logs_dir / "trade_journal.md").read_text()
        assert "MARKET CLOSED" in live_text
    print("[journal] render_market_closed_entry + prepend_entry round-trip OK")

    print("\nSMOKE TEST (market_calendar) PASSED")


if __name__ == "__main__":
    main()
