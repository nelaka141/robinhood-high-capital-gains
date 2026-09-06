"""Integration test for the price-history cache CLI (`price-cache-plan` / `price-cache-merge`)
that lets the orchestrating agent avoid re-fetching a full ~90-day get_equity_historicals
window for every target symbol on every cycle. Exercises, via subprocess (matching
_smoke_test_cli.py's style):

  1. Cold cache -> plan asks for a full ~90-day backfill for every symbol.
  2. Merge in fetched bars -> cache file written, daily_closes/daily_lows_highs sliced back out.
  3. Re-plan the next day -> only a 1-day incremental fetch is requested (cache already covers
     everything through "yesterday" from the first run).
  4. A brand-new symbol (simulating a portfolio_targets.json addition) -> full backfill for
     just that symbol, existing symbols stay incremental-only.

Run: PYTHONPATH=. python3 bot/_smoke_test_price_cache.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "bot.cli", *args],
        cwd=REPO, capture_output=True, text=True, env={"PYTHONPATH": str(REPO)},
    )


def fake_bars(symbols, start: date, end: date) -> dict:
    out = {}
    d = start
    for sym in symbols:
        out[sym] = []
    while d <= end:
        for i, sym in enumerate(symbols):
            p = 100.0 + i * 7.3
            out[sym].append({"date": d.isoformat(), "close": round(p, 4), "low": round(p * 0.98, 4), "high": round(p * 1.02, 4)})
        d += timedelta(days=1)
    return out


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cfg = json.loads((REPO / "portfolio_targets.json").read_text())
        (tmp / "portfolio_targets.json").write_text(json.dumps(cfg))
        symbols = sorted(set(cfg["targets"].keys()) | {cfg["portfolio_metadata"]["beta_benchmark_symbol"]})

        day1 = date(2026, 8, 6)

        # --- 1. Cold cache: everything needs a full ~90-day backfill ---
        plan1_out = tmp / "plan1.json"
        r = run("price-cache-plan", "--repo-dir", str(tmp), "--current-date", day1.isoformat(), "--out", str(plan1_out))
        assert r.returncode == 0, r.stderr
        plan1 = json.loads(plan1_out.read_text())
        assert plan1["up_to_date"] == [], "cold cache should have nothing up to date"
        fetched_symbols = {s for b in plan1["fetch_batches"] for s in b["symbols"]}
        assert fetched_symbols == set(symbols), f"expected all {len(symbols)} symbols in fetch_batches, got {len(fetched_symbols)}"
        for b in plan1["fetch_batches"]:
            span = (date.fromisoformat(b["end_date"]) - date.fromisoformat(b["start_date"])).days
            assert 85 <= span <= 91, f"expected ~90-day full backfill, got {span}-day span"
        print(f"[1] cold cache -> full backfill requested for all {len(fetched_symbols)} symbols")

        # --- 2. Merge in fetched bars ---
        start = day1 - timedelta(days=90)
        bars = fake_bars(symbols, start, day1 - timedelta(days=1))
        bars_path = tmp / "fetched_bars.json"
        bars_path.write_text(json.dumps(bars))
        merge1_out = tmp / "merge1.json"
        r = run("price-cache-merge", "--repo-dir", str(tmp), "--current-date", day1.isoformat(),
                "--bars-in", str(bars_path), "--out", str(merge1_out))
        assert r.returncode == 0, r.stderr
        assert (tmp / "price_history" / "daily_bars.json").exists()
        merge1 = json.loads(merge1_out.read_text())
        assert set(merge1["daily_closes"].keys()) == set(symbols)
        assert len(merge1["daily_closes"]["SPY" if "SPY" in symbols else symbols[0]]) > 0
        print(f"[2] merge OK -> price_history/daily_bars.json written, "
              f"{len(merge1['daily_closes'][symbols[0]])} bars sliced for {symbols[0]}")

        # --- 3. Next day: only an incremental fetch is needed ---
        day2 = day1 + timedelta(days=1)
        plan2_out = tmp / "plan2.json"
        r = run("price-cache-plan", "--repo-dir", str(tmp), "--current-date", day2.isoformat(), "--out", str(plan2_out))
        assert r.returncode == 0, r.stderr
        plan2 = json.loads(plan2_out.read_text())
        assert plan2["up_to_date"] == [], "day-1 bars don't cover day2's 'yesterday' yet"
        for b in plan2["fetch_batches"]:
            assert b["start_date"] == b["end_date"] == day1.isoformat(), \
                f"expected a single-day incremental fetch for {day1.isoformat()}, got {b['start_date']}..{b['end_date']}"
        print(f"[3] next-day plan -> incremental 1-day fetch only (not a full re-fetch)")

        # merge day2's single day in, then re-plan same-day -> should be fully up to date
        day2_bars = fake_bars(symbols, day1, day1)
        day2_bars_path = tmp / "fetched_bars2.json"
        day2_bars_path.write_text(json.dumps(day2_bars))
        merge2_out = tmp / "merge2.json"
        r = run("price-cache-merge", "--repo-dir", str(tmp), "--current-date", day2.isoformat(),
                "--bars-in", str(day2_bars_path), "--out", str(merge2_out))
        assert r.returncode == 0, r.stderr

        plan3_out = tmp / "plan3.json"
        r = run("price-cache-plan", "--repo-dir", str(tmp), "--current-date", day2.isoformat(), "--out", str(plan3_out))
        assert r.returncode == 0, r.stderr
        plan3 = json.loads(plan3_out.read_text())
        assert plan3["fetch_batches"] == [], "cache should now be fully up to date for day2"
        assert set(plan3["up_to_date"]) == set(symbols)
        print(f"[3b] same-day re-plan -> fully up to date, zero fetch_batches")

        # --- 4. A brand-new symbol needs its own full backfill; existing symbols stay incremental ---
        cfg2 = json.loads(json.dumps(cfg))
        cfg2["targets"]["ZZZZ"] = {"weight": 1.0, "drift": 0.5}
        (tmp / "portfolio_targets.json").write_text(json.dumps(cfg2))
        day3 = day2 + timedelta(days=1)
        plan4_out = tmp / "plan4.json"
        r = run("price-cache-plan", "--repo-dir", str(tmp), "--current-date", day3.isoformat(), "--out", str(plan4_out))
        assert r.returncode == 0, r.stderr
        plan4 = json.loads(plan4_out.read_text())
        batches_by_symbols = {tuple(sorted(b["symbols"])): b for b in plan4["fetch_batches"]}
        zzzz_batch = next(b for b in plan4["fetch_batches"] if "ZZZZ" in b["symbols"])
        assert len(zzzz_batch["symbols"]) == 1, "new symbol should get its own isolated full-backfill batch"
        span = (date.fromisoformat(zzzz_batch["end_date"]) - date.fromisoformat(zzzz_batch["start_date"])).days
        assert 85 <= span <= 91, f"new symbol should get a full ~90-day backfill, got {span}-day span"
        other_batches = [b for b in plan4["fetch_batches"] if "ZZZZ" not in b["symbols"]]
        for b in other_batches:
            assert b["start_date"] == b["end_date"] == day2.isoformat(), "existing symbols should stay incremental-only"
        print(f"[4] new symbol ZZZZ -> isolated full backfill; {len(symbols)} existing symbols stay incremental")

        print("\nSMOKE TEST (PRICE CACHE) PASSED — cold-start full backfill, incremental "
              "day-over-day fetch, and new-symbol isolation all behave correctly.")


if __name__ == "__main__":
    main()
