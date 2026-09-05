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
    DeferredLossNote, DriftResult, LossOnlyAsset, MomentumScore, Position, Quote, RunContext,
    SkippedTrade, TradeIntent,
)
from .state import AssetPriceState


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
        "tax_by_year": ctx.tax_by_year,
        "paid_taxes_by_year": ctx.paid_taxes_by_year,
        "net_realized_gains_ytd_pretrade": ctx.net_realized_gains_ytd_pretrade,
        "tax_reserve": ctx.tax_reserve,
        "drift_results": {sym: asdict(dr) for sym, dr in ctx.drift_results.items()},
        "excluded_symbols": ctx.excluded_symbols,
        "buy_guarded_symbols": ctx.buy_guarded_symbols,
        "blocked_symbols": ctx.blocked_symbols,
        "momentum_scores": {sym: asdict(m) for sym, m in ctx.momentum_scores.items()},
        "position_cap_topups": ctx.position_cap_topups,
        "blocked_liquidations": ctx.blocked_liquidations,
        "drawdown_liquidations": ctx.drawdown_liquidations,
        "loss_sale_symbols": ctx.loss_sale_symbols,
        "profit_taking_sells": [asdict(t) for t in ctx.profit_taking_sells],
        "cleanup_sells": [asdict(t) for t in ctx.cleanup_sells],
        "skipped": [asdict(s) for s in ctx.skipped],
        # Candidate loss-only assets, gathered in `plan` where the broker (and therefore tax-lot
        # data) is available. finalize has no broker, so it filters this list down by this
        # cycle's buys rather than recomputing it.
        "loss_only_assets": [asdict(a) for a in ctx.loss_only_assets],
        # v2.84.0: verify notes gathered in `plan` (broker needed); finalize appends the
        # in-window repurchase notes once this cycle's buys are known.
        "deferred_loss_notes": [asdict(n) for n in ctx.deferred_loss_notes],
        "total_high_beta_gains_realized": ctx.total_high_beta_gains_realized,
        "total_cleanup_gains_realized": ctx.total_cleanup_gains_realized,
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
    ctx.tax_by_year = data["tax_by_year"]
    ctx.paid_taxes_by_year = data.get("paid_taxes_by_year", {})
    ctx.net_realized_gains_ytd_pretrade = data["net_realized_gains_ytd_pretrade"]
    ctx.tax_reserve = data["tax_reserve"]
    ctx.drift_results = {sym: DriftResult(**dr) for sym, dr in data["drift_results"].items()}
    ctx.excluded_symbols = data["excluded_symbols"]
    ctx.buy_guarded_symbols = data["buy_guarded_symbols"]
    ctx.blocked_symbols = data.get("blocked_symbols", {})
    ctx.momentum_scores = {sym: MomentumScore(**m) for sym, m in data["momentum_scores"].items()}
    ctx.position_cap_topups = data.get("position_cap_topups", {})
    ctx.blocked_liquidations = data.get("blocked_liquidations", [])
    ctx.drawdown_liquidations = data["drawdown_liquidations"]
    ctx.loss_sale_symbols = data.get("loss_sale_symbols", [])
    ctx.profit_taking_sells = [TradeIntent(**t) for t in data["profit_taking_sells"]]
    ctx.cleanup_sells = [TradeIntent(**t) for t in data.get("cleanup_sells", [])]
    ctx.skipped = [SkippedTrade(**s) for s in data["skipped"]]
    ctx.loss_only_assets = [LossOnlyAsset(**a) for a in data.get("loss_only_assets", [])]
    ctx.deferred_loss_notes = [DeferredLossNote(**n) for n in data.get("deferred_loss_notes", [])]
    ctx.total_high_beta_gains_realized = data["total_high_beta_gains_realized"]
    ctx.total_cleanup_gains_realized = data.get("total_cleanup_gains_realized", 0.0)
    return ctx


def dump_json(obj: Any, path) -> None:
    from pathlib import Path
    Path(path).write_text(json.dumps(obj, indent=2, cls=_DateEncoder) + "\n")
