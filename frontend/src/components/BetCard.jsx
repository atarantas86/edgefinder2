import { useState } from "react";
import ConfidenceRing from "./ConfidenceRing.jsx";

const formatPercent = (value) => `${Number(value ?? 0).toFixed(1)}%`;
const formatOdds = (value) => Number(value ?? 0).toFixed(2);

export default function BetCard({ signal }) {
  const [expanded, setExpanded] = useState(false);
  const {
    match = "Match à venir",
    market = "Marché",
    league = "",
    kickoff = "",
    odds,
    edge,
    confidence,
    kelly,
    stake,
    xgHome,
    xgAway,
    formHome,
    formAway
  } = signal || {};

  return (
    <article className="rounded-2xl border border-white/5 bg-edge-card p-5 shadow-glow">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">{league}</p>
          <h3 className="text-lg font-semibold">{match}</h3>
          <p className="text-sm text-edge-muted">{market}</p>
          {kickoff && <p className="text-xs text-edge-muted">Kickoff: {kickoff}</p>}
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
          <p className="font-mono text-lg">{formatPercent(stake)}</p>
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
