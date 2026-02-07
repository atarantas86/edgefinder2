"""Configuration loader for EdgeFinder."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    football_api_key: str
    odds_api_key: str
    database_url: str


def load_settings() -> Settings:
    """Load environment variables and return settings."""
    load_dotenv()
    football_api_key = os.getenv("FOOTBALL_API_KEY", "").strip()
    odds_api_key = os.getenv("ODDS_API_KEY", "").strip()
    database_url = os.getenv("DATABASE_URL", "sqlite:///./edgefinder.db")

    if not football_api_key or not odds_api_key:
        missing = []
        if not football_api_key:
            missing.append("FOOTBALL_API_KEY")
        if not odds_api_key:
            missing.append("ODDS_API_KEY")
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return Settings(
        football_api_key=football_api_key,
        odds_api_key=odds_api_key,
        database_url=database_url,
    )


def get_settings() -> Settings:
    """Get cached settings instance."""
    if not hasattr(get_settings, "_settings"):
        get_settings._settings = load_settings()
    return get_settings._settings
