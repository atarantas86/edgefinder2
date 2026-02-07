"""Team name normalisation between The Odds API and Understat."""

from __future__ import annotations

from difflib import get_close_matches
from typing import Dict, Optional

from loguru import logger

# Odds API name  →  Understat name
# Only entries where the names differ are needed.
ODDS_TO_UNDERSTAT: Dict[str, str] = {
    # EPL
    "Brighton and Hove Albion": "Brighton",
    "Leeds United": "Leeds",
    "Leicester City": "Leicester",
    "Luton Town": "Luton",
    "Manchester City": "Manchester City",
    "Manchester United": "Manchester United",
    "Newcastle United": "Newcastle United",
    "Nottingham Forest": "Nottingham Forest",
    "Sheffield United": "Sheffield United",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolverhampton Wanderers",
    "Ipswich Town": "Ipswich",
    "Sunderland": "Sunderland",
    # La Liga
    "Atletico Madrid": "Atletico Madrid",
    "Atlético Madrid": "Atletico Madrid",
    "Athletic Bilbao": "Athletic Club",
    "CA Osasuna": "Osasuna",
    "Cadiz CF": "Cadiz",
    "Celta Vigo": "Celta Vigo",
    "Deportivo Alaves": "Alaves",
    "Alavés": "Alaves",
    "Elche CF": "Elche",
    "Rayo Vallecano": "Rayo Vallecano",
    "Real Betis": "Real Betis",
    "Real Sociedad": "Real Sociedad",
    "UD Almeria": "Almeria",
    "UD Las Palmas": "Las Palmas",
    # Bundesliga
    "Bayern Munich": "Bayern Munich",
    "Bayer Leverkusen": "Bayer Leverkusen",
    "Borussia Dortmund": "Borussia Dortmund",
    "Borussia Monchengladbach": "Borussia M.Gladbach",
    "Borussia Mönchengladbach": "Borussia M.Gladbach",
    "Eintracht Frankfurt": "Eintracht Frankfurt",
    "RB Leipzig": "RasenBallsport Leipzig",
    "FC Koln": "FC Cologne",
    "FC Köln": "FC Cologne",
    "SC Freiburg": "Freiburg",
    "VfB Stuttgart": "Stuttgart",
    "VfL Bochum": "Bochum",
    "VfL Wolfsburg": "Wolfsburg",
    "FC Augsburg": "Augsburg",
    "1. FC Heidenheim": "Heidenheim",
    "FC Union Berlin": "Union Berlin",
    "1. FC Union Berlin": "Union Berlin",
    "TSG Hoffenheim": "Hoffenheim",
    "Werder Bremen": "Werder Bremen",
    "1. FSV Mainz 05": "Mainz 05",
    "FSV Mainz 05": "Mainz 05",
    "SV Darmstadt 98": "Darmstadt",
    "Holstein Kiel": "Holstein Kiel",
    "FC St. Pauli": "St. Pauli",
    # Serie A
    "AC Milan": "Milan",
    "AC Monza": "Monza",
    "AS Roma": "Roma",
    "Atalanta BC": "Atalanta",
    "Hellas Verona": "Verona",
    "Inter Milan": "Inter",
    "SSC Napoli": "Napoli",
    "US Lecce": "Lecce",
    "US Salernitana 1919": "Salernitana",
    "Parma Calcio 1913": "Parma",
    "Venezia FC": "Venezia",
    "Como 1907": "Como",
    # Ligue 1
    "Paris Saint Germain": "Paris Saint Germain",
    "AS Monaco": "Monaco",
    "RC Lens": "Lens",
    "LOSC Lille": "Lille",
    "Olympique Lyonnais": "Lyon",
    "Olympique de Marseille": "Marseille",
    "Stade Brestois 29": "Brest",
    "Stade Rennais": "Rennes",
    "FC Nantes": "Nantes",
    "RC Strasbourg": "Strasbourg",
    "Clermont Foot": "Clermont Foot",
    "Montpellier HSC": "Montpellier",
    "FC Lorient": "Lorient",
    "Stade de Reims": "Reims",
    "Le Havre AC": "Le Havre",
    "Le Havre": "Le Havre",
    "AJ Auxerre": "Auxerre",
    "Angers SCO": "Angers",
}

# Build the reverse mapping automatically
UNDERSTAT_TO_ODDS: Dict[str, str] = {v: k for k, v in ODDS_TO_UNDERSTAT.items()}

# Collect all known Understat names for fuzzy matching
_ALL_UNDERSTAT_NAMES = list(set(ODDS_TO_UNDERSTAT.values()))


def normalize_team_name(
    odds_name: str,
    known_understat: list[str] | None = None,
) -> str:
    """Convert an Odds API team name to its Understat equivalent.

    1. Exact match in the static dictionary.
    2. Fuzzy match via difflib against known Understat names.
    3. Return the original name unchanged (with a warning log).
    """
    # 1) Static lookup
    if odds_name in ODDS_TO_UNDERSTAT:
        return ODDS_TO_UNDERSTAT[odds_name]

    # Maybe the name is already the Understat form
    candidates = known_understat or _ALL_UNDERSTAT_NAMES
    if odds_name in candidates:
        return odds_name

    # 2) Fuzzy fallback
    matches = get_close_matches(odds_name, candidates, n=1, cutoff=0.8)
    if matches:
        logger.warning(f"Fuzzy match: '{odds_name}' → '{matches[0]}'")
        return matches[0]

    # 3) No match – return as-is
    logger.warning(f"No Understat match for team: '{odds_name}'")
    return odds_name
