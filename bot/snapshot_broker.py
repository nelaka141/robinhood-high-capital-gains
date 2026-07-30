"""SnapshotBroker: a BrokerClient that reads from a pre-fetched JSON snapshot instead of
making live API calls. This is what makes bot/cli.py's `plan`/`finalize` commands runnable
with NO Robinhood credentials of their own: the calling agent (an MCP-connected Claude session,
or any other orchestrator) fetches the raw data via whatever connection it already has, dumps
it to snapshot.json, and this script only ever reasons about that snapshot — it never talks to
a broker and never places an order itself. See bot/README.md, "Snapshot-driven mode"."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import Position, Quote, TaxLot


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


class SnapshotBroker:
    """Read-only BrokerClient over a snapshot dict. `place_market_order` always raises — this
    broker is only ever used for the `plan`/`finalize` CLI commands, which never place orders
    themselves (see bot/cli.py)."""

    def __init__(self, snapshot: dict):
        self._snap = snapshot

    @classmethod
    def from_file(cls, path: str | Path) -> "SnapshotBroker":
        return cls(json.loads(Path(path).read_text()))

    def get_positions(self, account_number: str) -> Dict[str, Position]:
        out = {}
        for sym, p in self._snap.get("positions", {}).items():
            out[sym] = Position(
                symbol=sym,
                quantity=float(p["quantity"]),
                avg_cost_basis=(float(p["avg_cost_basis"]) if p.get("avg_cost_basis") is not None else None),
            )
        return out

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        quotes = self._snap.get("quotes", {})
        missing = [s for s in symbols if s not in quotes]
        if missing:
            raise ValueError(f"snapshot missing quotes for: {missing}")
        return {s: Quote(symbol=s, last_trade_price=float(quotes[s])) for s in symbols}

    def get_daily_closes(self, symbol: str, start: date, end: date) -> List[float]:
        bars = self._snap.get("daily_closes", {}).get(symbol, [])
        return [
            float(b["close"]) for b in bars
            if start.isoformat() <= b["date"] <= end.isoformat()
        ]

    def get_daily_lows_highs(self, symbol: str, start: date, end: date) -> List[tuple]:
        bars = self._snap.get("daily_lows_highs", {}).get(symbol, [])
        return [
            (float(b["low"]), float(b["high"])) for b in bars
            if start.isoformat() <= b["date"] <= end.isoformat()
        ]

    def get_tax_lots(self, account_number: str, symbol: str) -> List[TaxLot]:
        lots = self._snap.get("tax_lots", {}).get(symbol, [])
        return [
            TaxLot(
                open_lot_id=l["open_lot_id"],
                quantity=float(l["quantity"]),
                cost_per_share=(float(l["cost_per_share"]) if l.get("cost_per_share") is not None else None),
                open_date=_parse_date(l["open_date"]),
                is_selectable=bool(l.get("is_selectable", True)),
            )
            for l in lots
        ]

    def get_buying_power(self, account_number: str) -> float:
        return float(self._snap["account_cash"])

    def get_cash_ledger(self, account_number: str) -> float:
        return float(self._snap.get("account_cash_ledger", self._snap["account_cash"]))

    def get_realized_pnl_ytd(self, account_number: str, year_start: date, as_of: date) -> float:
        return float(self._snap["net_realized_gains_ytd_pretrade"])

    def place_market_order(self, *args, **kwargs) -> dict:
        raise RuntimeError(
            "SnapshotBroker never places orders — bot/cli.py's plan/finalize commands only "
            "return an order plan for the caller (your MCP-connected agent) to execute."
        )
