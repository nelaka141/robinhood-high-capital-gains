"""logs/trade_journal.md rendering + rotation — CLAUDE.md Step 7.

Rotation rule: keep only the last 5 entries in trade_journal.md; move older ones into
logs/history_trade_journal-<seq>.md, 10 entries per history file, incrementing <seq> once a
file fills up.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .models import RunContext

MAX_LIVE_ENTRIES = 5
MAX_HISTORY_ENTRIES_PER_FILE = 10
_ENTRY_HEADER_RE = re.compile(r"(?m)^# .*$")


def _split_entries(text: str) -> List[str]:
    """Split a journal file's text into whole entries, each starting at a top-level '# ' header."""
    starts = [m.start() for m in _ENTRY_HEADER_RE.finditer(text)]
    if not starts:
        return []
    starts.append(len(text))
    return [text[starts[i]:starts[i + 1]].rstrip("\n") + "\n" for i in range(len(starts) - 1)]


def _next_history_path(logs_dir: Path) -> Path:
    existing = sorted(logs_dir.glob("history_trade_journal-*.md"))
    if not existing:
        return logs_dir / "history_trade_journal-1.md"
    nums = [int(re.search(r"-(\d+)\.md$", f.name).group(1)) for f in existing]
    return logs_dir / f"history_trade_journal-{max(nums)}.md"


def prepend_entry(new_entry_md: str, logs_dir: str | Path = "logs") -> None:
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    journal_path = logs_dir / "trade_journal.md"

    existing_text = journal_path.read_text() if journal_path.exists() else ""
    entries = _split_entries(existing_text)

    combined = [new_entry_md.rstrip("\n") + "\n"] + entries
    live, overflow = combined[:MAX_LIVE_ENTRIES], combined[MAX_LIVE_ENTRIES:]

    journal_path.write_text("\n".join(live).rstrip("\n") + "\n")
    if not overflow:
        return

    history_path = _next_history_path(logs_dir)
    history_entries = _split_entries(history_path.read_text()) if history_path.exists() else []
    for entry in overflow:
        if len(history_entries) >= MAX_HISTORY_ENTRIES_PER_FILE:
            seq = int(re.search(r"-(\d+)\.md$", history_path.name).group(1)) + 1
            history_path = logs_dir / f"history_trade_journal-{seq}.md"
            history_entries = []
        history_entries.append(entry)
    history_path.write_text("\n".join(history_entries).rstrip("\n") + "\n")


def render_no_trades_entry(ctx: RunContext) -> str:
    ts = ctx.current_date.isoformat()
    lines = [
        f"# {ts} — Scheduled Rebalance Check — NO TRADES",
        "",
        "**Status:** NO TRADES. No asset exceeded its resolved `asset_drift_tolerance` and no "
        "Drawdown Audit breach was triggered.",
        "",
        f"- `buying_power`: **${ctx.account_cash:,.2f}**",
        f"- `account_balance`: **${ctx.account_balance:,.2f}**",
        "",
        "## Drift (all within tolerance)",
        "| Symbol | Drift | Tolerance |",
        "|---|---|---|",
    ]
    for sym, dr in sorted(ctx.drift_results.items()):
        lines.append(f"| {sym} | {dr.drift:.3f} | {dr.asset_drift_tolerance:.3f} |")
    lines += _render_dormant_assets_section(ctx)
    lines += _render_loss_only_assets_section(ctx)
    return "\n".join(lines) + "\n"


