# bot/ — Python implementation of CLAUDE.md

A direct, ordered translation of the markdown spec in `../CLAUDE.md` (v2.41.0) into runnable
Python. Each of CLAUDE.md's seven execution steps is a function you can read side-by-side with
its corresponding markdown section.

## Layout

| File | CLAUDE.md section | What it does |
|---|---|---|
| `config.py` | "Core Parameters & Risk Triggers", `targets`/`forceSell` | Loads `portfolio_targets.json` into typed dataclasses |
| `state.py` | `peak/prices.json`, `settlement/reserve.json`, `tax/realized_gains_by_year.json`, `transferred_basis.json` | Load/save the four persistent state files |
| `models.py` | — | Shared value objects (`Position`, `DriftResult`, `MomentumScore`, `TradeIntent`, `RunContext`, ...) |
| `broker.py` | "You execute actions via the connected Robinhood MCP Server" | `BrokerClient` Protocol + a `robin_stocks`-based reference implementation |
| `indicators.py` | Step 3's RSI/EMA formulas, Step 4's Beta formula | Pure-Python EMA(9), RSI(14), beta — no external indicator API needed |
| `fifo.py` | Step 4, "Dollar-gate accounting for PARTIAL sales" | FIFO lot-matched realized-profit calculation |
| `cost_basis.py` | Step 1, `avg_cost_basis` sourcing waterfall | primary → tax-lots → `transferred_basis.json` override → fail closed |
| `steps.py` | **Steps 1–6**, in order | The core logic: drift/drawdown, guardrails, Alpha Leader + multiplier, GET THE PROFITS / Momentum Reversal Trim / Overweight ranking, price-limit halts, trade execution |
| `journal.py` | Step 7, `logs/trade_journal.md` | Markdown entry rendering + the 5-live/10-per-history-file rotation rule |
| `gitops.py` | Step 7, "branch... merge it directly into main" | git branch/commit/push + GitHub REST API PR-and-merge |
| `notify.py` | Step 7, "Draft an email... via Gmail" | Gmail draft creation + `Send-With-Claude` label |
| `main.py` | The whole Execution Sequence | `run_cycle()` calls Steps 1→7 in strict order; CLI entrypoint |

## Running it

```bash
pip install -r bot/requirements.txt
python3 -m bot.main --account <account_number> --repo-dir .        # dry run (default) — no orders, no push, no email
python3 -m bot.main --account <account_number> --repo-dir . --live # places real orders
```

Dry run exercises the full decision pipeline (drift, drawdown, Alpha Leader, profit-taking
gates, price limits, buy sizing) and prints/returns a `RunContext` with everything a cycle
would have done — orders come back tagged `state: "DRY_RUN"` instead of hitting the broker.

`bot/_smoke_test.py` is a self-contained integration test against a synthetic in-memory broker
(no credentials needed) — run `PYTHONPATH=. python3 bot/_smoke_test.py` to sanity-check the
pipeline after any change.

## What you still need to wire up before running `--live`

This package is broker-agnostic by design (`BrokerClient` in `broker.py`), but two pieces of
CLAUDE.md's logic depend on endpoints the reference `RobinStocksBroker` doesn't implement,
because the unofficial `robin_stocks` library doesn't expose them:

1. **`get_tax_lots`** — needed for every FIFO dollar-gate check (Step 4). Without it, every
   partial GET THE PROFITS / Momentum Reversal Trim sale fails closed (0 lots → gate never
   passes) — sells simply won't fire, which is a safe (if overly conservative) default, not a
   silent miscalculation.
2. **`get_realized_pnl_ytd`** — needed for the tax reserve (Step 1/3/6). Without it, `tax_reserve`
   can't be computed; you'll want a local ledger reconciled from `get_all_stock_orders()` fills,
   or your broker's actual realized-P&L endpoint.

Also stubbed, clearly marked, not required for `--dry-run`:
- `notify.py` assumes you've already completed the Gmail API OAuth flow (a `token.json` next to
  wherever you run this).
- `gitops.py` assumes `GITHUB_TOKEN` is set in the environment and `repo-dir` is a working clone
  with `origin` configured.
- The settlement-reserve bridge (`steps._apply_settlement_bridge`) only bridges *pre-existing*
  `pending_draws` entries; creating a *fresh* entry for a same-cycle sell whose proceeds haven't
  settled requires checking that specific order's settlement status, which is broker-specific
  (CLAUDE.md's own workflow uses `review_equity_order` / a rejected buy for this) — left as a
  `# TODO` for your `BrokerClient`.

## Design notes / simplifications vs. the markdown spec

- **Float, not Decimal.** Real production money math should probably use `Decimal` throughout;
  this uses `float` for readability, matching how the numbers read in `logs/trade_journal.md`.
- **`get_daily_lows_highs`/`get_daily_closes` interfaces are broker-defined**, not tied to any
  specific historicals API shape — implement them against whatever your broker returns.
- **Specified-lot selling**: `TradeIntent.tax_lots` carries the exact FIFO selection through to
  `BrokerClient.place_market_order`, but `RobinStocksBroker` doesn't honor it (robin_stocks has
  no specified-lot-sell parameter) — if your broker supports it, wire it through there so the
  dollar amount actually realized matches what was gated on, per CLAUDE.md Step 4.
