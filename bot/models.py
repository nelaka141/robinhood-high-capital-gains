"""Shared value objects passed between pipeline steps. `RunContext` is threaded through
Steps 1-6 in order and accumulates everything Step 7 (journal/git/email) needs to report."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .config import PortfolioConfig
    from .state import AssetPriceState, SettlementReserve


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
class RunContext:
    """Accumulates state across Step 1..7; passed through the pipeline in strict order."""
    current_date: date
    config: "PortfolioConfig"
    account_number: str

    price_state: Dict[str, "AssetPriceState"] = field(default_factory=dict)
    positions: Dict[str, Position] = field(default_factory=dict)
    quotes: Dict[str, Quote] = field(default_factory=dict)

    account_cash: float = 0.0          # buying_power (settled, spendable) = account_cash/current_cash source
    account_cash_ledger: float = 0.0   # raw 'cash' (can include unsettled proceeds)
    current_cash: float = 0.0          # min(account_cash, cap_on_total_cash_balance_to_use + settlement_reserve_target)
    account_balance: float = 0.0       # equity market value + current_cash

    reserve: "SettlementReserve" = None  # type: ignore[assignment]
    reserve_available_to_draw: float = 0.0

    tax_by_year: Dict[str, float] = field(default_factory=dict)
    net_realized_gains_ytd_pretrade: float = 0.0
    net_realized_gains_ytd_effective: Optional[float] = None
    tax_reserve: float = 0.0

    drift_results: Dict[str, DriftResult] = field(default_factory=dict)
    excluded_symbols: Dict[str, str] = field(default_factory=dict)      # fully out of play (liquidation/full-exit)
    buy_guarded_symbols: Dict[str, str] = field(default_factory=dict)   # buys blocked, otherwise in play

    momentum_scores: Dict[str, MomentumScore] = field(default_factory=dict)
    alpha_leader: Optional[str] = None

    drawdown_liquidations: List[str] = field(default_factory=list)
    profit_taking_sells: List[TradeIntent] = field(default_factory=list)  # GET THE PROFITS + Momentum Reversal Trim
    overweight_trims: List[TradeIntent] = field(default_factory=list)
    buys: List[TradeIntent] = field(default_factory=list)

    skipped: List[SkippedTrade] = field(default_factory=list)
    executed_orders: List[dict] = field(default_factory=list)

    total_high_beta_gains_realized: float = 0.0
    high_beta_gain_rows: List[dict] = field(default_factory=list)
