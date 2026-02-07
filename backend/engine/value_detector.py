"""Value bet detection based on model probabilities and odds."""

from __future__ import annotations

from typing import Dict, List

from models.kelly import kelly_fraction

BLEND_MODEL: float = 0.65
BLEND_MARKET: float = 1.0 - BLEND_MODEL


def detect_value_bets(
    model_probs: Dict[str, float],
    market_odds: Dict[str, float],
    threshold: float = 0.03,
) -> List[Dict[str, float]]:
    """Detect value bets when model edge exceeds threshold.

    Probabilities are blended 65 % model + 35 % market-implied to
    prevent the model from diverging too far from market consensus.
    Edge is expected value: ``(odds * blended_prob) - 1``.
    """
    # Compute market-implied probabilities (margin-removed)
    implied_raw = {k: 1.0 / v for k, v in market_odds.items() if v > 0}
    margin = sum(implied_raw.values()) or 1.0
    market_probs = {k: v / margin for k, v in implied_raw.items()}

    value_bets = []
    for outcome, model_prob in model_probs.items():
        odds = market_odds.get(outcome)
        if not odds or odds > 15.0:
            continue
        market_prob = market_probs.get(outcome, 0.0)
        blended_prob = BLEND_MODEL * model_prob + BLEND_MARKET * market_prob
        edge = (odds * blended_prob) - 1.0
        edge = min(edge, 0.15)
        if edge > threshold:
            value_bets.append(
                {
                    "outcome": outcome,
                    "probability": blended_prob,
                    "odds": odds,
                    "edge": edge,
                    "kelly": kelly_fraction(blended_prob, odds),
                }
            )
    return value_bets
