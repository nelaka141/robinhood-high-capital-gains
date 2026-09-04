"""Load and represent portfolio_targets.json — CLAUDE.md's "Core Parameters & Risk Triggers"
and per-asset `targets` / `forceSell` list."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AssetTarget:
    symbol: str
    weight: float
    drift: Optional[float] = None  # per-asset drift override, weight units; None -> global default
    max_allocation_percent: Optional[float] = None  # per-asset cap override, percent of
        # account_balance; None -> global max_portfolio_percentage default
    max_position_value: Optional[float] = None  # v2.80.0: optional flat dollar cap on this
        # asset's own market value (existing holdings + everything planned this cycle). Unlike
        # max_allocation_percent (a percent-of-account_balance cap enforced on the normal
        # drift-gap fill), this is a Step 3 Position Cap Top-Up target — a distinct mechanism
        # that spends any deployable cash LEFT OVER after the momentum-ranked top-down fill by
        # topping the asset's market value up toward this dollar figure. None -> the asset never
        # participates in the top-up pass (its normal drift-gap fill is unaffected either way).


@dataclass(frozen=True)
class ForceSellEntry:
    asset: str
    trigger_price: Optional[float] = None  # None -> sell at whatever the current price is


@dataclass(frozen=True)
class SectorGroup:
    members: List[str]
    max_percentage: Optional[float] = None  # per-group override; None -> global max_sector_percentage


@dataclass(frozen=True)
class PortfolioMetadata:
    global_drift_tolerance: float
    max_trailing_drawdown_percentage: float
    min_recovery_price_percentage: float
    max_portfolio_percentage: float
    min_cash_absolute: float
    min_cash_target: float
    seek_approval_value: float
    sell_price_diff_limit: float
    buy_price_diff_limit: float
    fifty_two_week_high_guard: float  # JSON key: 52_week_high_guard
    no_of_days_for_price_compare: int
    cap_on_total_cash_balance_to_use: float
    cool_down_period_after_lquidation: int
    beta_benchmark_symbol: str
    beta_calculation_lookback_days: int
    sold_asset_repurchase_days: int
    leg1_price_change: float  # JSON key: 1st_leg_price_change
    leg2_price_change: float  # JSON key: 2nd_leg_price_change
    leg3_price_change: float  # JSON key: 3rd_leg_price_change
    lock_in_period: int  # retained but inert: the only routine sell (GET THE PROFITS) and the
        # emergency liquidations all override it — no remaining sell path consults it
    overweight_sell_minimum_profit_margin_percent: float  # retained but inert: Overweight trims
    overweight_sell_minimum_profit_margin_dollars: float  # no longer exist as a sell mechanism
    profit_resell_cooldown_days: int
    selling_price_change: float
    sell_or_buy_value_limit: float
    min_value_of_trade: float
    materialize_profit_percentage: float  # v2.78.0: the day-0 floor of the dynamic ramp — see
        # materialize_profit_percentage_max below; not a flat bar anymore
    profit_sell_percentage: float
    materialize_profit_in_dollars: float  # v2.78.0: same — the day-0 floor of the dynamic ramp,
        # see materialize_profit_in_dollars_max below
    min_raw_gain_percent_to_sell: float  # v2.77.0: floor on the position's OVERALL
        # blended-average raw_gain_pct required for GET THE PROFITS to fire at all — on top of,
        # not instead of, the percent/dollar OR-gate and the per-sold-lot profit check. Closes
        # the gap the v2.75.0 loss-lot sell guard opened: without this, GTP can cherry-pick a
        # losing position's few profitable lots and fire even while the position as a whole is
        # underwater or only marginally ahead.
    keep_aside_profits_for_tax_percent: float
    momentum_lookback_days: int
    min_momentum_score_to_fill_underweight: float
    max_sector_percentage: float
    wash_sale_lookback_days: int
    dormant_asset_days: int  # Step 7 reporting only — never gates a buy/sell decision

    # v2.78.0 — dynamic profit-threshold ramp. Defaulted (rather than required) so existing
    # PortfolioMetadata(...) call sites (mostly test fixtures) that predate this feature don't
    # need updating just to opt into it; portfolio_targets.json sets all three explicitly.
    materialize_profit_percentage_max: float = 10.0  # cap the percent leg of the GET THE PROFITS
        # OR-gate ramps to, parabolically, as the quantity-weighted average age of the specific
        # profitable lots a sale would consume increases — see profit_threshold_ramp_days
    materialize_profit_in_dollars_max: float = 200.0  # same ramp/cap pairing for the dollar leg,
        # independent of the percent leg's own ramp
    profit_threshold_ramp_days: float = 30  # number of days of (quantity-weighted-average)
        # profitable-lot age at which both legs' dynamic threshold reaches its own max

    # v2.80.0 — Sell Cleanup Pass (Step 4b): dollar market-value ceiling for cleanup rule (a) —
    # a currently-held target asset whose remaining position (after this cycle's GET THE PROFITS
    # sale, if any) is exactly one tax lot, that lot is not a loss, AND the remaining market
    # value is under this figure gets that whole remainder swept, bypassing every GET THE PROFITS
    # profit gate (percent/dollar OR-gate, min_raw_gain_percent_to_sell, cooldown,
    # selling_price_change) — purely a dust-cleanup mechanism, not a profit-taking decision.
    # Defaulted so existing PortfolioMetadata(...) call sites (mostly test fixtures) don't need
    # updating just to opt into this feature.
    cleanup_dust_threshold_dollars: float = 200.0


@dataclass(frozen=True)
class PortfolioConfig:
    meta: PortfolioMetadata
    targets: Dict[str, AssetTarget]
    force_sell: Dict[str, ForceSellEntry]  # keyed by asset symbol
    blocked: List[str]  # exempt from ALL buy/sell this cycle, except forceSell + currently held -> liquidate 100%
    sector_groups: Dict[str, SectorGroup] = field(default_factory=dict)  # theme/correlation groups
        # for max_sector_percentage; a symbol not listed in any group has no sector cap. Defaults
        # to empty (no cap) so existing PortfolioConfig(...) call sites (mostly test fixtures)
        # don't need updating just to opt out of this feature.
    target_price_to_sell: Dict[str, float] = field(default_factory=dict)  # symbol -> price floor;
        # a listed symbol may not be sold by ANY mechanism (incl. the emergency stop-losses) while
        # current_price is below its floor. A symbol not listed here is entirely unaffected.
    target_price_to_buy: Dict[str, float] = field(default_factory=dict)  # symbol -> price ceiling;
        # a listed symbol may not be bought by ANY mechanism
        # while current_price is above its ceiling. A symbol not listed here
        # is entirely unaffected.

    @property
    def sum_of_weights(self) -> float:
        return sum(t.weight for t in self.targets.values())

    def sector_of(self, symbol: str) -> Optional[str]:
        """The sector_groups key `symbol` belongs to, or None if it's in no group (uncapped)."""
        for group, sector in self.sector_groups.items():
            if symbol in sector.members:
                return group
        return None

    def sector_cap_percentage(self, group: str) -> float:
        """Effective max_sector_percentage for `group`: its own maxPercentage override if set,
        else the global max_sector_percentage."""
        override = self.sector_groups[group].max_percentage
        return override if override is not None else self.meta.max_sector_percentage

    def target_percentage(self, symbol: str) -> float:
        """target_percentage = (weight / sum_of_all_weights) * 100"""
        return self.targets[symbol].weight / self.sum_of_weights * 100

    def drift_tolerance(self, symbol: str) -> float:
        """asset_drift_tolerance: the asset's own `drift` override if present, else the global
        `global_drift_tolerance` — both in weight units."""
        override = self.targets[symbol].drift
        return override if override is not None else self.meta.global_drift_tolerance

    def max_allocation_percentage(self, symbol: str) -> float:
        """Effective per-asset concentration cap, as a percent of account_balance: the asset's
        own `max_allocation_percent` override if present, else the global
        `max_portfolio_percentage`. Used by step3_underweight_buys's `_headroom()` to cap each
        Underweight fill so a single symbol's
        market value (existing holdings + this cycle's planned buy) never exceeds this cap."""
        override = self.targets[symbol].max_allocation_percent
        return override if override is not None else self.meta.max_portfolio_percentage

    def sell_price_target_blocks(self, symbol: str, current_price: float) -> bool:
        """target_price_to_sell: True while `symbol` has a configured sell-price floor and
        `current_price` hasn't yet crossed (reached/exceeded) it. Blocks a sale by ANY mechanism —
        Drawdown Audit, blocked+forceSell liquidation, and GET THE PROFITS alike — until price
        recovers to at least the target. A symbol not listed in `target_price_to_sell` is never
        affected (always returns False)."""
        target = self.target_price_to_sell.get(symbol)
        return target is not None and current_price < target

    def buy_price_target_blocks(self, symbol: str, current_price: float) -> bool:
        """target_price_to_buy: True while `symbol` has a configured buy-price ceiling and
        `current_price` is still above it. Blocks a buy by ANY mechanism — an Underweight
        allocation or a profit-sell repurchase — until
        price drops to at least the target. A symbol not listed in `target_price_to_buy` is never
        affected (always returns False)."""
        target = self.target_price_to_buy.get(symbol)
        return target is not None and current_price > target

    def force_sell_active(self, symbol: str, current_price: float) -> bool:
        """Whether forceSell's override (bypassing the profit-margin/lock-in/blocked-freeze
        gates) is currently in effect for `symbol`. Not listed in forceSell at all -> False.
        Listed with no `triggerPrice` -> always True (sell at whatever the current price is).
        Listed with a `triggerPrice` -> True only once `current_price` has recovered strictly
        above it; re-evaluated fresh every cycle as price moves, so the override can flip back
        off if price falls back below the trigger before the sale fires."""
        entry = self.force_sell.get(symbol)
        if entry is None:
            return False
        if entry.trigger_price is None:
            return True
        return current_price > entry.trigger_price


