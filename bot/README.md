# bot/ — Python implementation of CLAUDE.md

A direct, ordered translation of the markdown spec in `../CLAUDE.md` (v2.42.0) into runnable
Python. `CLAUDE.md` stays the maintained business-rules spec; this package is what actually
executes it. Two ways to run it:

- **Snapshot-driven mode** (`bot/cli.py`) — the mode this repo actually uses. An MCP-connected
  agent (a scheduled Claude Code session) supplies market data as a JSON snapshot; the script
  returns an exact order plan; the agent executes it via its own broker connection. The script
  never touches a broker and needs no credentials of its own.
- **Standalone mode** (`bot/main.py`) — bot/ owns a direct broker connection and does
  everything itself, for running completely outside of any agent/MCP setup.

## Snapshot-driven mode (production)

This is what `CLAUDE.md`'s "Execution Mode" section instructs the scheduled routine to do each
cycle. Two commands, with the agent doing the actual order placement between them:

```bash
python3 -m bot.cli plan     --snapshot snapshot.json --repo-dir . --out plan_result.json
# agent executes plan_result.json's sells_to_place via its broker, then re-fetches
# net_realized_gains_ytd and buying_power
python3 -m bot.cli finalize --resume plan_result.json \
    --post-sell-pnl <float> --buying-power <float> \
    --repo-dir . --out finalize_result.json
# agent executes finalize_result.json's buys_to_place via its broker
```

Neither command calls `place_market_order`. Both are read-a-JSON-file-in,
write-a-JSON-file-out — safe to run repeatedly while testing, and trivially unit-testable
(`bot/_smoke_test_cli.py` runs both via `subprocess`, no mocking needed).

### `plan`

Reads `--snapshot` (schema below) plus the repo's state files (`peak/prices.json`,
`settlement/reserve.json`, `tax/realized_gains_by_year.json`, `transferred_basis.json`). Runs
Steps 1–5 and Step 6's sell-side planning. Writes `--out` as one of:

- `{"no_trades": true, ...}` — Step 1's early exit (no drift breach, no drawdown). Already wrote
  the NO TRADES journal entry and updated peak prices / the tax file — nothing left to do except
  commit those changes.
- `{"halted_for_approval": true, "halt_reason": "...", ...}` — gross sell value exceeds
  `seek_approval_value`. **Stop. Do not execute anything. Nothing was written to any state
  file.** Report `halt_reason` to the user and wait for explicit confirmation before re-running
  with a manual override (this package has no "confirmed" flag — that's a deliberate forcing
  function to keep a human in the loop for large sells).
