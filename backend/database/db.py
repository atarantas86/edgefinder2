"""Database setup for EdgeFinder."""

from __future__ import annotations

import os

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edgefinder.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Columns to add to existing tables (table, column, type, default)
_MIGRATIONS = [
    ("signals", "market_type", "TEXT", "'h2h'"),
    ("team_stats", "form_home", "REAL", "0.5"),
    ("team_stats", "form_away", "REAL", "0.5"),
    ("bets", "opening_odds", "REAL", "0.0"),
]


def init_db() -> None:
    """Create database tables and run lightweight migrations."""
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        for table, col, col_type, default in _MIGRATIONS:
            try:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT {default}")
                )
                conn.commit()
                logger.info(f"Migration: added {table}.{col}")
            except Exception:
                conn.rollback()
