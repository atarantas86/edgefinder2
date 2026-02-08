"""Historical backtesting utilities for EdgeFinder."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import csv
import io

import httpx

from models.kelly import kelly_fraction
from models.poisson import run_bivariate_poisson


DATE_FORMATS = ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d")
TRAIN_SEASONS = (2021, 2022)
TEST_SEASONS = (2023,)


@dataclass(frozen=True)
class BacktestConfig:
    seasons: List[int]
    leagues: List[str]
    shrinkage_k: int = 50
    blend_model_weight: float = 0.50
    hfa: float = 1.07
    edge_threshold: float = 0.05
    min_matches: int = 5
    bankroll: float = 1000.0
    flat_stake_pct: float = 0.01
    kelly_cap: float = 0.15
    markets: Tuple[str, ...] = ("totals",)


@dataclass
class MatchRecord:
    date: datetime
    league: str
    home: str
    away: str
    home_goals: int
    away_goals: int
    odds_h: Optional[float]
    odds_d: Optional[float]
    odds_a: Optional[float]
    odds_over25: Optional[float]
    odds_under25: Optional[float]
    odds_btts_yes: Optional[float]
    odds_btts_no: Optional[float]
    avg_h: Optional[float]
    avg_d: Optional[float]
    avg_a: Optional[float]


@dataclass
class BetRecord:
    date: datetime
    league: str
    market: str
    outcome: str
    probability: float
    odds: float
    edge: float
    won: bool
    clv: float


LEAGUE_CODES: Dict[str, str] = {
    "EPL": "E0",
    "La Liga": "SP1",
    "Bundesliga": "D1",
    "Serie A": "I1",
    "Ligue 1": "F1",
    "Eredivisie": "N1",
    "Primeira Liga": "P1",
    "Championship": "E1",
    "Superliga": "DK1",
    "Allsvenskan": "S1",
}


MARKET_LABELS = {
    "home": "1",
    "draw": "X",
    "away": "2",
    "over_25": "O2.5",
    "under_25": "U2.5",
    "btts_yes": "BTTS Oui",
    "btts_no": "BTTS Non",
}


def _season_code(season_start: int) -> str:
    end_year = (season_start + 1) % 100
    start_year = season_start % 100
    return f"{start_year:02d}{end_year:02d}"


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _season_start(date: datetime) -> int:
    return date.year if date.month >= 7 else date.year - 1


def _float_or_none(value: str) -> Optional[float]:
    if value is None:
        return None
    value = str(value).strip()
    if value in {"", "NA", "N/A"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _get_odds(row: Dict[str, str], candidates: Iterable[str]) -> Optional[float]:
    for key in candidates:
        if key in row:
            value = _float_or_none(row.get(key))
            if value:
                return value
    return None


def _download_league_csv(season_start: int, league_code: str) -> List[MatchRecord]:
    season_code = _season_code(season_start)
    url = f"https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.text
    reader = csv.DictReader(io.StringIO(data))
    matches: List[MatchRecord] = []
    for row in reader:
        date = _parse_date(row.get("Date", ""))
        if not date:
            continue
        home = row.get("HomeTeam") or ""
        away = row.get("AwayTeam") or ""
        if not home or not away:
            continue
        home_goals = int(float(row.get("FTHG", 0) or 0))
        away_goals = int(float(row.get("FTAG", 0) or 0))
        odds_h = _get_odds(row, ["B365H", "BWH", "PSH", "AvgH"])
        odds_d = _get_odds(row, ["B365D", "BWD", "PSD", "AvgD"])
        odds_a = _get_odds(row, ["B365A", "BWA", "PSA", "AvgA"])
        odds_over25 = _get_odds(row, ["B365>2.5", "B365O25", "Avg>2.5", "AvgO25"])
        odds_under25 = _get_odds(row, ["B365<2.5", "B365U25", "Avg<2.5", "AvgU25"])
        odds_btts_yes = _get_odds(row, ["B365BTTSY", "B365Y", "AvgBTTSY", "AvgY"])
        odds_btts_no = _get_odds(row, ["B365BTTSN", "B365N", "AvgBTTSN", "AvgN"])
        avg_h = _get_odds(row, ["AvgH"])
        avg_d = _get_odds(row, ["AvgD"])
        avg_a = _get_odds(row, ["AvgA"])
        matches.append(
            MatchRecord(
                date=date,
                league=league_code,
                home=home,
                away=away,
                home_goals=home_goals,
                away_goals=away_goals,
                odds_h=odds_h,
                odds_d=odds_d,
                odds_a=odds_a,
                odds_over25=odds_over25,
                odds_under25=odds_under25,
                odds_btts_yes=odds_btts_yes,
                odds_btts_no=odds_btts_no,
                avg_h=avg_h,
                avg_d=avg_d,
                avg_a=avg_a,
            )
        )
    return matches


def load_matches(seasons: List[int], leagues: List[str]) -> List[MatchRecord]:
    matches: List[MatchRecord] = []
    for league in leagues:
        league_code = LEAGUE_CODES.get(league, league)
        for season in seasons:
            matches.extend(_download_league_csv(season, league_code))
    matches.sort(key=lambda m: m.date)
    return matches


class TeamTracker:
    def __init__(self) -> None:
        self.home_for = 0
        self.home_against = 0
        self.away_for = 0
        self.away_against = 0
        self.home_matches = 0
        self.away_matches = 0
        self.recent_points: List[int] = []

    def update(self, home_goals: int, away_goals: int, is_home: bool) -> None:
        if is_home:
            self.home_for += home_goals
            self.home_against += away_goals
            self.home_matches += 1
            points = 3 if home_goals > away_goals else 1 if home_goals == away_goals else 0
        else:
            self.away_for += away_goals
            self.away_against += home_goals
            self.away_matches += 1
            points = 3 if away_goals > home_goals else 1 if home_goals == away_goals else 0
        self.recent_points.insert(0, points)
        if len(self.recent_points) > 5:
            self.recent_points.pop()

    def form(self) -> float:
        if not self.recent_points:
            return 0.5
        return sum(self.recent_points) / (3 * len(self.recent_points))


@dataclass
class LeagueTracker:
    home_goals: int = 0
    away_goals: int = 0
    matches: int = 0

    @property
    def avg_home(self) -> float:
        return self.home_goals / self.matches if self.matches else 1.4

    @property
    def avg_away(self) -> float:
        return self.away_goals / self.matches if self.matches else 1.1

    @property
    def avg_total(self) -> float:
        return (self.avg_home + self.avg_away) / 2.0

    def update(self, home_goals: int, away_goals: int) -> None:
        self.home_goals += home_goals
        self.away_goals += away_goals
        self.matches += 1


def _shrink(team_avg: float, league_avg: float, n: int, k: int) -> float:
    return (n * team_avg + k * league_avg) / (n + k)


def _market_probs(odds: Dict[str, float]) -> Dict[str, float]:
    implied = {k: 1.0 / v for k, v in odds.items() if v and v > 1.0}
    total = sum(implied.values()) or 1.0
    return {k: v / total for k, v in implied.items()}


def _blend_prob(model_prob: float, market_prob: float, weight: float) -> float:
    return weight * model_prob + (1.0 - weight) * market_prob


def _expected_goals(
    home: TeamTracker,
    away: TeamTracker,
    league: LeagueTracker,
    k: int,
    hfa: float,
) -> Tuple[float, float, float, float]:
    avg_home = league.avg_home
    avg_away = league.avg_away
    avg_total = league.avg_total

    home_att = _shrink(
        home.home_for / home.home_matches if home.home_matches else avg_home,
        avg_home,
        home.home_matches,
        k,
    )
    home_def = _shrink(
        home.home_against / home.home_matches if home.home_matches else avg_away,
        avg_away,
        home.home_matches,
        k,
    )
    away_att = _shrink(
        away.away_for / away.away_matches if away.away_matches else avg_away,
        avg_away,
        away.away_matches,
        k,
    )
    away_def = _shrink(
        away.away_against / away.away_matches if away.away_matches else avg_home,
        avg_home,
        away.away_matches,
        k,
    )

    lambda_home = (home_att / avg_home) * (away_def / avg_home) * avg_total * hfa
    lambda_away = (away_att / avg_away) * (home_def / avg_away) * avg_total

    form_home = 1.0 + 0.10 * (home.form() - 0.5) / 0.5
    form_away = 1.0 + 0.10 * (away.form() - 0.5) / 0.5
    lambda_home *= form_home
    lambda_away *= form_away

    lambda_home = max(0.2, min(lambda_home, 5.0))
    lambda_away = max(0.2, min(lambda_away, 5.0))

    return lambda_home, lambda_away, avg_home, avg_away


def _match_outcomes(match: MatchRecord) -> Dict[str, bool]:
    home_goals = match.home_goals
    away_goals = match.away_goals
    return {
        "home": home_goals > away_goals,
        "draw": home_goals == away_goals,
        "away": away_goals > home_goals,
        "over_25": home_goals + away_goals > 2,
        "under_25": home_goals + away_goals <= 2,
        "btts_yes": home_goals > 0 and away_goals > 0,
        "btts_no": home_goals == 0 or away_goals == 0,
    }


def _simulate(
    matches: List[MatchRecord],
    config: BacktestConfig,
) -> Tuple[List[BetRecord], Dict[str, List[Tuple[float, int]]]]:
    teams: Dict[str, TeamTracker] = {}
    league_tracker: Dict[str, LeagueTracker] = {}
    bets: List[BetRecord] = []
    predictions: Dict[str, List[Tuple[float, int]]] = {"h2h": [], "totals": [], "btts": []}

    for match in matches:
        home_tracker = teams.setdefault(match.home, TeamTracker())
        away_tracker = teams.setdefault(match.away, TeamTracker())
        league = league_tracker.setdefault(match.league, LeagueTracker())

        outcomes = _match_outcomes(match)
        if (
            home_tracker.home_matches >= config.min_matches
            and away_tracker.away_matches >= config.min_matches
        ):
            lambda_home, lambda_away, _, _ = _expected_goals(
                home_tracker, away_tracker, league, config.shrinkage_k, config.hfa
            )
            model = run_bivariate_poisson(lambda_home, lambda_away)
            model_probs = {
                "home": model.home_win,
                "draw": model.draw,
                "away": model.away_win,
                "over_25": model.over_25,
                "under_25": model.under_25,
                "btts_yes": model.btts_yes,
                "btts_no": model.btts_no,
            }

            if "h2h" in config.markets and match.odds_h and match.odds_d and match.odds_a:
                market_probs = _market_probs(
                    {"home": match.odds_h, "draw": match.odds_d, "away": match.odds_a}
                )
                for key in ("home", "draw", "away"):
                    blended = _blend_prob(model_probs[key], market_probs.get(key, 0.0), config.blend_model_weight)
                    predictions["h2h"].append((blended, int(outcomes[key])))
                    odds_value = match.odds_h if key == "home" else match.odds_d if key == "draw" else match.odds_a
                    if odds_value > 15.0:
                        continue
                    edge_value = (odds_value * blended) - 1.0
                    if edge_value > config.edge_threshold:
                        clv_ref = match.avg_h if key == "home" else match.avg_d if key == "draw" else match.avg_a
                        clv = (clv_ref - odds_value) / odds_value if clv_ref else 0.0
                        bets.append(
                            BetRecord(
                                date=match.date,
                                league=match.league,
                                market="h2h",
                                outcome=key,
                                probability=blended,
                                odds=odds_value,
                                edge=edge_value,
                                won=outcomes[key],
                                clv=clv,
                            )
                        )

            if "totals" in config.markets and match.odds_over25 and match.odds_under25:
                market_probs = _market_probs(
                    {"over_25": match.odds_over25, "under_25": match.odds_under25}
                )
                for key in ("over_25", "under_25"):
                    blended = _blend_prob(model_probs[key], market_probs.get(key, 0.0), config.blend_model_weight)
                    predictions["totals"].append((blended, int(outcomes[key])))
                    odds_value = match.odds_over25 if key == "over_25" else match.odds_under25
                    if odds_value > 15.0:
                        continue
                    edge_value = (odds_value * blended) - 1.0
                    if edge_value > config.edge_threshold:
                        bets.append(
                            BetRecord(
                                date=match.date,
                                league=match.league,
                                market="totals",
                                outcome=key,
                                probability=blended,
                                odds=odds_value,
                                edge=edge_value,
                                won=outcomes[key],
                                clv=0.0,
                            )
                        )

            if "btts" in config.markets and match.odds_btts_yes and match.odds_btts_no:
                market_probs = _market_probs(
                    {"btts_yes": match.odds_btts_yes, "btts_no": match.odds_btts_no}
                )
                for key in ("btts_yes", "btts_no"):
                    blended = _blend_prob(model_probs[key], market_probs.get(key, 0.0), config.blend_model_weight)
                    predictions["btts"].append((blended, int(outcomes[key])))
                    odds_value = match.odds_btts_yes if key == "btts_yes" else match.odds_btts_no
                    if odds_value > 15.0:
                        continue
                    edge_value = (odds_value * blended) - 1.0
                    if edge_value > config.edge_threshold:
                        bets.append(
                            BetRecord(
                                date=match.date,
                                league=match.league,
                                market="btts",
                                outcome=key,
                                probability=blended,
                                odds=odds_value,
                                edge=edge_value,
                                won=outcomes[key],
                                clv=0.0,
                            )
                        )

        home_tracker.update(match.home_goals, match.away_goals, True)
        away_tracker.update(match.home_goals, match.away_goals, False)
        league.update(match.home_goals, match.away_goals)

    return bets, predictions


def _equity_curve(
    bets: List[BetRecord],
    config: BacktestConfig,
    strategy: str,
) -> Tuple[List[Tuple[str, float]], Dict[str, float]]:
    bankroll = config.bankroll
    equity: List[Tuple[str, float]] = [("start", bankroll)]
    total_profit = 0.0
    total_staked = 0.0
    returns: List[float] = []
    wins = 0
    for bet in bets:
        if strategy == "flat":
            stake = bankroll * config.flat_stake_pct
        else:
            fraction = 1.0 if strategy == "kelly" else 0.25
            stake_pct = kelly_fraction(bet.probability, bet.odds, fraction=fraction, cap=config.kelly_cap)
            stake = bankroll * stake_pct
        if stake <= 0.0:
            continue
        total_staked += stake
        if bet.won:
            profit = stake * (bet.odds - 1.0)
            wins += 1
        else:
            profit = -stake
        bankroll += profit
        total_profit += profit
        returns.append(profit / stake)
        equity.append((bet.date.strftime("%Y-%m-%d"), bankroll))

    roi = (total_profit / total_staked) * 100 if total_staked else 0.0
    hit_rate = (wins / len(returns)) * 100 if returns else 0.0
    sharpe = 0.0
    if len(returns) > 1:
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std = variance ** 0.5
        sharpe = (mean_ret / std) * (len(returns) ** 0.5) if std else 0.0

    max_drawdown = 0.0
    peak = equity[0][1]
    for _, value in equity:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    metrics = {
        "roi": round(roi, 2),
        "profit": round(total_profit, 2),
        "staked": round(total_staked, 2),
        "win_rate": round(hit_rate, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "bets": len(returns),
        "ending_bankroll": round(bankroll, 2),
    }
    return equity, metrics


def _calibration(predictions: List[Tuple[float, int]], bins: int = 10) -> List[Dict[str, float]]:
    if not predictions:
        return []
    bucketed: List[List[int]] = [[] for _ in range(bins)]
    bucketed_probs: List[List[float]] = [[] for _ in range(bins)]
    for prob, outcome in predictions:
        idx = min(bins - 1, max(0, int(prob * bins)))
        bucketed[idx].append(outcome)
        bucketed_probs[idx].append(prob)
    result = []
    for idx in range(bins):
        if not bucketed[idx]:
            continue
        avg_prob = sum(bucketed_probs[idx]) / len(bucketed_probs[idx])
        observed = sum(bucketed[idx]) / len(bucketed[idx])
        result.append(
            {
                "bin": idx,
                "predicted": round(avg_prob, 3),
                "observed": round(observed, 3),
                "count": len(bucketed[idx]),
            }
        )
    return result


def _roi_by_group(bets: List[BetRecord], key: str) -> List[Dict[str, float]]:
    aggregates: Dict[str, List[float]] = {}
    for bet in bets:
        label = bet.league if key == "league" else bet.market
        profit = (bet.odds - 1.0) if bet.won else -1.0
        aggregates.setdefault(label, []).append(profit)
    result = []
    for label, profits in aggregates.items():
        roi = (sum(profits) / len(profits)) * 100 if profits else 0.0
        result.append({"label": label, "roi": round(roi, 2), "bets": len(profits)})
    result.sort(key=lambda item: item["roi"], reverse=True)
    return result


def _edge_distribution(bets: List[BetRecord], bins: int = 8) -> List[Dict[str, float]]:
    if not bets:
        return []
    edges = [bet.edge for bet in bets]
    min_edge, max_edge = min(edges), max(edges)
    if min_edge == max_edge:
        return [{"min": round(min_edge, 3), "max": round(max_edge, 3), "count": len(edges)}]
    step = (max_edge - min_edge) / bins
    buckets = [0 for _ in range(bins)]
    for edge in edges:
        idx = min(bins - 1, int((edge - min_edge) / step))
        buckets[idx] += 1
    distribution = []
    for i, count in enumerate(buckets):
        distribution.append(
            {
                "min": round(min_edge + step * i, 3),
                "max": round(min_edge + step * (i + 1), 3),
                "count": count,
            }
        )
    return distribution


def _avg_clv(bets: List[BetRecord]) -> float:
    clvs = [bet.clv for bet in bets if bet.clv]
    if not clvs:
        return 0.0
    return round(sum(clvs) / len(clvs) * 100, 2)


def run_backtest(config: BacktestConfig) -> Dict[str, object]:
    matches = load_matches(config.seasons, config.leagues)
    if not matches:
        return {"error": "No historical data found"}

    train_seasons = [season for season in config.seasons if season in TRAIN_SEASONS]
    test_seasons = [season for season in config.seasons if season in TEST_SEASONS]

    train_matches = [match for match in matches if _season_start(match.date) in train_seasons]
    test_matches = [match for match in matches if _season_start(match.date) in test_seasons]
    if not train_matches or not test_matches:
        split_idx = int(len(matches) * 0.7)
        train_matches = matches[:split_idx]
        test_matches = matches[split_idx:]

    grid_k = [30, 50, 70]
    grid_blend = [0.45, 0.50, 0.55]
    grid_hfa = [1.05, 1.08, 1.11]
    grid_edge = [0.05, 0.07, 0.10]

    best_params = {
        "shrinkage_k": config.shrinkage_k,
        "blend_model_weight": config.blend_model_weight,
        "hfa": config.hfa,
        "edge_threshold": config.edge_threshold,
    }
    best_roi = float("-inf")

    # Optimized: simulate once per (k, blend, hfa) with edge=0,
    # then filter bets by each edge threshold (avoids redundant Poisson runs).
    for k in grid_k:
        for blend in grid_blend:
            for hfa in grid_hfa:
                trial_base = BacktestConfig(
                    seasons=config.seasons,
                    leagues=config.leagues,
                    shrinkage_k=k,
                    blend_model_weight=blend,
                    hfa=hfa,
                    edge_threshold=0.0,
                    min_matches=config.min_matches,
                    bankroll=config.bankroll,
                    flat_stake_pct=config.flat_stake_pct,
                    kelly_cap=config.kelly_cap,
                    markets=config.markets,
                )
                all_bets, _ = _simulate(train_matches, trial_base)
                for edge in grid_edge:
                    filtered = [b for b in all_bets if b.edge > edge]
                    trial_for_equity = BacktestConfig(
                        seasons=config.seasons,
                        leagues=config.leagues,
                        shrinkage_k=k,
                        blend_model_weight=blend,
                        hfa=hfa,
                        edge_threshold=edge,
                        min_matches=config.min_matches,
                        bankroll=config.bankroll,
                        flat_stake_pct=config.flat_stake_pct,
                        kelly_cap=config.kelly_cap,
                        markets=config.markets,
                    )
                    equity, metrics = _equity_curve(filtered, trial_for_equity, "quarter")
                    if metrics["bets"] < 30:
                        continue
                    if metrics["roi"] > best_roi:
                        best_roi = metrics["roi"]
                        best_params = {
                            "shrinkage_k": k,
                            "blend_model_weight": blend,
                            "hfa": hfa,
                            "edge_threshold": edge,
                        }

    optimized = BacktestConfig(
        seasons=config.seasons,
        leagues=config.leagues,
        shrinkage_k=best_params["shrinkage_k"],
        blend_model_weight=best_params["blend_model_weight"],
        hfa=best_params["hfa"],
        edge_threshold=best_params["edge_threshold"],
        min_matches=config.min_matches,
        bankroll=config.bankroll,
        flat_stake_pct=config.flat_stake_pct,
        kelly_cap=config.kelly_cap,
        markets=config.markets,
    )

    train_bets, train_predictions = _simulate(train_matches, optimized)
    test_bets, test_predictions = _simulate(test_matches, optimized)

    train_equity, train_metrics = _equity_curve(train_bets, optimized, "quarter")

    strategies = {}
    equity_curves = {}
    for strategy in ("kelly", "quarter", "flat"):
        equity, metrics = _equity_curve(test_bets, optimized, strategy)
        label = "kelly" if strategy == "kelly" else "quarter_kelly" if strategy == "quarter" else "flat"
        strategies[label] = metrics
        equity_curves[label] = equity

    calibration = {
        "h2h": _calibration(test_predictions["h2h"]),
        "totals": _calibration(test_predictions["totals"]),
        "btts": _calibration(test_predictions["btts"]),
    }

    result = {
        "summary": {
            "matches": len(matches),
            "train": train_metrics,
            "test": strategies.get("quarter_kelly", {}),
            "avg_clv": _avg_clv(test_bets),
            "best_params": best_params,
            "split": {"train_seasons": train_seasons, "test_seasons": test_seasons},
        },
        "strategies": strategies,
        "equity_curves": equity_curves,
        "calibration": calibration,
        "edge_distribution": _edge_distribution(test_bets),
        "roi_by_league": _roi_by_group(test_bets, "league"),
        "roi_by_market": _roi_by_group(test_bets, "market"),
        "bets": len(test_bets),
        "generated_at": datetime.utcnow().isoformat(),
        "market_labels": MARKET_LABELS,
    }
    return result
