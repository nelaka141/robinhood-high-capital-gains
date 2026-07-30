"""FIFO lot-matched realized-profit accounting for PARTIAL sales — CLAUDE.md Step 4's
"Dollar-gate accounting for PARTIAL sales" rule. `avg_cost_basis` is a whole-position blended
average and understates/overstates the true realized gain on a sale that disposes of less than
100% of a position; the dollar gates (`materialize_profit_in_dollars`,
`momentum_reversal_minimum_profit_dollars`) must be checked against the FIFO figure computed
here, not the avg_cost_basis estimate."""
from __future__ import annotations

from typing import List

from .models import FifoSaleResult, TaxLot


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
