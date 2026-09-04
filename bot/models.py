"""Shared value objects passed between pipeline steps. `RunContext` is threaded through
Steps 1-6 in order and accumulates everything Step 7 (journal/git/email) needs to report."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .config import PortfolioConfig
    from .state import AssetPriceState


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost_basis: Optional[float]  # None => cost basis unresolved -> fail closed on this symbol's sell gates


@dataclass
class Quote:
    symbol: str
    last_trade_price: float


@dataclass
class TaxLot:
    open_lot_id: str
    quantity: float
    cost_per_share: Optional[float]
    open_date: date
    is_selectable: bool = True


@dataclass
class DriftResult:
    symbol: str
    current_percentage: float
    actual_weight: float
    target_weight: float
    target_percentage: float
    drift: float                 # abs(target_weight - actual_weight), weight units
    asset_drift_tolerance: float # resolved per-asset tolerance, weight units
    market_value: float

    @property
    def breached(self) -> bool:
        return self.drift > self.asset_drift_tolerance

    @property
    def is_overweight(self) -> bool:
        return self.actual_weight > self.target_weight

    @property
    def is_underweight(self) -> bool:
        return self.target_weight > self.actual_weight


@dataclass
class MomentumScore:
    symbol: str
    rsi14: float
    ema9_now: float
    ema9_prior: float
    price_vs_ema_pct: float
    ema_slope_pct: float

    @property
    def score(self) -> float:
        """Momentum_Score = Price_vs_EMA_Pct + EMA_Slope_Pct + (RSI14 - 50)"""
        return self.price_vs_ema_pct + self.ema_slope_pct + (self.rsi14 - 50)


@dataclass
class FifoSaleResult:
    realized_profit_dollars: float
    lots_consumed: List[dict]     # [{"open_lot_id", "quantity", "cost_per_share"}, ...]
    quantity_sold: float
    fully_covered: bool           # False => not enough priced/selectable lots -> fail closed


@dataclass
class TradeIntent:
    symbol: str
    side: str                       # "buy" | "sell"
    dollar_amount: Optional[float] = None
    quantity: Optional[float] = None
    reason: str = ""
    tax_lots: Optional[List[dict]] = None          # sells only: [{"open_lot_id", "quantity"}, ...]
    realized_profit_dollars: Optional[float] = None  # sells only: FIFO-matched realized gain
    beta: Optional[float] = None
    raw_gain_pct: Optional[float] = None


@dataclass
class SkippedTrade:
    symbol: str
    reason: str
    would_be_action: str


@dataclass
class DormantAsset:
    """A currently-held target asset with no recent trading activity — Step 7 reporting only,
    see `dormant_asset_days`. Never influences any buy/sell decision."""
    symbol: str
    days_since_activity: Optional[int]  # None => no lastPurchaseDate/profitSellDate on record at all
    last_activity_date: Optional[str]   # ISO date string, or None to match days_since_activity
    unrealized_dollars: float
    unrealized_pct: float


@dataclass
class LossOnlyAsset:
    """A currently-held target asset whose EVERY sellable lot is underwater at today's price —
    Step 7 reporting only, never influences any buy/sell decision.

    This is the population the v2.75.0 loss-lot sell guard can never sell any part of: with no
    profitable lot to fall back on, GET THE PROFITS is structurally unable to fire, so the
    position can only leave the portfolio via an emergency stop or a manual/off-platform action.
    Computed AFTER this cycle's buys are sized, so a symbol bought this cycle is excluded — its
    fresh at-market lot means it no longer holds only losing lots.

    Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's
    blended `avg_cost_basis`, so they can never contradict this list's own membership test. The
    two disagree in practice — e.g. a position whose `average_buy_price` reads below the current
    price while every real lot sits above it — so `basis_mismatch` flags that divergence rather
    than silently presenting one number as the other."""
    symbol: str
    quantity: float
    avg_cost_basis: float       # broker's blended average, for reference
    lot_weighted_cost: float    # Σ(qty × cost) / Σ(qty) over the priced lots — the basis used below
    current_price: float
    market_value: float
    unrealized_dollars: float   # lot basis
    unrealized_pct: float       # lot basis
    lot_count: int              # sellable+priced lots, all of them underwater
    worst_lot_cost: float       # highest cost_per_share held (furthest underwater)
    best_lot_cost: float        # lowest cost_per_share held (closest to breakeven)
    basis_mismatch: bool        # broker avg_cost_basis materially disagrees with lot_weighted_cost


@dataclass
class RunContext:
    """Accumulates state across Step 1..7; passed through the pipeline in strict order."""
    current_date: date
    config: "PortfolioConfig"
    account_number: str

    price_state: Dict[str, "AssetPriceState"] = field(default_factory=dict)
    positions: Dict[str, Position] = field(default_factory=dict)
    quotes: Dict[str, Quote] = field(default_factory=dict)

    account_cash: float = 0.0          # buying_power (with limited margin enabled, already reflects
                                        # unsettled proceeds immediately) = account_cash/current_cash source
    account_cash_ledger: float = 0.0   # raw 'cash' (informational only)
    current_cash: float = 0.0          # min(account_cash, cap_on_total_cash_balance_to_use)
    account_balance: float = 0.0       # equity market value + current_cash

    tax_by_year: Dict[str, float] = field(default_factory=dict)
    paid_taxes_by_year: Dict[str, float] = field(default_factory=dict)  # user-maintained,
        # tax/paid_taxes_by_year.json — subtracted dollar-for-dollar from tax_reserve
    net_realized_gains_ytd_pretrade: float = 0.0
    net_realized_gains_ytd_effective: Optional[float] = None
    tax_reserve: float = 0.0

    drift_results: Dict[str, DriftResult] = field(default_factory=dict)
    excluded_symbols: Dict[str, str] = field(default_factory=dict)      # fully out of play (liquidation/full-exit)
    buy_guarded_symbols: Dict[str, List[str]] = field(default_factory=dict)  # buys blocked, otherwise in play —
                                                                          # one reason string per guard mechanism
                                                                          # active for that symbol (a symbol can be
                                                                          # caught by more than one at once). Gates
                                                                          # every new buy: Underweight fills and
                                                                          # profit-sell repurchases alike.
    blocked_symbols: Dict[str, str] = field(default_factory=dict)       # `blocked` list — exempt from ALL buy/sell
                                                                          # this cycle (drawdown, GET THE PROFITS,
                                                                          # Underweight buys), including
                                                                          # any symbol liquidated via blocked_liquidations

    momentum_scores: Dict[str, MomentumScore] = field(default_factory=dict)  # ranks the
                                                                          # Underweight fill order (Step 3)

    position_cap_topups: Dict[str, float] = field(default_factory=dict)  # v2.80.0 — Step 3
        # Position Cap Top-Up: symbol -> extra dollars allocated beyond its normal drift-gap
        # fill, out of cash left over after the momentum-ranked top-down fill, toward that
        # symbol's configured max_position_value. Reporting-only breakdown; the dollars
        # themselves are already folded into step3_underweight_buys's returned allocations dict
        # and flow through Step 5/6 exactly like any other planned buy.

    blocked_liquidations: List[str] = field(default_factory=list)  # blocked AND forceSell AND held -> liquidate 100%
    drawdown_liquidations: List[str] = field(default_factory=list)
    loss_sale_symbols: List[str] = field(default_factory=list)  # any sell this cycle (any
        # mechanism) that realized a loss -> Step 7 stamps lastLossSaleDate/Price, arming the
        # wash-sale buy-guard (Step 2) for wash_sale_lookback_days
    profit_taking_sells: List[TradeIntent] = field(default_factory=list)  # GET THE PROFITS
    cleanup_sells: List[TradeIntent] = field(default_factory=list)  # v2.80.0 — Step 4b Sell
        # Cleanup Pass: full-remainder sells of small/single-lot green positions, bypassing every
        # GET THE PROFITS profit gate. Tracked separately from profit_taking_sells so the two
        # mechanisms report distinctly in the journal even though both realize a profit.
    buys: List[TradeIntent] = field(default_factory=list)

    skipped: List[SkippedTrade] = field(default_factory=list)
    executed_orders: List[dict] = field(default_factory=list)

    total_high_beta_gains_realized: float = 0.0
    total_cleanup_gains_realized: float = 0.0  # v2.80.0 — sum of ctx.cleanup_sells' realized
        # dollars; kept separate from total_high_beta_gains_realized (GET THE PROFITS only, per
        # CLAUDE.md's existing definition of that metric)
    high_beta_gain_rows: List[dict] = field(default_factory=list)

    dormant_assets: List["DormantAsset"] = field(default_factory=list)  # Step 7 reporting only
    loss_only_assets: List["LossOnlyAsset"] = field(default_factory=list)  # Step 7 reporting only
