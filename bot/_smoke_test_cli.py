"""Integration test for the snapshot-driven `plan`/`finalize` CLI — the mode a scheduled
Claude Code session (or any other MCP-connected orchestrator) actually uses: no broker
credentials anywhere, just a JSON snapshot in, a JSON order plan out.

Run: PYTHONPATH=. python3 bot/_smoke_test_cli.py
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

random.seed(13)
REPO = Path(__file__).resolve().parent.parent


def build_snapshot(cfg_path: Path, out_path: Path) -> dict:
    cfg = json.loads(cfg_path.read_text())
    symbols = list(cfg["targets"].keys())
    today = date.today()

    quotes, daily_closes, daily_lows_highs, positions, tax_lots = {}, {}, {}, {}, {}

    for i, sym in enumerate(symbols + ["SPY"]):
        p = {"TQQQ": 63.0, "MU": 880.0, "SPY": 742.0}.get(sym, 100.0 + i * 7.3)
        closes = []
        d = today - timedelta(days=90)
        while d < today:
            if d.weekday() < 5:
                p *= 1 + random.uniform(-0.03, 0.032)
                closes.append({"date": d.isoformat(), "close": round(p, 4)})
            d += timedelta(days=1)
        daily_closes[sym] = closes
        daily_lows_highs[sym] = [
            {"date": c["date"], "low": round(c["close"] * 0.98, 4), "high": round(c["close"] * 1.02, 4)}
            for c in closes[-10:]
        ]
        if sym != "SPY":
            quotes[sym] = closes[-1]["close"]

    for i, sym in enumerate(symbols):
        if i % 5 == 0:
            continue  # a few intentionally unheld
        qty = round(random.uniform(1, 6), 4)
        avg = quotes[sym] * random.uniform(0.85, 1.15)
        positions[sym] = {"quantity": qty, "avg_cost_basis": round(avg, 4)}
        tax_lots[sym] = [
            {"open_lot_id": f"{sym}-1", "quantity": qty * 0.5, "cost_per_share": round(avg * 0.7, 4),
             "open_date": (today - timedelta(days=40)).isoformat(), "is_selectable": True},
            {"open_lot_id": f"{sym}-2", "quantity": qty * 0.5, "cost_per_share": round(avg * 0.9, 4),
             "open_date": (today - timedelta(days=10)).isoformat(), "is_selectable": True},
        ]

    snapshot = {
        "current_date": today.isoformat(),
        "account_number": "TEST",
        "account_cash": 25000.0,
        "account_cash_ledger": 25000.0,
        "quotes": quotes,
        "positions": positions,
        "daily_closes": daily_closes,
        "daily_lows_highs": daily_lows_highs,
        "tax_lots": tax_lots,
        "net_realized_gains_ytd_pretrade": 8000.0,
    }
    out_path.write_text(json.dumps(snapshot, indent=2))
    return snapshot


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "bot.cli", *args],
        cwd=REPO, capture_output=True, text=True, env={"PYTHONPATH": str(REPO)},
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "logs").mkdir()
        (tmp / "peak").mkdir()
        (tmp / "tax").mkdir()
        shutil.copy(REPO / "portfolio_targets.json", tmp / "portfolio_targets.json")
        (tmp / "peak" / "prices.json").write_text("{}")
        (tmp / "tax" / "realized_gains_by_year.json").write_text('{"2025": 4000.0}')
        (tmp / "transferred_basis.json").write_text("{}")

        snapshot_path = tmp / "snapshot.json"
        build_snapshot(REPO / "portfolio_targets.json", snapshot_path)

        plan_out = tmp / "plan_result.json"
        r = run("plan", "--snapshot", str(snapshot_path), "--repo-dir", str(tmp), "--out", str(plan_out))
        print("--- plan stdout ---\n", r.stdout)
        if r.returncode != 0:
            print("--- plan stderr ---\n", r.stderr)
        assert r.returncode == 0, "plan command failed"
        assert plan_out.exists()

        plan_result = json.loads(plan_out.read_text())
        print(f"[plan] no_trades={plan_result.get('no_trades')} "
              f"halted={plan_result.get('halted_for_approval')} "
              f"sells_to_place={[s['symbol'] for s in plan_result.get('sells_to_place', [])]}")

        if plan_result.get("no_trades"):
            print("SMOKE TEST (CLI): no_trades cycle — plan-only path exercised, nothing to finalize.")
            assert (tmp / "logs" / "trade_journal.md").exists()
            print("PASSED")
            return

        if plan_result.get("halted_for_approval"):
            print("SMOKE TEST (CLI): halted_for_approval path exercised (gross sell value over seek_approval_value).")
            print("PASSED")
            return

        # Caller (a real orchestrator) would now execute plan_result['sells_to_place'] via its
        # broker/MCP connection, then re-fetch these two figures. Here we synthesize plausible
        # post-sell values for the smoke test.
        realized_this_cycle = sum(s.get("dollar_amount") or 0 for s in []) + 500.0  # placeholder delta
        post_sell_pnl = 8000.0 + realized_this_cycle
        buying_power_after_sells = 25000.0 + sum(
            (s["quantity"] or 0) * 50 for s in plan_result["sells_to_place"]
        )  # rough — real orchestrator uses the broker's actual post-fill figure

        finalize_out = tmp / "finalize_result.json"
        r = run(
            "finalize", "--resume", str(plan_out),
            "--post-sell-pnl", str(post_sell_pnl),
            "--buying-power", str(buying_power_after_sells),
            "--repo-dir", str(tmp), "--out", str(finalize_out),
        )
        print("--- finalize stdout ---\n", r.stdout)
        if r.returncode != 0:
            print("--- finalize stderr ---\n", r.stderr)
        assert r.returncode == 0, "finalize command failed"
        assert finalize_out.exists()

        finalize_result = json.loads(finalize_out.read_text())
        print(f"[finalize] buys_to_place={[b['symbol'] for b in finalize_result['buys_to_place']]} "
              f"tax_reserve={finalize_result['tax_reserve']:.2f} "
             )

        assert (tmp / "logs" / "trade_journal.md").exists()
        assert (tmp / "peak" / "prices.json").exists()
        peak_state = json.loads((tmp / "peak" / "prices.json").read_text())
        assert set(peak_state.keys()) == set(json.loads((REPO / "portfolio_targets.json").read_text())["targets"].keys())
        for f in finalize_result["files_changed"]:
            assert (tmp / f).exists() or (tmp / f).is_dir(), f"expected {f} to exist"

        print("\nSMOKE TEST (CLI) PASSED — plan -> (caller executes sells) -> finalize -> "
              "(caller executes buys) ran end-to-end via subprocess, no exceptions, all state files written.")


if __name__ == "__main__":
    main()
