"""Value bet detection based on model probabilities and odds."""

from __future__ import annotations

from typing import Dict, List

from models.kelly import kelly_fraction


def detect_value_bets(
    model_probs: Dict[str, float],
    market_odds: Dict[str, float],
    threshold: float = 0.03,
) -> List[Dict[str, float]]:
    """Detect value bets when model edge exceeds threshold.

    Edge is expected value: ``(odds * probability) - 1``.
    A 3 % edge means 3 % expected profit per unit staked.
    """
    value_bets = []
    for outcome, prob in model_probs.items():
        odds = market_odds.get(outcome)
        if not odds or odds > 15.0:
            continue
        edge = (odds * prob) - 1.0
        edge = min(edge, 0.25)
        if edge > threshold:
            value_bets.append(
                {
                    "outcome": outcome,
                    "probability": prob,
                    "odds": odds,
                    "edge": edge,
                    "kelly": kelly_fraction(prob, odds),
                }
            )
    return value_bets
