"""SQLAlchemy models for EdgeFinder."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database.db import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, unique=True, index=True, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    league = Column(String, nullable=False)
    kickoff = Column(String, nullable=False)
    status = Column(String, default="scheduled")
    home_goals = Column(Integer, default=0)
    away_goals = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    odds = relationship("Odds", back_populates="match", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="match", cascade="all, delete-orphan")


class Odds(Base):
    __tablename__ = "odds"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    market = Column(String, nullable=False)
    outcome = Column(String, nullable=False)
    odds = Column(Float, nullable=False)
    source = Column(String, default="the_odds_api")
    fetched_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="odds")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    outcome = Column(String, nullable=False)
    market_type = Column(String, default="h2h")
    probability = Column(Float, nullable=False)
    odds = Column(Float, nullable=False)
    edge = Column(Float, nullable=False)
    kelly = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="signals")
    bets = relationship("Bet", back_populates="signal", cascade="all, delete-orphan")


class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    stake = Column(Float, nullable=False)
    opening_odds = Column(Float, default=0.0)
    result = Column(String, default="open")
    profit = Column(Float, default=0.0)
    placed_at = Column(DateTime, default=datetime.utcnow)

    signal = relationship("Signal", back_populates="bets")
    closing_line = relationship("ClosingLine", back_populates="bet", uselist=False)


class ClosingLine(Base):
    __tablename__ = "closing_lines"

    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=False, unique=True)
    opening_odds = Column(Float, nullable=False)
    closing_odds = Column(Float, nullable=False)
    clv = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    bet = relationship("Bet", back_populates="closing_line")


class TeamStats(Base):
    __tablename__ = "team_stats"
    __table_args__ = (
        UniqueConstraint("team", "league", "season", name="uq_team_league_season"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team = Column(String, nullable=False, index=True)
    league = Column(String, nullable=False, index=True)
    season = Column(String, nullable=False)
    xg_att_home = Column(Float, nullable=False)
    xg_att_away = Column(Float, nullable=False)
    xga_def_home = Column(Float, nullable=False)
    xga_def_away = Column(Float, nullable=False)
    matches_home = Column(Integer, default=0)
    matches_away = Column(Integer, default=0)
    form_home = Column(Float, default=0.5)
    form_away = Column(Float, default=0.5)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PerformanceSnapshot(Base):
    __tablename__ = "performance"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    roi = Column(Float, default=0.0)
    yield_pct = Column(Float, default=0.0)
    bets = Column(Integer, default=0)
    hit_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
