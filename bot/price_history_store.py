"""Local read/write side of the price-history cache's JSON-delta storage.

`price_history/daily_bars.json`'s old rolling ~90-day OHLC cache used to be one git-tracked JSON
file, rewritten in full every cycle. It's now a folder of small JSON delta files on Google Drive
(never git-tracked), one per cycle that actually fetched new bars, named `<date>.json` — `date`
being the run date (`current_date`), not necessarily the bars' own dates (a brand-new symbol's
first cycle writes a ~90-day backfill dated that cycle's run date).

Why deltas instead of one big file: price history is fully re-derivable from Robinhood (a
`get_equity_historicals` backfill) if ever lost, unlike peak prices or tax carryover (see
bot/state_store.py) — so it doesn't need to survive as one always-fully-relayed blob. Splitting
it into small per-cycle deltas means a normal cycle only has to upload ~1 day's worth of new bars
through the Google-Drive MCP tool instead of the whole rolling window.

Plain JSON, not Parquet — confirmed empirically (2026-09-06) that the actual source of
unreliability was base64-encoded binary content (both a documented class of Google Drive API
bugs around base64 writes, and the orchestrating agent having to reproduce an opaque several-KB
base64 string verbatim inside a tool call — exactly what silently corrupted one Parquet upload
that day, caught only by a post-upload hash check), not file size — Drive's real ceiling is
30MB, nowhere near where that corruption happened. Plain JSON sent as `textContent` needs no
base64 at all and is far more reliable to relay verbatim (a dropped brace or truncated string
tends to surface as a loud parse failure, not silently-wrong data). No shard/row-count limit is
applied here for the same reason bot/state_store.py dropped its symbol sharding — a large delta
(a multi-day gap after a skipped cycle, or several brand-new symbols backfilling ~90 days at
once) is still a comfortably reproducible amount of plain text, nowhere near Drive's actual
limit.

Per the operator's decision, DELTA FILES ARE NEVER DELETED FROM DRIVE, even once their bars fall
outside the bot's ~90-day rolling window — Drive is meant to hold the full historical archive,
distinct from the trailing window this module reconstructs into memory for the bot's own
calculations. CLAUDE.md's Execution Mode Step 2 only ever downloads the delta files whose
filename-date falls within the rolling window (`LOOKBACK_DAYS + PRUNE_BUFFER_DAYS` of
`current_date` — see `bot/price_cache.py`) into the local `price_history/` directory before this
module reads them — this module itself never talks to Drive and never deletes anything, local or
remote.

See bot/price_cache.py for the pure in-memory cache logic (DailyBar, plan_fetches, merge_bars,
prune_cache, slice_for_snapshot) — unaffected by this storage change.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, List

from .price_cache import DailyBar

DEFAULT_LOCAL_DIR = "price_history"


def load_cache_from_deltas(dir_path: str | Path = DEFAULT_LOCAL_DIR) -> Dict[str, List[DailyBar]]:
    """Reads every `*.json` file already present in `dir_path` (the agent downloads whichever
    delta files it needs from Drive into this local directory before calling this) and merges
    them into the same in-memory cache shape `bot/price_cache.py` has always used. Files are
    processed in filename order so a later delta's bar for a given (symbol, date) — a same-day
    restatement, same as the old `merge_bars` behavior — wins over an earlier one. An
    empty/missing directory is normal (cold start, or every needed delta is still to be fetched
    this cycle) and yields an empty cache."""
    d = Path(dir_path)
    if not d.exists():
        return {}

    cache: Dict[str, List[DailyBar]] = {}
    by_symbol_date: Dict[str, Dict[str, DailyBar]] = {}
    for f in sorted(d.glob("*.json")):
        raw = json.loads(f.read_text())
        for symbol, bars in raw.items():
            for bar in bars:
                by_symbol_date.setdefault(symbol, {})[bar["date"]] = DailyBar(
                    date=bar["date"], close=bar["close"], low=bar["low"], high=bar["high"]
                )

    for symbol, by_date in by_symbol_date.items():
        cache[symbol] = [by_date[d] for d in sorted(by_date)]
    return cache


def write_delta_json(
    new_bars: Dict[str, List[dict]], current_date: date, dir_path: str | Path = DEFAULT_LOCAL_DIR
) -> List[Path]:
    """Writes THIS CYCLE's freshly fetched bars only (i.e. `fetched_bars.json`'s content, not the
    full merged cache) as one small JSON file, `<current_date>.json`. Returns an empty list
    (writes nothing) if `new_bars` is empty — a cycle where every symbol was already up to date
    has nothing new to persist, so there's nothing for the agent to upload to Drive either."""
    if not new_bars:
        return []

    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    out_path = d / f"{current_date.isoformat()}.json"
    payload = {
        symbol: [
            {"date": bar["date"], "close": float(bar["close"]), "low": float(bar["low"]), "high": float(bar["high"])}
            for bar in bars
        ]
        for symbol, bars in new_bars.items()
    }
    out_path.write_text(json.dumps(payload, separators=(",", ":")))
    return [out_path]
