# 2026-09-07 — Scheduled Rebalance Check — ABORTED (market holiday, planned sell unfilled)

**Status:** ABORTED after Step 4 planning. 1 sell candidate identified by `bot.cli plan`; order placed defensively, found unfilled/queued, cancelled. `bot.cli finalize` was deliberately NOT run this cycle — its precondition ("this cycle's sells confirmed filled") was false, and running it anyway would have falsely recorded a MU sale that never happened.

**Timestamp:** 2026-09-07 09:53 AM EDT

## Root Cause
2026-09-07 is Labor Day — a full NYSE/NASDAQ market holiday. No regular-hours, pre-market, or after-hours session opened at any point today. `bot.cli plan` (Steps 1–5, snapshot-driven, has no market-calendar awareness) correctly identified a qualifying GET THE PROFITS net-profit full exit for MU and returned `sells_to_place`, exactly as it would on any trading day. The account snapshot's live quotes were unavoidably stale (last trade Fri 2026-09-04, since nothing has traded since).

## What Was Attempted
- `bot.cli drive-pull` — OK, state synced from Drive.
- `bot.cli price-cache-plan` / `price-cache-merge` — OK, cache updated through 2026-09-04 (Friday's close, the most recent trading session).
- `bot.cli plan --snapshot snapshot.json` — OK. Returned 1 sell:
  - **MU** — GET THE PROFITS net-profit FULL EXIT (v2.83.0): +6.64% raw gain, net FIFO $50.90 across all 1.700544 shares (dynamic thresholds 1.95% / $44.30 at 12.0d weighted lot age) — includes 0.7667 underwater share(s) carrying $-18.50 of lot loss, netted against $69.40 from the profitable lots. Ordinary order (Robinhood default FIFO lot matching); wash-sale buy-guard would NOT have armed (net gain).
- Placed the MU sell as a fractional market order (`regular_hours` — fractional orders cannot route any other way). Order `6a9ec1a2-3426-4f73-8c69-0c65c0518e7c` came back **`queued`**, `cumulative_quantity: 0`, no executions — confirming no session is open today.
- Re-checked order state via `get_equity_orders`: still `queued`, unfilled.
- **Cancelled** the order (`cancel_equity_order` → accepted → confirmed `state: cancelled`, `cumulative_quantity: 0.000000`) rather than leave a GFD order sitting exposed to an uncontrolled fill later today or tomorrow, outside of any cycle's price/tax-reserve accounting.
- **No position change occurred.** MU holding is untouched (1.700544 shares, avg cost basis $951.72, unchanged).

## Why This Halted Instead of Improvising
CLAUDE.md's snapshot-driven pipeline (`plan` → execute sells → `finalize` → execute buys) assumes a planned sell fills same-cycle before `finalize` sizes buys, updates `peak/prices.json` / `tax/realized_gains_by_year.json`, and renders the journal entry. CLAUDE.md's Step 6 "Extended Hours Execution" / SKIPPED-PENDING language covers a *partial* trading day (some symbols ineligible for extended-hours fractional routing while a session is otherwise open); it does not explicitly address a **full-day closure** where the market never opens at all despite `plan` still finding a valid candidate. Rather than manually re-deriving `finalize`'s state writes (peak-price tracking, tax-reserve math, buy sizing) by hand — which CLAUDE.md explicitly forbids ("Do not second-guess or override the script's decisions"; "abort, log, do not fall back to manually re-deriving the decision") — this cycle aborts here and reports the gap.

## State File Impact
- `peak/prices.json`, `tax/realized_gains_by_year.json`, `price_history/daily_bars.json`: **unchanged this cycle** beyond the routine price-history cache update (Friday's close merged in). No peak-price/profit-sell/liquidation fields were touched, since `finalize` never ran.
- No buys were sized or placed (buy-side planning never runs without confirmed sells).
- No git-tracked state beyond this journal entry.

## Next Steps
- Next scheduled cycle (assuming a normal trading day) will re-run `plan` fresh — MU's GET THE PROFITS gate will very likely re-fire since nothing about the position changed, so no manual follow-up should be needed.
- Recommend the schedule account for US market holidays if this keeps producing no-op cycles on holidays.

# 2026-09-04 — Scheduled Rebalance Check — EXECUTED (8 sell(s), 0 buy(s))

**Status:** EXECUTED. 8 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$78,159.39**
- `cash` (ledger): **$78,159.39**
- `current_cash` (post-cap): **$78,159.39**
- `account_balance`: **$140,443.21**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **MSTR** (excluded): Profit-sell buy-guard: profit-sold 2026-09-04 @ 140.57 (full exit) — blocked because: cooldown not met (0d/1d required); dip not confirmed (leg2 close_1d_back→close_yesterday change=-15.057%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.811%, need > 0.150%)
- **SPCX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-04 @ 148.065 (full exit) — blocked because: cooldown not met (0d/1d required); dip not confirmed (leg2 close_1d_back→close_yesterday change=-6.064%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.561%, need > 0.150%)
- **LLY** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 1284.3 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.007%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-1.652%, need > 0.150%)
- **JNJ** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 275.33 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.460%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.169%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.113%, need > 0.150%)
- **JPM** (excluded): Profit-sell buy-guard: profit-sold 2026-08-13 @ 363.54 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.355%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.631%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.131%, need > 0.150%)
- **V** (excluded): Profit-sell buy-guard: profit-sold 2026-08-26 @ 383.44 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.526%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.093%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.891%, need > 0.150%)
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-08-17 @ 873.055 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.622%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.971%, need > -0.050%)
- **COST** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 972.77 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.838%, need > 0.150%)
- **CVX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-01 @ 207.89 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.350%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-1.384%, need > 0.150%)
- **COP** (excluded): Profit-sell buy-guard: profit-sold 2026-09-04 @ 133.4425 (full exit) — blocked because: cooldown not met (0d/1d required); earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.751%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-0.883%, need > 0.150%)
- **EQIX** (excluded): Profit-sell buy-guard: profit-sold 2026-08-14 @ 1086.12 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.080%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.264%, need > 0.150%)
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 76.6899 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.625%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.377%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.097%, need > 0.150%)
- **INTC** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.141%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.712%, need > -0.050%)
- **PLTR** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-27 @ 184.7042 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-7.510%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-4.875%, need > 0.150%)
- **MU** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 949.47 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.262%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.208%, need > -0.050%)
- **COIN** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-03 @ 192.27 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-9.597%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-4.252%, need > 0.150%)
- **ARM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 282.4199 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.016%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.098%, need > -0.050%)
- **SMCI** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-25 @ 37.75 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.737%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.211%, need > -0.050%)
- **IONQ** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.500%, need > -0.050%)
- **AMZN** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-12 @ 271.44 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.023%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.518%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.280%, need > 0.150%)
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-04 @ 324.92 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.260%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-5.467%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-6.303%, need > 0.150%)
- **NVDA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-27 @ 224.76 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-3.029%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.756%, need > -0.050%)
- **ORCL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 146.45 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.819%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-5.275%, need > -0.050%)
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 377.07 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.521%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.578%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.944%, need > 0.150%)
- **MSFT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-28 @ 512.754 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.659%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.971%, need > 0.150%)
- **HOOD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 99.5005 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.833%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-14.436%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.547%, need > 0.150%)
- **AAPL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-07-17 @ 333.4801 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.053%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.010%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.989%, need > 0.150%)
- **META** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.321%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.892%, need > -0.050%)
- **NEE** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.204%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.151%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.785%, need > 0.150%)
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-12 @ 296.415 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.263%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-4.375%, need > -0.050%)
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.371%, need > 0.150%)
- **F** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-14 @ 14.4276 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.060%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.854%, need > -0.050%)
- **GM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 89.55 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.689%, need > -0.050%)
- **IBM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-03 @ 236.04 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.128%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.285%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.209%, need > 0.150%)
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.430%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-4.626%, need > 0.150%)
- **UNH** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.847%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.323%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.126%, need > 0.150%)
- **GE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 382.1775 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.185%, need > -0.050%)
- **BRK.B** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.575%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.571%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.483%, need > 0.150%)
- **WMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 116.365 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.158%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.171%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.044%, need > 0.150%)
- **PG** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.977%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-0.389%, need > 0.150%)
- **XOM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-11 @ 159.73 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.473%, need > 0.150%)
- **SO** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.250%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.522%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.806%, need > 0.150%)
- **PLD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 141.89 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.281%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.684%, need > 0.150%)
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 174.68 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.744%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.983%, need > 0.150%)
- **LIN** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.144%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-0.958%, need > 0.150%)
- **FCX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 76.0501 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.008%, need > 0.200%)
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.391%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.304%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=+0.087%, need > 0.150%)
- **DUK** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.141%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.699%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.956%, need > 0.150%)

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $1.90) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| HOOD | 71.60 | 108.70 | 104.12 | +12.99 | +4.40 | +38.99 |
| AAPL | 68.22 | 319.95 | 311.48 | +0.58 | +2.72 | +21.53 |
| META | 61.37 | 582.88 | 567.24 | +5.77 | +2.76 | +19.89 |
| COIN | 63.26 | 180.68 | 175.83 | +2.30 | +2.76 | +18.32 |
| TSLA | 66.12 | 358.07 | 347.42 | -1.12 | +3.06 | +18.06 |
| SMCI | 61.24 | 37.15 | 36.92 | +5.92 | +0.62 | +17.78 |
| NFLX | 67.12 | 81.20 | 79.61 | -2.69 | +1.99 | +16.42 |
| NVDA | 60.52 | 221.07 | 217.32 | +4.09 | +1.73 | +16.33 |
| MU | 57.85 | 945.51 | 936.36 | +5.84 | +0.98 | +14.66 |
| ORCL | 57.02 | 148.02 | 147.02 | +6.17 | +0.68 | +13.86 |
| MSFT | 58.13 | 501.15 | 492.83 | -0.18 | +1.69 | +9.64 |
| F | 55.18 | 14.07 | 14.02 | +3.45 | +0.38 | +9.01 |
| XOM | 59.06 | 161.66 | 160.42 | -1.11 | +0.77 | +8.71 |
| PLTR | 58.52 | 178.91 | 176.73 | -2.72 | +1.23 | +7.04 |
| VRT | 52.28 | 262.37 | 266.17 | +5.67 | -1.43 | +6.53 |
| AMT | 53.78 | 175.59 | 175.20 | +0.25 | +0.22 | +4.25 |
| PG | 50.22 | 145.75 | 144.63 | +0.41 | +0.78 | +1.40 |
| GM | 49.84 | 86.19 | 86.35 | +1.40 | -0.19 | +1.04 |
| IBM | 50.47 | 233.67 | 234.34 | +0.24 | -0.29 | +0.42 |
| WMT | 49.64 | 106.40 | 106.80 | +0.85 | -0.38 | +0.11 |
| FCX | 52.51 | 74.33 | 75.36 | -2.16 | -1.37 | -1.01 |
| UNH | 48.78 | 396.86 | 396.53 | -0.10 | +0.08 | -1.23 |
| TQQQ | 47.69 | 71.18 | 71.81 | +1.10 | -0.89 | -2.10 |
| BRK.B | 46.62 | 504.98 | 504.24 | +0.14 | +0.15 | -3.10 |
| INTC | 42.59 | 90.77 | 92.00 | +4.25 | -1.33 | -4.49 |
| LIN | 45.78 | 486.25 | 486.07 | -1.77 | +0.04 | -5.96 |
| DUK | 44.75 | 121.09 | 122.00 | -0.69 | -0.75 | -6.69 |
| PLD | 45.29 | 139.74 | 141.84 | -1.66 | -1.48 | -7.86 |
| NEE | 41.41 | 83.55 | 84.49 | -0.17 | -1.12 | -9.88 |
| IONQ | 46.12 | 39.78 | 42.37 | -0.90 | -6.10 | -10.88 |
| AMZN | 39.81 | 259.29 | 261.39 | -0.43 | -0.81 | -11.42 |
| ARM | 38.48 | 243.38 | 252.90 | +2.52 | -3.76 | -12.77 |
| AMD | 36.04 | 465.92 | 477.25 | +1.21 | -2.37 | -15.12 |
| UNP | 36.62 | 297.53 | 305.69 | -2.47 | -2.67 | -18.52 |
| GOOG | 31.55 | 338.29 | 342.22 | -0.70 | -1.15 | -20.30 |
| SO | 32.19 | 89.03 | 90.41 | -1.08 | -1.53 | -20.42 |
| SHW | 32.60 | 339.28 | 349.88 | -1.98 | -3.03 | -22.42 |
| GE | 32.29 | 339.78 | 352.62 | -1.17 | -3.64 | -22.52 |
| HD | 29.24 | 326.49 | 336.82 | -1.60 | -3.07 | -25.43 |
| AVGO | 26.91 | 367.44 | 371.68 | -3.16 | -1.14 | -27.39 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$69,884.21**
- `net_realized_gains_ytd_effective` (post-sells): **$69,904.38**
- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **$0.00**
- `tax_reserve` (final, after subtracting paid taxes): **$24,466.53**

