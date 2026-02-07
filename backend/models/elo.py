"""Elo rating system with home/away adjustment."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EloRating:
    """Elo rating engine."""

    k_factor: float = 20.0
    home_advantage: float = 80.0

    def expected_score(self, home_rating: float, away_rating: float) -> float:
        """Expected score for home team."""
        adjusted_home = home_rating + self.home_advantage
        return 1 / (1 + 10 ** ((away_rating - adjusted_home) / 400))

    def update_ratings(
        self,
        home_rating: float,
        away_rating: float,
        home_goals: int,
        away_goals: int,
    ) -> tuple[float, float]:
        """Update ratings based on match outcome."""
        expected_home = self.expected_score(home_rating, away_rating)
        result_home = 0.5
        if home_goals > away_goals:
            result_home = 1.0
        elif home_goals < away_goals:
            result_home = 0.0

        goal_diff = abs(home_goals - away_goals)
        margin_multiplier = 1.0 + (goal_diff / 3.0)
        delta = self.k_factor * margin_multiplier * (result_home - expected_home)
        return home_rating + delta, away_rating - delta
