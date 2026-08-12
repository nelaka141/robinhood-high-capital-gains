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
python3 -m bot.cli price-cache-plan  --repo-dir . --current-date <today> --out price_fetch_plan.json
# agent fetches only price_fetch_plan.json's fetch_batches via get_equity_historicals,
# writes them to fetched_bars.json
python3 -m bot.cli price-cache-merge --repo-dir . --current-date <today> \
    --bars-in fetched_bars.json --out price_cache_result.json
# price_cache_result.json's daily_closes/daily_lows_highs drop straight into snapshot.json

python3 -m bot.cli plan     --snapshot snapshot.json --repo-dir . --out plan_result.json
# agent executes plan_result.json's sells_to_place via its broker, then re-fetches
# net_realized_gains_ytd and buying_power
python3 -m bot.cli finalize --resume plan_result.json \
    --post-sell-pnl <float> --buying-power <float> \
    --repo-dir . --out finalize_result.json
# agent executes finalize_result.json's buys_to_place via its broker
```

None of these commands call `place_market_order`. All are read-a-JSON-file-in,
write-a-JSON-file-out — safe to run repeatedly while testing, and trivially unit-testable
(`bot/_smoke_test_cli.py` and `bot/_smoke_test_price_cache.py` run them via `subprocess`, no
mocking needed).

### Price history cache

`price_history/daily_bars.json` is a persistent, git-tracked rolling ~90-day daily-bar cache
(`bot/price_cache.py`) covering every target symbol plus `beta_benchmark_symbol`. It exists so
the agent doesn't re-fetch a full ~90-day `get_equity_historicals` window for every symbol on
every cycle — after the first cycle (a one-time full backfill), a normal day-over-day cycle
only needs a 1-day incremental fetch per symbol.

- **`price-cache-plan`** reads the cache and tells you, per symbol, whether it's `up_to_date`
  (cache already covers through yesterday — no fetch needed) or needs a fetch: a full
  ~90-day backfill if the symbol is missing/empty from the cache (new target, or the cache
  doesn't exist yet), otherwise just the day(s) since the last cached bar (normally 1, more if
  a cycle was skipped). Symbols needing the identical date range are grouped into one
  `fetch_batches` entry so you can batch `get_equity_historicals` calls the normal way.
- Fetch only what `fetch_batches` asks for, and write it to a JSON file shaped
  `{"SYMBOL": [{"date": "YYYY-MM-DD", "close": ..., "low": ..., "high": ...}, ...]}` — map each
  returned bar's `begins_at` (truncated to the date) to `date`, and `close_price`/`low_price`/
  `high_price` to `close`/`low`/`high`. Omit a symbol entirely if it was already `up_to_date`.
- **`price-cache-merge`** unions those bars into `price_history/daily_bars.json` (a fresh bar
  overwrites any existing same-date entry), prunes anything older than the rolling window, and
  writes `daily_closes`/`daily_lows_highs` — already sliced to the last ~90 calendar days, in
  the exact `snapshot.json` schema shape — ready to copy straight in. Pass `--bars-in` only if
  `fetch_batches` was non-empty; omitting it just re-slices/re-prunes the existing cache.
- `price_history/daily_bars.json` is a normal state file — commit it alongside `peak/prices.json`
  etc. whenever it changes (CLAUDE.md Step 7/8).

### `plan`

Reads `--snapshot` (schema below) plus the repo's state files (`peak/prices.json`,
`tax/realized_gains_by_year.json`, `transferred_basis.json`). Runs Steps 1–5 and Step 6's
sell-side planning. Writes `--out` as one of:

- `{"no_trades": true, ...}` — Step 1's early exit (no drift breach, no drawdown). Already wrote
  the NO TRADES journal entry and updated peak prices / the tax file — nothing left to do except
  commit those changes.
- `{"halted_for_approval": true, "halt_reason": "...", ...}` — some individual planned trade
  this cycle (a single sell, or a single provisionally-sized buy) exceeds `seek_approval_value`
  — checked per trade, not against the summed total of the cycle. **Stop. Do not execute
  anything. Nothing was written to any state file.** Report `halt_reason` to the user and wait
  for explicit confirmation before re-running with a manual override (this package has no
  "confirmed" flag — that's a deliberate forcing function to keep a human in the loop for large
  trades).
- Otherwise: `{"sells_to_place": [...], "resume_state": {...}}`. Execute `sells_to_place`
  exactly as given — each entry is `{"symbol", "side": "sell", "quantity", "tax_lots", "reason"}`;
  pass `tax_lots` straight through to your sell order's specified-lot parameter if your broker
  supports it (the FIFO selection was already computed against the snapshot's `tax_lots`).
  `resume_state` is opaque — hand the whole `plan_result.json` file to `finalize` unmodified.

### `finalize`

After the sells from `plan` are confirmed filled, re-fetch exactly two live figures and pass
them in: `net_realized_gains_ytd` (same Jan-1-to-today window, via your realized-P&L endpoint)
and `buying_power` (fresh, post-sell). `finalize` uses these — not the snapshot's pre-trade
estimates — to finalize `tax_reserve`, apply the hard-cap scaling, and size the final buys. With
limited margin enabled on the account, `buying_power` already reflects this cycle's own sale
proceeds immediately, so no settlement-reserve bridging is needed. It also writes
`peak/prices.json`, `tax/realized_gains_by_year.json`, and prepends the rendered entry to
`logs/trade_journal.md` — all direct file writes, no MCP/broker needed for any of that.

Output: `{"buys_to_place": [...], "journal_entry_markdown": "...", "email_summary": "...",
"files_changed": [...]}`. Execute `buys_to_place` exactly as given (each entry is
`{"symbol", "side": "buy", "dollar_amount", "reason"}`), then commit `files_changed` and draft
the summary email using `email_summary` + `journal_entry_markdown`.

### snapshot.json schema

```jsonc
{
  "current_date": "2026-07-31",                 // US/Eastern calendar date
  "account_number": "795732718",
  "account_cash": 17178.18,                      // buying_power straight from Robinhood (limited margin enabled — reflects unsettled proceeds immediately) — the CLAUDE.md account_cash/current_cash source
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
| `state.py` | `peak/prices.json`, `tax/realized_gains_by_year.json`, `alpha_reserve.json`, `transferred_basis.json` | Load/save the persistent state files |
| `models.py` | — | Shared value objects (`Position`, `DriftResult`, `MomentumScore`, `TradeIntent`, `RunContext`, ...) |
| `broker.py` | "You execute actions via the connected Robinhood MCP Server" | `BrokerClient` Protocol + a `robin_stocks` reference implementation (standalone mode only) |
| `snapshot_broker.py` | — | `SnapshotBroker` — reads the same `BrokerClient` interface from a JSON snapshot instead of a live connection (snapshot-driven mode) |
| `price_cache.py` | Execution Mode Step 2, `daily_closes`/`daily_lows_highs` sourcing | `price_history/daily_bars.json` — persistent rolling ~90-day cache; `price-cache-plan`/`price-cache-merge` (see "Price history cache" above) |
| `serialize.py` | — | JSON round-trip of `RunContext` between `plan` and `finalize` |
| `indicators.py` | Step 3's RSI/EMA formulas, Step 4's Beta formula | Pure-Python EMA(9), RSI(14), beta — no external indicator API needed |
| `fifo.py` | Step 4, "Dollar-gate accounting for PARTIAL sales" | FIFO lot-matched realized-profit calculation |
| `cost_basis.py` | Step 1, `avg_cost_basis` sourcing waterfall | primary → tax-lots → `transferred_basis.json` override → fail closed |
| `steps.py` | **Steps 1–6**, in order | Drift/drawdown, guardrails (incl. the universal three-leg Z-score buy-timing guard, `z_score_downward_points`/`z_score_points`/`z_score_upward_points` — gates every buy EXCEPT the Alpha Leader allocation, which is deliberately exempt; `ctx.alpha_buy_guarded_symbols` is the subset that also blocks the Alpha Leader, currently wash-sale only — the flat-calendar `profit_resell_cooldown_days` resell guard, and the `z_score_sell_points` resell-timing guard requiring `Z_yesterday - Z_today < z_score_sell_points`), Alpha Leader buy-guard cascade + multiplier (`step3_alpha_leader` picks the Top Momentum Symbol's first candidate not in `alpha_buy_guarded_symbols` down to `alpha_leader_least_momentum_score`; `resolve_alpha_leader_reserve` computes the resulting `alpha_reserve.json` audit record after Step 6b), and `harvest_needed_dollars` sizing — the multiplier injection plus fully closing Underweight gaps), GET THE PROFITS / Momentum Reversal Trim (both percent/dollar gate pairs OR'd, not AND'd) / Overweight ranking (margin/dollar gate pair also OR'd) + harvest sizing (`_size_overweight_trims`, incl. the `minimum_alpha_leader_sell_profit` guard), price-limit halts, and `compute_dormant_assets` (Step 7's reporting-only Dormant Assets section, `dormant_asset_days`). Step 6 is split: `step6a_prepare_sells`/`step6b_finalize_buys` (planning-only, used by `cli.py`) vs. `step6_execute_live` (actually places orders, used by `main.py`) |
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
(needs `GITHUB_TOKEN` + a repo clone).

## Design notes / simplifications vs. the markdown spec

- **Float, not Decimal.** Real production money math should probably use `Decimal` throughout;
  this uses `float` for readability, matching how the numbers read in `logs/trade_journal.md`.
- **Specified-lot selling**: sell entries in `sells_to_place` carry the exact FIFO `tax_lots`
  selection computed against the snapshot — pass it through to your broker's specified-lot-sell
  parameter if it has one, so the dollar amount actually realized matches what was gated on.