## GET THE PROFITS Sells
- none fired this cycle

## Sell Cleanup Pass
- **NVDA**: Sell Cleanup Pass: sweeping 0.2081 remaining share(s) ($47.89, lot cost $217.73 vs. price $230.10) — dust (<$200.00, single green lot)
- **ORCL**: Sell Cleanup Pass: sweeping 0.0890 remaining share(s) ($13.98, lot cost $143.99 vs. price $157.15) — dust (<$200.00, single green lot)
- **TQQQ**: Sell Cleanup Pass: sweeping 0.0676 remaining share(s) ($4.87, lot cost $71.44 vs. price $71.96) — dust (<$200.00, single green lot)
- **SMCI**: Sell Cleanup Pass: sweeping 0.5661 remaining share(s) ($22.27, lot cost $37.20 vs. price $39.34) — dust (<$200.00, single green lot)
- **HOOD**: Sell Cleanup Pass: sweeping 0.3822 remaining share(s) ($46.94, lot cost $103.03 vs. price $122.82) — dust (<$200.00, single green lot)
- **VRT**: Sell Cleanup Pass: sweeping 0.1637 remaining share(s) ($45.39, lot cost $274.20 vs. price $277.26) — dust (<$200.00, single green lot)
- **IBM**: Sell Cleanup Pass: sweeping 0.4028 remaining share(s) ($94.35, lot cost $231.92 vs. price $234.22) — dust (<$200.00, single green lot)
- **XOM**: Sell Cleanup Pass: sweeping 0.2323 remaining share(s) ($37.13, lot cost $152.11 vs. price $159.85) — dust (<$200.00, single green lot)

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)
- none this cycle

## Total_High_Beta_Gains_Realized: **$0.00**
## Total_Cleanup_Gains_Realized: **$15.78**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| AMD | Momentum_Score (-15.12) below min_momentum_score_to_fill_underweight (0.00) | Underweight buy |
| UNP | Momentum_Score (-18.52) below min_momentum_score_to_fill_underweight (0.00) | Underweight buy |
| AMD | Position Cap Top-Up: Momentum_Score (-15.12) below min_momentum_score_to_fill_underweight (0.00) | Position Cap Top-Up |
| HD | Position Cap Top-Up: Momentum_Score (-25.43) below min_momentum_score_to_fill_underweight (0.00) | Position Cap Top-Up |
| UNP | Position Cap Top-Up: Momentum_Score (-18.52) below min_momentum_score_to_fill_underweight (0.00) | Position Cap Top-Up |
| PLTR | loss-lot sell guard: every sellable lot is at or above the current price ($174.04) — nothing can be sold at a gain | partial profit-take sale |
| MU | loss-lot sell guard: every sellable lot is at or above the current price ($1000.68) — nothing can be sold at a gain | partial profit-take sale |
| AMZN | loss-lot sell guard: every sellable lot is at or above the current price ($258.18) — nothing can be sold at a gain | partial profit-take sale |
| NVDA | even selling all 0.2081 fractional share(s) held ($47.89) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| ORCL | even selling all 0.0890 fractional share(s) held ($13.98) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| MSFT | loss-lot sell guard: every sellable lot is at or above the current price ($500.26) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | even selling all 0.0676 fractional share(s) held ($4.87) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| COIN | loss-lot sell guard: every sellable lot is at or above the current price ($184.84) — nothing can be sold at a gain | partial profit-take sale |
| ARM | loss-lot sell guard: every sellable lot is at or above the current price ($249.51) — nothing can be sold at a gain | partial profit-take sale |
| SMCI | even selling all 0.5661 fractional share(s) held ($22.27) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| IONQ | loss-lot sell guard: every sellable lot is at or above the current price ($39.42) — nothing can be sold at a gain | partial profit-take sale |
| HOOD | even selling all 0.3822 fractional share(s) held ($46.94) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($471.56) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($83.41) — nothing can be sold at a gain | partial profit-take sale |
| VRT | even selling all 0.1637 fractional share(s) held ($45.39) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($355.84) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($14.56) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($87.39) — nothing can be sold at a gain | partial profit-take sale |
| IBM | even selling all 0.4028 fractional share(s) held ($94.35) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| NFLX | loss-lot sell guard: every sellable lot is at or above the current price ($79.02) — nothing can be sold at a gain | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($396.48) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($335.82) — nothing can be sold at a gain | partial profit-take sale |
| HD | loss-lot sell guard: every sellable lot is at or above the current price ($321.26) — nothing can be sold at a gain | partial profit-take sale |
| WMT | loss-lot sell guard: every sellable lot is at or above the current price ($107.30) — nothing can be sold at a gain | partial profit-take sale |
| XOM | even selling all 0.2323 fractional share(s) held ($37.13) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($88.06) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($137.41) — nothing can be sold at a gain | partial profit-take sale |
| AMT | loss-lot sell guard: every sellable lot is at or above the current price ($176.02) — nothing can be sold at a gain | partial profit-take sale |
| LIN | loss-lot sell guard: every sellable lot is at or above the current price ($477.62) — nothing can be sold at a gain | partial profit-take sale |
| DUK | loss-lot sell guard: every sellable lot is at or above the current price ($120.25) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($332.55) — nothing can be sold at a gain | partial profit-take sale |
| FCX | loss-lot sell guard: every sellable lot is at or above the current price ($72.72) — nothing can be sold at a gain | partial profit-take sale |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-1,531.50 | -72.93% |
| AAPL | 35d | 2026-07-31 | $27.07 | +1.94% |
| TSLA | 31d | 2026-08-04 | $-317.17 | -8.86% |
| GM | 30d | 2026-08-05 | $-8.88 | -0.42% |
| HD | 29d | 2026-08-06 | $-154.85 | -7.75% |
| LIN | 29d | 2026-08-06 | $-39.63 | -2.08% |
| SHW | 29d | 2026-08-06 | $-165.91 | -8.29% |
| GOOG | 28d | 2026-08-07 | $-304.23 | -5.04% |
| NEE | 28d | 2026-08-07 | $-100.69 | -3.94% |
| UNH | 28d | 2026-08-07 | $-109.70 | -4.35% |
| GE | 28d | 2026-08-07 | $-240.43 | -9.78% |
| PG | 28d | 2026-08-07 | $2.04 | +0.08% |
| SO | 28d | 2026-08-07 | $-127.45 | -5.15% |
| DUK | 28d | 2026-08-07 | $-70.88 | -2.87% |
| AVGO | 23d | 2026-08-12 | $-662.46 | -15.48% |
| AMZN | 22d | 2026-08-13 | $-174.67 | -3.89% |
| ARM | 22d | 2026-08-13 | $-15.81 | -8.45% |
| AMD | 22d | 2026-08-13 | $-1.02 | -3.18% |
| PLD | 22d | 2026-08-13 | $-1.57 | -1.75% |
| F | 21d | 2026-08-14 | $-25.84 | -1.15% |
| WMT | 16d | 2026-08-19 | $-1.95 | -6.77% |
| IONQ | 14d | 2026-08-21 | $-162.19 | -7.47% |
| AMT | 7d | 2026-08-28 | $-6.57 | -0.30% |

