"""Load and represent portfolio_targets.json — CLAUDE.md's "Core Parameters & Risk Triggers"
and per-asset `targets` / `forceSell` list."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AssetTarget:
    symbol: str
    weight: float
    drift: Optional[float] = None  # per-asset drift override, weight units; None -> global default


@dataclass(frozen=True)
class PortfolioMetadata:
    global_drift_tolerance: float
    max_trailing_drawdown_percentage: float
    min_recovery_price_percentage: float
    reinvestment_multiplier_factor: float
    max_portfolio_percentage: float
    alpha_cash_allocation_percentage: float
    min_cash_absolute: float
    min_cash_target: float
    seek_approval_value: float
    sell_price_diff_limit: float
    buy_price_diff_limit: float
    no_of_days_for_price_compare: int
    cap_on_total_cash_balance_to_use: float
    cool_down_period_after_lquidation: int
    beta_benchmark_symbol: str
    beta_calculation_lookback_days: int
    sold_asset_repurchase_days: int
    sold_asset_price_change_percentage: float
    lock_in_period: int
    overweight_sell_minimum_profit_margin_percent: float
    momentum_reversal_minimum_profit_margin_percent: float
    momentum_reversal_minimum_profit_dollars: float
    profit_resell_cooldown_days: int
    sell_or_buy_value_limit: float
    min_value_of_trade: float
    settlement_reserve_target: float
    settlement_lag_days: int
    materialize_profit_percentage: float
    profit_sell_percentage: float
    materialize_profit_in_dollars: float
    keep_aside_profits_for_tax_percent: float
    momentum_lookback_days: int
    momentum_reversal_threshold: float


@dataclass(frozen=True)
class PortfolioConfig:
    meta: PortfolioMetadata
    targets: Dict[str, AssetTarget]
    force_sell: List[str]
    blocked: List[str]  # exempt from ALL buy/sell this cycle, except forceSell + currently held -> liquidate 100%

    @property
    def sum_of_weights(self) -> float:
        return sum(t.weight for t in self.targets.values())

    def target_percentage(self, symbol: str) -> float:
        """target_percentage = (weight / sum_of_all_weights) * 100"""
        return self.targets[symbol].weight / self.sum_of_weights * 100

    def drift_tolerance(self, symbol: str) -> float:
        """asset_drift_tolerance: the asset's own `drift` override if present, else the global
        `global_drift_tolerance` — both in weight units."""
        override = self.targets[symbol].drift
        return override if override is not None else self.meta.global_drift_tolerance


# Fields present in portfolio_targets.json's portfolio_metadata that are informational only
# (not risk parameters) and shouldn't be passed into PortfolioMetadata's constructor.
_METADATA_IGNORE_KEYS = {"version", "last_updated"}


def load_portfolio_config(path: str | Path = "portfolio_targets.json") -> PortfolioConfig:
    data = json.loads(Path(path).read_text())

    meta_fields = {k: v for k, v in data["portfolio_metadata"].items() if k not in _METADATA_IGNORE_KEYS}
    meta = PortfolioMetadata(**meta_fields)

    targets = {
        sym: AssetTarget(symbol=sym, weight=t["weight"], drift=t.get("drift"))
        for sym, t in data["targets"].items()
    }

    return PortfolioConfig(
        meta=meta, targets=targets,
        force_sell=list(data.get("forceSell", [])),
        blocked=list(data.get("blocked", [])),
    )