- Otherwise: `{"sells_to_place": [...], "resume_state": {...}}`. Execute `sells_to_place`
  exactly as given — each entry is `{"symbol", "side": "sell", "quantity", "tax_lots", "reason"}`;
  pass `tax_lots` straight through to your sell order's specified-lot parameter if your broker
  supports it (the FIFO selection was already computed against the snapshot's `tax_lots`).
  `resume_state` is opaque — hand the whole `plan_result.json` file to `finalize` unmodified.

### `finalize`

After the sells from `plan` are confirmed filled, re-fetch exactly two live figures and pass
them in: `net_realized_gains_ytd` (same Jan-1-to-today window, via your realized-P&L endpoint)
and `buying_power` (settled, spendable cash). `finalize` uses these — not the snapshot's
pre-trade estimates — to finalize `tax_reserve`, apply the settlement-bridge/hard-cap scaling,
and size the final buys. It also writes `peak/prices.json`, `settlement/reserve.json`,
`tax/realized_gains_by_year.json`, and prepends the rendered entry to `logs/trade_journal.md` —
all direct file writes, no MCP/broker needed for any of that.

Output: `{"buys_to_place": [...], "journal_entry_markdown": "...", "email_summary": "...",
"files_changed": [...]}`. Execute `buys_to_place` exactly as given (each entry is
`{"symbol", "side": "buy", "dollar_amount", "reason"}`), then commit `files_changed` and draft
the summary email using `email_summary` + `journal_entry_markdown`.

### snapshot.json schema

```jsonc
{
  "current_date": "2026-07-31",                 // US/Eastern calendar date
  "account_number": "795732718",
  "account_cash": 17178.18,                      // buying_power (settled, spendable) — the CLAUDE.md account_cash/current_cash source
  "account_cash_ledger": 32167.10,               // raw cash ledger (informational; can include unsettled proceeds)
  "quotes": { "TQQQ": 63.68, "...": 0.0 },       // every target symbol, live last-trade price
  "positions": {                                 // OMIT a symbol entirely if not currently held
    "TQQQ": { "quantity": 37.07, "avg_cost_basis": 73.92 }  // avg_cost_basis: null if unresolved (triggers the fail-closed path)
  },
  "daily_closes": {                              // ascending date, ~90 calendar days through YESTERDAY (regular session), every target symbol PLUS the beta_benchmark_symbol (SPY)
    "TQQQ": [ { "date": "2026-06-01", "close": 61.2 }, "..." ]
  },
  "daily_lows_highs": {                          // ascending date, at least 3x no_of_days_for_price_compare trading days through YESTERDAY — same historicals call as daily_closes, just also carrying low/high
    "TQQQ": [ { "date": "2026-07-28", "low": 60.1, "high": 64.2 }, "..." ]
  },
  "tax_lots": {                                  // only for currently-held symbols; any order (fifo.py sorts by open_date itself)
    "TQQQ": [ { "open_lot_id": "...", "quantity": 10, "cost_per_share": 70.5, "open_date": "2026-06-01", "is_selectable": true } ]
  },
  "net_realized_gains_ytd_pretrade": 20113.23    // Jan 1 -> current_date, equity asset class, BEFORE this cycle's sells
}
```

One historicals fetch per symbol covers both `daily_closes` and `daily_lows_highs` — pull once,
populate both.

## Standalone mode

```bash
pip install -r bot/requirements.txt
python3 -m bot.main --account <account_number> --repo-dir .        # dry run (default) — no orders, no push, no email
python3 -m bot.main --account <account_number> --repo-dir . --live # places real orders
```

Runs the full Step 1→7 pipeline with `bot/` owning the broker connection directly
(`broker.RobinStocksBroker` by default). Two of its methods raise `NotImplementedError` —
`robin_stocks` has no public tax-lot or aggregate realized-P&L endpoint — so this mode isn't
`--live`-ready without wiring those to a real source first. Not the mode this repo actually
uses; kept for fully-standalone use outside of any MCP/agent setup.

## Layout

| File | CLAUDE.md section | What it does |
|---|---|---|
| `config.py` | "Core Parameters & Risk Triggers", `targets`/`forceSell` | Loads `portfolio_targets.json` into typed dataclasses |
| `state.py` | `peak/prices.json`, `settlement/reserve.json`, `tax/realized_gains_by_year.json`, `transferred_basis.json` | Load/save the four persistent state files |
| `models.py` | — | Shared value objects (`Position`, `DriftResult`, `MomentumScore`, `TradeIntent`, `RunContext`, ...) |
| `broker.py` | "You execute actions via the connected Robinhood MCP Server" | `BrokerClient` Protocol + a `robin_stocks` reference implementation (standalone mode only) |
| `snapshot_broker.py` | — | `SnapshotBroker` — reads the same `BrokerClient` interface from a JSON snapshot instead of a live connection (snapshot-driven mode) |
| `serialize.py` | — | JSON round-trip of `RunContext` between `plan` and `finalize` |
| `indicators.py` | Step 3's RSI/EMA formulas, Step 4's Beta formula | Pure-Python EMA(9), RSI(14), beta — no external indicator API needed |
| `fifo.py` | Step 4, "Dollar-gate accounting for PARTIAL sales" | FIFO lot-matched realized-profit calculation |
| `cost_basis.py` | Step 1, `avg_cost_basis` sourcing waterfall | primary → tax-lots → `transferred_basis.json` override → fail closed |
| `steps.py` | **Steps 1–6**, in order | Drift/drawdown, guardrails, Alpha Leader + multiplier, GET THE PROFITS / Momentum Reversal Trim / Overweight ranking, price-limit halts. Step 6 is split: `step6a_prepare_sells`/`step6b_finalize_buys` (planning-only, used by `cli.py`) vs. `step6_execute_live` (actually places orders, used by `main.py`) |
| `journal.py` | Step 7, `logs/trade_journal.md` | Markdown entry rendering + the 5-live/10-per-history-file rotation rule |
| `gitops.py` | Step 7, "branch... merge it directly into main" | git branch/commit/push + GitHub REST API PR-and-merge (standalone mode only — the agent does this itself in snapshot-driven mode) |
| `notify.py` | Step 7, "Draft an email... via Gmail" | Gmail draft creation + `Send-With-Claude` label (standalone mode only) |
| `cli.py` | The whole Execution Sequence | `plan` / `finalize` — the snapshot-driven commands |
| `main.py` | The whole Execution Sequence | `run_cycle()` — the standalone commands |

`bot/_smoke_test.py` and `bot/_smoke_test_cli.py` are self-contained integration tests (no
credentials needed) — run `PYTHONPATH=. python3 bot/_smoke_test.py` and
`PYTHONPATH=. python3 bot/_smoke_test_cli.py` after any change.

## What's still stubbed (standalone mode only — doesn't affect snapshot-driven mode)

1. **`RobinStocksBroker.get_tax_lots`** — `robin_stocks` has no public tax-lots endpoint.
2. **`RobinStocksBroker.get_realized_pnl_ytd`** — `robin_stocks` has no aggregate realized-P&L
   endpoint. A local ledger reconciled from order fills is a reasonable fallback.

Neither of these matters for snapshot-driven mode — the agent supplies both directly as part of
the snapshot / `finalize` arguments, sourced from whatever real connection it has (e.g. the
Robinhood MCP server's `get_equity_tax_lots` / `get_realized_pnl`).

Also standalone-only and stubbed: `notify.py` (needs a Gmail OAuth `token.json`), `gitops.py`
(needs `GITHUB_TOKEN` + a repo clone). The settlement-reserve bridge
(`steps._apply_settlement_bridge`) only bridges *pre-existing* `pending_draws` entries in both
modes; creating a *fresh* entry for a same-cycle sell whose proceeds haven't settled requires
checking that specific order's settlement status, which the agent/broker must do itself
(CLAUDE.md's own workflow uses `review_equity_order` / a rejected buy for this).

## Design notes / simplifications vs. the markdown spec

- **Float, not Decimal.** Real production money math should probably use `Decimal` throughout;
  this uses `float` for readability, matching how the numbers read in `logs/trade_journal.md`.
- **Specified-lot selling**: sell entries in `sells_to_place` carry the exact FIFO `tax_lots`
  selection computed against the snapshot — pass it through to your broker's specified-lot-sell
  parameter if it has one, so the dollar amount actually realized matches what was gated on.
