"""Persistent rolling ~90-day daily-bar price cache: `price_history/daily_bars.json`.

Lets the orchestrating agent avoid re-fetching a full ~90-day `get_equity_historicals` window
for every target symbol (+ the beta benchmark) on every cycle. Instead:

  1. `python3 -m bot.cli price-cache-plan`   — tells the agent exactly which symbols need a
     fetch and what date range: a full ~LOOKBACK_DAYS-day backfill only for a symbol that's
     missing/empty from the cache (a new target, or the cache was never built), otherwise just
     the day(s) since the last cached bar (normally 1 day if the bot ran yesterday, more if a
     cycle was skipped).
  2. Agent fetches only what's asked for via `get_equity_historicals`.
  3. `python3 -m bot.cli price-cache-merge`  — merges the freshly fetched bars into the cache,
     prunes bars older than the rolling window, and emits `daily_closes`/`daily_lows_highs`
     pre-sliced to the last ~LOOKBACK_DAYS calendar days, ready to drop straight into
     `snapshot.json`.

See bot/README.md, "Price history cache", for the full CLI usage and CLAUDE.md's Execution
Mode Step 2 for how the agent drives this each cycle.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

LOOKBACK_DAYS = 90    # calendar days of history the snapshot needs (CLAUDE.md's ~90-day window)
PRUNE_BUFFER_DAYS = 10  # extra slack kept in the cache beyond LOOKBACK_DAYS before a bar is pruned


@dataclass
class DailyBar:
    date: str
    close: float
    low: float
    high: float


def load_price_cache(path: str | Path = "price_history/daily_bars.json") -> Dict[str, List[DailyBar]]:
    p = Path(path)
    if not p.exists():
        return {}
    raw = json.loads(p.read_text())
    return {sym: [DailyBar(**b) for b in bars] for sym, bars in raw.items()}


def save_price_cache(cache: Dict[str, List[DailyBar]], path: str | Path = "price_history/daily_bars.json") -> None:
    payload = {
        sym: [{"date": b.date, "close": b.close, "low": b.low, "high": b.high} for b in bars]
        for sym, bars in cache.items()
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def cache_symbols(cfg) -> List[str]:
    """Every symbol the snapshot's daily_closes/daily_lows_highs needs: all portfolio targets
    plus the beta benchmark (CLAUDE.md Step 2 — "every target symbol PLUS beta_benchmark_symbol")."""
    return sorted(set(cfg.targets.keys()) | {cfg.meta.beta_benchmark_symbol})


def plan_fetches(cache: Dict[str, List[DailyBar]], symbols: List[str], current_date: date) -> dict:
    """For each symbol: no fetch needed (cache already covers through yesterday), an
    incremental fetch (from the day after the latest cached bar through yesterday), or a full
    ~LOOKBACK_DAYS-day backfill (symbol missing/empty from the cache entirely). Symbols needing
    the same date range are grouped into one `fetch_batches` entry so the agent can batch its
    `get_equity_historicals` calls the normal way."""
    yesterday = current_date - timedelta(days=1)
    batches: Dict[Tuple[str, str], List[str]] = {}
    up_to_date: List[str] = []

    for sym in symbols:
        bars = cache.get(sym, [])
        if not bars:
            start = current_date - timedelta(days=LOOKBACK_DAYS)
            end = yesterday
        else:
            latest = max(date.fromisoformat(b.date) for b in bars)
            if latest >= yesterday:
                up_to_date.append(sym)
                continue
            start = latest + timedelta(days=1)
            end = yesterday
        batches.setdefault((start.isoformat(), end.isoformat()), []).append(sym)

    fetch_batches = [
        {"start_date": s, "end_date": e, "symbols": sorted(syms)}
        for (s, e), syms in sorted(batches.items())
    ]
    return {"fetch_batches": fetch_batches, "up_to_date": sorted(up_to_date)}


def merge_bars(cache: Dict[str, List[DailyBar]], new_bars: Dict[str, List[dict]]) -> None:
    """Union newly fetched bars into the cache by date, per symbol. A freshly fetched bar
    overwrites any existing same-date entry (handles a rare same-day restatement)."""
    for sym, bars in new_bars.items():
        by_date = {b.date: b for b in cache.get(sym, [])}
        for raw in bars:
            by_date[raw["date"]] = DailyBar(
                date=raw["date"], close=float(raw["close"]), low=float(raw["low"]), high=float(raw["high"])
            )
        cache[sym] = [by_date[d] for d in sorted(by_date)]


def prune_cache(cache: Dict[str, List[DailyBar]], current_date: date) -> None:
    """Drop bars older than the rolling window (LOOKBACK_DAYS + a small buffer) so the
    git-tracked cache file doesn't grow unbounded."""
    cutoff = (current_date - timedelta(days=LOOKBACK_DAYS + PRUNE_BUFFER_DAYS)).isoformat()
    for sym in list(cache.keys()):
        cache[sym] = [b for b in cache[sym] if b.date >= cutoff]


def slice_for_snapshot(cache: Dict[str, List[DailyBar]], current_date: date) -> Tuple[dict, dict]:
    """daily_closes / daily_lows_highs sliced to the last LOOKBACK_DAYS calendar days, in the
    exact snapshot.json schema shape (bot/README.md)."""
    cutoff = (current_date - timedelta(days=LOOKBACK_DAYS)).isoformat()
    daily_closes, daily_lows_highs = {}, {}
    for sym, bars in cache.items():
        in_window = [b for b in bars if b.date >= cutoff]
        daily_closes[sym] = [{"date": b.date, "close": b.close} for b in in_window]
        daily_lows_highs[sym] = [{"date": b.date, "low": b.low, "high": b.high} for b in in_window]
    return daily_closes, daily_lows_highs
