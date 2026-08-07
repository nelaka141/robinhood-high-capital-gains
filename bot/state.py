"""Load/save the bot's persistent state files:
  peak/prices.json, settlement/reserve.json, tax/realized_gains_by_year.json,
  transferred_basis.json
These are the four files CLAUDE.md Step 7 commits every cycle (whichever changed)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


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


def load_price_state(path: str | Path = "peak/prices.json") -> Dict[str, AssetPriceState]:
    raw = json.loads(Path(path).read_text())
    return {sym: AssetPriceState(**fields) for sym, fields in raw.items()}


def save_price_state(state: Dict[str, AssetPriceState], path: str | Path = "peak/prices.json") -> None:
    payload = {sym: asdict(s) for sym, s in state.items()}
    Path(path).write_text(json.dumps(payload, indent="\t") + "\n")


@dataclass
class PendingDraw:
    """One entry in settlement/reserve.json's pending_draws array."""
    saleDate: str
    expectedSettleDate: str
    reserveDrawn: float
    saleProceeds: float
    settled: bool = False
    symbol: Optional[str] = None


@dataclass
class SettlementReserve:
    pending_draws: List[PendingDraw] = field(default_factory=list)


def load_settlement_reserve(path: str | Path = "settlement/reserve.json") -> SettlementReserve:
    raw = json.loads(Path(path).read_text())
    draws = [PendingDraw(**d) for d in raw.get("pending_draws", [])]
    return SettlementReserve(pending_draws=draws)


def save_settlement_reserve(reserve: SettlementReserve, path: str | Path = "settlement/reserve.json") -> None:
    # Step 1: settled entries are removed from pending_draws entirely (they "return" the capital).
    still_pending = [d for d in reserve.pending_draws if not d.settled]
    payload = {"pending_draws": [asdict(d) for d in still_pending]}
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")


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
class AlphaReserve:
    """alpha_reserve.json — cash set aside for the Alpha Leader when its Step 3 multiplier
    allocation couldn't be deployed this cycle (buy-guarded, a same-cycle sell of the same
    symbol, a price-limit halt, etc.), instead of being redirected to Underweight targets. A
    fresh snapshot every cycle (never cumulative) tied to whichever symbol is Alpha Leader
    today — see CLAUDE.md Step 3, "Alpha Reserve"."""
    symbol: Optional[str] = None
    amount: float = 0.0
    lastUpdatedDate: Optional[str] = None


def load_alpha_reserve(path: str | Path = "alpha_reserve.json") -> AlphaReserve:
    p = Path(path)
    if not p.exists():
        return AlphaReserve()
    return AlphaReserve(**json.loads(p.read_text()))


def save_alpha_reserve(reserve: AlphaReserve, path: str | Path = "alpha_reserve.json") -> None:
    Path(path).write_text(json.dumps(asdict(reserve), indent=2) + "\n")