## Loss-Only Lot Assets (every sellable lot underwater)
20 asset(s), $33,544.72 market value, $-3,528.04 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $1.90 | $568.50 | $-1,531.50 | -72.93% | 1 | $7.00 / $7.00 |
| AVGO | 10.1667 | $421.00 | $355.84 | $3,617.70 | $-662.49 | -15.48% | 2 | $377.86 / $423.11 |
| GE | 6.6016 | $372.24 | $335.82 | $2,216.96 | $-240.45 | -9.78% | 2 | $356.04 / $373.67 |
| ARM | 0.6867 | $272.54 | $249.51 | $171.34 | $-15.81 | -8.45% | 1 | $272.54 / $272.54 |
| SHW | 5.5210 | $362.60 | $332.55 | $1,836.01 | $-165.91 | -8.29% | 1 | $362.60 / $362.60 |
| HD | 5.7373 | $348.26 | $321.26 | $1,843.15 | $-154.88 | -7.75% | 2 | $342.23 / $348.34 |
| IONQ | 50.9222 | $42.61 | $39.42 | $2,007.61 | $-162.19 | -7.47% | 1 | $42.61 / $42.61 |
| WMT | 0.2499 | $115.09 | $107.30 | $26.81 | $-1.95 | -6.77% | 1 | $115.09 / $115.09 |
| SO | 26.6631 | $92.85 | $88.06 | $2,347.95 | $-127.60 | -5.15% | 4 | $91.84 / $93.28 |
| UNH | 6.0861 | $414.50 | $396.48 | $2,413.00 | $-109.68 | -4.35% | 5 | $405.49 / $430.15 |
| NEE | 29.3977 | $86.83 | $83.41 | $2,451.91 | $-100.82 | -3.95% | 5 | $83.94 / $90.00 |
| AMD | 0.0658 | $487.06 | $471.56 | $31.04 | $-1.02 | -3.18% | 1 | $487.06 / $487.06 |
| DUK | 19.9650 | $123.80 | $120.25 | $2,400.80 | $-70.93 | -2.87% | 4 | $122.69 / $124.67 |
| MSFT | 10.4840 | $512.01 | $500.26 | $5,244.71 | $-123.19 | -2.29% | 1 | $512.01 / $512.01 |
| NFLX | 0.0830 | $80.80 | $79.02 | $6.56 | $-0.15 | -2.21% | 1 | $80.80 / $80.80 |
| LIN | 3.9100 | $487.75 | $477.62 | $1,867.48 | $-39.62 | -2.08% | 3 | $482.36 / $490.48 |
| PLD | 0.6429 | $139.86 | $137.41 | $88.33 | $-1.57 | -1.75% | 1 | $139.86 / $139.86 |
| COIN | 0.6810 | $187.22 | $184.84 | $125.87 | $-1.62 | -1.27% | 1 | $187.22 / $187.22 |
| GM | 24.0013 | $87.76 | $87.39 | $2,097.47 | $-8.85 | -0.42% | 2 | $87.66 / $87.82 |
| AMT | 12.3935 | $176.65 | $176.02 | $2,181.51 | $-7.81 | -0.36% | 1 | $176.65 / $176.65 |

## Orders Placed
```
```

# 2026-09-04 — Scheduled Rebalance Check — EXECUTED (3 sell(s), 0 buy(s))

**Status:** EXECUTED. 3 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$77,901.18**
- `cash` (ledger): **$77,901.18**
- `current_cash` (post-cap): **$77,901.18**
- `account_balance`: **$140,670.25**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **LLY** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 1284.3 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.007%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-1.017%, need > 0.150%)
- **JNJ** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 275.33 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.451%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.162%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.469%, need > 0.150%)
- **JPM** (excluded): Profit-sell buy-guard: profit-sold 2026-08-13 @ 363.54 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.352%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.618%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.310%, need > 0.150%)
- **V** (excluded): Profit-sell buy-guard: profit-sold 2026-08-26 @ 383.44 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.525%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.093%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.815%, need > 0.150%)
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-08-17 @ 873.055 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.605%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.962%, need > -0.050%)
- **COST** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 972.77 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=+0.110%, need > 0.150%)
- **CVX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-01 @ 207.89 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.351%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-1.474%, need > 0.150%)
- **EQIX** (excluded): Profit-sell buy-guard: profit-sold 2026-08-14 @ 1086.12 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.071%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=+0.145%, need > 0.150%)
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 76.6899 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.619%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.343%, need > -0.050%)
- **INTC** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.158%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.737%, need > -0.050%)
- **PLTR** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-27 @ 184.7042 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-7.368%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-2.898%, need > 0.150%)
- **MU** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 949.47 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.303%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.212%, need > -0.050%)
- **MSTR** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-03 @ 142.175 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-15.387%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-3.023%, need > 0.150%)
- **COIN** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-03 @ 192.27 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-9.553%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-3.771%, need > 0.150%)
- **ARM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 282.4199 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.016%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.066%, need > -0.050%)
- **SMCI** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-25 @ 37.75 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.743%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.230%, need > -0.050%)
- **IONQ** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.520%, need > -0.050%)
- **SPCX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-03 @ 151.96 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-6.099%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.131%, need > 0.150%)
- **AMZN** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-12 @ 271.44 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.023%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.518%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.277%, need > 0.150%)
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-04 @ 324.92 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.257%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-5.412%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-5.237%, need > 0.150%)
- **NVDA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-27 @ 224.76 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.985%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.730%, need > -0.050%)
- **ORCL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 146.45 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.822%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-5.280%, need > -0.050%)
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 377.07 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.518%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.569%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.371%, need > 0.150%)
- **MSFT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-28 @ 512.754 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.639%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.222%, need > 0.150%)
- **HOOD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 99.5005 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.865%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-14.599%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-2.697%, need > 0.150%)
- **AAPL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-07-17 @ 333.4801 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.052%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.002%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.196%, need > 0.150%)
- **META** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.359%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.940%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.684%, need > 0.150%)
- **NEE** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.203%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.145%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.238%, need > 0.150%)
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-12 @ 296.415 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.265%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-4.396%, need > -0.050%)
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=+0.067%, need > 0.150%)
- **F** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-14 @ 14.4276 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.065%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.858%, need > -0.050%)
- **GM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 89.55 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.704%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.357%, need > 0.150%)
- **IBM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-03 @ 236.04 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.129%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.298%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.225%, need > 0.150%)
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.350%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-1.175%, need > 0.150%)
- **UNH** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.839%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.320%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.132%, need > 0.150%)
- **GE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 382.1775 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.192%, need > -0.050%)
- **LTRN** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.081%, need > 0.150%)
- **BRK.B** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.574%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.570%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.279%, need > 0.150%)
- **WMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 116.365 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.156%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.136%, need > -0.050%)
- **PG** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.973%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=+0.024%, need > 0.150%)
- **XOM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-11 @ 159.73 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.103%, need > 0.150%)
- **COP** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-11 @ 125.6775 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.757%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-1.707%, need > 0.150%)
- **SO** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.248%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.518%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.023%, need > 0.150%)
- **PLD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 141.89 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.274%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.119%, need > 0.150%)
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 174.68 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.729%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.412%, need > 0.150%)
- **LIN** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.144%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-0.587%, need > 0.150%)
- **FCX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 76.0501 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.021%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-0.429%, need > 0.150%)
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.392%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.304%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.066%, need > 0.150%)
- **DUK** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.140%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.693%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.132%, need > 0.150%)

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $1.85) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| HOOD | 71.60 | 108.70 | 104.12 | +11.72 | +4.40 | +37.73 |
| MSTR | 69.22 | 127.61 | 118.73 | +10.16 | +7.47 | +36.85 |
| COP | 70.57 | 133.41 | 130.12 | +0.02 | +2.53 | +23.12 |
| AAPL | 68.22 | 319.95 | 311.48 | +1.37 | +2.72 | +22.31 |
| SPCX | 62.52 | 142.14 | 137.85 | +4.17 | +3.11 | +19.80 |
| NFLX | 67.12 | 81.20 | 79.61 | +0.63 | +1.99 | +19.74 |
| TSLA | 66.12 | 358.07 | 347.42 | -0.12 | +3.06 | +19.06 |
| COIN | 63.26 | 180.68 | 175.83 | +2.78 | +2.76 | +18.80 |
| META | 61.37 | 582.88 | 567.24 | +4.06 | +2.76 | +18.18 |
| NVDA | 60.52 | 221.07 | 217.32 | +5.61 | +1.73 | +17.86 |
| SMCI | 61.24 | 37.15 | 36.92 | +5.03 | +0.62 | +16.89 |
| ORCL | 57.02 | 148.02 | 147.02 | +6.07 | +0.68 | +13.76 |
| MU | 57.85 | 945.51 | 936.36 | +3.99 | +0.98 | +12.82 |
| MSFT | 58.13 | 501.15 | 492.83 | +0.56 | +1.69 | +10.38 |
| XOM | 59.06 | 161.66 | 160.42 | -0.75 | +0.77 | +9.07 |
| PLTR | 58.52 | 178.91 | 176.73 | -0.85 | +1.23 | +8.91 |
| F | 55.18 | 14.07 | 14.02 | +3.23 | +0.38 | +8.80 |
| VRT | 52.28 | 262.37 | 266.17 | +5.16 | -1.43 | +6.02 |
| AMT | 53.78 | 175.59 | 175.20 | +0.82 | +0.22 | +4.82 |
| PG | 50.22 | 145.75 | 144.63 | +0.83 | +0.78 | +1.82 |
| WMT | 49.64 | 106.40 | 106.80 | +2.54 | -0.38 | +1.80 |
| GM | 49.84 | 86.19 | 86.35 | +0.84 | -0.19 | +0.49 |
| UNH | 48.78 | 396.86 | 396.53 | +0.89 | +0.08 | -0.24 |
| IBM | 50.47 | 233.67 | 234.34 | -0.77 | -0.29 | -0.59 |
| TQQQ | 47.69 | 71.18 | 71.81 | +2.14 | -0.89 | -1.06 |
| FCX | 52.51 | 74.33 | 75.36 | -2.80 | -1.37 | -1.65 |
| BRK.B | 46.62 | 504.98 | 504.24 | +0.34 | +0.15 | -2.89 |
| LIN | 45.78 | 486.25 | 486.07 | -1.41 | +0.04 | -5.60 |
| DUK | 44.75 | 121.09 | 122.00 | +0.13 | -0.75 | -5.88 |
| INTC | 42.59 | 90.77 | 92.00 | +2.76 | -1.33 | -5.98 |
| PLD | 45.29 | 139.74 | 141.84 | -1.11 | -1.48 | -7.30 |
| NEE | 41.41 | 83.55 | 84.49 | +0.38 | -1.12 | -9.33 |
| IONQ | 46.12 | 39.78 | 42.37 | -1.44 | -6.10 | -11.42 |
| AMZN | 39.81 | 259.29 | 261.39 | -0.42 | -0.81 | -11.42 |
| ARM | 38.48 | 243.38 | 252.90 | +3.59 | -3.76 | -11.70 |
| AMD | 36.04 | 465.92 | 477.25 | +0.32 | -2.37 | -16.01 |
| UNP | 36.62 | 297.53 | 305.69 | -2.28 | -2.67 | -18.34 |
| SO | 32.19 | 89.03 | 90.41 | -0.31 | -1.53 | -19.65 |
| GOOG | 31.55 | 338.29 | 342.22 | -0.14 | -1.15 | -19.74 |
| SHW | 32.60 | 339.28 | 349.88 | -2.13 | -3.03 | -22.57 |
| GE | 32.29 | 339.78 | 352.62 | -1.71 | -3.64 | -23.06 |
| HD | 29.24 | 326.49 | 336.82 | -2.26 | -3.07 | -26.09 |
| AVGO | 26.91 | 367.44 | 371.68 | -2.73 | -1.14 | -26.96 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$69,870.67**
- `net_realized_gains_ytd_effective` (post-sells): **$69,884.21**
- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **$0.00**
- `tax_reserve` (final, after subtracting paid taxes): **$24,459.47**

