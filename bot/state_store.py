"""Local read/write side of the `peak_prices` / `realized_gains_by_year` state stores.

Both used to be single git-tracked JSON files (`peak/prices.json`,
`tax/realized_gains_by_year.json`), rewritten in full every cycle. They're now dated JSON
snapshots on Google Drive instead — `peak/prices/<date>[-partN].json`,
`tax/realized_gains_by_year/<date>.json` — never git-tracked, for the same reason
`bot/price_history_store.py`'s price history moved to Drive: relaying one big ever-growing file
as inline content through the Google-Drive MCP tool on every cycle is what made the original
single-SQLite-file design unreliable.

JSON, not Parquet, on purpose: confirmed empirically (2026-09-06) that Parquet's per-column
schema/statistics footer is a FIXED cost per file — `peak_prices`' 14 columns floor out around
~1.7-1.8KB no matter how few rows are in a shard, which sits in untested territory between a
confirmed-reliable transfer (727 bytes) and a confirmed-corrupted one (5.4KB). Plain JSON has no
such per-file floor (it scales with actual data, not column count) and — being text, not binary
— can be sent via the Google-Drive MCP tool's `textContent` directly, skipping ~33% of base64
bloat AND being materially easier for the orchestrating agent to reproduce verbatim than opaque
base64. `price_history` stays Parquet+gzip (bot/price_history_store.py) because it's higher-
volume and genuinely benefits from columnar compression; these two tables are small and sparse
enough that Parquet's overhead was pure cost with no payoff.

`peak_prices` is still SHARDED (SHARD_SIZE symbols per file) because even compact JSON for the
full symbol list is comparable in size to the Parquet file that got corrupted — dropping the
Parquet floor doesn't remove the need for a safety margin, it just means far fewer shards are
needed to reach one (SHARD_SIZE=6 keeps every shard under ~800 characters against real data,
comfortably inside the confirmed-safe zone). Each symbol's dict omits any field equal to
`AssetPriceState`'s own default, shrinking the common case (an untouched symbol has almost
nothing to say) — `load_price_state` relies on the dataclass's defaults to fill in what's
omitted, so this is lossless. `realized_gains_by_year` never needs sharding — it's only ever a
handful of year->amount entries.

Per the operator's decision, these snapshots are NEVER deleted from Google Drive, even once a
newer one supersedes them for the bot's own purposes — same "keep the full archive, never purge"
policy as the price-history deltas, and a handy side effect: Drive ends up holding a complete
state-audit-trail at every past cycle.

CLAUDE.md's Execution Mode Step 1 downloads every file for the latest date in each of
`peak/prices/` and `tax/realized_gains_by_year/` from Drive into these same local paths before
`plan` runs (via `textContent`/`read_file_content`, not base64); Step 8 uploads whatever new
dated file(s) this cycle wrote back to Drive as brand new files — it never overwrites or deletes
an existing one, local or remote.
"""
from __future__ import annotations

import json
from dataclasses import asdict, fields as dataclass_fields
from datetime import date
from pathlib import Path
from typing import Dict, List

from .state import AssetPriceState

DEFAULT_PEAK_PRICES_DIR = "peak/prices"
DEFAULT_TAX_DIR = "tax/realized_gains_by_year"

# Symbols per peak_prices shard file — see the module docstring for why this exists and how it
# was chosen (every shard stays under ~800 characters against real portfolio data).
SHARD_SIZE = 6

_PRICE_STATE_DEFAULTS = {f.name: f.default for f in dataclass_fields(AssetPriceState)}


def _latest_date_files(dir_path: str | Path, suffix: str) -> List[Path]:
    """Every file sharing the lexicographically-last date prefix in `dir_path` — filenames are
    `<date>{suffix}` or `<date>-partN{suffix}`, and ISO dates sort chronologically as plain
    strings. Empty list if the directory doesn't exist or is empty (cold start — nothing has
    ever been downloaded/written yet)."""
    d = Path(dir_path)
    if not d.exists():
        return []
    by_date: Dict[str, List[Path]] = {}
    for f in d.glob(f"*{suffix}"):
        by_date.setdefault(f.name[: -len(suffix)].split("-part")[0], []).append(f)
    if not by_date:
        return []
    return sorted(by_date[max(by_date)])


def load_price_state(dir_path: str | Path = DEFAULT_PEAK_PRICES_DIR) -> Dict[str, AssetPriceState]:
    """A key absent from an entry (because it equaled the field's default when written, or
    because the file predates a future schema addition) loads as that field's own
    `AssetPriceState` default — lossless for the former, and the same forgiving posture the
    original JSON-file loader always had for the latter."""
    result: Dict[str, AssetPriceState] = {}
    for f in _latest_date_files(dir_path, ".json"):
        raw = json.loads(f.read_text())
        for symbol, fields in raw.items():
            result[symbol] = AssetPriceState(**{k: v for k, v in fields.items() if k in _PRICE_STATE_DEFAULTS})
    return result


def save_price_state(
    state: Dict[str, AssetPriceState],
    current_date: date,
    dir_path: str | Path = DEFAULT_PEAK_PRICES_DIR,
) -> List[Path]:
    """Writes `state` as one or more `<date>-partN.json` shards (SHARD_SIZE symbols each,
    omitting any field equal to its own default) and returns every path written, in order — the
    caller (bot/cli.py) reports all of them as needing upload to Drive this cycle."""
    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    symbols = list(state.items())
    shards = [symbols[i:i + SHARD_SIZE] for i in range(0, len(symbols), SHARD_SIZE)] or [[]]

    out_paths = []
    for part_num, shard in enumerate(shards, start=1):
        payload = {
            symbol: {k: v for k, v in asdict(st).items() if v != _PRICE_STATE_DEFAULTS[k]}
            for symbol, st in shard
        }
        out_path = d / f"{current_date.isoformat()}-part{part_num}.json"
        out_path.write_text(json.dumps(payload, separators=(",", ":")))
        out_paths.append(out_path)
    return out_paths


def load_tax_by_year(dir_path: str | Path = DEFAULT_TAX_DIR) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for f in _latest_date_files(dir_path, ".json"):
        result.update(json.loads(f.read_text()))
    return result


def save_tax_by_year(
    data: Dict[str, float], current_date: date, dir_path: str | Path = DEFAULT_TAX_DIR
) -> Path:
    """Never sharded — a year->amount table has at most a handful of entries, nowhere near the
    size that made peak_prices need one."""
    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    out_path = d / f"{current_date.isoformat()}.json"
    out_path.write_text(json.dumps(data, separators=(",", ":")))
    return out_path