# Fields present in portfolio_targets.json's portfolio_metadata that are informational only
# (not risk parameters) and shouldn't be passed into PortfolioMetadata's constructor.
_METADATA_IGNORE_KEYS = {"version", "last_updated"}

# portfolio_targets.json spells these four with a leading digit ("1st_leg_price_change",
# "52_week_high_guard", ...) — not a legal Python identifier/dataclass field name, so they're
# renamed on the way into PortfolioMetadata. `selling_price_change` needs no rename (already a
# valid identifier).
_METADATA_KEY_RENAMES = {
    "1st_leg_price_change": "leg1_price_change",
    "2nd_leg_price_change": "leg2_price_change",
    "3rd_leg_price_change": "leg3_price_change",
    "52_week_high_guard": "fifty_two_week_high_guard",
}


def _parse_force_sell(raw: list) -> Dict[str, ForceSellEntry]:
    """Each entry is either a plain string (just the symbol, no trigger price — sell at
    whatever the current price is, same as the old list-of-strings format) or an object
    `{"asset": "SYM", "triggerPrice": <number>}` (triggerPrice optional there too)."""
    out: Dict[str, ForceSellEntry] = {}
    for entry in raw:
        if isinstance(entry, str):
            out[entry] = ForceSellEntry(asset=entry)
        else:
            asset = entry["asset"]
            trigger = entry.get("triggerPrice")
            out[asset] = ForceSellEntry(asset=asset, trigger_price=float(trigger) if trigger is not None else None)
    return out