## GET THE PROFITS Sells
- none fired this cycle

## Sell Cleanup Pass
- **SPCX**: Sell Cleanup Pass: sweeping 0.8805 remaining share(s) ($130.36, lot cost $145.61 vs. price $148.06) — dust (<$200.00, single green lot)
- **MSTR**: Sell Cleanup Pass: sweeping 0.5237 remaining share(s) ($73.62, lot cost $132.35 vs. price $140.57) — dust (<$200.00, single green lot)
- **COP**: Sell Cleanup Pass: sweeping 0.4089 remaining share(s) ($54.56, lot cost $115.35 vs. price $133.44) — dust (<$200.00, single green lot)

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)
- none this cycle

## Total_High_Beta_Gains_Realized: **$0.00**
## Total_Cleanup_Gains_Realized: **$13.86**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| AMD | Momentum_Score (-16.01) below min_momentum_score_to_fill_underweight (0.00) | Underweight buy |
| UNP | Momentum_Score (-18.34) below min_momentum_score_to_fill_underweight (0.00) | Underweight buy |
| AMD | Position Cap Top-Up: Momentum_Score (-16.01) below min_momentum_score_to_fill_underweight (0.00) | Position Cap Top-Up |
| HD | Position Cap Top-Up: Momentum_Score (-26.09) below min_momentum_score_to_fill_underweight (0.00) | Position Cap Top-Up |
| UNP | Position Cap Top-Up: Momentum_Score (-18.34) below min_momentum_score_to_fill_underweight (0.00) | Position Cap Top-Up |
| PLTR | loss-lot sell guard: every sellable lot is at or above the current price ($177.39) — nothing can be sold at a gain | partial profit-take sale |
| MU | loss-lot sell guard: every sellable lot is at or above the current price ($983.24) — nothing can be sold at a gain | partial profit-take sale |
| AMZN | loss-lot sell guard: every sellable lot is at or above the current price ($258.19) — nothing can be sold at a gain | partial profit-take sale |
| NVDA | even selling all 0.2081 fractional share(s) held ($48.59) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| ORCL | even selling all 0.0890 fractional share(s) held ($13.97) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| MSFT | loss-lot sell guard: every sellable lot is at or above the current price ($503.96) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | even selling all 0.0676 fractional share(s) held ($4.92) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| MSTR | even selling all 0.5237 fractional share(s) held ($73.62) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| COIN | loss-lot sell guard: every sellable lot is at or above the current price ($185.70) — nothing can be sold at a gain | partial profit-take sale |
| ARM | loss-lot sell guard: every sellable lot is at or above the current price ($252.11) — nothing can be sold at a gain | partial profit-take sale |
| SMCI | even selling all 0.5661 fractional share(s) held ($22.09) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| IONQ | loss-lot sell guard: every sellable lot is at or above the current price ($39.21) — nothing can be sold at a gain | partial profit-take sale |
| HOOD | even selling all 0.3822 fractional share(s) held ($46.42) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($467.42) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($83.86) — nothing can be sold at a gain | partial profit-take sale |
| VRT | even selling all 0.1637 fractional share(s) held ($45.17) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($357.40) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($14.53) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($86.91) — nothing can be sold at a gain | partial profit-take sale |
| IBM | loss-lot sell guard: every sellable lot is at or above the current price ($231.87) — nothing can be sold at a gain | partial profit-take sale |
| NFLX | even selling all 0.0830 fractional share(s) held ($6.79) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($400.41) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($333.99) — nothing can be sold at a gain | partial profit-take sale |
| HD | loss-lot sell guard: every sellable lot is at or above the current price ($319.10) — nothing can be sold at a gain | partial profit-take sale |
| WMT | loss-lot sell guard: every sellable lot is at or above the current price ($109.09) — nothing can be sold at a gain | partial profit-take sale |
| XOM | even selling all 0.2323 fractional share(s) held ($37.27) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| COP | even selling all 0.4089 fractional share(s) held ($54.56) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($88.75) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($138.19) — nothing can be sold at a gain | partial profit-take sale |
| LIN | loss-lot sell guard: every sellable lot is at or above the current price ($479.38) — nothing can be sold at a gain | partial profit-take sale |
| DUK | loss-lot sell guard: every sellable lot is at or above the current price ($121.24) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($332.04) — nothing can be sold at a gain | partial profit-take sale |
| FCX | loss-lot sell guard: every sellable lot is at or above the current price ($72.25) — nothing can be sold at a gain | partial profit-take sale |
| NVDA | below sell_or_buy_value_limit | sell |
| ORCL | below sell_or_buy_value_limit | sell |
| TQQQ | below sell_or_buy_value_limit | sell |
| SMCI | below sell_or_buy_value_limit | sell |
| HOOD | below sell_or_buy_value_limit | sell |
| VRT | below sell_or_buy_value_limit | sell |
| NFLX | below sell_or_buy_value_limit | sell |
| XOM | below sell_or_buy_value_limit | sell |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-1,545.00 | -73.57% |
| AAPL | 35d | 2026-07-31 | $38.24 | +2.73% |
| TSLA | 31d | 2026-08-04 | $-284.14 | -7.94% |
| GM | 30d | 2026-08-05 | $-20.40 | -0.97% |
| HD | 29d | 2026-08-06 | $-167.24 | -8.37% |
| LIN | 29d | 2026-08-06 | $-32.75 | -1.72% |
| SHW | 29d | 2026-08-06 | $-168.72 | -8.43% |
| GOOG | 28d | 2026-08-07 | $-271.52 | -4.50% |
| NEE | 28d | 2026-08-07 | $-87.31 | -3.42% |
| UNH | 28d | 2026-08-07 | $-85.75 | -3.40% |
| GE | 28d | 2026-08-07 | $-252.55 | -10.28% |
| PG | 28d | 2026-08-07 | $12.32 | +0.50% |
| SO | 28d | 2026-08-07 | $-109.05 | -4.41% |
| DUK | 28d | 2026-08-07 | $-51.11 | -2.07% |
| XOM | 24d | 2026-08-11 | $1.93 | +5.48% |
| VRT | 23d | 2026-08-12 | $0.28 | +0.63% |
| AVGO | 23d | 2026-08-12 | $-646.60 | -15.11% |
| AMZN | 22d | 2026-08-13 | $-174.54 | -3.88% |
| TQQQ | 22d | 2026-08-13 | $0.09 | +1.76% |
| ARM | 22d | 2026-08-13 | $-14.03 | -7.50% |
| HOOD | 22d | 2026-08-13 | $11.41 | +32.58% |
| AMD | 22d | 2026-08-13 | $-1.29 | -4.03% |
| PLD | 22d | 2026-08-13 | $-1.08 | -1.20% |
| F | 21d | 2026-08-14 | $-30.40 | -1.36% |
| WMT | 16d | 2026-08-19 | $-1.50 | -5.21% |
| ORCL | 14d | 2026-08-21 | $1.16 | +9.04% |
| IONQ | 14d | 2026-08-21 | $-173.19 | -7.98% |
| SMCI | 10d | 2026-08-25 | $1.03 | +4.88% |
| NVDA | 8d | 2026-08-27 | $3.28 | +7.23% |
| AMT | 7d | 2026-08-28 | $5.82 | +0.27% |

