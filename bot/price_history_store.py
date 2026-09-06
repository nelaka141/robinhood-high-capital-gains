"""Local read/write side of the price-history cache's Parquet-delta storage.

`price_history/daily_bars.json`'s old rolling ~90-day OHLC cache used to be one git-tracked JSON
file, rewritten in full every cycle. It's now a folder of small gzip-compressed Parquet files on
Google Drive (never git-tracked), one per cycle that actually fetched new bars, named
`<date>.parquet.gz` — `date` being the run date (`current_date`), not necessarily the bars' own
dates (a brand-new symbol's first cycle writes a ~90-day backfill dated that cycle's run date).

Why Parquet deltas instead of one big file (like a single always-fully-rewritten table): price
history is fully re-derivable from Robinhood (a `get_equity_historicals` backfill) if ever lost,
unlike peak prices or tax carryover — so unlike those (see bot/state_store.py), it doesn't need
to survive as one always-fully-relayed blob. Splitting it into small per-cycle deltas means a
normal cycle only has to upload ~1 day's worth of new bars through the Google-Drive MCP tool
instead of the whole rolling window (hundreds of KB and growing) — the whole window's size is
exactly what made relaying it as inline tool-call content unreliable in the first place.

Gzip, on top of Parquet's own snappy compression, because the two compress very different things:
Parquet's per-file schema/statistics footer is fixed overhead that snappy doesn't touch, while
gzip's dictionary-based compression collapses that same footer (and the repeated symbol/date
strings across rows) hard — confirmed empirically (2026-09-06) that even an unusually large delta
(a multi-day gap after a skipped cycle, ~1,000 rows / ~14KB raw) gzips down to ~1.2KB, comfortably
inside the confirmed-safe zone for relaying as inline tool-call content (as base64 — Parquet is
binary either way, so gzip is pure benefit here, unlike bot/state_store.py's JSON tables where
gzipping would force them back into base64 and undo the point of using JSON at all).

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

import gzip
import io
from datetime import date
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from .price_cache import DailyBar

DEFAULT_LOCAL_DIR = "price_history"

# See bot/state_store.py's docstring for why these are off: pyarrow's defaults add several KB of
# fixed per-file overhead that a table this small gets no benefit from (gzip below compresses
# what's left further still).
_COMPACT_WRITE_KWARGS = dict(compression="snappy", store_schema=False, use_dictionary=False, write_statistics=False)


def load_cache_from_deltas(dir_path: str | Path = DEFAULT_LOCAL_DIR) -> Dict[str, List[DailyBar]]:
    """Reads every `*.parquet.gz` file already present in `dir_path` (the agent downloads
    whichever delta files it needs from Drive into this local directory before calling this) and
    merges them into the same in-memory cache shape `bot/price_cache.py` has always used. Files
    are processed in filename order so a later delta's bar for a given (symbol, date) — a
    same-day restatement, same as the old `merge_bars` behavior — wins over an earlier one. An
    empty/missing directory is normal (cold start, or every needed delta is still to be fetched
    this cycle) and yields an empty cache."""
    d = Path(dir_path)
    if not d.exists():
        return {}

    cache: Dict[str, List[DailyBar]] = {}
    by_symbol_date: Dict[str, Dict[str, DailyBar]] = {}
    for f in sorted(d.glob("*.parquet.gz")):
        table = pq.read_table(io.BytesIO(gzip.decompress(f.read_bytes())))
        for symbol, bar_date, close, low, high in zip(
            table["symbol"].to_pylist(), table["date"].to_pylist(),
            table["close"].to_pylist(), table["low"].to_pylist(), table["high"].to_pylist(),
        ):
            by_symbol_date.setdefault(symbol, {})[bar_date] = DailyBar(
                date=bar_date, close=close, low=low, high=high
            )

    for symbol, by_date in by_symbol_date.items():
        cache[symbol] = [by_date[d] for d in sorted(by_date)]
    return cache


def write_delta_parquet(
    new_bars: Dict[str, List[dict]], current_date: date, dir_path: str | Path = DEFAULT_LOCAL_DIR
) -> List[Path]:
    """Writes THIS CYCLE's freshly fetched bars only (i.e. `fetched_bars.json`'s content, not the
    full merged cache) as one small gzip-compressed Parquet file, `<current_date>.parquet.gz`.
    Returns an empty list (writes nothing) if `new_bars` is empty — a cycle where every symbol
    was already up to date has nothing new to persist, so there's nothing for the agent to
    upload to Drive either. Always returns at most one path — a list for symmetry with
    bot/state_store.py's sharded snapshots, not because this ever needs more than one file
    (gzip keeps even an unusually large multi-day gap-fill well within the safe-to-relay size)."""
    rows = [
        (symbol, bar["date"], float(bar["close"]), float(bar["low"]), float(bar["high"]))
        for symbol, bars in new_bars.items()
        for bar in bars
    ]
    if not rows:
        return []

    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    out_path = d / f"{current_date.isoformat()}.parquet.gz"
    table = pa.table({
        "symbol": [r[0] for r in rows],
        "date": [r[1] for r in rows],
        "close": [r[2] for r in rows],
        "low": [r[3] for r in rows],
        "high": [r[4] for r in rows],
    })
    buf = io.BytesIO()
    pq.write_table(table, buf, **_COMPACT_WRITE_KWARGS)
    out_path.write_bytes(gzip.compress(buf.getvalue(), compresslevel=9))
    return [out_path]
