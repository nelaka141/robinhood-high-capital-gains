"""JSON round-tripping for RunContext between the `plan` and `finalize` CLI commands
(bot/cli.py). `plan` runs Steps 1-5 (and Step 6's sell-side), then serializes the resulting
RunContext to a "resume state" blob; `finalize` deserializes it, runs Step 6's buy-side tail
with the caller-supplied post-sell figures, and renders the Step 7 journal entry.

Only the fields finalize.py actually needs are round-tripped in full; `config` is NOT
serialized (finalize reloads portfolio_targets.json fresh from repo_dir, since it's always
available on disk and re-reading avoids shipping the whole parameter set through the blob).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from typing import Any, Dict

from .config import PortfolioConfig
from .models import (
    DriftResult, MomentumScore, Position, Quote, RunContext, SkippedTrade, TradeIntent,
)
from .state import AssetPriceState, PendingDraw, SettlementReserve


class _DateEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


def ctx_to_jsonable(ctx: RunContext) -> Dict[str, Any]:
    """Everything `finalize` needs, minus `config` (reloaded from disk) and minus anything
    only meaningful mid-Step-6 (executed_orders — finalize hasn't placed anything yet)."""
    return {
        "current_date": ctx.current_date.isoformat(),
        "account_number": ctx.account_number,
        "price_state": {sym: asdict(st) for sym, st in ctx.price_state.items()},
        "positions": {sym: asdict(p) for sym, p in ctx.positions.items()},
        "quotes": {sym: asdict(q) for sym, q in ctx.quotes.items()},
        "account_cash": ctx.account_cash,
        "account_cash_ledger": ctx.account_cash_ledger,
        "current_cash": ctx.current_cash,
        "account_balance": ctx.account_balance,
        "reserve": {"pending_draws": [asdict(d) for d in ctx.reserve.pending_draws]},
        "reserve_available_to_draw": ctx.reserve_available_to_draw,
        "tax_by_year": ctx.tax_by_year,
        "net_realized_gains_ytd_pretrade": ctx.net_realized_gains_ytd_pretrade,
        "tax_reserve": ctx.tax_reserve,
        "drift_results": {sym: asdict(dr) for sym, dr in ctx.drift_results.items()},
        "excluded_symbols": ctx.excluded_symbols,
        "buy_guarded_symbols": ctx.buy_guarded_symbols,
        "blocked_symbols": ctx.blocked_symbols,
        "momentum_scores": {sym: asdict(m) for sym, m in ctx.momentum_scores.items()},
        "alpha_leader": ctx.alpha_leader,
        "blocked_liquidations": ctx.blocked_liquidations,
        "drawdown_liquidations": ctx.drawdown_liquidations,
        "profit_taking_sells": [asdict(t) for t in ctx.profit_taking_sells],
        "overweight_trims": [asdict(t) for t in ctx.overweight_trims],
        "skipped": [asdict(s) for s in ctx.skipped],
        "total_high_beta_gains_realized": ctx.total_high_beta_gains_realized,
    }


def ctx_from_jsonable(data: Dict[str, Any], cfg: PortfolioConfig) -> RunContext:
    ctx = RunContext(
        current_date=date.fromisoformat(data["current_date"]),
        config=cfg,
        account_number=data["account_number"],
    )
    ctx.price_state = {sym: AssetPriceState(**st) for sym, st in data["price_state"].items()}
    ctx.positions = {sym: Position(**p) for sym, p in data["positions"].items()}
    ctx.quotes = {sym: Quote(**q) for sym, q in data["quotes"].items()}
    ctx.account_cash = data["account_cash"]
    ctx.account_cash_ledger = data["account_cash_ledger"]
    ctx.current_cash = data["current_cash"]
    ctx.account_balance = data["account_balance"]
    ctx.reserve = SettlementReserve(pending_draws=[PendingDraw(**d) for d in data["reserve"]["pending_draws"]])
    ctx.reserve_available_to_draw = data["reserve_available_to_draw"]
    ctx.tax_by_year = data["tax_by_year"]
    ctx.net_realized_gains_ytd_pretrade = data["net_realized_gains_ytd_pretrade"]
    ctx.tax_reserve = data["tax_reserve"]
    ctx.drift_results = {sym: DriftResult(**dr) for sym, dr in data["drift_results"].items()}
    ctx.excluded_symbols = data["excluded_symbols"]
    ctx.buy_guarded_symbols = data["buy_guarded_symbols"]
    ctx.blocked_symbols = data.get("blocked_symbols", {})
    ctx.momentum_scores = {sym: MomentumScore(**m) for sym, m in data["momentum_scores"].items()}
    ctx.alpha_leader = data["alpha_leader"]
    ctx.blocked_liquidations = data.get("blocked_liquidations", [])
    ctx.drawdown_liquidations = data["drawdown_liquidations"]
    ctx.profit_taking_sells = [TradeIntent(**t) for t in data["profit_taking_sells"]]
    ctx.overweight_trims = [TradeIntent(**t) for t in data["overweight_trims"]]
    ctx.skipped = [SkippedTrade(**s) for s in data["skipped"]]
    ctx.total_high_beta_gains_realized = data["total_high_beta_gains_realized"]
    return ctx


def dump_json(obj: Any, path) -> None:
    from pathlib import Path
    Path(path).write_text(json.dumps(obj, indent=2, cls=_DateEncoder) + "\n")
