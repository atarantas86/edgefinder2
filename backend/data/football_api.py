"""API-Football v3 integration."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from config import get_settings


class FootballAPI:
    """Client for API-Football v3."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.football_api_key
        self.base_url = "https://v3.football.api-sports.io"

    def _headers(self) -> Dict[str, str]:
        return {"x-apisports-key": self.api_key}

    def get_fixtures(
        self,
        date: Optional[str] = None,
        league: Optional[int] = None,
        season: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if date:
            params["date"] = date
        if league:
            params["league"] = league
        if season:
            params["season"] = season
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._get("/fixtures", params)

    def get_team_stats(self, league: int, season: int, team: int) -> Dict[str, Any]:
        params = {"league": league, "season": season, "team": team}
        return self._get("/teams/statistics", params)

    def get_fixture_statistics(self, fixture_id: int) -> Dict[str, Any]:
        params = {"fixture": fixture_id}
        return self._get("/fixtures/statistics", params)

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()
