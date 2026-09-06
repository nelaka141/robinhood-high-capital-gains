"""Snapshot-driven CLI: `plan` and `finalize`. Neither ever calls a broker directly — both
read/write plain JSON files and operate purely on data the caller supplies. This is the mode
built for a scheduled Claude Code session (or any other MCP/API-connected orchestrator) that
already has its own live Robinhood connection: it fetches data, runs `plan`, executes exactly
the sell orders `plan` returns, re-fetches the two post-sell figures, runs `finalize`, then
executes exactly the buy orders `finalize` returns. See bot/README.md, "Snapshot-driven mode",
for the exact snapshot.json schema and the end-to-end sequence.

Usage:
    python3 -m bot.cli plan     --snapshot snapshot.json --repo-dir . --out plan_result.json
    python3 -m bot.cli finalize --resume resume_state.json --post-sell-pnl <float> \\
                                 --buying-power <float> --repo-dir . --out finalize_result.json

    python3 -m bot.cli price-cache-plan  --repo-dir . --current-date <today> --out price_fetch_plan.json
    python3 -m bot.cli price-cache-merge --repo-dir . --current-date <today> \\
                                          --bars-in fetched_bars.json --out price_cache_result.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from . import journal, price_cache, steps
from .config import load_portfolio_config
from .models import RunContext
from .serialize import ctx_from_jsonable, ctx_to_jsonable, dump_json
from .snapshot_broker import SnapshotBroker
from .state import (
    AssetPriceState, load_paid_taxes_by_year, load_price_state, load_tax_by_year,
    save_price_state, save_tax_by_year,
)


def _intent_to_dict(t) -> dict:
    return {
        "symbol": t.symbol, "side": t.side, "quantity": t.quantity,
        "dollar_amount": t.dollar_amount, "tax_lots": t.tax_lots, "reason": t.reason,
    }


def cmd_plan(args: argparse.Namespace) -> None:
    repo_dir = args.repo_dir
    cfg = load_portfolio_config(f"{repo_dir}/portfolio_targets.json")
    broker = SnapshotBroker.from_file(args.snapshot)
    snapshot = json.loads(Path(args.snapshot).read_text())

    ctx = RunContext(
        current_date=date.fromisoformat(snapshot["current_date"]),
        config=cfg,
        account_number=snapshot.get("account_number", "SNAPSHOT"),
    )
    ctx.price_state = load_price_state(f"{repo_dir}/peak/prices.json")
    ctx.tax_by_year = load_tax_by_year(f"{repo_dir}/tax/realized_gains_by_year.json")
    ctx.paid_taxes_by_year = load_paid_taxes_by_year(f"{repo_dir}/tax/paid_taxes_by_year.json")

    steps.step1_fetch_state(ctx, broker, repo_dir)
    # v2.84.0: follow up on any in-window repurchase recorded on an earlier cycle — needs the
    # broker's tax lots, so it runs here (both the NO TRADES and the normal path) before any
    # state is written; a cleared/kept washVerifyPending rides along in price_state to the save.
    ctx.deferred_loss_notes = steps.verify_deferred_losses(ctx, broker)

    if not steps.has_any_breach(ctx):
        # NO TRADES cycle — CLAUDE.md Step 1's early exit. Still update peak prices + the tax
        # file (Step 6 says "do this every cycle, including NO TRADES cycles") and log.
        _update_peak_prices(ctx)
        save_price_state(ctx.price_state, f"{repo_dir}/peak/prices.json")
        ctx.tax_by_year[str(ctx.current_date.year)] = max(0.0, ctx.net_realized_gains_ytd_pretrade)
        save_tax_by_year(ctx.tax_by_year, f"{repo_dir}/tax/realized_gains_by_year.json")
        ctx.dormant_assets = steps.compute_dormant_assets(ctx)
        # No buys happen on a NO TRADES cycle, so the candidate list is already final.
        ctx.loss_only_assets = steps.compute_loss_only_assets(ctx, broker)
        entry_md = journal.render_no_trades_entry(ctx)
        journal.prepend_entry(entry_md, f"{repo_dir}/logs")
        dump_json({
            "no_trades": True,
            "journal_entry_markdown": entry_md,
            "email_summary": (
                f"No trades this cycle — all {len(ctx.drift_results)} assets within tolerance. "
                f"Dormant assets (no activity > {cfg.meta.dormant_asset_days}d): {len(ctx.dormant_assets)}. "
                f"Loss-only-lot assets: {len(ctx.loss_only_assets)}."
            ),
            "files_changed": ["peak/prices.json", "tax/realized_gains_by_year.json", "logs/trade_journal.md"],
        }, args.out)
        print(f"NO TRADES — wrote {args.out}")
        return

    steps.step2_guardrails(ctx, broker)
    planned_buys = steps.step3_underweight_buys(ctx, broker)
    steps.step4_profit_taking(ctx, broker)
    steps.step4b_sell_cleanup(ctx, broker)
    planned_buys = steps.step5_price_limits(ctx, broker, planned_buys)
    sells_to_place, halted, halt_reason = steps.step6a_prepare_sells(ctx, planned_buys)
    # Gathered here because tax lots need the broker; finalize filters it by this cycle's buys.
    ctx.loss_only_assets = steps.compute_loss_only_assets(ctx, broker)

    result = {
        "no_trades": False,
        "halted_for_approval": halted,
        "halt_reason": halt_reason,
        "sells_to_place": [_intent_to_dict(t) for t in sells_to_place],
        # Informational total only — the seek_approval_value halt is checked per individual
        # trade (steps.step6a_prepare_sells), not against this summed figure.
        "gross_sell_value": sum((t.quantity or 0.0) * ctx.quotes[t.symbol].last_trade_price for t in sells_to_place),
        # planned_buys is pre-tax-reserve-finalization — carried in resume_state for `finalize`.
        "resume_state": {
            "ctx": ctx_to_jsonable(ctx),
            "planned_buys": planned_buys,
        },
    }
    dump_json(result, args.out)

    if halted:
        print(f"HALTED FOR APPROVAL: {halt_reason}\nWrote {args.out} — do not proceed without user confirmation.")
    else:
        print(f"PLAN OK — {len(sells_to_place)} sell(s) to execute, then re-fetch post-sell "
              f"realized P&L + buying power and run `finalize`. Wrote {args.out}.")


def cmd_finalize(args: argparse.Namespace) -> None:
    repo_dir = args.repo_dir
    cfg = load_portfolio_config(f"{repo_dir}/portfolio_targets.json")

    resume = json.loads(Path(args.resume).read_text())
    resume_state = resume["resume_state"] if "resume_state" in resume else resume
    ctx = ctx_from_jsonable(resume_state["ctx"], cfg)
    planned_buys = resume_state["planned_buys"]

    buys_to_place = steps.step6b_finalize_buys(
        ctx, planned_buys, net_realized_gains_ytd_effective=args.post_sell_pnl, buying_power_now=args.buying_power
    )

    # v2.84.0: this cycle's buys are now known — journal any repurchase that lands inside the
    # wash-sale window of an earlier net-profit full exit, and arm the follow-up verify check.
    # Runs BEFORE the state stamping below so it reads the EARLIER exit's lastNettedLoss* fields.
    ctx.deferred_loss_notes += steps.note_wash_window_repurchases(ctx)

    _update_peak_prices(ctx)
    _update_profit_sell_and_purchase_dates(ctx)
    save_price_state(ctx.price_state, f"{repo_dir}/peak/prices.json")
    ctx.tax_by_year[str(ctx.current_date.year)] = max(0.0, ctx.net_realized_gains_ytd_effective or 0.0)
    save_tax_by_year(ctx.tax_by_year, f"{repo_dir}/tax/realized_gains_by_year.json")

    ctx.dormant_assets = steps.compute_dormant_assets(ctx)
    ctx.loss_only_assets = steps.drop_bought_symbols(ctx.loss_only_assets, ctx)
    entry_md = journal.render_entry(ctx)
    journal.prepend_entry(entry_md, f"{repo_dir}/logs")

    files_changed = ["peak/prices.json", "tax/realized_gains_by_year.json", "logs/trade_journal.md"]

    result = {
        "buys_to_place": [_intent_to_dict(t) for t in buys_to_place],
        "tax_reserve": ctx.tax_reserve,
        "net_realized_gains_ytd_effective": ctx.net_realized_gains_ytd_effective,
        "total_high_beta_gains_realized": ctx.total_high_beta_gains_realized,
        "journal_entry_markdown": entry_md,
        "email_summary": journal.render_email_summary(ctx),
        "files_changed": files_changed,
    }
    dump_json(result, args.out)
    print(f"FINALIZE OK — {len(buys_to_place)} buy(s) to execute. State files written. Wrote {args.out}.")


def _update_peak_prices(ctx: RunContext) -> None:
    today = ctx.current_date.isoformat()
    for sym in ctx.config.targets:
        st = ctx.price_state.setdefault(sym, AssetPriceState())
        price = ctx.quotes[sym].last_trade_price
        if st.peakPrice is None or price > st.peakPrice:
            st.peakPrice, st.peakDate = price, today
        if sym in ctx.drawdown_liquidations or sym in ctx.blocked_liquidations:
            st.liquidatedPrice, st.liquidatedDate = price, today
        if sym in ctx.loss_sale_symbols:
            # Wash-sale buy-guard (Step 2) basis: arms wash_sale_lookback_days regardless of
            # which mechanism realized the loss. Membership is decided on the sale's NET realized
            # figure (see steps._is_loss and the GTP backstop) — a v2.83.0 net-profit full exit
            # that sells an underwater lot alongside bigger winners is a net gain and is
            # deliberately NOT stamped here (operator decision, 2026-09-04).
            st.lastLossSalePrice, st.lastLossSaleDate = price, today


def _update_profit_sell_and_purchase_dates(ctx: RunContext) -> None:
    today = ctx.current_date.isoformat()
    # Cleanup sells (Step 4b) realize a profit (or breakeven) just like GET THE PROFITS — never a
    # loss, by construction — so they arm the same profit-sell buy-guard/cooldown and reset the
    # peak on a later repurchase exactly like a GTP sale would.
    for t in ctx.profit_taking_sells + ctx.cleanup_sells:
        st = ctx.price_state[t.symbol]
        st.profitSellPrice = ctx.quotes[t.symbol].last_trade_price
        st.profitSellDate = today
        if t.netted_loss_dollars:
            # v2.84.0: a net-profit full exit netted an underwater lot's loss inside this
            # net-gain sale — record it so Step 7 can journal (and later verify) the deferral
            # if the symbol is bought back inside wash_sale_lookback_days. Observational only.
            st.lastNettedLossDollars = round(t.netted_loss_dollars, 2)
            st.lastNettedLossShares = t.netted_loss_shares
            st.lastNettedLossDate = today
    for t in ctx.buys:
        st = ctx.price_state[t.symbol]
        st.lastPurchaseDate = today
        # Repurchase after a FULL-exit profit-sell (Step 6): reset the peak to the purchase
        # price. Detected by: this symbol carries a profitSellDate AND held zero shares going
        # into this buy (a partial-sell remainder always leaves nonzero shares, so this only
        # fires for the true full-exit case).
        pos = ctx.positions.get(t.symbol)
        was_full_exit = st.profitSellDate is not None and (not pos or pos.quantity <= 0)
        if was_full_exit:
            st.peakPrice, st.peakDate = ctx.quotes[t.symbol].last_trade_price, today
        # Clear a stale liquidation record now that this symbol is being bought (Step 6).
        # A buy can only have fired here if step2_guardrails did NOT exclude the symbol —
        # which means either it was never liquidated, or the recovery/cooldown gate passed
        # this cycle, or it's currently held despite a leftover liquidatedPrice from before an
        # earlier repurchase (steps.py's currently_held check). In every one of those cases the
        # liquidation record is no longer relevant, so it's always safe to clear it here.
        if st.liquidatedPrice not in (None, ""):
            st.liquidatedPrice, st.liquidatedDate = "", None


def cmd_price_cache_plan(args: argparse.Namespace) -> None:
    cfg = load_portfolio_config(f"{args.repo_dir}/portfolio_targets.json")
    cache = price_cache.load_price_cache(f"{args.repo_dir}/price_history/daily_bars.json")
    symbols = price_cache.cache_symbols(cfg)
    result = price_cache.plan_fetches(cache, symbols, date.fromisoformat(args.current_date))
    dump_json(result, args.out)
    n_fetch = sum(len(b["symbols"]) for b in result["fetch_batches"])
    print(f"PRICE CACHE PLAN — {n_fetch} symbol(s) across {len(result['fetch_batches'])} "
          f"batch(es) need fetching, {len(result['up_to_date'])} already up to date. Wrote {args.out}.")


def cmd_price_cache_merge(args: argparse.Namespace) -> None:
    cache_path = f"{args.repo_dir}/price_history/daily_bars.json"
    cache = price_cache.load_price_cache(cache_path)
    if args.bars_in:
        new_bars = json.loads(Path(args.bars_in).read_text())
        price_cache.merge_bars(cache, new_bars)
    current_date = date.fromisoformat(args.current_date)
    price_cache.prune_cache(cache, current_date)
    price_cache.save_price_cache(cache, cache_path)
    daily_closes, daily_lows_highs = price_cache.slice_for_snapshot(cache, current_date)
    dump_json({"daily_closes": daily_closes, "daily_lows_highs": daily_lows_highs}, args.out)
    print(f"PRICE CACHE MERGE — cache now covers {len(cache)} symbol(s). "
          f"Wrote {cache_path} and {args.out}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot-driven CLAUDE.md pipeline (no broker credentials needed).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Steps 1-5 + sell planning. Reads snapshot.json, writes plan_result.json.")
    p_plan.add_argument("--snapshot", required=True)
    p_plan.add_argument("--repo-dir", default=".")
    p_plan.add_argument("--out", default="plan_result.json")
    p_plan.set_defaults(func=cmd_plan)

    p_final = sub.add_parser("finalize", help="Step 6 buy-side tail + Step 7. Reads plan_result.json's resume_state.")
    p_final.add_argument("--resume", required=True, help="The plan_result.json written by `plan`")
    p_final.add_argument("--post-sell-pnl", required=True, type=float,
                          help="net_realized_gains_ytd, re-fetched AFTER this cycle's sells are confirmed filled")
    p_final.add_argument("--buying-power", required=True, type=float,
                          help="buying_power, re-fetched AFTER this cycle's sells are confirmed filled")
    p_final.add_argument("--repo-dir", default=".")
    p_final.add_argument("--out", default="finalize_result.json")
    p_final.set_defaults(func=cmd_finalize)

    p_pc_plan = sub.add_parser(
        "price-cache-plan",
        help="Decide which symbols/date-ranges still need a get_equity_historicals fetch, per price_history/daily_bars.json.",
    )
    p_pc_plan.add_argument("--repo-dir", default=".")
    p_pc_plan.add_argument("--current-date", required=True, help="YYYY-MM-DD, US/Eastern")
    p_pc_plan.add_argument("--out", default="price_fetch_plan.json")
    p_pc_plan.set_defaults(func=cmd_price_cache_plan)

    p_pc_merge = sub.add_parser(
        "price-cache-merge",
        help="Merge freshly fetched bars into price_history/daily_bars.json, prune, and slice daily_closes/daily_lows_highs for snapshot.json.",
    )
    p_pc_merge.add_argument("--repo-dir", default=".")
    p_pc_merge.add_argument("--current-date", required=True, help="YYYY-MM-DD, US/Eastern")
    p_pc_merge.add_argument(
        "--bars-in", default=None,
        help='JSON {"SYMBOL": [{"date","close","low","high"}, ...]} from this cycle\'s get_equity_historicals '
             'fetches; omit if price-cache-plan\'s fetch_batches was empty (nothing needed fetching)',
    )
    p_pc_merge.add_argument("--out", default="price_cache_result.json")
    p_pc_merge.set_defaults(func=cmd_price_cache_merge)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
