"""Scheduler setup for EdgeFinder."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from data.football_api import FootballAPI
from data.odds_api import OddsAPI
from database.db import SessionLocal, init_db
from database.models import Match, Odds, Signal
from engine.confidence import compute_confidence
from engine.value_detector import detect_value_bets
from models.poisson import run_bivariate_poisson


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


def generate_signals() -> None:
    logger.info("Generating signals")
    init_db()
    db = SessionLocal()
    try:
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
            implied = {key: 1 / value for key, value in odds.items()}
            total_implied = sum(implied.values()) or 1.0
            normalized = {key: value / total_implied for key, value in implied.items()}
            total_goals = 2.6
            home_share = normalized.get("home", 0.45) + 0.5 * normalized.get("draw", 0.25)
            home_xg = total_goals * home_share
            away_xg = total_goals * (1 - home_share)
            model_output = run_bivariate_poisson(home_xg, away_xg)
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


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_odds, "interval", hours=1)
    scheduler.add_job(refresh_fixtures, "interval", hours=6)
    scheduler.add_job(generate_signals, "cron", hour=7, minute=0)
    return scheduler
