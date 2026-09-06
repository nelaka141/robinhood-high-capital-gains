"""AssetPriceState + the bucket-1 (code/config) user-maintained JSON inputs:
  tax/paid_taxes_by_year.json, transferred_basis.json
Both stay plain JSON files in git — the bot only ever reads them, never writes them, since it
has no way to know when the user actually paid a given year's taxes or supplied a transferred
cost basis. `AssetPriceState` itself is defined here (it's the shared shape used throughout
`bot/steps.py`) but its persistence (`load_price_state`/`save_price_state`) now lives in
`bot/db.py`, backed by the SQLite state DB synced with Google Drive — see that module's
docstring for why."""
from __future__ import annotations

import json
from dataclasses import dataclass
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
