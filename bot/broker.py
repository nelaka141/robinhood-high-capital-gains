"""Broker abstraction. CLAUDE.md's rules are broker-agnostic; `BrokerClient` is the seam
between the pipeline logic (steps.py) and whatever Robinhood client you actually have wired up.

`RobinStocksBroker` is a reference implementation on top of the unofficial `robin_stocks`
package, provided so the package is runnable end-to-end. Two methods
(`get_tax_lots`, `get_realized_pnl_ytd`) raise NotImplementedError — robin_stocks doesn't
expose the same tax-lot / aggregate-realized-P&L endpoints the Robinhood app (and the MCP
server this repo was originally driven by) use internally. Wire those to whatever your broker
actually exposes (a private API endpoint, a CSV export, a local ledger reconciled from order
history, etc.) before running Steps 4/6 live. Everything else (positions, quotes, historicals,
market orders) is implemented.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Protocol

from .models import Position, Quote, TaxLot


class BrokerClient(Protocol):
    def get_positions(self, account_number: str) -> Dict[str, Position]:
        """Every open equity position, keyed by symbol. avg_cost_basis=None if unresolved —
        the pipeline will attempt the Step 1 tax-lot/transferred-basis fallback for those."""
        ...

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]: ...

    def get_daily_closes(self, symbol: str, start: date, end: date) -> List[float]:
        """Ascending-date daily closing prices, `start`..`end` inclusive (regular session)."""
        ...

    def get_daily_lows_highs(self, symbol: str, start: date, end: date) -> List[tuple]:
        """Ascending-date (low, high) tuples, for the Step 5 pump/dump price-limit checks."""
        ...

    def get_fifty_two_week_high(self, symbol: str) -> Optional[float]:
        """52-week high price, for the Step 5 `52_week_high_guard` chasing check. None if
        unavailable — callers fail OPEN (allow the buy) on a missing value, same posture as the
        rest of Step 5's price-limit checks when historical data is missing."""
        ...

    def get_tax_lots(self, account_number: str, symbol: str) -> List[TaxLot]:
        """All open tax lots for `symbol`, any order — fifo.py sorts by open_date itself."""
        ...

    def get_buying_power(self, account_number: str) -> float:
        """Settled, spendable cash — CLAUDE.md's account_cash/current_cash source, NOT the raw
        cash ledger (which can include unsettled proceeds)."""
        ...

    def get_cash_ledger(self, account_number: str) -> float:
        """Raw cash balance, informational only (used to detect unsettled proceeds)."""
        ...

    def get_realized_pnl_ytd(self, account_number: str, year_start: date, as_of: date) -> float:
        """Net realized equity gains, Jan 1 of `year_start`'s year through `as_of` inclusive.
        Called twice per cycle: once pre-trade (Step 1 placeholder), once post-sells
        (Step 6, to finalize tax_reserve) — must reflect same-session fills immediately."""
        ...

    def place_market_order(
        self,
        account_number: str,
        symbol: str,
        side: str,
        dollar_amount: Optional[float] = None,
        quantity: Optional[float] = None,
        tax_lots: Optional[List[dict]] = None,
    ) -> dict:
        """Places a REAL order. `tax_lots`, if given (sells only), is the exact FIFO lot
        selection from fifo.py — pass it through to specified-lot selling if your broker
        supports it; otherwise document that default (broker) matching may not equal the FIFO
        figure the sale was gated on. Returns a dict with at least {'id', 'state', 'symbol'}."""
        ...


class RobinStocksBroker:
    """Reference BrokerClient built on `pip install robin_stocks`. You must call
    `robin_stocks.robinhood.login(...)` yourself (interactively or via a stored session) before
    constructing this class — it does not manage authentication."""

    def __init__(self) -> None:
        import robin_stocks.robinhood as rh  # optional dependency — only imported when used
        self._rh = rh

    def get_positions(self, account_number: str) -> Dict[str, Position]:
        holdings = self._rh.account.build_holdings()
        out: Dict[str, Position] = {}
        for symbol, h in holdings.items():
            avg = h.get("average_buy_price")
            out[symbol] = Position(
                symbol=symbol,
                quantity=float(h["quantity"]),
                avg_cost_basis=float(avg) if avg not in (None, "") else None,
            )
        return out

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        prices = self._rh.stocks.get_latest_price(symbols, includeExtendedHours=True)
        return {sym: Quote(symbol=sym, last_trade_price=float(p)) for sym, p in zip(symbols, prices)}

    def get_daily_closes(self, symbol: str, start: date, end: date) -> List[float]:
        span = "year" if (end - start).days > 90 else "3month"
        bars = self._rh.stocks.get_stock_historicals(symbol, interval="day", span=span, bounds="regular")
        return [
            float(b["close_price"]) for b in bars
            if start.isoformat() <= b["begins_at"][:10] <= end.isoformat()
        ]

    def get_daily_lows_highs(self, symbol: str, start: date, end: date) -> List[tuple]:
        span = "year" if (end - start).days > 90 else "3month"
        bars = self._rh.stocks.get_stock_historicals(symbol, interval="day", span=span, bounds="regular")
        return [
            (float(b["low_price"]), float(b["high_price"])) for b in bars
            if start.isoformat() <= b["begins_at"][:10] <= end.isoformat()
        ]

    def get_fifty_two_week_high(self, symbol: str) -> Optional[float]:
        fundamentals = self._rh.stocks.get_fundamentals(symbol, info="high_52_weeks")
        if not fundamentals or fundamentals[0] in (None, ""):
            return None
        return float(fundamentals[0])

    def get_tax_lots(self, account_number: str, symbol: str) -> List[TaxLot]:
        raise NotImplementedError(
            "robin_stocks has no public tax-lots endpoint. Wire this to your broker's real "
            "source (private API, CSV export, etc.) before running Step 4/6 live — until then, "
            "every FIFO dollar-gate check will fail closed (0 lots -> fully_covered=False)."
        )

    def get_buying_power(self, account_number: str) -> float:
        profile = self._rh.profiles.load_account_profile()
        return float(profile["buying_power"])

    def get_cash_ledger(self, account_number: str) -> float:
        profile = self._rh.profiles.load_account_profile()
        return float(profile["cash"])

    def get_realized_pnl_ytd(self, account_number: str, year_start: date, as_of: date) -> float:
        raise NotImplementedError(
            "robin_stocks doesn't expose the aggregate realized-P&L endpoint the Robinhood app "
            "uses. A local ledger reconciled from get_all_stock_orders() fills is a reasonable "
            "fallback — wire it up before running Step 1/6 live."
        )

    def place_market_order(
        self,
        account_number: str,
        symbol: str,
        side: str,
        dollar_amount: Optional[float] = None,
        quantity: Optional[float] = None,
        tax_lots: Optional[List[dict]] = None,
    ) -> dict:
        if side == "buy":
            if dollar_amount is not None:
                return self._rh.orders.order_buy_fractional_by_price(symbol, dollar_amount)
            if quantity is not None:
                return self._rh.orders.order_buy_market(symbol, quantity)
            raise ValueError("buy orders require dollar_amount or quantity")
        if side == "sell":
            if quantity is None:
                raise ValueError("sell orders require an explicit quantity")
            # NOTE: robin_stocks has no specified-lot-selling parameter — `tax_lots` is accepted
            # for interface parity but silently NOT honored here. Default (broker) matching may
            # then not equal the FIFO figure fifo.py gated the sale on; if your broker supports
            # specified-lot selling, pass tax_lots through to it here instead.
            return self._rh.orders.order_sell_market(symbol, quantity)
        raise ValueError(f"unknown side {side!r}")