## Loss-Only Lot Assets (every sellable lot underwater)
19 asset(s), $31,526.77 market value, $-3,443.38 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $1.85 | $555.00 | $-1,545.00 | -73.57% | 1 | $7.00 / $7.00 |
| AVGO | 10.1667 | $421.00 | $357.40 | $3,633.56 | $-646.63 | -15.11% | 2 | $377.86 / $423.11 |
| GE | 6.6016 | $372.24 | $333.99 | $2,204.85 | $-252.57 | -10.28% | 2 | $356.04 / $373.67 |
| SHW | 5.5210 | $362.60 | $332.04 | $1,833.20 | $-168.72 | -8.43% | 1 | $362.60 / $362.60 |
| HD | 5.7373 | $348.26 | $319.10 | $1,830.76 | $-167.27 | -8.37% | 2 | $342.23 / $348.34 |
| IONQ | 50.9222 | $42.61 | $39.21 | $1,996.61 | $-173.19 | -7.98% | 1 | $42.61 / $42.61 |
| ARM | 0.6867 | $272.54 | $252.11 | $173.12 | $-14.03 | -7.50% | 1 | $272.54 / $272.54 |
| WMT | 0.2499 | $115.09 | $109.09 | $27.26 | $-1.50 | -5.21% | 1 | $115.09 / $115.09 |
| SO | 26.6631 | $92.85 | $88.75 | $2,366.35 | $-109.20 | -4.41% | 4 | $91.84 / $93.28 |
| AMD | 0.0658 | $487.06 | $467.42 | $30.77 | $-1.29 | -4.03% | 1 | $487.06 / $487.06 |
| NEE | 29.3977 | $86.83 | $83.86 | $2,465.29 | $-87.44 | -3.43% | 5 | $83.94 / $90.00 |
| UNH | 6.0861 | $414.50 | $400.41 | $2,436.95 | $-85.73 | -3.40% | 5 | $405.49 / $430.15 |
| DUK | 19.9650 | $123.80 | $121.24 | $2,420.56 | $-51.17 | -2.07% | 4 | $122.69 / $124.67 |
| LIN | 3.9100 | $487.75 | $479.38 | $1,874.36 | $-32.74 | -1.72% | 3 | $482.36 / $490.48 |
| MSFT | 10.4840 | $512.01 | $503.96 | $5,283.50 | $-84.40 | -1.57% | 1 | $512.01 / $512.01 |
| PLD | 0.6429 | $139.86 | $138.19 | $88.83 | $-1.08 | -1.20% | 1 | $139.86 / $139.86 |
| GM | 24.0013 | $87.76 | $86.91 | $2,085.95 | $-20.37 | -0.97% | 2 | $87.66 / $87.82 |
| COIN | 0.6810 | $187.22 | $185.70 | $126.45 | $-1.04 | -0.81% | 1 | $187.22 / $187.22 |
| IBM | 0.4028 | $231.92 | $231.87 | $93.40 | $-0.02 | -0.02% | 1 | $231.92 / $231.92 |

## Orders Placed
```
```

# 2026-09-03 — Scheduled Rebalance Check — EXECUTED (3 sell(s), 0 buy(s))

**Status:** EXECUTED. 3 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$71,676.49**
- `cash` (ledger): **$71,676.49**
- `current_cash` (post-cap): **$71,676.49**
- `account_balance`: **$141,149.90**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **LLY** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 1284.3 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.282%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-0.137%, need > 0.150%)
- **JNJ** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 275.33 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.916%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.442%, need > -0.050%)
- **JPM** (excluded): Profit-sell buy-guard: profit-sold 2026-08-13 @ 363.54 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.351%, need > -0.050%)
- **V** (excluded): Profit-sell buy-guard: profit-sold 2026-08-26 @ 383.44 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.510%, need > -0.050%)
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-08-17 @ 873.055 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.655%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=+0.052%, need > 0.150%)
- **COST** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 972.77 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.086%, need > 0.150%)
- **CVX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-01 @ 207.89 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.319%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.345%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.009%, need > 0.150%)
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 76.6899 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.624%, need > -0.050%)
- **INTC** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.186%, need > -0.050%)
- **MU** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 949.47 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.385%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.725%, need > 0.150%)
- **SMCI** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-25 @ 37.75 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.764%, need > -0.050%)
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-04 @ 324.92 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.242%, need > -0.050%)
- **NVDA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-27 @ 224.76 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.037%, need > -0.050%)
- **ORCL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 146.45 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.853%, need > -0.050%)
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 377.07 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.515%, need > -0.050%)
- **HOOD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 99.5005 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.831%, need > -0.050%)
- **AAPL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-07-17 @ 333.4801 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.528%, need > 0.200%)
- **META** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.012%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.335%, need > -0.050%)
- **AMD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 494.02 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.116%, need > 0.150%)
- **NEE** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.702%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.202%, need > -0.050%)
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-12 @ 296.415 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.272%, need > -0.050%)
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.185%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-2.811%, need > 0.150%)
- **F** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-14 @ 14.4276 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.081%, need > -0.050%)
- **IBM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-03 @ 236.04 (partial, remainder still held) — blocked because: cooldown not met (0d/1d required); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.129%, need > -0.050%)
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.324%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.127%, need > 0.150%)
- **UNH** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.722%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.840%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=+0.090%, need > 0.150%)
- **LTRN** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.660%, need > 0.150%)
- **BRK.B** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.573%, need > -0.050%)
- **HD** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=+0.020%, need > 0.150%)
- **WMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 116.365 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.966%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.156%, need > -0.050%)
- **PG** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.739%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.970%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.129%, need > 0.150%)
- **XOM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-11 @ 159.73 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.207%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-0.650%, need > 0.150%)
- **COP** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-11 @ 125.6775 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.722%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.743%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.938%, need > 0.150%)
- **SO** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.101%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.247%, need > -0.050%)
- **PLD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 141.89 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.174%, need > 0.200%)
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 174.68 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.179%, need > 0.200%)
- **LIN** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.143%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.999%, need > 0.150%)
- **FCX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 76.0501 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.018%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-2.170%, need > 0.150%)
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.391%, need > -0.050%)
- **DUK** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.395%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.140%, need > -0.050%)

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $1.88) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| MSTR | 59.75 | 123.27 | 113.97 | +15.33 | +8.16 | +33.25 |
| HOOD | 60.59 | 104.69 | 102.67 | +17.41 | +1.96 | +29.96 |
| COP | 72.57 | 132.85 | 130.32 | +2.31 | +1.94 | +26.82 |
| AAPL | 68.76 | 317.85 | 310.59 | +3.04 | +2.34 | +24.14 |
| SPCX | 60.82 | 140.22 | 137.01 | +8.37 | +2.34 | +21.53 |
| NFLX | 67.60 | 80.84 | 79.58 | +2.21 | +1.58 | +21.39 |
| TSLA | 59.98 | 353.53 | 345.69 | +7.70 | +2.27 | +19.95 |
| COIN | 56.35 | 177.65 | 172.03 | +8.23 | +3.27 | +17.85 |
| PLTR | 61.53 | 177.82 | 173.87 | +3.09 | +2.27 | +16.89 |
| NVDA | 59.84 | 219.18 | 214.54 | +4.71 | +2.17 | +16.72 |
| SMCI | 62.65 | 36.98 | 36.57 | +2.66 | +1.10 | +16.41 |
| META | 55.14 | 575.92 | 566.25 | +6.42 | +1.71 | +13.27 |
| MU | 61.89 | 942.43 | 936.87 | +0.72 | +0.59 | +13.21 |
| XOM | 61.67 | 161.53 | 161.45 | +0.97 | +0.05 | +12.69 |
| PG | 58.37 | 145.45 | 144.97 | +1.38 | +0.33 | +10.08 |
| ORCL | 51.55 | 146.50 | 145.73 | +6.00 | +0.52 | +8.08 |
| MSFT | 52.49 | 498.85 | 489.60 | +2.61 | +1.89 | +7.00 |
| FCX | 58.66 | 74.73 | 74.48 | -3.18 | +0.34 | +5.82 |
| LIN | 53.80 | 487.21 | 486.09 | -0.94 | +0.23 | +3.09 |
| IBM | 52.24 | 233.35 | 233.05 | -0.03 | +0.13 | +2.34 |
| TQQQ | 50.71 | 70.95 | 71.39 | +1.58 | -0.63 | +1.66 |
| F | 48.60 | 14.00 | 14.05 | +3.00 | -0.40 | +1.20 |
| INTC | 49.77 | 90.51 | 91.86 | +0.61 | -1.47 | -1.09 |
| AMT | 47.20 | 175.07 | 175.55 | +1.83 | -0.27 | -1.24 |
| VRT | 46.90 | 260.77 | 265.41 | +2.86 | -1.75 | -1.99 |
| BRK.B | 46.43 | 504.09 | 504.09 | +0.66 | -0.00 | -2.91 |
| UNH | 45.04 | 395.87 | 396.98 | +1.05 | -0.28 | -4.20 |
| WMT | 44.99 | 105.89 | 107.83 | +2.60 | -1.80 | -4.21 |
| ARM | 47.22 | 243.40 | 251.80 | -0.63 | -3.33 | -6.74 |
| GM | 41.17 | 85.92 | 86.38 | +1.39 | -0.53 | -7.97 |
| DUK | 41.10 | 121.01 | 122.31 | +0.33 | -1.06 | -9.64 |
| EQIX | 43.13 | 1048.64 | 1072.00 | -1.15 | -2.18 | -10.20 |
| AMD | 43.58 | 468.50 | 477.82 | -2.55 | -1.95 | -10.92 |
| AVGO | 42.52 | 369.74 | 370.91 | -3.39 | -0.31 | -11.19 |
| IONQ | 45.92 | 39.97 | 42.34 | -2.40 | -5.59 | -12.07 |
| NEE | 36.80 | 83.43 | 84.77 | +0.74 | -1.59 | -14.06 |
| UNP | 40.61 | 299.60 | 305.13 | -3.01 | -1.81 | -14.22 |
| AMZN | 32.57 | 259.39 | 262.70 | -0.28 | -1.26 | -18.97 |
| SHW | 35.54 | 340.96 | 350.83 | -2.48 | -2.81 | -19.76 |
| HD | 34.73 | 328.50 | 338.57 | -3.02 | -2.97 | -21.26 |
| PLD | 30.85 | 140.11 | 141.92 | -1.56 | -1.28 | -21.99 |
| SO | 29.52 | 89.09 | 90.76 | -0.12 | -1.84 | -22.44 |
| GE | 32.63 | 341.34 | 355.04 | -2.65 | -3.86 | -23.88 |
| GOOG | 26.65 | 338.14 | 343.47 | +0.42 | -1.55 | -24.49 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$69,570.12**
- `net_realized_gains_ytd_effective` (post-sells): **$69,870.67**
- `tax_reserve` (final): **$24,454.73**

