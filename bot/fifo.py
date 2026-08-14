"""FIFO lot-matched realized-profit accounting for PARTIAL sales — CLAUDE.md Step 4's
"Dollar-gate accounting for PARTIAL sales" rule. `avg_cost_basis` is a whole-position blended
average and understates/overstates the true realized gain on a sale that disposes of less than
100% of a position; the dollar gate (`materialize_profit_in_dollars`)
must be checked against the FIFO figure computed
here, not the avg_cost_basis estimate."""
from __future__ import annotations

import math
from typing import List

from .models import FifoSaleResult, TaxLot


def round_sell_quantity(desired_quantity: float, available_quantity: float) -> float:
    """Rounds a partial-sale target quantity to the nearest whole share, capped at the whole
    shares actually held (never rounds up past what's available).

    Discovered 2026-08-04: this broker's `place_equity_order` rejects a specified-lot
    (`tax_lots`) sell whose top-level order `quantity` is fractional — even though the same
    account trades fractional shares freely on an ordinary (non-specified-lot) order, and even
    though `review_equity_order` does not simulate/catch the rejection. Every GET THE PROFITS
    quantity is `position_quantity * profit_sell_percentage / 100`, which
    almost never lands on a whole-share boundary, so every specified-lot partial sale must be
    rounded *before* `fifo_realized_profit` walks the lots — rounding after the fact would
    desync the dollar-gate figure (`materialize_profit_in_dollars`)
    from what actually gets sold.

    Returns 0.0 if the rounded quantity is 0 (position too small for `profit_sell_percentage` to
    round to at least one whole share) — the caller must skip the sale in that case rather than
    place a zero-quantity order.
    """
    return max(0.0, min(round(desired_quantity), math.floor(available_quantity)))


def fifo_realized_profit(lots: List[TaxLot], sell_quantity: float, current_price: float) -> FifoSaleResult:
    """Walk tax lots oldest-open_date-first, consuming exactly `sell_quantity` shares, and
    compute the FIFO-matched realized dollar profit for that sale.

    Skips any lot with is_selectable=False or cost_per_share=None (still syncing/pending). If
    that leaves insufficient priced+selectable quantity to cover `sell_quantity`,
    `fully_covered` is False — per CLAUDE.md's Fail-Closed rule, the caller must then treat
    every cost-basis-dependent gate for this sale as NOT satisfied this cycle.
    """
    usable = sorted(
        (lot for lot in lots if lot.is_selectable and lot.cost_per_share is not None),
        key=lambda lot: lot.open_date,
    )

    remaining = sell_quantity
    realized = 0.0
    consumed = []
    for lot in usable:
        if remaining <= 1e-9:
            break
        take = min(lot.quantity, remaining)
        if take <= 0:
            continue
        realized += (current_price - lot.cost_per_share) * take
        consumed.append({
            "open_lot_id": lot.open_lot_id,
            "quantity": take,
            "cost_per_share": lot.cost_per_share,
        })
        remaining -= take

    fully_covered = remaining <= 1e-9
    return FifoSaleResult(
        realized_profit_dollars=realized if fully_covered else 0.0,
        lots_consumed=consumed if fully_covered else [],
        quantity_sold=sell_quantity - max(remaining, 0.0),
        fully_covered=fully_covered,
    )
