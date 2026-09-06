"""Load/save the bot's persistent state files:
  peak/prices.json, tax/realized_gains_by_year.json, tax/paid_taxes_by_year.json,
  transferred_basis.json
These are the files CLAUDE.md Step 7 commits every cycle (whichever changed) — except
tax/paid_taxes_by_year.json, which (like transferred_basis.json) is purely user-maintained: the
bot only ever reads it, never writes it, since it has no way to know when the user actually paid
a given year's taxes."""
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
    # v2.84.0 — Deferred Wash-Sale Loss Tracking (Step 7, observational only). Stamped by a
    # net-profit full exit (Step 4, v2.83.0) that disposed of an underwater lot inside a net-gain
    # sale: the size of that lot's loss, its share count, and the exit date. Read by Step 7 when
    # the symbol is bought back inside wash_sale_lookback_days — the IRS defers that loss into the
    # new lot's basis and Robinhood applies the adjustment itself, so the bot only journals it
    # and verifies it; it never adjusts any basis figure of its own.
    lastNettedLossDollars: Optional[float] = None   # positive magnitude, e.g. 29.44
    lastNettedLossShares: Optional[float] = None
    lastNettedLossDate: Optional[str] = None
    washVerifyPending: Optional[dict] = None        # {"purchaseDate", "buyQuotePrice",
                                                    #  "expectedLossDollars", "exitDate",
                                                    #  "exitShares"} — set on the in-window
                                                    # repurchase, cleared once verified/expired


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


def load_paid_taxes_by_year(path: str | Path = "tax/paid_taxes_by_year.json") -> Dict[str, float]:
    """{ "2026": 20000.00, ... } — user-maintained record of actual taxes paid per calendar year,
    manually edited (never auto-cleared/decayed, same posture as realized_gains_by_year.json's
    manual-clearing model). Every entry across ALL years is summed and subtracted, dollar-for-
    dollar, from the percentage-based tax_reserve figure (see steps.py's `_compute_tax_reserve`)
    — the reserve still ramps as a percentage of realized gains, but money already paid out no
    longer needs to be held aside on top of that. Missing file/empty dict is normal (no taxes
    recorded as paid yet)."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def load_transferred_basis(path: str | Path = "transferred_basis.json") -> Dict[str, dict]:
    """{ "SYMBOL": {"quantity": <shares>, "cost_per_share": <usd>}, ... } — user-supplied basis
    for transferred-in shares Robinhood hasn't reconciled yet. Empty file/dict is normal."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())
