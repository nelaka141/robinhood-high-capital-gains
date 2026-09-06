"""Local read/write side of the `peak_prices` / `realized_gains_by_year` state stores.

Both used to be single git-tracked JSON files (`peak/prices.json`,
`tax/realized_gains_by_year.json`), rewritten in full every cycle. They're now dated JSON
snapshots on Google Drive instead — `peak/prices/<date>.json`,
`tax/realized_gains_by_year/<date>.json` — never git-tracked, for the same reason
`bot/price_history_store.py`'s price history moved to Drive: relaying an ever-growing file as
inline content through the Google-Drive MCP tool on every cycle is what made the original
single-SQLite-file design unreliable.

JSON, not Parquet, on purpose — and no base64 for either of these two tables, only plain text
(`textContent`): confirmed empirically (2026-09-06) that base64-encoded binary content is where
the actual unreliability lives — both a documented class of Google Drive API bugs around base64
writes, and (independently) the orchestrating agent having to reproduce an opaque several-KB
base64 string verbatim inside a tool call, which is exactly what silently corrupted one Parquet
upload that day (caught only by a post-upload hash check). Google Drive's real size ceiling is
30MB, nowhere near where that corruption happened — so the fix isn't "make files small," it's
"don't force binary/base64 where plain text will do." Plain JSON sent as `textContent` sidesteps
both problems at once, and structural JSON errors (a dropped brace, a truncated string) tend to
surface as a loud parse failure rather than silently-wrong data, unlike a single flipped base64
character. Each symbol's dict omits any field equal to `AssetPriceState`'s own default, shrinking
the common case (an untouched symbol has almost nothing to say) — `load_price_state` relies on
the dataclass's defaults to fill in what's omitted, so this is lossless. Neither table is sharded
— a realistic full `peak_prices` snapshot is a few KB of plain text, comfortably within what the
agent can reproduce reliably as `textContent`, and `realized_gains_by_year` is smaller still.

Per the operator's decision, these snapshots are NEVER deleted from Google Drive, even once a
newer one supersedes them for the bot's own purposes — same "keep the full archive, never purge"
policy as the price-history deltas, and a handy side effect: Drive ends up holding a complete
state-audit-trail at every past cycle.

CLAUDE.md's Execution Mode Step 1 downloads the latest-dated file in each of `peak/prices/` and
`tax/realized_gains_by_year/` from Drive into these same local paths before `plan` runs (via
`textContent`/`read_file_content`, never base64); Step 8 uploads whatever new dated file this
cycle wrote back to Drive as a brand new file — it never overwrites or deletes an existing one,
local or remote. (An older deployment of this bot sharded `peak_prices` across several
`<date>-partN.json` files per cycle — `load_price_state` still transparently merges those if it
ever encounters them, since they're indistinguishable from any other same-date file, but nothing
writes that shape anymore.)
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

_PRICE_STATE_DEFAULTS = {f.name: f.default for f in dataclass_fields(AssetPriceState)}


def _latest_date_files(dir_path: str | Path, suffix: str) -> List[Path]:
    """Every file sharing the lexicographically-last date prefix in `dir_path` — filenames are
    `<date>{suffix}` or (an older deployment's) `<date>-partN{suffix}`, and ISO dates sort
    chronologically as plain strings. Empty list if the directory doesn't exist or is empty
    (cold start — nothing has ever been downloaded/written yet)."""
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
    """Writes `state` as one `<date>.json` file (omitting any field equal to its own default)
    and returns its path in a single-element list — the caller (bot/cli.py) reports it as
    needing upload to Drive this cycle. A list, not a single path, for interface symmetry with
    bot/price_history_store.py's delta writer, not because this ever needs more than one file."""
    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        symbol: {k: v for k, v in asdict(st).items() if v != _PRICE_STATE_DEFAULTS[k]}
        for symbol, st in state.items()
    }
    out_path = d / f"{current_date.isoformat()}.json"
    out_path.write_text(json.dumps(payload, separators=(",", ":")))
    return [out_path]


def load_tax_by_year(dir_path: str | Path = DEFAULT_TAX_DIR) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for f in _latest_date_files(dir_path, ".json"):
        result.update(json.loads(f.read_text()))
    return result


def save_tax_by_year(
    data: Dict[str, float], current_date: date, dir_path: str | Path = DEFAULT_TAX_DIR
) -> Path:
    d = Path(dir_path)
    d.mkdir(parents=True, exist_ok=True)
    out_path = d / f"{current_date.isoformat()}.json"
    out_path.write_text(json.dumps(data, separators=(",", ":")))
    return out_path
