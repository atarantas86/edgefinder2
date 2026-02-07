"""Scraper for Understat xG data."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup


UNDERSTAT_BASE = "https://understat.com"


def _extract_json_from_script(html: str, var_name: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"var {var_name} = JSON.parse\('(.+)'\);")
    for script in soup.find_all("script"):
        if not script.string:
            continue
        match = pattern.search(script.string)
        if match:
            raw = match.group(1)
            decoded = raw.encode("utf-8").decode("unicode_escape")
            return json.loads(decoded)
    return []


def fetch_league_xg(league: str, season: int) -> List[Dict[str, Any]]:
    """Fetch match xG data for a league season."""
    url = f"{UNDERSTAT_BASE}/league/{league}/{season}"
    with httpx.Client(timeout=20.0) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text
    return _extract_json_from_script(html, "matchesData")
