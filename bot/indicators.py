"""Pure-Python technical indicators: EMA(9), RSI(14), beta, and price Z-score — computed
directly from daily closes, matching the exact formulas CLAUDE.md Step 2/3/4 specify for
Momentum_Score, High_Beta_Gain_Score, and the Z-score buy-back/resell guards. No external
indicator API is required."""
from __future__ import annotations

import statistics
from typing import List, Optional, Sequence


def ema_series(closes: Sequence[float], period: int = 9) -> List[float]:
    """Exponential moving average, seeded with a simple average of the first `period` closes.
    Returns one EMA value per close from index `period-1` onward (so len(out) == len(closes) - period + 1)."""
    if len(closes) < period:
        raise ValueError(f"need at least {period} closes, got {len(closes)}")
    k = 2 / (period + 1)
    seed = sum(closes[:period]) / period
    out = [seed]
    for price in closes[period:]:
        out.append(price * k + out[-1] * (1 - k))
    return out


def rsi_series(closes: Sequence[float], period: int = 14) -> List[float]:
    """Wilder's RSI(period). Returns one RSI value per close from index `period` onward."""
    if len(closes) < period + 1:
        raise ValueError(f"need at least {period + 1} closes, got {len(closes)}")

    gains, losses = [], []
    for prev, cur in zip(closes, closes[1:]):
        change = cur - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi(avg_g: float, avg_l: float) -> float:
        if avg_l == 0:
            return 100.0
        rs = avg_g / avg_l
        return 100 - (100 / (1 + rs))

    out = [_rsi(avg_gain, avg_loss)]
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        out.append(_rsi(avg_gain, avg_loss))
    return out


def daily_returns(closes: Sequence[float]) -> List[float]:
    return [(b - a) / a for a, b in zip(closes, closes[1:])]


def beta(asset_returns: Sequence[float], benchmark_returns: Sequence[float]) -> float:
    """Beta_asset = Covariance(Asset_Daily_Returns, Benchmark_Daily_Returns) / Variance(Benchmark_Daily_Returns)"""
    n = len(asset_returns)
    if n != len(benchmark_returns):
        raise ValueError(
            f"asset_returns ({n}) and benchmark_returns ({len(benchmark_returns)}) must be equal length"
        )
    if n < 2:
        raise ValueError("need at least 2 return observations to compute beta")

    mean_a = sum(asset_returns) / n
    mean_b = sum(benchmark_returns) / n
    cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(asset_returns, benchmark_returns)) / (n - 1)
    var_b = sum((b - mean_b) ** 2 for b in benchmark_returns) / (n - 1)
    if var_b == 0:
        raise ValueError("benchmark variance is zero — cannot compute beta")
    return cov / var_b


def price_zscore(closes: Sequence[float], price: float) -> Optional[float]:
    """Z = (price - mean) / stdev, where mean/stdev are the sample mean/stdev of `closes`
    (CLAUDE.md's z_score_points / z_score_upward_points buy-guard, Step 2).
    Returns None if there isn't enough history (fewer than 2 closes) or the history is perfectly
    flat (stdev == 0) — callers should fail closed (guard stays active) when this returns None."""
    if len(closes) < 2:
        return None
    stdev = statistics.stdev(closes)
    if stdev == 0:
        return None
    return (price - statistics.mean(closes)) / stdev
