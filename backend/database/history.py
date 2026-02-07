"""Database helpers for history and performance."""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from database.models import Bet, PerformanceSnapshot, Signal


def record_signal(session: Session, signal_data: Dict[str, float]) -> Signal:
    signal = Signal(**signal_data)
    session.add(signal)
    session.commit()
    session.refresh(signal)
    return signal


def record_bet(session: Session, signal_id: int, stake: float) -> Bet:
    bet = Bet(signal_id=signal_id, stake=stake)
    session.add(bet)
    session.commit()
    session.refresh(bet)
    return bet


def list_bets(session: Session) -> List[Bet]:
    return session.query(Bet).order_by(Bet.placed_at.desc()).all()


def list_signals(session: Session) -> List[Signal]:
    return session.query(Signal).order_by(Signal.created_at.desc()).all()


def record_performance(session: Session, snapshot: Dict[str, float]) -> PerformanceSnapshot:
    performance = PerformanceSnapshot(**snapshot)
    session.add(performance)
    session.commit()
    session.refresh(performance)
    return performance


def list_performance(session: Session) -> List[PerformanceSnapshot]:
    return session.query(PerformanceSnapshot).order_by(PerformanceSnapshot.date.desc()).all()
