import { useState } from "react";
import ConfidenceRing from "./ConfidenceRing.jsx";

const formatPercent = (value) => `${Number(value ?? 0).toFixed(1)}%`;
const formatOdds = (value) => Number(value ?? 0).toFixed(2);

const LEAGUE_FLAGS = {
  "Premier League": "EN",
  "La Liga": "ES",
  "Bundesliga": "DE",
  "Serie A": "IT",
  "Ligue 1": "FR",
};

const MARKET_COLORS = {
  h2h: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  totals: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  btts: "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

const MARKET_LABELS = {
  h2h: "1X2",
  totals: "O/U",
  btts: "BTTS",
};

export default function BetCard({ signal, bankroll = 2500 }) {
  const [expanded, setExpanded] = useState(false);
  const {
    match = "Match à venir",
    market = "Marché",
    market_type = "h2h",
    league = "",
    kickoff = "",
    odds,
    edge,
    confidence,
    kelly,
    capped,
    xgHome,
    xgAway,
    formHome,
    formAway
  } = signal || {};

  const isFiable = Number(edge ?? 0) < 8;
  const flag = LEAGUE_FLAGS[league] || "";
  const marketColor = MARKET_COLORS[market_type] || MARKET_COLORS.h2h;
  const marketLabel = MARKET_LABELS[market_type] || market_type;

  return (
    <article className="rounded-2xl border border-white/5 bg-edge-card p-5 shadow-glow">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="mb-1 flex flex-wrap items-center gap-2">
            {flag && (
              <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-edge-muted">
                {flag}
              </span>
            )}
            <span className="text-xs uppercase tracking-[0.2em] text-edge-muted">{league}</span>
          </div>
          <h3 className="text-lg font-semibold">{match}</h3>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${marketColor}`}>
              {marketLabel}
            </span>
            <span className="text-sm text-edge-muted">{market}</span>
            {isFiable ? (
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-400">
                Fiable
              </span>
            ) : (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-400">
                Spéculatif
              </span>
            )}
            {capped && (
              <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-red-400">
                Capped
              </span>
            )}
          </div>
          {kickoff && <p className="mt-1 text-xs text-edge-muted">Kickoff: {kickoff}</p>}
        </div>
        <div className="flex items-center gap-4">
          <ConfidenceRing value={confidence ?? 0} />
          <div className="text-right">
            <p className="text-xs text-edge-muted">Edge</p>
            <p className="text-lg font-semibold text-edge-green">{formatPercent(edge)}</p>
            <p className="text-xs text-edge-muted">Mise Kelly</p>
            <p className="text-sm font-semibold text-white">{formatPercent(kelly)}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 rounded-xl border border-white/5 bg-edge-surface/70 p-4 text-sm sm:grid-cols-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">Cote</p>
          <p className="font-mono text-lg">{formatOdds(odds)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">Stake</p>
          <p className="font-mono text-lg">{(bankroll * (Number(kelly ?? 0) / 100)).toFixed(0)}€</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">Confiance</p>
          <p className="font-mono text-lg">{formatPercent(confidence)}</p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="mt-4 flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-edge-muted transition hover:border-edge-green/40 hover:text-white"
      >
        Détails avancés
        <span className="text-edge-green">{expanded ? "−" : "+"}</span>
      </button>

      {expanded && (
        <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div className="rounded-xl border border-white/5 bg-edge-surface/60 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">xG</p>
            <p className="mt-2 flex items-center justify-between font-mono">
              <span>Domicile</span>
              <span className="text-edge-green">{Number(xgHome ?? 0).toFixed(2)}</span>
            </p>
            <p className="mt-1 flex items-center justify-between font-mono">
              <span>Extérieur</span>
              <span className="text-edge-orange">{Number(xgAway ?? 0).toFixed(2)}</span>
            </p>
          </div>
          <div className="rounded-xl border border-white/5 bg-edge-surface/60 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">Forme récente</p>
            <p className="mt-2 flex items-center justify-between font-mono">
              <span>Domicile</span>
              <span className="text-edge-green">{formHome ?? "—"}</span>
            </p>
            <p className="mt-1 flex items-center justify-between font-mono">
              <span>Extérieur</span>
              <span className="text-edge-orange">{formAway ?? "—"}</span>
            </p>
          </div>
        </div>
      )}
    </article>
  );
}