## GET THE PROFITS Sells
- **SPCX**: GET THE PROFITS: +4.36%, FIFO $76.20 (dynamic thresholds 2.93% / $58.90 at 17.0d weighted profitable-lot age)
- **MSTR**: GET THE PROFITS: +7.42%, FIFO $157.20 (dynamic thresholds 1.00% / $30.00 at 0.0d weighted profitable-lot age) (ordinary order — no priced/selectable lots yet, e.g. a same-day buy still syncing broker-side; Robinhood default lot matching, dollar figure is an avg_cost_basis estimate, not a FIFO walk)
- **COIN**: GET THE PROFITS: +2.70%, FIFO $55.55 (dynamic thresholds 1.00% / $30.00 at 0.0d weighted profitable-lot age) (ordinary order — no priced/selectable lots yet, e.g. a same-day buy still syncing broker-side; Robinhood default lot matching, dollar figure is an avg_cost_basis estimate, not a FIFO walk)

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Total_High_Beta_Gains_Realized: **$288.95**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| ARM | Momentum_Score (-6.74) below min_momentum_score_to_fill_underweight (0.00) | Underweight buy |
| UNP | Momentum_Score (-14.22) below min_momentum_score_to_fill_underweight (0.00) | Underweight buy |
| EQIX | Momentum_Score (-10.20) below min_momentum_score_to_fill_underweight (0.00) | Underweight buy |
| PLTR | cost basis pending transfer on required lots (fail-closed) | partial profit-take sale |
| MU | loss-lot sell guard: every sellable lot is at or above the current price ($949.20) — nothing can be sold at a gain | partial profit-take sale |
| AMZN | loss-lot sell guard: every sellable lot is at or above the current price ($258.66) — nothing can be sold at a gain | partial profit-take sale |
| NVDA | even selling all 0.2081 fractional share(s) held ($47.76) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| ORCL | even selling all 0.0890 fractional share(s) held ($13.81) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| TQQQ | even selling all 0.0676 fractional share(s) held ($4.87) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| ARM | loss-lot sell guard: every sellable lot is at or above the current price ($241.87) — nothing can be sold at a gain | partial profit-take sale |
| SMCI | even selling all 0.5661 fractional share(s) held ($21.49) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| IONQ | loss-lot sell guard: every sellable lot is at or above the current price ($39.01) — nothing can be sold at a gain | partial profit-take sale |
| HOOD | even selling all 0.3822 fractional share(s) held ($46.98) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($456.53) — nothing can be sold at a gain | partial profit-take sale |
| VRT | loss-lot sell guard: every sellable lot is at or above the current price ($268.23) — nothing can be sold at a gain | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($357.20) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($14.41) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($87.11) — nothing can be sold at a gain | partial profit-take sale |
| IBM | even selling all 0.4028 fractional share(s) held ($93.97) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| NFLX | even selling all 0.0830 fractional share(s) held ($6.86) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($400.02) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($332.29) — nothing can be sold at a gain | partial profit-take sale |
| HD | loss-lot sell guard: every sellable lot is at or above the current price ($318.57) — nothing can be sold at a gain | partial profit-take sale |
| WMT | loss-lot sell guard: every sellable lot is at or above the current price ($108.64) — nothing can be sold at a gain | partial profit-take sale |
| XOM | even selling all 0.2323 fractional share(s) held ($37.88) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| COP | even selling all 0.4089 fractional share(s) held ($55.57) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($88.98) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($137.93) — nothing can be sold at a gain | partial profit-take sale |
| LIN | loss-lot sell guard: every sellable lot is at or above the current price ($482.63) — nothing can be sold at a gain | partial profit-take sale |
| DUK | loss-lot sell guard: every sellable lot is at or above the current price ($121.41) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($332.49) — nothing can be sold at a gain | partial profit-take sale |
| FCX | loss-lot sell guard: every sellable lot is at or above the current price ($72.36) — nothing can be sold at a gain | partial profit-take sale |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-1,536.00 | -73.14% |
| AAPL | 34d | 2026-07-31 | $52.39 | +3.75% |
| TSLA | 30d | 2026-08-04 | $-71.05 | -1.98% |
| GM | 29d | 2026-08-05 | $-15.48 | -0.73% |
| HD | 28d | 2026-08-06 | $-170.25 | -8.52% |
| LIN | 28d | 2026-08-06 | $-20.02 | -1.05% |
| SHW | 28d | 2026-08-06 | $-166.24 | -8.30% |
| GOOG | 27d | 2026-08-07 | $-242.15 | -4.01% |
| NEE | 27d | 2026-08-07 | $-82.02 | -3.21% |
| UNH | 27d | 2026-08-07 | $-88.13 | -3.49% |
| GE | 27d | 2026-08-07 | $-263.74 | -10.73% |
| PG | 27d | 2026-08-07 | $20.72 | +0.83% |
| SO | 27d | 2026-08-07 | $-102.79 | -4.15% |
| DUK | 27d | 2026-08-07 | $-47.72 | -1.93% |
| XOM | 23d | 2026-08-11 | $2.55 | +7.22% |
| COP | 23d | 2026-08-11 | $8.41 | +17.84% |
| VRT | 22d | 2026-08-12 | $-0.98 | -2.18% |
| AVGO | 22d | 2026-08-12 | $-648.63 | -15.15% |
| AMZN | 21d | 2026-08-13 | $-166.60 | -3.71% |
| TQQQ | 21d | 2026-08-13 | $0.04 | +0.87% |
| ARM | 21d | 2026-08-13 | $-21.06 | -11.25% |
| HOOD | 21d | 2026-08-13 | $11.97 | +34.18% |
| AMD | 21d | 2026-08-13 | $-2.01 | -6.27% |
| PLD | 21d | 2026-08-13 | $-1.24 | -1.38% |
| F | 20d | 2026-08-14 | $-47.87 | -2.14% |
| WMT | 15d | 2026-08-19 | $-1.61 | -5.60% |
| ORCL | 13d | 2026-08-21 | $1.00 | +7.84% |
| IONQ | 13d | 2026-08-21 | $-183.32 | -8.45% |
| SMCI | 9d | 2026-08-25 | $0.43 | +2.04% |
| NVDA | 7d | 2026-08-27 | $2.45 | +5.41% |
| AMT | 6d | 2026-08-28 | $21.38 | +0.98% |

