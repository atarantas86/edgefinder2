"""Confidence scoring for value bets."""

from __future__ import annotations


def compute_confidence(
    edge: float,
    convergence: float,
    volume: float,
    stability: float,
    inefficiency: float,
) -> float:
    """Compute a 0-100 confidence score."""
    score = (
        edge * 0.30
        + convergence * 0.25
        + volume * 0.20
        + stability * 0.15
        + inefficiency * 0.10
    )
    return round(max(0.0, min(score * 100, 100.0)), 2)
