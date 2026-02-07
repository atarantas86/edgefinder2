"""Kelly criterion calculations."""

from __future__ import annotations


def kelly_fraction(probability: float, odds: float, fraction: float = 0.25, cap: float = 0.10) -> float:
    """Return fractional Kelly stake size with cap."""
    if odds <= 1.0 or probability <= 0.0:
        return 0.0
    b = odds - 1.0
    q = 1.0 - probability
    full_kelly = (b * probability - q) / b
    stake = max(0.0, full_kelly * fraction)
    return min(stake, cap)
