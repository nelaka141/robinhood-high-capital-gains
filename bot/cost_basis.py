"""CLAUDE.md Step 1's `avg_cost_basis` sourcing waterfall: primary -> tax-lots -> transferred-
basis override -> fail closed. Resolves the average cost of the ENTIRE position (every share
held), never a partial/guessed figure."""
from __future__ import annotations

from typing import Dict, List, Optional

from .models import TaxLot


def resolve_avg_cost_basis(
    symbol: str,
    position_quantity: float,
    primary_avg_cost_basis: Optional[float],
    tax_lots: List[TaxLot],
    transferred_basis: Dict[str, dict],
    quantity_tolerance: float = 1e-4,
) -> Optional[float]:
    """Returns the resolved avg_cost_basis, or None if it can't be fully reconciled — the
    caller must then treat every cost-basis-dependent gate for `symbol` as NOT satisfied this
    cycle (Drawdown Audit cost-basis leg, overweight/GTP/MRT profit gates, High-Beta raw-gain
    score) and log the asset as SKIPPED (cost basis pending transfer). Drift/Overweight/
    Underweight sizing is unaffected — it uses market value only.
    """
    # 1. Primary: get_equity_positions.average_buy_price, if populated.
    if primary_avg_cost_basis is not None:
        return primary_avg_cost_basis

    # 2. Tax-lots, only when primary is null — reconcile coverage first.
    priced_lots = [lot for lot in tax_lots if lot.cost_per_share is not None]
    covered_qty = sum(lot.quantity for lot in priced_lots)

    if abs(covered_qty - position_quantity) <= quantity_tolerance:
        total_cost = sum(lot.quantity * lot.cost_per_share for lot in priced_lots)
        return total_cost / covered_qty if covered_qty else None

    # 3. Shortfall -> transferred_basis.json override, only if the combined quantity reconciles.
    override = transferred_basis.get(symbol)
    if override:
        combined_qty = covered_qty + override["quantity"]
        if abs(combined_qty - position_quantity) <= quantity_tolerance:
            total_cost = (
                sum(lot.quantity * lot.cost_per_share for lot in priced_lots)
                + override["quantity"] * override["cost_per_share"]
            )
            return total_cost / combined_qty

    # 4. Fail closed.
    return None