def _parse_sector_groups(raw: dict) -> Dict[str, SectorGroup]:
    """{"group_name": ["SYM1", "SYM2", ...], ...} for a group using the global
    max_sector_percentage, OR {"group_name": {"members": [...], "maxPercentage": <number>}, ...}
    for a group with its own override — same plain-value-or-object union pattern as `forceSell`.
    A symbol must appear in at most one group — ambiguous double-membership would make
    max_sector_percentage's cap math double-count (or silently pick one group arbitrarily), so
    this fails loudly rather than guessing."""
    groups: Dict[str, SectorGroup] = {}
    for group, entry in raw.items():
        if isinstance(entry, list):
            groups[group] = SectorGroup(members=list(entry))
        else:
            max_pct = entry.get("maxPercentage")
            groups[group] = SectorGroup(
                members=list(entry["members"]),
                max_percentage=float(max_pct) if max_pct is not None else None,
            )

    seen: Dict[str, str] = {}
    for group, sector in groups.items():
        for sym in sector.members:
            if sym in seen:
                raise ValueError(
                    f"sector_groups: {sym!r} appears in both {seen[sym]!r} and {group!r} — "
                    "a symbol may belong to at most one sector group"
                )
            seen[sym] = group
    return groups


def load_portfolio_config(path: str | Path = "portfolio_targets.json") -> PortfolioConfig:
    data = json.loads(Path(path).read_text())

    meta_fields = {
        _METADATA_KEY_RENAMES.get(k, k): v
        for k, v in data["portfolio_metadata"].items() if k not in _METADATA_IGNORE_KEYS
    }
    meta = PortfolioMetadata(**meta_fields)

    targets = {
        sym: AssetTarget(
            symbol=sym, weight=t["weight"], drift=t.get("drift"),
            max_allocation_percent=t.get("max_allocation_percent"),
            max_position_value=t.get("max_position_value"),
        )
        for sym, t in data["targets"].items()
    }

    return PortfolioConfig(
        meta=meta, targets=targets,
        force_sell=_parse_force_sell(data.get("forceSell", [])),
        blocked=list(data.get("blocked", [])),
        sector_groups=_parse_sector_groups(data.get("sector_groups", {})),
        target_price_to_sell={sym: float(p) for sym, p in data.get("target_price_to_sell", {}).items()},
        target_price_to_buy={sym: float(p) for sym, p in data.get("target_price_to_buy", {}).items()},
    )
