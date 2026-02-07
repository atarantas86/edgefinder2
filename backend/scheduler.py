"""Scheduler setup for EdgeFinder."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from data.football_api import FootballAPI
from data.odds_api import OddsAPI
from database.db import SessionLocal, init_db
from database.models import Match, Odds, Signal, TeamStats
from engine.confidence import compute_confidence
from engine.team_names import normalize_team_name
from engine.value_detector import detect_value_bets
from engine.xg_provider import LeagueAverages, refresh_xg_to_db
from models.dixon_coles import run_dixon_coles
from models.poisson import PoissonOutput, run_bivariate_poisson


# ---------------------------------------------------------------------------
# Fixtures & Odds (unchanged)
# ---------------------------------------------------------------------------


def refresh_fixtures() -> int:
    logger.info("Refreshing fixtures")
    api = FootballAPI()
    today = datetime.utcnow().date().isoformat()
    response = api.get_fixtures(date=today)
    init_db()
    db = SessionLocal()
    fixtures_added = 0
    try:
        for item in response.get("response", []):
            fixture = item.get("fixture", {})
            teams = item.get("teams", {})
            league = item.get("league", {})
            fixture_id = fixture.get("id")
            if not fixture_id:
                continue
            existing = db.query(Match).filter(Match.fixture_id == fixture_id).first()
            if existing:
                continue
            db.add(
                Match(
                    fixture_id=fixture_id,
                    home_team=teams.get("home", {}).get("name", "Home"),
                    away_team=teams.get("away", {}).get("name", "Away"),
                    league=league.get("name", "Unknown"),
                    kickoff=fixture.get("date", ""),
                    status=fixture.get("status", {}).get("short", "scheduled"),
                )
            )
            fixtures_added += 1
        db.commit()
    finally:
        db.close()
    return fixtures_added


def refresh_odds() -> int:
    logger.info("Refreshing odds")
    api = OddsAPI()
    sports = ["soccer_epl", "soccer_france_ligue_one", "soccer_spain_la_liga"]
    init_db()
    db = SessionLocal()
    odds_added = 0
    try:
        for sport in sports:
            fixtures = api.fetch_odds_for_sport(db, sport=sport)
            for event, match in fixtures:
                home = event.get("home_team") or ""
                away = event.get("away_team") or ""
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        market_key = market.get("key")
                        for outcome in market.get("outcomes", []):
                            outcome_name = outcome.get("name")
                            price = outcome.get("price")
                            if not price or not outcome_name:
                                continue
                            normalized_outcome = outcome_name.lower()
                            if normalized_outcome == home.lower():
                                normalized_outcome = "home"
                            elif normalized_outcome == away.lower():
                                normalized_outcome = "away"
                            elif normalized_outcome in {"draw", "tie"}:
                                normalized_outcome = "draw"
                            db.add(
                                Odds(
                                    match_id=match.id,
                                    market=market_key,
                                    outcome=normalized_outcome,
                                    odds=price,
                                    source=bookmaker.get("title", "the_odds_api"),
                                )
                            )
                            odds_added += 1
        db.commit()
    finally:
        db.close()
    return odds_added


# ---------------------------------------------------------------------------
# xG refresh
# ---------------------------------------------------------------------------


def refresh_xg() -> int:
    """Refresh xG data from Understat (max once per 24 h per league)."""
    logger.info("Refreshing xG data from Understat")
    init_db()
    db = SessionLocal()
    try:
        return refresh_xg_to_db(db)
    except Exception as exc:
        logger.error(f"xG refresh failed: {exc}")
        return 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------


def _fallback_model(odds: Dict[str, float]) -> PoissonOutput:
    """Derive xG from odds (circular fallback when xG data is unavailable)."""
    implied = {k: 1 / v for k, v in odds.items() if v > 0}
    total_implied = sum(implied.values()) or 1.0
    normalized = {k: v / total_implied for k, v in implied.items()}
    total_goals = 2.6
    home_share = normalized.get("home", 0.45) + 0.5 * normalized.get("draw", 0.25)
    return run_bivariate_poisson(total_goals * home_share, total_goals * (1 - home_share))


def _compute_league_averages(all_stats: List[TeamStats]) -> Dict[str, LeagueAverages]:
    """Group TeamStats by league and compute averages."""
    buckets: Dict[str, List[TeamStats]] = {}
    for s in all_stats:
        buckets.setdefault(s.league, []).append(s)

    result: Dict[str, LeagueAverages] = {}
    for league, stats in buckets.items():
        home_vals = [s.xg_att_home for s in stats if s.matches_home > 0]
        away_vals = [s.xg_att_away for s in stats if s.matches_away > 0]
        result[league] = LeagueAverages(
            avg_xg_home=sum(home_vals) / len(home_vals) if home_vals else 1.4,
            avg_xg_away=sum(away_vals) / len(away_vals) if away_vals else 1.1,
        )
    return result


def generate_signals() -> None:
    logger.info("Generating signals")
    init_db()
    db = SessionLocal()
    try:
        db.query(Signal).delete()
        db.commit()

        # Pre-load xG data
        all_stats = db.query(TeamStats).all()
        stats_by_name: Dict[str, TeamStats] = {s.team: s for s in all_stats}
        league_avgs = _compute_league_averages(all_stats)

        # Known Understat names for fuzzy matching
        known_names = list(stats_by_name.keys())

        matches = db.query(Match).all()
        for match in matches:
            odds_entries = (
                db.query(Odds)
                .filter(Odds.match_id == match.id, Odds.market == "h2h")
                .all()
            )
            if not odds_entries:
                continue
            odds = {entry.outcome: entry.odds for entry in odds_entries}

            # Try Dixon-Coles with independent xG
            home_us = normalize_team_name(match.home_team, known_names)
            away_us = normalize_team_name(match.away_team, known_names)
            home_stats = stats_by_name.get(home_us)
            away_stats = stats_by_name.get(away_us)

            if home_stats and away_stats:
                lg_avg = league_avgs.get(
                    home_stats.league,
                    LeagueAverages(1.4, 1.1),
                )
                model_output = run_dixon_coles(
                    xg_att_home=home_stats.xg_att_home,
                    xga_def_away=away_stats.xga_def_away,
                    xg_att_away=away_stats.xg_att_away,
                    xga_def_home=home_stats.xga_def_home,
                    league_avg=lg_avg,
                )
            else:
                model_output = _fallback_model(odds)

            model_probs = {
                "home": model_output.home_win,
                "draw": model_output.draw,
                "away": model_output.away_win,
            }
            value_bets = detect_value_bets(model_probs, odds)
            for bet in value_bets:
                confidence = compute_confidence(
                    edge=bet["edge"],
                    convergence=0.7,
                    volume=0.6,
                    stability=0.65,
                    inefficiency=0.5,
                )
                existing = (
                    db.query(Signal)
                    .filter(
                        Signal.match_id == match.id,
                        Signal.outcome == bet["outcome"],
                    )
                    .first()
                )
                if existing:
                    continue
                db.add(
                    Signal(
                        match_id=match.id,
                        outcome=bet["outcome"],
                        probability=bet["probability"],
                        odds=bet["odds"],
                        edge=bet["edge"],
                        kelly=bet["kelly"],
                        confidence=confidence,
                    )
                )
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_xg, "cron", hour=5, minute=0)
    scheduler.add_job(refresh_fixtures, "interval", hours=6)
    scheduler.add_job(refresh_odds, "interval", hours=1)
    scheduler.add_job(generate_signals, "cron", hour=7, minute=0)
    return scheduler
