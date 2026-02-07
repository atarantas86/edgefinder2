"""Generate textual analysis for matches."""

from __future__ import annotations

from typing import Any, Dict, List


def analyze_match(
    match: Dict[str, Any],
    model_output: Dict[str, Any],
    odds: Dict[str, Any],
    value_bets: List[Dict[str, Any]],
    confidence: float,
) -> str:
    """Return a textual analysis for a match."""
    home = match.get("home_team", "Home")
    away = match.get("away_team", "Away")
    league = match.get("league", "Unknown League")
    kickoff = match.get("kickoff", "TBD")

    summary = (
        f"{home} vs {away} ({league}) - coup d'envoi: {kickoff}. "
        f"Modèle: {model_output.get('home_win', 0):.1%} "
        f"domicile, {model_output.get('draw', 0):.1%} nul, "
        f"{model_output.get('away_win', 0):.1%} extérieur."
    )

    odds_info = ""
    if odds:
        odds_info = " Cotes marché: " + ", ".join(
            f"{key} {value}" for key, value in odds.items()
        )

    value_info = ""
    if value_bets:
        value_entries = "; ".join(
            f"{bet['outcome']} edge {bet['edge']:.1%}, Kelly {bet['kelly']:.1%}"
            for bet in value_bets
        )
        value_info = f" Value bets détectés: {value_entries}."
    else:
        value_info = " Aucun value bet >3% détecté."

    return f"{summary}{odds_info}{value_info} Confiance: {confidence:.1f}/100."
