"""Quick backtest runner — parameter sweep to find profitable combo."""

import sys
import time

sys.path.insert(0, ".")

from engine.backtest import (
    BacktestConfig,
    load_matches,
    _simulate,
    _equity_curve,
    _calibration,
    _roi_by_group,
    _edge_distribution,
    _avg_clv,
)

LEAGUES_ALL = ["EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"]
SEASONS = [2021, 2022, 2023]

print("=" * 70, flush=True)
print("EDGEFINDER — PARAMETER SWEEP", flush=True)
print("=" * 70, flush=True)

t0 = time.time()
print("Loading data for 5 leagues x 3 seasons...", flush=True)
all_matches = load_matches(SEASONS, LEAGUES_ALL)
print(f"  -> {len(all_matches)} matches in {time.time()-t0:.1f}s\n", flush=True)

split_idx = int(len(all_matches) * 0.7)
train = all_matches[:split_idx]
test = all_matches[split_idx:]

# Sweep parameters
combos = [
    # (label, blend_model, edge_thresh, leagues_filter)
    ("A: blend50 edge5% 5ligs",   0.50, 0.05, None),
    ("B: blend40 edge5% 5ligs",   0.40, 0.05, None),
    ("C: blend50 edge7% 5ligs",   0.50, 0.07, None),
    ("D: blend40 edge7% 5ligs",   0.40, 0.07, None),
    ("E: blend40 edge10% 5ligs",  0.40, 0.10, None),
    ("F: blend50 edge7% EPL+SerA", 0.50, 0.07, {"EPL", "Serie_A"}),
    ("G: blend40 edge5% EPL+SerA", 0.40, 0.05, {"EPL", "Serie_A"}),
    ("H: blend40 edge7% EPL+SerA", 0.40, 0.07, {"EPL", "Serie_A"}),
    ("I: blend35 edge7% 5ligs",   0.35, 0.07, None),
    ("J: blend35 edge5% EPL+SerA", 0.35, 0.05, {"EPL", "Serie_A"}),
]

print(f"{'Combo':<30s} {'ROI':>7s} {'WinR':>6s} {'Sharpe':>7s} {'DD':>6s} {'Bets':>5s} {'Profit':>9s} {'BankEnd':>8s}", flush=True)
print("-" * 82, flush=True)

best_combo = None
best_roi = float("-inf")

for label, blend, edge, league_filter in combos:
    config = BacktestConfig(
        seasons=SEASONS,
        leagues=LEAGUES_ALL,
        markets=("totals",),
        blend_model_weight=blend,
        edge_threshold=edge,
    )
    # Simulate on test set
    test_bets, _ = _simulate(test, config)
    if league_filter:
        test_bets = [b for b in test_bets if b.league in league_filter]

    if not test_bets:
        print(f"{label:<30s} {'N/A':>7s}  (no bets)", flush=True)
        continue

    _, metrics = _equity_curve(test_bets, config, "quarter")

    roi = metrics["roi"]
    if roi > best_roi:
        best_roi = roi
        best_combo = (label, blend, edge, league_filter)

    print(
        f"{label:<30s} {roi:>+6.2f}% {metrics['win_rate']:>5.1f}% {metrics['sharpe']:>+6.2f} "
        f"{metrics['max_drawdown']:>5.1f}% {metrics['bets']:>5d} {metrics['profit']:>+8.2f} {metrics['ending_bankroll']:>8.2f}",
        flush=True,
    )

print("-" * 82, flush=True)
if best_combo:
    print(f"\nBEST: {best_combo[0]} (ROI {best_roi:+.2f}%)", flush=True)

# Detailed report for best combo
if best_combo:
    label, blend, edge, league_filter = best_combo
    config = BacktestConfig(
        seasons=SEASONS,
        leagues=LEAGUES_ALL,
        markets=("totals",),
        blend_model_weight=blend,
        edge_threshold=edge,
    )

    test_bets, test_preds = _simulate(test, config)
    if league_filter:
        test_bets = [b for b in test_bets if b.league in league_filter]
    train_bets, _ = _simulate(train, config)
    if league_filter:
        train_bets = [b for b in train_bets if b.league in league_filter]

    print("\n" + "=" * 70, flush=True)
    print(f"DETAILED RESULTS — {label}", flush=True)
    print(f"Blend: model {blend:.0%} / market {1-blend:.0%} | Edge >= {edge:.0%}", flush=True)
    if league_filter:
        print(f"Leagues: {league_filter}", flush=True)
    print("=" * 70, flush=True)

    for strat in ("quarter", "kelly", "flat"):
        eq, m = _equity_curve(test_bets, config, strat)
        name = {"quarter": "Kelly 1/4", "kelly": "Full Kelly", "flat": "Flat 1%"}[strat]
        print(f"\n--- {name} ---", flush=True)
        print(f"  ROI:          {m['roi']:+.2f}%", flush=True)
        print(f"  Win Rate:     {m['win_rate']:.1f}%", flush=True)
        print(f"  Sharpe:       {m['sharpe']:.2f}", flush=True)
        print(f"  Max Drawdown: {m['max_drawdown']:.1f}%", flush=True)
        print(f"  Bets:         {m['bets']}", flush=True)
        print(f"  Profit:       {m['profit']:+.2f}", flush=True)
        print(f"  Bankroll:     {m['ending_bankroll']:.2f}", flush=True)

    print(f"\n  Avg CLV:      {_avg_clv(test_bets):+.2f}%", flush=True)

    print("\n  ROI by League:", flush=True)
    for item in _roi_by_group(test_bets, "league"):
        print(f"    {item['label']:12s}  ROI: {item['roi']:+6.2f}%  ({item['bets']} bets)", flush=True)

    print("\n  Calibration (Totals):", flush=True)
    cal = _calibration(test_preds.get("totals", []))
    for c in cal:
        diff = c["observed"] - c["predicted"]
        print(f"    Bin {c['bin']:2d} | pred: {c['predicted']:.3f} | obs: {c['observed']:.3f} | n={c['count']:4d} | {'OK' if abs(diff)<0.03 else 'BIAS'}", flush=True)

    print("\n  Edge Distribution:", flush=True)
    for item in _edge_distribution(test_bets):
        bar = "#" * max(1, item["count"] // 2)
        print(f"    [{item['min']:.3f} - {item['max']:.3f}]  {item['count']:4d} bets  {bar}", flush=True)

    _, train_m = _equity_curve(train_bets, config, "quarter")
    print(f"\n  Train Check (Kelly 1/4): ROI {train_m['roi']:+.2f}%, WR {train_m['win_rate']:.1f}%, {train_m['bets']} bets, Sharpe {train_m['sharpe']:.2f}", flush=True)

print(f"\nTotal time: {time.time()-t0:.1f}s", flush=True)
