"""FastAPI entrypoint for EdgeFinder."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import SessionLocal, init_db
from database.history import list_bets, list_performance, list_signals, record_bet
from database.models import Bet, ClosingLine, Match, Odds, Signal
from engine.analyzer import analyze_match
from engine.confidence import compute_confidence
from engine.backtest import BacktestConfig, LEAGUE_CODES, run_backtest
from engine.value_detector import detect_value_bets
from models.poisson import run_bivariate_poisson
from scheduler import create_scheduler, generate_signals, refresh_fixtures, refresh_odds, refresh_xg


app = FastAPI(title="EdgeFinder API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BetRequest(BaseModel):
    signal_id: int
    stake: float


OUTCOME_LABELS = {
    "home": "Domicile",
    "draw": "Nul",
    "away": "Extérieur",
    "over_25": "Plus de 2.5",
    "under_25": "Moins de 2.5",
    "btts_yes": "Les 2 marquent",
    "btts_no": "Les 2 ne marquent pas",
}


class SignalResponse(BaseModel):
    id: int
    match_id: int
    match: str
    market: str
    market_type: str
    league: str
    kickoff: str
    outcome: str
    probability: float
    odds: float
    edge: float
    kelly: float
    confidence: float
    capped: bool
    created_at: datetime


def _model_from_odds(odds: Dict[str, float]) -> Dict[str, float]:
    total_goals = 2.6
    implied = {key: 1 / value for key, value in odds.items() if value > 1}
    if implied:
        total_implied = sum(implied.values()) or 1.0
        normalized = {key: value / total_implied for key, value in implied.items()}
    else:
        normalized = {"home": 0.45, "draw": 0.25, "away": 0.30}
    home_share = normalized.get("home", 0.45) + 0.5 * normalized.get("draw", 0.25)
    home_xg = total_goals * home_share
    away_xg = total_goals * (1 - home_share)
    output = run_bivariate_poisson(home_xg, away_xg)
    return {
        "home_win": output.home_win,
        "draw": output.draw,
        "away_win": output.away_win,
        "over_25": output.over_25,
        "under_25": output.under_25,
        "expected_home_goals": output.expected_home_goals,
        "expected_away_goals": output.expected_away_goals,
    }


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    scheduler = create_scheduler()
    scheduler.start()


@app.get("/api/signals", response_model=List[SignalResponse])
def get_signals(db: Session = Depends(get_db)) -> List[SignalResponse]:
    signals = list_signals(db)
    enriched = []
    for s in signals:
        m = db.query(Match).filter(Match.id == s.match_id).first()
        edge_pct = round(s.edge * 100, 2)
        enriched.append(
            SignalResponse(
                id=s.id,
                match_id=s.match_id,
                match=f"{m.home_team} vs {m.away_team}" if m else "Match inconnu",
                market=OUTCOME_LABELS.get(s.outcome, s.outcome),
                market_type=getattr(s, "market_type", None) or "h2h",
                league=m.league if m else "",
                kickoff=m.kickoff if m else "",
                outcome=s.outcome,
                probability=s.probability,
                odds=s.odds,
                edge=edge_pct,
                kelly=round(s.kelly * 100, 2),
                confidence=s.confidence,
                capped=edge_pct >= 15.0,
                created_at=s.created_at,
            )
        )
    return enriched


@app.get("/api/match/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    odds_entries = db.query(Odds).filter(Odds.match_id == match_id).all()
    odds_by_market: Dict[str, Dict[str, float]] = {}
    for entry in odds_entries:
        odds_by_market.setdefault(entry.market, {})[entry.outcome] = entry.odds
    signals = db.query(Signal).filter(Signal.match_id == match_id).all()
    model_output = _model_from_odds(odds_by_market.get("h2h", {}))
    value_bets = detect_value_bets(model_output, odds_by_market.get("h2h", {}))
    confidence = compute_confidence(
        edge=max((bet["edge"] for bet in value_bets), default=0.0),
        convergence=0.7,
        volume=0.6,
        stability=0.65,
        inefficiency=0.5,
    )
    analysis = analyze_match(
        {
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": match.league,
            "kickoff": match.kickoff,
        },
        model_output,
        odds_by_market.get("h2h", {}),
        value_bets,
        confidence,
    )
    return {
        "match": match,
        "odds": odds_by_market,
        "signals": signals,
        "analysis": analysis,
    }


@app.get("/api/history")
def get_history(db: Session = Depends(get_db)) -> Dict[str, Any]:
    bets = list_bets(db)
    return {"bets": bets}


@app.post("/api/bet")
def place_bet(request: BetRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    signal = db.query(Signal).filter(Signal.id == request.signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    bet = record_bet(db, signal_id=signal.id, stake=request.stake)
    # Store opening odds from signal
    bet_obj = db.query(Bet).filter(Bet.id == bet.id).first()
    if bet_obj:
        bet_obj.opening_odds = signal.odds
        db.commit()
    return {"bet": bet}


class ClosingOddsRequest(BaseModel):
    closing_odds: float


@app.post("/api/bet/{bet_id}/closing")
def record_closing_odds(
    bet_id: int,
    request: ClosingOddsRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    bet = db.query(Bet).filter(Bet.id == bet_id).first()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    opening = bet.opening_odds or bet.signal.odds
    clv = (request.closing_odds - opening) / opening if opening > 0 else 0.0
    existing = db.query(ClosingLine).filter(ClosingLine.bet_id == bet_id).first()
    if existing:
        existing.closing_odds = request.closing_odds
        existing.clv = clv
        existing.recorded_at = datetime.utcnow()
    else:
        db.add(
            ClosingLine(
                bet_id=bet_id,
                opening_odds=opening,
                closing_odds=request.closing_odds,
                clv=clv,
            )
        )
    db.commit()
    return {"bet_id": bet_id, "opening_odds": opening, "closing_odds": request.closing_odds, "clv": round(clv * 100, 2)}


@app.get("/api/clv")
def get_clv_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    lines = db.query(ClosingLine).all()
    if not lines:
        return {"count": 0, "avg_clv": 0.0, "positive_rate": 0.0}
    clvs = [cl.clv for cl in lines]
    positive = sum(1 for c in clvs if c > 0)
    return {
        "count": len(clvs),
        "avg_clv": round(sum(clvs) / len(clvs) * 100, 2),
        "positive_rate": round(positive / len(clvs) * 100, 1),
    }


@app.post("/api/refresh")
def refresh_data() -> Dict[str, Any]:
    # 1) xG from Understat
    try:
        xg_updated = refresh_xg()
    except Exception as exc:
        logger.warning(f"xG refresh échoué: {exc}")
        xg_updated = 0
    # 2) Fixtures from API-Football
    try:
        fixtures_added = refresh_fixtures()
    except Exception as exc:
        logger.warning(f"API-Football échoué: {exc}")
        fixtures_added = 0
    if fixtures_added == 0:
        logger.info(
            "Fixtures API-Football: 0, utilisation Odds API comme source principale"
        )
    # 3) Odds from The Odds API
    odds_added = refresh_odds()
    # 4) Generate signals (Dixon-Coles + fallback)
    generate_signals()
    return {
        "xg_updated": xg_updated,
        "fixtures_added": fixtures_added,
        "odds_added": odds_added,
    }


@app.get("/api/performance")
def get_performance(db: Session = Depends(get_db)) -> Dict[str, Any]:
    performance = list_performance(db)
    bets = list_bets(db)
    total_stake = sum(bet.stake for bet in bets)
    total_profit = sum(bet.profit for bet in bets)
    roi = (total_profit / total_stake) * 100 if total_stake else 0.0
    return {"performance": performance, "roi": roi, "bets": len(bets)}


_BACKTEST_CACHE: Dict[str, Dict[str, Any]] = {}


@app.get("/api/backtest")
def get_backtest(
    seasons: str = "2021,2022,2023,2024,2025",
    leagues: str = "EPL,La Liga,Bundesliga,Serie A,Ligue 1",
    markets: str = "totals",
    blend: float = 0.50,
    edge: float = 0.07,
    split_mode: str = "cross_val",
    refresh: bool = False,
) -> Dict[str, Any]:
    season_list = [int(s.strip()) for s in seasons.split(",") if s.strip().isdigit()]
    league_list = [l.strip() for l in leagues.split(",") if l.strip()]
    market_list = tuple(m.strip() for m in markets.split(",") if m.strip())
    cache_key = (
        f"{','.join(map(str, season_list))}:{','.join(league_list)}:"
        f"{','.join(market_list)}:{blend}:{edge}:{split_mode}"
    )
    if not refresh and cache_key in _BACKTEST_CACHE:
        return _BACKTEST_CACHE[cache_key]
    config = BacktestConfig(
        seasons=season_list,
        leagues=league_list,
        markets=market_list,
        blend_model_weight=blend,
        edge_threshold=edge,
    )
    result = run_backtest(config=config, split_mode=split_mode)
    result["available_leagues"] = list(LEAGUE_CODES.keys())
    _BACKTEST_CACHE[cache_key] = result
    return result