def render_entry(ctx: RunContext) -> str:
    ts = ctx.current_date.isoformat()
    n_sells = (
        len(ctx.drawdown_liquidations) + len(ctx.blocked_liquidations)
        + len(ctx.profit_taking_sells) + len(ctx.cleanup_sells)
    )
    n_buys = len(ctx.buys)

    lines = [
        f"# {ts} — Scheduled Rebalance Check — EXECUTED ({n_sells} sell(s), {n_buys} buy(s))",
        "",
        f"**Status:** EXECUTED. {n_sells} sell order(s), {n_buys} buy order(s) sized this cycle.",
        "",
        "## Account Snapshot",
        f"- `buying_power` (settled): **${ctx.account_cash:,.2f}**",
        f"- `cash` (ledger): **${ctx.account_cash_ledger:,.2f}**",
        f"- `current_cash` (post-cap): **${ctx.current_cash:,.2f}**",
        f"- `account_balance`: **${ctx.account_balance:,.2f}**",
        "",
        "## Drawdown Audit",
        f"Emergency liquidations: {', '.join(ctx.drawdown_liquidations) or 'none'}",
        "",
        "## Excluded / Buy-Guarded Symbols (Step 2)",
    ]
    for sym, reason in ctx.excluded_symbols.items():
        lines.append(f"- **{sym}** (excluded): {reason}")
    for sym, reasons in ctx.buy_guarded_symbols.items():
        if sym not in ctx.excluded_symbols:
            if len(reasons) == 1:
                lines.append(f"- **{sym}** (buy-guarded only): {reasons[0]}")
            else:
                # More than one guard mechanism is active on this symbol at once (e.g. the
                # profit-sell guard and the wash-sale guard both armed) — list each separately
                # rather than only showing whichever one happened to be computed last.
                joined = " | ".join(f"[{i}] {r}" for i, r in enumerate(reasons, 1))
                lines.append(
                    f"- **{sym}** (buy-guarded only, {len(reasons)} guard(s) active): {joined}"
                )

    lines += ["", "## Blocked Assets (`blocked` list)"]
    for sym, reason in ctx.blocked_symbols.items():
        lines.append(f"- **{sym}**: {reason}")
    if not ctx.blocked_symbols:
        lines.append("- none this cycle")

    lines += [
        "",
        "## Underweight Fill Ranking — Momentum_Score",
        "| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |",
        "|---|---|---|---|---|---|---|",
    ]
    for sym, m in sorted(ctx.momentum_scores.items(), key=lambda kv: -kv[1].score):
        lines.append(
            f"| {sym} | {m.rsi14:.2f} | {m.ema9_now:.2f} | {m.ema9_prior:.2f} | "
            f"{m.price_vs_ema_pct:+.2f} | {m.ema_slope_pct:+.2f} | {m.score:+.2f} |"
        )

    total_paid_taxes = sum(ctx.paid_taxes_by_year.values())
    lines += [
        "",
        "## Tax Reserve",
        f"- `net_realized_gains_ytd_pretrade`: **${ctx.net_realized_gains_ytd_pretrade:,.2f}**",
        f"- `net_realized_gains_ytd_effective` (post-sells): "
        f"**${(ctx.net_realized_gains_ytd_effective or 0):,.2f}**",
        f"- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **${total_paid_taxes:,.2f}**",
        f"- `tax_reserve` (final, after subtracting paid taxes): **${ctx.tax_reserve:,.2f}**",
        "",
        "## GET THE PROFITS Sells",
    ]
    for t in ctx.profit_taking_sells:
        lines.append(f"- **{t.symbol}**: {t.reason}")
    if not ctx.profit_taking_sells:
        lines.append("- none fired this cycle")

    lines += ["", "## Sell Cleanup Pass"]
    for t in ctx.cleanup_sells:
        lines.append(f"- **{t.symbol}**: {t.reason}")
    if not ctx.cleanup_sells:
        lines.append("- none fired this cycle")

    lines += ["", "## Buys (Underweight fills, momentum-ranked top-down)"]
    for t in ctx.buys:
        topup = ctx.position_cap_topups.get(t.symbol)
        note = f" (includes ${topup:,.2f} Position Cap Top-Up)" if topup else ""
        lines.append(f"- **{t.symbol}**: ${t.dollar_amount:,.2f}{note}")
    if not ctx.buys:
        lines.append("- none fired this cycle")

    lines += ["", "## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)"]
    for sym, dollars in ctx.position_cap_topups.items():
        target = ctx.config.resolved_max_position_value(sym)
        lines.append(f"- **{sym}**: +${dollars:,.2f} (target max_position_value ${target:,.2f})")
    if not ctx.position_cap_topups:
        lines.append("- none this cycle")

    lines += [
        "",
        f"## Total_High_Beta_Gains_Realized: **${ctx.total_high_beta_gains_realized:,.2f}**",
        f"## Total_Cleanup_Gains_Realized: **${ctx.total_cleanup_gains_realized:,.2f}**",
        "",
        "## SKIPPED/PENDING",
        "| Symbol | Reason | Would-be action |",
        "|---|---|---|",
    ]
    for s in ctx.skipped:
        lines.append(f"| {s.symbol} | {s.reason} | {s.would_be_action} |")

    lines += _render_dormant_assets_section(ctx)
    lines += _render_loss_only_assets_section(ctx)

    lines += [
        "",
        "## Orders Placed",
        "```",
        *[str(o) for o in ctx.executed_orders],
        "```",
    ]
    return "\n".join(lines) + "\n"


