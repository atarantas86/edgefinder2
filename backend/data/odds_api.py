"""The Odds API integration."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from config import get_settings


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

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
