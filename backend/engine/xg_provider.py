"""xG data provider – fetches from Understat via soccerdata."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from database.models import TeamStats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEAGUE_MAP: Dict[str, str] = {
    "soccer_epl": "ENG-Premier League",
    "soccer_spain_la_liga": "ESP-La Liga",
    "soccer_germany_bundesliga": "GER-Bundesliga",
    "soccer_italy_serie_a": "ITA-Serie A",
    "soccer_france_ligue_one": "FRA-Ligue 1",
}

DECAY_ALPHA: float = 0.01
SHRINKAGE_K: int = 50


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


FORM_WINDOW: int = 5


@dataclass(frozen=True)
class TeamXG:
    team: str
    league: str
    xg_att_home: float
    xg_att_away: float
    xga_def_home: float
    xga_def_away: float
    matches_home: int
    matches_away: int
    form_home: float  # 0.0 (all losses) to 1.0 (all wins) over last 5
    form_away: float


@dataclass(frozen=True)
class LeagueAverages:
    avg_xg_home: float  # avg xG scored by home teams per game
    avg_xg_away: float  # avg xG scored by away teams per game


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_current_season() -> int:
    """Return the starting year of the current football season.

    Understat uses the start year: ``2024`` for the 2024-2025 season.
    We target the most recent season with substantial data available,
    which lags the calendar by one year during the second half of the
    season (Jan-Jul).
    """
    now = datetime.utcnow()
    return now.year - 1 if now.month >= 8 else now.year - 2


def _decay_weighted_avg(values: List[float], alpha: float = DECAY_ALPHA) -> float:
    """Weighted average with exponential decay (index 0 = most recent)."""
    if not values:
        return 0.0
    weights = [math.exp(-alpha * i) for i in range(len(values))]
    total_w = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total_w if total_w else 0.0


def _shrink(team_avg: float, league_avg: float, n: int, k: int = SHRINKAGE_K) -> float:
    """Bayesian shrinkage toward the league mean."""
    return (n * team_avg + k * league_avg) / (n + k)


def _compute_form(pairs: List[Tuple[float, float]]) -> float:
    """Compute form as points ratio from xG-based results.

    Each pair is (xG_scored, xG_conceded). Win=3pts, draw=1pt, loss=0pt.
    Returns 0.0 to 1.0 (points / max_points). Default 0.5 if no data.
    """
    if not pairs:
        return 0.5
    points = 0
    for scored, conceded in pairs:
        if scored > conceded + 0.3:  # clear xG win
            points += 3
        elif conceded > scored + 0.3:  # clear xG loss
            points += 0
        else:  # close = draw
            points += 1
    return points / (3 * len(pairs))


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------


def fetch_team_xg(sport_key: str) -> Tuple[Dict[str, TeamXG], LeagueAverages]:
    """Fetch per-team xG from Understat via soccerdata for *sport_key*.

    Returns (team_dict, league_averages).
    """
    import soccerdata as sd  # lazy import to keep startup fast

    sd_league = LEAGUE_MAP.get(sport_key)
    if not sd_league:
        raise ValueError(f"Unknown sport key: {sport_key}")

    season = get_current_season()
    season_str = str(season)

    logger.info(f"Fetching xG from Understat: {sd_league} season {season}")
    understat = sd.Understat(leagues=sd_league, seasons=season_str)
    schedule = understat.read_schedule()

    # schedule is a DataFrame with columns like:
    #   home_team, away_team, home_xG (or xG columns), date, etc.
    # Column names vary; normalise what we need.
    df = schedule.reset_index()

    # Identify xG columns (soccerdata names vary by version)
    home_xg_col = _find_col(df, ["home_xg", "home_xG", "xG_home"])
    away_xg_col = _find_col(df, ["away_xg", "away_xG", "xG_away"])
    home_col = _find_col(df, ["home_team", "home"])
    away_col = _find_col(df, ["away_team", "away"])
    date_col = _find_col(df, ["date", "datetime", "match_date"])

    if not all([home_xg_col, away_xg_col, home_col, away_col]):
        logger.error(f"Missing expected columns in soccerdata output. Columns: {list(df.columns)}")
        return {}, LeagueAverages(1.4, 1.1)

    # Drop rows without xG (future/unplayed matches)
    df = df.dropna(subset=[home_xg_col, away_xg_col])
    if df.empty:
        return {}, LeagueAverages(1.4, 1.1)

    # Sort most-recent first
    if date_col:
        df = df.sort_values(date_col, ascending=False)

    # Collect per-team raw data
    teams_home: Dict[str, List[Tuple[float, float]]] = {}  # team -> [(xG_scored, xG_conceded)]
    teams_away: Dict[str, List[Tuple[float, float]]] = {}

    for _, row in df.iterrows():
        h_team = str(row[home_col])
        a_team = str(row[away_col])
        h_xg = float(row[home_xg_col])
        a_xg = float(row[away_xg_col])

        teams_home.setdefault(h_team, []).append((h_xg, a_xg))
        teams_away.setdefault(a_team, []).append((a_xg, h_xg))

    # League averages (raw, un-decayed)
    all_home_xg = [h_xg for pairs in teams_home.values() for h_xg, _ in pairs]
    all_away_xg = [a_xg for pairs in teams_away.values() for a_xg, _ in pairs]
    avg_xg_home = sum(all_home_xg) / len(all_home_xg) if all_home_xg else 1.4
    avg_xg_away = sum(all_away_xg) / len(all_away_xg) if all_away_xg else 1.1
    league_avg = LeagueAverages(avg_xg_home, avg_xg_away)

    # Build TeamXG for every team
    all_teams = set(teams_home.keys()) | set(teams_away.keys())
    result: Dict[str, TeamXG] = {}

    for team in all_teams:
        home_pairs = teams_home.get(team, [])
        away_pairs = teams_away.get(team, [])
        n_home = len(home_pairs)
        n_away = len(away_pairs)

        raw_att_home = _decay_weighted_avg([s for s, _ in home_pairs]) if home_pairs else avg_xg_home
        raw_def_home = _decay_weighted_avg([c for _, c in home_pairs]) if home_pairs else avg_xg_away
        raw_att_away = _decay_weighted_avg([s for s, _ in away_pairs]) if away_pairs else avg_xg_away
        raw_def_away = _decay_weighted_avg([c for _, c in away_pairs]) if away_pairs else avg_xg_home

        # Form: xG-based points over last FORM_WINDOW matches
        form_home = _compute_form(home_pairs[:FORM_WINDOW])
        form_away = _compute_form(away_pairs[:FORM_WINDOW])

        result[team] = TeamXG(
            team=team,
            league=sd_league,
            xg_att_home=_shrink(raw_att_home, avg_xg_home, n_home),
            xg_att_away=_shrink(raw_att_away, avg_xg_away, n_away),
            xga_def_home=_shrink(raw_def_home, avg_xg_away, n_home),
            xga_def_away=_shrink(raw_def_away, avg_xg_home, n_away),
            matches_home=n_home,
            matches_away=n_away,
            form_home=form_home,
            form_away=form_away,
        )

    logger.info(f"Fetched xG for {len(result)} teams in {sd_league}")
    return result, league_avg


def _find_col(df: Any, candidates: List[str]) -> str | None:
    """Return the first column name from *candidates* present in *df*."""
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------


def refresh_xg_to_db(db: Session) -> int:
    """Fetch xG for all leagues and upsert into *team_stats*.

    Skips a league if its data was updated less than 24 h ago.
    Returns: total number of teams upserted.
    """
    teams_updated = 0
    season = str(get_current_season())

    for sport_key, sd_league in LEAGUE_MAP.items():
        # Staleness check
        recent = (
            db.query(TeamStats)
            .filter(TeamStats.league == sd_league, TeamStats.season == season)
            .order_by(TeamStats.updated_at.desc())
            .first()
        )
        if recent and (datetime.utcnow() - recent.updated_at).total_seconds() < 86400:
            logger.info(f"xG for {sd_league} is fresh, skipping")
            continue

        try:
            team_data, _ = fetch_team_xg(sport_key)
        except Exception as exc:
            logger.warning(f"Failed to fetch xG for {sd_league}: {exc}")
            continue

        for team_name, txg in team_data.items():
            existing = (
                db.query(TeamStats)
                .filter(
                    TeamStats.team == team_name,
                    TeamStats.league == sd_league,
                    TeamStats.season == season,
                )
                .first()
            )
            if existing:
                existing.xg_att_home = txg.xg_att_home
                existing.xg_att_away = txg.xg_att_away
                existing.xga_def_home = txg.xga_def_home
                existing.xga_def_away = txg.xga_def_away
                existing.matches_home = txg.matches_home
                existing.matches_away = txg.matches_away
                existing.form_home = txg.form_home
                existing.form_away = txg.form_away
                existing.updated_at = datetime.utcnow()
            else:
                db.add(
                    TeamStats(
                        team=team_name,
                        league=sd_league,
                        season=season,
                        xg_att_home=txg.xg_att_home,
                        xg_att_away=txg.xg_att_away,
                        xga_def_home=txg.xga_def_home,
                        xga_def_away=txg.xga_def_away,
                        matches_home=txg.matches_home,
                        matches_away=txg.matches_away,
                        form_home=txg.form_home,
                        form_away=txg.form_away,
                    )
                )
            teams_updated += 1

        db.commit()
        logger.info(f"Upserted {len(team_data)} teams for {sd_league}")

    return teams_updated
