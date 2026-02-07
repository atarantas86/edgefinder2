"""Dixon-Coles model for football match probabilities."""

from __future__ import annotations

import numpy as np
from scipy.stats import poisson

from engine.xg_provider import LeagueAverages
from models.poisson import PoissonOutput, ScoreMatrix, summarize_from_matrix

DEFAULT_RHO: float = -0.05
DEFAULT_HFA: float = 1.07


def _tau(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    lambda_away: float,
    rho: float,
) -> float:
    """Dixon-Coles correction for low-scoring outcomes."""
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lambda_home * lambda_away * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lambda_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lambda_home * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def run_dixon_coles(
    xg_att_home: float,
    xga_def_away: float,
    xg_att_away: float,
    xga_def_home: float,
    league_avg: LeagueAverages,
    hfa: float = DEFAULT_HFA,
    rho: float = DEFAULT_RHO,
    max_goals: int = 7,
    form_home: float = 0.5,
    form_away: float = 0.5,
) -> PoissonOutput:
    """Run Dixon-Coles model and return match probabilities.

    Strength ratios are relative to the league average:
        att_home = xg_att_home / league_avg_xG_home
        def_away = xga_def_away / league_avg_xGA_away  (= avg_xg_home)

    Both lambdas use a single league_avg_goals base;
    the home–away asymmetry comes solely from the HFA multiplier.
    """
    avg_h = league_avg.avg_xg_home or 1.4
    avg_a = league_avg.avg_xg_away or 1.1
    league_avg_goals = (avg_h + avg_a) / 2.0

    att_home_ratio = xg_att_home / avg_h
    def_away_ratio = xga_def_away / avg_h   # away team concedes vs home avg
    att_away_ratio = xg_att_away / avg_a
    def_home_ratio = xga_def_home / avg_a   # home team concedes vs away avg

    lambda_home = att_home_ratio * def_away_ratio * league_avg_goals * hfa
    lambda_away = att_away_ratio * def_home_ratio * league_avg_goals

    # Form factor: ±10% adjustment based on recent form (0.0-1.0, 0.5=neutral)
    form_factor_home = 1.0 + 0.10 * (form_home - 0.5) / 0.5
    form_factor_away = 1.0 + 0.10 * (form_away - 0.5) / 0.5
    lambda_home *= form_factor_home
    lambda_away *= form_factor_away

    # Clamp to avoid extreme values
    lambda_home = max(0.2, min(lambda_home, 5.0))
    lambda_away = max(0.2, min(lambda_away, 5.0))

    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            matrix[i, j] = (
                poisson.pmf(i, lambda_home)
                * poisson.pmf(j, lambda_away)
                * _tau(i, j, lambda_home, lambda_away, rho)
            )
    matrix /= matrix.sum()

    score_matrix = ScoreMatrix(matrix=matrix, max_goals=max_goals)
    summary = summarize_from_matrix(score_matrix)

    return PoissonOutput(
        score_matrix=score_matrix,
        expected_home_goals=lambda_home,
        expected_away_goals=lambda_away,
        home_win=summary["home_win"],
        draw=summary["draw"],
        away_win=summary["away_win"],
        over_25=summary["over_25"],
        under_25=summary["under_25"],
        btts_yes=summary["btts_yes"],
        btts_no=summary["btts_no"],
    )