def _render_dormant_assets_section(ctx: RunContext) -> List[str]:
    """CLAUDE.md Step 7's Dormant Assets report (`dormant_asset_days`) — purely observational,
    shared by both render_entry and render_no_trades_entry."""
    lines = [
        "",
        f"## Dormant Assets (no activity > {ctx.config.meta.dormant_asset_days}d)",
    ]
    if not ctx.dormant_assets:
        lines.append(f"- none — every held asset traded within the last {ctx.config.meta.dormant_asset_days} day(s)")
        return lines

    lines += ["| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |", "|---|---|---|---|---|"]
    for d in ctx.dormant_assets:
        days = f"{d.days_since_activity}d" if d.days_since_activity is not None else "never"
        last_activity = d.last_activity_date or "n/a"
        lines.append(
            f"| {d.symbol} | {days} | {last_activity} | ${d.unrealized_dollars:,.2f} | {d.unrealized_pct:+.2f}% |"
        )
    return lines


def _render_loss_only_assets_section(ctx: RunContext) -> List[str]:
    """CLAUDE.md Step 7's Loss-Only Lot Assets report — purely observational, shared by both
    render_entry and render_no_trades_entry. Computed after this cycle's buys are sized."""
    lines = [
        "",
        "## Loss-Only Lot Assets (every sellable lot underwater)",
    ]
    if not ctx.loss_only_assets:
        lines.append("- none — every held asset still has at least one lot that could be sold at a gain")
        return lines

    total = sum(a.unrealized_dollars for a in ctx.loss_only_assets)
    mv = sum(a.market_value for a in ctx.loss_only_assets)
    lines += [
        f"{len(ctx.loss_only_assets)} asset(s), ${mv:,.2f} market value, "
        f"${total:,.2f} total unrealized. GET THE PROFITS is structurally unable to fire on these "
        "(the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency "
        "stop or a manual action.",
        "",
        "Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's "
        "blended `avg_cost_basis` — so they can never contradict this list's own membership test.",
        "",
        "| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for a in ctx.loss_only_assets:
        flag = " ⚠" if a.basis_mismatch else ""
        lines.append(
            f"| {a.symbol}{flag} | {a.quantity:.4f} | ${a.lot_weighted_cost:,.2f} | ${a.current_price:,.2f} | "
            f"${a.market_value:,.2f} | ${a.unrealized_dollars:,.2f} | {a.unrealized_pct:+.2f}% | "
            f"{a.lot_count} | ${a.best_lot_cost:,.2f} / ${a.worst_lot_cost:,.2f} |"
        )

    mismatched = [a for a in ctx.loss_only_assets if a.basis_mismatch]
    if mismatched:
        lines += [
            "",
            "⚠ = the broker's blended `avg_cost_basis` materially disagrees with the cost of the "
            "actual lots, so the two views of this position tell different stories:",
        ]
        for a in mismatched:
            lines.append(
                f"- **{a.symbol}**: `avg_cost_basis` ${a.avg_cost_basis:,.2f} vs. lot-weighted "
                f"${a.lot_weighted_cost:,.2f} (price ${a.current_price:,.2f}) — the blended average "
                f"implies {(a.current_price - a.avg_cost_basis) / a.avg_cost_basis * 100:+.2f}%, "
                f"the lots imply {a.unrealized_pct:+.2f}%"
            )
    return lines


def render_email_summary(ctx: RunContext) -> str:
    n_sells = (
        len(ctx.drawdown_liquidations) + len(ctx.blocked_liquidations)
        + len(ctx.profit_taking_sells) + len(ctx.cleanup_sells)
    )
    return (
        f"Scheduled rebalance {ctx.current_date.isoformat()}: "
        f"{len(ctx.buys)} buy(s), "
        f"{n_sells} sell(s). "
        f"Total_High_Beta_Gains_Realized: ${ctx.total_high_beta_gains_realized:,.2f}. "
        f"Total_Cleanup_Gains_Realized: ${ctx.total_cleanup_gains_realized:,.2f}. "
        f"Final buying_power: ${ctx.account_cash:,.2f}. "
        f"Dormant assets (no activity > {ctx.config.meta.dormant_asset_days}d): {len(ctx.dormant_assets)}. "
        f"Loss-only-lot assets (no lot sellable at a gain): {len(ctx.loss_only_assets)}. "
        "See attached journal entry for full detail."
    )