## Loss-Only Lot Assets (every sellable lot underwater)
15 asset(s), $21,716.98 market value, $-3,249.43 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $1.88 | $564.00 | $-1,536.00 | -73.14% | 1 | $7.00 / $7.00 |
| AVGO | 10.1667 | $421.00 | $357.20 | $3,631.53 | $-648.66 | -15.15% | 2 | $377.86 / $423.11 |
| ARM | 0.6867 | $272.54 | $241.87 | $166.09 | $-21.06 | -11.25% | 1 | $272.54 / $272.54 |
| GE | 6.6016 | $372.24 | $332.29 | $2,193.66 | $-263.76 | -10.73% | 2 | $356.04 / $373.67 |
| HD | 5.7373 | $348.26 | $318.57 | $1,827.75 | $-170.28 | -8.52% | 2 | $342.23 / $348.34 |
| IONQ | 50.9222 | $42.61 | $39.01 | $1,986.48 | $-183.32 | -8.45% | 1 | $42.61 / $42.61 |
| SHW | 5.5210 | $362.60 | $332.49 | $1,835.68 | $-166.24 | -8.30% | 1 | $362.60 / $362.60 |
| AMD | 0.0658 | $487.06 | $456.53 | $30.05 | $-2.01 | -6.27% | 1 | $487.06 / $487.06 |
| WMT | 0.2499 | $115.09 | $108.64 | $27.15 | $-1.61 | -5.60% | 1 | $115.09 / $115.09 |
| SO | 26.6631 | $92.85 | $88.98 | $2,372.61 | $-102.94 | -4.16% | 4 | $91.84 / $93.28 |
| UNH | 6.0861 | $414.50 | $400.02 | $2,434.58 | $-88.11 | -3.49% | 5 | $405.49 / $430.15 |
| VRT | 0.1637 | $274.20 | $268.23 | $43.91 | $-0.98 | -2.18% | 1 | $274.20 / $274.20 |
| DUK | 19.9650 | $123.80 | $121.41 | $2,423.96 | $-47.77 | -1.93% | 4 | $122.69 / $124.67 |
| PLD | 0.6429 | $139.86 | $137.93 | $88.67 | $-1.24 | -1.38% | 1 | $139.86 / $139.86 |
| GM | 24.0013 | $87.76 | $87.11 | $2,090.87 | $-15.45 | -0.73% | 2 | $87.66 / $87.82 |

## Orders Placed
```
```

# 2026-09-03 — Scheduled Rebalance Check — EXECUTED (1 sell(s), 4 buy(s))

**Status:** EXECUTED. 1 sell order(s), 4 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$84,673.48**
- `cash` (ledger): **$84,673.48**
- `current_cash` (post-cap): **$84,673.48**
- `account_balance`: **$140,558.62**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **LLY** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 1284.3 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.287%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-1.747%, need > 0.150%)
- **JNJ** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 275.33 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.946%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.465%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.288%, need > 0.150%)
- **JPM** (excluded): Profit-sell buy-guard: profit-sold 2026-08-13 @ 363.54 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.353%, need > -0.050%)
- **V** (excluded): Profit-sell buy-guard: profit-sold 2026-08-26 @ 383.44 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.513%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=+0.087%, need > 0.150%)
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-08-17 @ 873.055 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.662%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.336%, need > 0.150%)
- **UNP** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 306.56 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.385%, need > 0.150%)
- **COST** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 972.77 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.810%, need > 0.150%)
- **CVX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-01 @ 207.89 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.310%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.344%, need > -0.050%)
- **EQIX** (excluded): Profit-sell buy-guard: profit-sold 2026-08-14 @ 1086.12 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.295%, need > 0.150%)
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 76.6899 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.636%, need > -0.050%)
- **INTC** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.206%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.525%, need > 0.150%)
- **MU** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 949.47 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.410%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.784%, need > 0.150%)
- **ARM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 282.4199 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.790%, need > 0.150%)
- **SMCI** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-25 @ 37.75 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.799%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.928%, need > 0.150%)
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-04 @ 324.92 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.245%, need > -0.050%)
- **NVDA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-27 @ 224.76 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.061%, need > -0.050%)
- **ORCL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 146.45 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.965%, need > -0.050%)
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 377.07 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.515%, need > -0.050%)
- **HOOD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 99.5005 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.887%, need > -0.050%)
- **AAPL** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-07-17 @ 333.4801 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.536%, need > 0.200%)
- **META** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.002%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.312%, need > -0.050%)
- **AMD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 494.02 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.017%, need > 0.150%)
- **NEE** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.704%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.203%, need > -0.050%)
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-12 @ 296.415 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.283%, need > -0.050%)
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.191%, need > 0.200%); upturn not confirmed (leg3 close_yesterday→today change=-6.110%, need > 0.150%)
- **F** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-14 @ 14.4276 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.112%, need > -0.050%)
- **IBM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 236.91 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.127%, need > -0.050%)
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.307%, need > -0.050%)
- **UNH** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.728%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.843%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.223%, need > 0.150%)
- **LTRN** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.047%, need > 0.150%)
- **BRK.B** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.573%, need > -0.050%)
- **HD** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.225%, need > 0.150%)
- **WMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 116.365 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.983%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.159%, need > -0.050%)
- **PG** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.741%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.972%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.353%, need > 0.150%)
- **XOM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-11 @ 159.73 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.187%, need > 0.200%)
- **COP** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-11 @ 125.6775 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.706%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.739%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.355%, need > 0.150%)
- **SO** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.102%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.248%, need > -0.050%)
- **PLD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-13 @ 141.89 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.175%, need > 0.200%)
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-19 @ 174.68 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.182%, need > 0.200%)
- **LIN** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.142%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-0.292%, need > 0.150%)
- **FCX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-21 @ 76.0501 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.009%, need > -0.050%); upturn not confirmed (leg3 close_yesterday→today change=-1.713%, need > 0.150%)
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.391%, need > -0.050%)
- **DUK** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.396%, need > 0.200%); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.140%, need > -0.050%)

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $1.91) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| HOOD | 60.59 | 104.69 | 102.67 | +15.14 | +1.96 | +27.69 |
| COP | 72.57 | 132.85 | 130.32 | +2.91 | +1.94 | +27.42 |
| MSTR | 59.75 | 123.27 | 113.97 | +7.09 | +8.16 | +25.00 |
| AAPL | 68.76 | 317.85 | 310.59 | +2.71 | +2.34 | +23.80 |
| NFLX | 67.60 | 80.84 | 79.58 | +2.96 | +1.58 | +22.14 |
| TSLA | 59.98 | 353.53 | 345.69 | +6.31 | +2.27 | +18.56 |
| SPCX | 60.82 | 140.22 | 137.01 | +5.32 | +2.34 | +18.48 |
| NVDA | 59.84 | 219.18 | 214.54 | +3.89 | +2.17 | +15.90 |
| COIN | 56.35 | 177.65 | 172.03 | +5.90 | +3.27 | +15.52 |
| PLTR | 61.53 | 177.82 | 173.87 | +1.21 | +2.27 | +15.01 |
| META | 55.14 | 575.92 | 566.25 | +7.46 | +1.71 | +14.31 |
| XOM | 61.67 | 161.53 | 161.45 | +1.92 | +0.05 | +13.64 |
| MU | 61.89 | 942.43 | 936.87 | -0.33 | +0.59 | +12.16 |
| SMCI | 62.65 | 36.98 | 36.57 | -1.83 | +1.10 | +11.92 |
| PG | 58.37 | 145.45 | 144.97 | +1.15 | +0.33 | +9.85 |
| MSFT | 52.49 | 498.85 | 489.60 | +2.66 | +1.89 | +7.05 |
| FCX | 58.66 | 74.73 | 74.48 | -2.74 | +0.34 | +6.26 |
| ORCL | 51.55 | 146.50 | 145.73 | +1.98 | +0.52 | +4.06 |
| LIN | 53.80 | 487.21 | 486.09 | -0.24 | +0.23 | +3.79 |
| IBM | 52.24 | 233.35 | 233.05 | +1.15 | +0.13 | +3.52 |
| TQQQ | 50.71 | 70.95 | 71.39 | -0.30 | -0.63 | -0.22 |
| F | 48.60 | 14.00 | 14.05 | +1.50 | -0.40 | -0.30 |
| AMT | 47.20 | 175.07 | 175.55 | +0.56 | -0.27 | -2.51 |
| INTC | 49.77 | 90.51 | 91.86 | -1.03 | -1.47 | -2.73 |
| BRK.B | 46.43 | 504.09 | 504.09 | +0.69 | -0.00 | -2.88 |
| UNH | 45.04 | 395.87 | 396.98 | +0.73 | -0.28 | -4.51 |
| WMT | 44.99 | 105.89 | 107.83 | +0.88 | -1.80 | -5.93 |
| VRT | 46.90 | 260.77 | 265.41 | -1.11 | -1.75 | -5.96 |
| GM | 41.17 | 85.92 | 86.38 | -0.04 | -0.53 | -9.40 |
| DUK | 41.10 | 121.01 | 122.31 | +0.06 | -1.06 | -9.90 |
| ARM | 47.22 | 243.40 | 251.80 | -5.21 | -3.33 | -11.32 |
| IONQ | 45.92 | 39.97 | 42.34 | -2.15 | -5.59 | -11.82 |
| AMD | 43.58 | 468.50 | 477.82 | -4.37 | -1.95 | -12.74 |
| AVGO | 42.52 | 369.74 | 370.91 | -6.40 | -0.31 | -14.19 |
| NEE | 36.80 | 83.43 | 84.77 | +0.47 | -1.59 | -14.32 |
| AMZN | 32.57 | 259.39 | 262.70 | -0.13 | -1.26 | -18.83 |
| SHW | 35.54 | 340.96 | 350.83 | -2.53 | -2.81 | -19.80 |
| HD | 34.73 | 328.50 | 338.57 | -3.26 | -2.97 | -21.50 |
| PLD | 30.85 | 140.11 | 141.92 | -2.32 | -1.28 | -22.75 |
| SO | 29.52 | 89.09 | 90.76 | -0.50 | -1.84 | -22.82 |
| GE | 32.63 | 341.34 | 355.04 | -2.43 | -3.86 | -23.66 |
| GOOG | 26.65 | 338.14 | 343.47 | +0.59 | -1.55 | -24.32 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$69,546.82**
- `net_realized_gains_ytd_effective` (post-sells): **$69,570.12**
- `tax_reserve` (final): **$24,349.54**

