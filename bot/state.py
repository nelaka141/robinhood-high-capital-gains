"""Load/save the bot's persistent state files:
  peak/prices.json, tax/realized_gains_by_year.json, transferred_basis.json
These are the files CLAUDE.md Step 7 commits every cycle (whichever changed)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields as dataclass_fields
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
    lastLossSalePrice: Optional[float] = None  # price of the most recent sale that realized a
    lastLossSaleDate: Optional[str] = None     # loss (any mechanism) — basis for the wash-sale
                                                # buy-guard (Step 2): blocks repurchase for
                                                # wash_sale_lookback_days after ANY loss sale


_PRICE_STATE_FIELDS = {f.name for f in dataclass_fields(AssetPriceState)}


def load_price_state(path: str | Path = "peak/prices.json") -> Dict[str, AssetPriceState]:
    """Unknown keys in the file (e.g. the retired lastAlphaLeaderBuyPrice/Date fields written by
    pre-removal versions of this bot) are silently dropped on load — and therefore disappear from
    the file on the next save — rather than crashing the pipeline."""
    raw = json.loads(Path(path).read_text())
    return {
        sym: AssetPriceState(**{k: v for k, v in fields.items() if k in _PRICE_STATE_FIELDS})
        for sym, fields in raw.items()
    }


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
