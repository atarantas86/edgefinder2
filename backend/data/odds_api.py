"""The Odds API integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import get_settings
from database.models import Match


SPORT_KEYS: Dict[str, Dict[str, Any]] = {
    "soccer_epl": {"league_id": 39, "league_name": "Premier League"},
    "soccer_france_ligue_one": {"league_id": 61, "league_name": "Ligue 1"},
    "soccer_spain_la_liga": {"league_id": 140, "league_name": "La Liga"},
    "soccer_germany_bundesliga": {"league_id": 78, "league_name": "Bundesliga"},
    "soccer_italy_serie_a": {"league_id": 135, "league_name": "Serie A"},
}


class OddsAPI:
    """Client for The Odds API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.odds_api_key
        self.base_url = "https://api.the-odds-api.com"

    def get_sports(self) -> Dict[str, Any]:
        return self._get("/v4/sports", {})

    def get_odds(
        self,
        sport: str,
        regions: str = "eu",
        markets: str = "h2h,totals,spreads",
        odds_format: str = "decimal",
        date_format: str = "iso",
    ) -> Dict[str, Any]:
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
            "dateFormat": date_format,
        }
        return self._get(f"/v4/sports/{sport}/odds", params)

    def fetch_odds_for_sport(
        self,
        db: Session,
        sport: str,
    ) -> List[Tuple[Dict[str, Any], Match]]:
        odds_response = self.get_odds(sport=sport)
        fixtures: List[Tuple[Dict[str, Any], Match]] = []
        for event in odds_response:
            match = self._match_fixture(db, event)
            if not match:
                home = event.get("home_team", "Unknown")
                away = event.get("away_team", "Unknown")
                commence = event.get("commence_time", "")
                if not commence:
                    continue
                event_dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                min_id = db.query(func.min(Match.fixture_id)).scalar() or 0
                new_id = min(min_id, 0) - 1
                l_name = SPORT_KEYS.get(sport, {}).get("league_name", f"League {sport}")
                match = Match(
                    fixture_id=new_id,
                    home_team=home,
                    away_team=away,
                    league=l_name,
                    kickoff=event_dt.isoformat(),
                    status="NS",
                )
                db.add(match)
                db.commit()
                logger.info(f"Fixture créée depuis Odds API: {home} vs {away} (id={new_id})")
            fixtures.append((event, match))
        return fixtures

    def _match_fixture(self, db: Session, event: Dict[str, Any]) -> Optional[Match]:
        home_team = event.get("home_team")
        away_team = event.get("away_team")
        if not home_team or not away_team:
            return None
        return (
            db.query(Match)
            .filter(Match.home_team == home_team, Match.away_team == away_team)
            .first()
        )

    def _next_negative_fixture_id(
        self,
        db: Session,
        current: Optional[int],
    ) -> int:
        if current is None:
            min_fixture_id = (
                db.query(Match.fixture_id)
                .filter(Match.fixture_id < 0)
                .order_by(Match.fixture_id.asc())
                .first()
            )
            current = min_fixture_id[0] if min_fixture_id else 0
        return current - 1

    def _league_details(self, sport: str, fallback_name: str) -> Tuple[Optional[int], str]:
        details = SPORT_KEYS.get(sport, {})
        league_id = details.get("league_id")
        league_name = details.get("league_name", fallback_name)
        return league_id, league_name

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