## GET THE PROFITS Sells
- **IBM**: GET THE PROFITS: +1.78%, FIFO $37.16 (dynamic thresholds 1.01% / $30.12 at 1.1d weighted profitable-lot age)

## Buys (Underweight fills, momentum-ranked top-down)
- **MSFT**: $5,367.87
- **PLTR**: $5,365.75
- **MSTR**: $2,186.91
- **COIN**: $2,186.91

## Total_High_Beta_Gains_Realized: **$37.16**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| PLTR | even selling all 0.0118 fractional share(s) held ($2.11) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| MU | loss-lot sell guard: every sellable lot is at or above the current price ($939.32) — nothing can be sold at a gain | partial profit-take sale |
| AMZN | loss-lot sell guard: every sellable lot is at or above the current price ($259.05) — nothing can be sold at a gain | partial profit-take sale |
| NVDA | even selling all 0.2081 fractional share(s) held ($47.39) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| ORCL | even selling all 0.0890 fractional share(s) held ($13.29) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| TQQQ | loss-lot sell guard: every sellable lot is at or above the current price ($70.73) — nothing can be sold at a gain | partial profit-take sale |
| ARM | loss-lot sell guard: every sellable lot is at or above the current price ($230.73) — nothing can be sold at a gain | partial profit-take sale |
| SMCI | loss-lot sell guard: every sellable lot is at or above the current price ($36.30) — nothing can be sold at a gain | partial profit-take sale |
| IONQ | loss-lot sell guard: every sellable lot is at or above the current price ($39.11) — nothing can be sold at a gain | partial profit-take sale |
| HOOD | even selling all 0.3822 fractional share(s) held ($46.07) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($448.02) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($83.82) — nothing can be sold at a gain | partial profit-take sale |
| VRT | loss-lot sell guard: every sellable lot is at or above the current price ($257.87) — nothing can be sold at a gain | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($346.10) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($14.21) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($85.89) — nothing can be sold at a gain | partial profit-take sale |
| NFLX | even selling all 0.0830 fractional share(s) held ($6.91) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($398.77) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($333.06) — nothing can be sold at a gain | partial profit-take sale |
| HD | loss-lot sell guard: every sellable lot is at or above the current price ($317.80) — nothing can be sold at a gain | partial profit-take sale |
| WMT | loss-lot sell guard: every sellable lot is at or above the current price ($106.82) — nothing can be sold at a gain | partial profit-take sale |
| XOM | even selling all 0.2323 fractional share(s) held ($38.24) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| COP | even selling all 0.4089 fractional share(s) held ($55.90) falls short of min_value_of_trade ($100.00) | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($88.65) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($136.85) — nothing can be sold at a gain | partial profit-take sale |
| AMT | loss-lot sell guard: every sellable lot is at or above the current price ($176.05) — nothing can be sold at a gain | partial profit-take sale |
| DUK | loss-lot sell guard: every sellable lot is at or above the current price ($121.09) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($332.35) — nothing can be sold at a gain | partial profit-take sale |
| FCX | loss-lot sell guard: every sellable lot is at or above the current price ($72.69) — nothing can be sold at a gain | partial profit-take sale |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-1,527.00 | -72.71% |
| AAPL | 34d | 2026-07-31 | $47.65 | +3.41% |
| TSLA | 30d | 2026-08-04 | $-116.52 | -3.26% |
| GM | 29d | 2026-08-05 | $-44.88 | -2.13% |
| HD | 28d | 2026-08-06 | $-174.73 | -8.75% |
| LIN | 28d | 2026-08-06 | $-6.73 | -0.35% |
| SHW | 28d | 2026-08-06 | $-167.01 | -8.34% |
| GOOG | 27d | 2026-08-07 | $-232.43 | -3.85% |
| NEE | 27d | 2026-08-07 | $-88.49 | -3.47% |
| UNH | 27d | 2026-08-07 | $-95.73 | -3.79% |
| GE | 27d | 2026-08-07 | $-258.65 | -10.53% |
| PG | 27d | 2026-08-07 | $15.13 | +0.61% |
| SO | 27d | 2026-08-07 | $-111.72 | -4.51% |
| DUK | 27d | 2026-08-07 | $-54.11 | -2.19% |
| XOM | 23d | 2026-08-11 | $2.91 | +8.23% |
| COP | 23d | 2026-08-11 | $8.74 | +18.52% |
| VRT | 22d | 2026-08-12 | $-2.67 | -5.96% |
| AVGO | 22d | 2026-08-12 | $-761.53 | -17.79% |
| AMZN | 21d | 2026-08-13 | $-160.15 | -3.56% |
| TQQQ | 21d | 2026-08-13 | $-0.05 | -0.99% |
| ARM | 21d | 2026-08-13 | $-28.71 | -15.34% |
| HOOD | 21d | 2026-08-13 | $11.06 | +31.59% |
| AMD | 21d | 2026-08-13 | $-2.57 | -8.01% |
| PLD | 21d | 2026-08-13 | $-1.93 | -2.15% |
| F | 20d | 2026-08-14 | $-79.79 | -3.56% |
| SPCX | 17d | 2026-08-17 | $26.68 | +1.42% |
| WMT | 15d | 2026-08-19 | $-2.07 | -7.19% |
| ORCL | 13d | 2026-08-21 | $0.48 | +3.76% |
| IONQ | 13d | 2026-08-21 | $-178.23 | -8.21% |
| SMCI | 9d | 2026-08-25 | $-0.51 | -2.42% |
| NVDA | 7d | 2026-08-27 | $2.08 | +4.58% |
| AMT | 6d | 2026-08-28 | $-6.20 | -0.28% |

## Loss-Only Lot Assets (every sellable lot underwater)
21 asset(s), $29,982.20 market value, $-3,665.38 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $1.91 | $573.00 | $-1,527.00 | -72.71% | 1 | $7.00 / $7.00 |
| AVGO | 10.1667 | $421.00 | $346.10 | $3,518.63 | $-761.56 | -17.79% | 2 | $377.86 / $423.11 |
| ARM | 0.6867 | $272.54 | $230.73 | $158.44 | $-28.71 | -15.34% | 1 | $272.54 / $272.54 |
| GE | 6.6016 | $372.24 | $333.06 | $2,198.74 | $-258.67 | -10.53% | 2 | $356.04 / $373.67 |
| HD | 5.7373 | $348.26 | $317.80 | $1,823.27 | $-174.76 | -8.75% | 2 | $342.23 / $348.34 |
| SHW | 5.5210 | $362.60 | $332.35 | $1,834.91 | $-167.01 | -8.34% | 1 | $362.60 / $362.60 |
| IONQ | 50.9222 | $42.61 | $39.11 | $1,991.57 | $-178.23 | -8.21% | 1 | $42.61 / $42.61 |
| AMD | 0.0658 | $487.06 | $448.02 | $29.49 | $-2.57 | -8.01% | 1 | $487.06 / $487.06 |
| WMT | 0.2499 | $115.09 | $106.82 | $26.69 | $-2.07 | -7.19% | 1 | $115.09 / $115.09 |
| VRT | 0.1637 | $274.20 | $257.87 | $42.22 | $-2.67 | -5.96% | 1 | $274.20 / $274.20 |
| MU ⚠ | 1.7005 | $985.02 | $939.32 | $1,597.35 | $-77.72 | -4.64% | 2 | $940.64 / $1,039.08 |
| SO | 26.6631 | $92.85 | $88.65 | $2,363.68 | $-111.87 | -4.52% | 4 | $91.84 / $93.28 |
| UNH | 6.0861 | $414.50 | $398.77 | $2,426.97 | $-95.71 | -3.79% | 5 | $405.49 / $430.15 |
| F | 151.9817 | $14.73 | $14.21 | $2,158.90 | $-79.28 | -3.54% | 4 | $14.30 / $14.85 |
| NEE | 29.3977 | $86.83 | $83.82 | $2,464.11 | $-88.62 | -3.47% | 5 | $83.94 / $90.00 |
| SMCI | 0.5661 | $37.20 | $36.30 | $20.55 | $-0.51 | -2.42% | 1 | $37.20 / $37.20 |
| DUK | 19.9650 | $123.80 | $121.09 | $2,417.57 | $-54.16 | -2.19% | 4 | $122.69 / $124.67 |
| PLD | 0.6429 | $139.86 | $136.85 | $87.98 | $-1.93 | -2.15% | 1 | $139.86 / $139.86 |
| GM | 24.0013 | $87.76 | $85.89 | $2,061.47 | $-44.85 | -2.13% | 2 | $87.66 / $87.82 |
| TQQQ | 0.0676 | $71.44 | $70.73 | $4.78 | $-0.05 | -0.99% | 1 | $71.44 / $71.44 |
| AMT | 12.3935 | $176.65 | $176.05 | $2,181.88 | $-7.44 | -0.34% | 1 | $176.65 / $176.65 |

⚠ = the broker's blended `avg_cost_basis` materially disagrees with the cost of the actual lots, so the two views of this position tell different stories:
- **MU**: `avg_cost_basis` $951.72 vs. lot-weighted $985.02 (price $939.32) — the blended average implies -1.30%, the lots imply -4.64%

## Orders Placed
```
```
