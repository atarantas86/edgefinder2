"""Bivariate Poisson model for football scorelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
from scipy.stats import poisson


@dataclass(frozen=True)
class ScoreMatrix:
    """Score matrix with probabilities for each scoreline."""

    matrix: np.ndarray
    max_goals: int

    def probability(self, home_goals: int, away_goals: int) -> float:
        if home_goals > self.max_goals or away_goals > self.max_goals:
            return 0.0
        return float(self.matrix[home_goals, away_goals])


@dataclass(frozen=True)
class PoissonOutput:
    """Model output including probabilities and expected goals."""

    score_matrix: ScoreMatrix
    expected_home_goals: float
    expected_away_goals: float
    home_win: float
    draw: float
    away_win: float
    over_25: float
    under_25: float


def _bivariate_poisson_pmf(
    home_goals: int, away_goals: int, lambda_home: float, lambda_away: float, lambda_shared: float
) -> float:
    prob = 0.0
    for k in range(0, min(home_goals, away_goals) + 1):
        prob += (
            poisson.pmf(home_goals - k, lambda_home)
            * poisson.pmf(away_goals - k, lambda_away)
            * poisson.pmf(k, lambda_shared)
        )
    return float(prob)


def build_score_matrix(
    lambda_home: float,
    lambda_away: float,
    lambda_shared: float = 0.1,
    max_goals: int = 7,
) -> ScoreMatrix:
    """Compute score matrix for bivariate Poisson distribution."""
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            matrix[home_goals, away_goals] = _bivariate_poisson_pmf(
                home_goals, away_goals, lambda_home, lambda_away, lambda_shared
            )
    matrix /= matrix.sum()
    return ScoreMatrix(matrix=matrix, max_goals=max_goals)


def summarize_from_matrix(score_matrix: ScoreMatrix) -> Dict[str, float]:
    """Summarize win/draw/lose and totals probabilities."""
    max_goals = score_matrix.max_goals
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over_25 = 0.0
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            prob = score_matrix.probability(home_goals, away_goals)
            if home_goals > away_goals:
                home_win += prob
            elif home_goals == away_goals:
                draw += prob
            else:
                away_win += prob
            if home_goals + away_goals > 2:
                over_25 += prob
    under_25 = 1.0 - over_25
    return {
        "home_win": home_win,
        "draw": draw,
        "away_win": away_win,
        "over_25": over_25,
        "under_25": under_25,
    }


def run_bivariate_poisson(
    lambda_home: float,
    lambda_away: float,
    lambda_shared: float = 0.1,
    max_goals: int = 7,
) -> PoissonOutput:
    """Run bivariate Poisson and return summary."""
    matrix = build_score_matrix(lambda_home, lambda_away, lambda_shared, max_goals)
    summary = summarize_from_matrix(matrix)
    return PoissonOutput(
        score_matrix=matrix,
        expected_home_goals=lambda_home + lambda_shared,
        expected_away_goals=lambda_away + lambda_shared,
        home_win=summary["home_win"],
        draw=summary["draw"],
        away_win=summary["away_win"],
        over_25=summary["over_25"],
        under_25=summary["under_25"],
    )
