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
    return "\n".join(lines) + "\n"


def render_entry(ctx: RunContext) -> str:
    ts = ctx.current_date.isoformat()
    n_sells = len(ctx.drawdown_liquidations) + len(ctx.profit_taking_sells) + len(ctx.overweight_trims)
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
    for sym, reason in ctx.buy_guarded_symbols.items():
        if sym not in ctx.excluded_symbols:
            lines.append(f"- **{sym}** (buy-guarded only): {reason}")

    lines += [
        "",
        "## Alpha Leader Selection — Momentum_Score",
        "| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |",
        "|---|---|---|---|---|---|---|",
    ]
    for sym, m in sorted(ctx.momentum_scores.items(), key=lambda kv: -kv[1].score):
        leader_tag = " ← ALPHA LEADER" if sym == ctx.alpha_leader else ""
        lines.append(
            f"| {sym}{leader_tag} | {m.rsi14:.2f} | {m.ema9_now:.2f} | {m.ema9_prior:.2f} | "
            f"{m.price_vs_ema_pct:+.2f} | {m.ema_slope_pct:+.2f} | {m.score:+.2f} |"
        )

    lines += [
        "",
        "## Tax Reserve",
        f"- `net_realized_gains_ytd_pretrade`: **${ctx.net_realized_gains_ytd_pretrade:,.2f}**",
        f"- `net_realized_gains_ytd_effective` (post-sells): "
        f"**${(ctx.net_realized_gains_ytd_effective or 0):,.2f}**",
        f"- `tax_reserve` (final): **${ctx.tax_reserve:,.2f}**",
        "",
        "## GET THE PROFITS / Momentum Reversal Trim Sells",
    ]
    for t in ctx.profit_taking_sells:
        lines.append(f"- **{t.symbol}**: {t.reason}")
    if not ctx.profit_taking_sells:
        lines.append("- none fired this cycle")

    lines += ["", "## Overweight High-Beta Trims"]
    for t in ctx.overweight_trims:
        lines.append(f"- **{t.symbol}**: {t.reason}")
    if not ctx.overweight_trims:
        lines.append("- none fired this cycle")

    lines += ["", "## Buys"]
    for t in ctx.buys:
        lines.append(f"- **{t.symbol}**: ${t.dollar_amount:,.2f}")
    if not ctx.buys:
        lines.append("- none fired this cycle")

    lines += [
        "",
        f"## Total_High_Beta_Gains_Realized: **${ctx.total_high_beta_gains_realized:,.2f}**",
        "",
        "## SKIPPED/PENDING",
        "| Symbol | Reason | Would-be action |",
        "|---|---|---|",
    ]
    for s in ctx.skipped:
        lines.append(f"| {s.symbol} | {s.reason} | {s.would_be_action} |")

    lines += [
        "",
        "## Orders Placed",
        "```",
        *[str(o) for o in ctx.executed_orders],
        "```",
    ]
    return "\n".join(lines) + "\n"


def render_email_summary(ctx: RunContext) -> str:
    return (
        f"Scheduled rebalance {ctx.current_date.isoformat()}: "
        f"{len(ctx.buys)} buy(s), "
        f"{len(ctx.drawdown_liquidations) + len(ctx.profit_taking_sells) + len(ctx.overweight_trims)} sell(s). "
        f"Alpha Leader: {ctx.alpha_leader or 'n/a'}. "
        f"Total_High_Beta_Gains_Realized: ${ctx.total_high_beta_gains_realized:,.2f}. "
        f"Final buying_power: ${ctx.account_cash:,.2f}. "
        "See attached journal entry for full detail."
    )
