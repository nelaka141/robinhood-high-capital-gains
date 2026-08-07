"""CLI entrypoint for STANDALONE mode — bot/ owns a direct broker connection (broker.py) and
does everything itself: fetch data, decide, place orders, commit, email. Use this only if you
run bot/ completely outside of any MCP-connected agent and give it its own credentials.

Usage:
    python -m bot.main --account <account_number> --repo-dir . [--live]

Defaults to --dry-run (no real orders, no git push, no email) so you can inspect a cycle's
decisions before ever routing a real order. Pass --live to actually place orders, commit,
open+merge a PR, and draft the summary email.

--- If you're running this FROM a scheduled Claude Code session (or any other agent that
already has its own MCP/API connection to Robinhood and Gmail) — which is the setup this repo
actually uses — use bot/cli.py's `plan`/`finalize` commands instead. That mode never needs its
own broker credentials: the agent supplies a market-data snapshot, bot/ returns an exact order
plan, and the agent (which already has a live connection) executes it. See bot/README.md,
"Snapshot-driven mode".
"""
from __future__ import annotations

import argparse
from datetime import datetime

from zoneinfo import ZoneInfo

from . import gitops, journal, notify, steps
from .broker import BrokerClient, RobinStocksBroker
from .config import load_portfolio_config
from .models import RunContext
from .state import (
    AssetPriceState,
    load_alpha_reserve,
    load_price_state,
    load_settlement_reserve,
    load_tax_by_year,
    save_alpha_reserve,
    save_price_state,
    save_settlement_reserve,
    save_tax_by_year,
)

GITHUB_OWNER = "nelaka141"
GITHUB_REPO = "robinhood-high-capital-gains"
NOTIFY_EMAIL = "adarsh_141@yahoo.com"


def run_cycle(account_number: str, repo_dir: str, broker: BrokerClient, dry_run: bool = True) -> RunContext:
    now_et = datetime.now(ZoneInfo("America/New_York"))
    cfg = load_portfolio_config(f"{repo_dir}/portfolio_targets.json")

    ctx = RunContext(current_date=now_et.date(), config=cfg, account_number=account_number)
    ctx.price_state = load_price_state(f"{repo_dir}/peak/prices.json")
    ctx.reserve = load_settlement_reserve(f"{repo_dir}/settlement/reserve.json")
    ctx.tax_by_year = load_tax_by_year(f"{repo_dir}/tax/realized_gains_by_year.json")
    ctx.alpha_reserve = load_alpha_reserve(f"{repo_dir}/alpha_reserve.json")

    # ---- Step 1 ----
    steps.step1_fetch_state(ctx, broker, repo_dir)

    if not steps.has_any_breach(ctx):
        # No drift breach, no drawdown -> log status & terminate safely (Step 1's early exit).
        journal.prepend_entry(journal.render_no_trades_entry(ctx), f"{repo_dir}/logs")
        return ctx

    # ---- Step 2 ----
    steps.step2_guardrails(ctx)

    # ---- Step 3 ----
    planned_buys = steps.step3_alpha_leader(ctx, broker)

    # ---- Step 4 ----
    steps.step4_profit_taking(ctx, broker)

    # ---- Step 5 ----
    planned_buys = steps.step5_price_limits(ctx, broker, planned_buys)

    # ---- Step 6 ----
    steps.step6_execute_live(ctx, broker, planned_buys, dry_run=dry_run)

    # ---- Step 7 ----
    _finalize_step7(ctx, repo_dir, dry_run)
    return ctx


def _update_price_state(ctx: RunContext) -> None:
    today = ctx.current_date.isoformat()
    bought = {t.symbol for t in ctx.buys}
    sold_for_profit = {t.symbol for t in ctx.profit_taking_sells}
    liquidated = set(ctx.drawdown_liquidations) | set(ctx.blocked_liquidations)

    for sym in ctx.config.targets:
        st = ctx.price_state.setdefault(sym, AssetPriceState())
        price = ctx.quotes[sym].last_trade_price

        if st.peakPrice is None or price > st.peakPrice:
            st.peakPrice, st.peakDate = price, today

        if sym in liquidated:
            st.liquidatedPrice, st.liquidatedDate = price, today

        if sym in sold_for_profit:
            st.profitSellPrice, st.profitSellDate = price, today

        if sym in bought:
            st.lastPurchaseDate = today
            if st.profitSellDate and (sym not in sold_for_profit):
                # Repurchased after a FULL-exit profit-sell -> fresh peak at the purchase price.
                # A partial-sell remainder always leaves nonzero shares, so this only fires for
                # the true full-exit case: zero (or no) position going into this buy.
                pos = ctx.positions.get(sym)
                if not pos or pos.quantity <= 0:
                    st.peakPrice, st.peakDate = price, today
            # Clear a stale liquidation record now that this symbol is being bought — a buy can
            # only fire here if step2_guardrails did not exclude the symbol (never liquidated,
            # recovery/cooldown passed this cycle, or currently held despite a leftover
            # liquidatedPrice from an earlier repurchase), so it's always safe to clear here.
            if st.liquidatedPrice not in (None, ""):
                st.liquidatedPrice, st.liquidatedDate = "", None


def _finalize_step7(ctx: RunContext, repo_dir: str, dry_run: bool) -> None:
    _update_price_state(ctx)
    save_price_state(ctx.price_state, f"{repo_dir}/peak/prices.json")
    save_settlement_reserve(ctx.reserve, f"{repo_dir}/settlement/reserve.json")
    save_alpha_reserve(steps.resolve_alpha_reserve(ctx), f"{repo_dir}/alpha_reserve.json")

    ctx.tax_by_year[str(ctx.current_date.year)] = max(
        0.0, ctx.net_realized_gains_ytd_effective if ctx.net_realized_gains_ytd_effective is not None else 0.0
    )
    save_tax_by_year(ctx.tax_by_year, f"{repo_dir}/tax/realized_gains_by_year.json")

    entry_md = journal.render_entry(ctx)
    journal.prepend_entry(entry_md, f"{repo_dir}/logs")

    if dry_run:
        return

    branch = gitops.commit_and_push_cycle(
        repo_dir,
        changed_paths=["peak/prices.json", "settlement/reserve.json",
                        "tax/realized_gains_by_year.json", "alpha_reserve.json", "logs/"],
        commit_message=f"Scheduled rebalance {ctx.current_date.isoformat()}",
    )
    gitops.open_and_merge_pr(
        owner=GITHUB_OWNER, repo=GITHUB_REPO, branch=branch,
        title=f"Scheduled rebalance {ctx.current_date.isoformat()}",
        body="Automated cycle — see logs/trade_journal.md for full detail.",
    )
    notify.draft_summary_email(
        to_address=NOTIFY_EMAIL,
        subject=f"Robinhood Bot — {ctx.current_date.isoformat()} Rebalance",
        body=journal.render_email_summary(ctx),
        journal_entry_md=entry_md,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one CLAUDE.md rebalance cycle.")
    parser.add_argument("--account", required=True, help="Brokerage account number")
    parser.add_argument("--repo-dir", default=".", help="Path to the cloned repo (state files live here)")
    parser.add_argument("--live", action="store_true", help="Place real orders, push, open+merge a PR, email")
    args = parser.parse_args()

    broker = RobinStocksBroker()  # assumes robin_stocks.robinhood.login(...) already called
    run_cycle(args.account, args.repo_dir, broker, dry_run=not args.live)


if __name__ == "__main__":
    main()
