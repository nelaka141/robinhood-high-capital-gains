"""Load/save the bot's persistent state files:
  peak/prices.json, tax/realized_gains_by_year.json, transferred_basis.json
These are the files CLAUDE.md Step 7 commits every cycle (whichever changed)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class AssetPriceState:
    """One entry in peak/prices.json, keyed by symbol."""
    peakPrice: Optional[float] = None
    peakDate: Optional[str] = None
    liquidatedPrice: Optional[float] = ""   # "" (not null) is the repo's "never liquidated" convention
    liquidatedDate: Optional[str] = None
    profitSellPrice: Optional[float] = None
    profitSellDate: Optional[str] = None
    lastPurchaseDate: Optional[str] = None
    lastAlphaLeaderBuyPrice: Optional[float] = None  # price of the most recent buy fired while
    lastAlphaLeaderBuyDate: Optional[str] = None     # this symbol was the acting Alpha Leader —
                                                      # basis for the Fresh Alpha Leader Stop (Step 1)


def load_price_state(path: str | Path = "peak/prices.json") -> Dict[str, AssetPriceState]:
    raw = json.loads(Path(path).read_text())
    return {sym: AssetPriceState(**fields) for sym, fields in raw.items()}


def save_price_state(state: Dict[str, AssetPriceState], path: str | Path = "peak/prices.json") -> None:
    payload = {sym: asdict(s) for sym, s in state.items()}
    Path(path).write_text(json.dumps(payload, indent="\t") + "\n")


def load_tax_by_year(path: str | Path = "tax/realized_gains_by_year.json") -> Dict[str, float]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def save_tax_by_year(data: Dict[str, float], path: str | Path = "tax/realized_gains_by_year.json") -> None:
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def load_transferred_basis(path: str | Path = "transferred_basis.json") -> Dict[str, dict]:
    """{ "SYMBOL": {"quantity": <shares>, "cost_per_share": <usd>}, ... } — user-supplied basis
    for transferred-in shares Robinhood hasn't reconciled yet. Empty file/dict is normal."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


@dataclass
class AlphaLeaderReserve:
    """alpha_reserve.json — a per-cycle AUDIT RECORD of Step 3's Alpha Leader buy-guard cascade
    and the resulting reserve: how much of the Top Momentum Symbol's would-be allocation is
    sitting aside (unspent, not redirected to Underweight targets) because it was buy-guarded
    and either no fallback qualified, or a fallback qualified but didn't need the full amount.
    Recalculated FROM SCRATCH every cycle (CLAUDE.md Step 3, "Alpha Leader Reserve") — unlike
    the pre-cascade design, nothing here is ever read back in to influence a future cycle's
    calculation; this file exists purely for the trade journal / audit trail."""
    date: Optional[str] = None
    top_momentum_symbol: Optional[str] = None
    alpha_leader_symbol: Optional[str] = None  # the acting Alpha Leader this cycle, if any
    reserve_cash: float = 0.0


def save_alpha_leader_reserve(
    reserve: AlphaLeaderReserve, path: str | Path = "alpha_reserve.json"
) -> None:
    Path(path).write_text(json.dumps(asdict(reserve), indent=2) + "\n")
