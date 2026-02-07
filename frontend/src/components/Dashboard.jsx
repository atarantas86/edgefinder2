import { useState, useMemo } from "react";
import BetCard from "./BetCard.jsx";
import useApi from "../hooks/useApi.js";

const getAverage = (items, key) => {
  if (!Array.isArray(items) || items.length === 0) return 0;
  const total = items.reduce((acc, item) => acc + Number(item?.[key] ?? 0), 0);
  return total / items.length;
};

export default function Dashboard({ bankroll = 2500 }) {
  const [leagueFilter, setLeagueFilter] = useState("all");
  const {
    data: signalsData,
    loading: signalsLoading,
    error: signalsError
  } = useApi("/api/signals");
  const { data: performanceData } = useApi("/api/performance");

  const signals = signalsData?.signals ?? signalsData ?? [];

  // Extract unique leagues for filter
  const leagues = useMemo(() => {
    if (!Array.isArray(signals)) return [];
    const set = new Set(signals.map((s) => s?.league).filter(Boolean));
    return [...set].sort();
  }, [signals]);

  // Filter by league then sort: FIABLE first, then by edge desc
  const sorted = useMemo(() => {
    if (!Array.isArray(signals)) return [];
    let filtered = signals;
    if (leagueFilter !== "all") {
      filtered = signals.filter((s) => s?.league === leagueFilter);
    }
    return [...filtered].sort((a, b) => {
      const aFiable = Number(a?.edge ?? 0) < 8 ? 0 : 1;
      const bFiable = Number(b?.edge ?? 0) < 8 ? 0 : 1;
      if (aFiable !== bFiable) return aFiable - bFiable;
      return Number(b?.edge ?? 0) - Number(a?.edge ?? 0);
    });
  }, [signals, leagueFilter]);

  const totalSignals = Array.isArray(sorted) ? sorted.length : 0;
  const avgEdge = getAverage(sorted, "edge");
  const avgConfidence = getAverage(sorted, "confidence");

  const summaryCards = [
    {
      title: "Signaux du jour",
      value: totalSignals,
      sub: "Opportunités détectées"
    },
    {
      title: "Edge moyen",
      value: `${avgEdge.toFixed(1)}%`,
      sub: "Sur la sélection"
    },
    {
      title: "Confiance",
      value: `${avgConfidence.toFixed(0)}%`,
      sub: "Confiance moyenne"
    }
  ];

  return (
    <section className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-3">
        {summaryCards.map((card) => (
          <div
            key={card.title}
            className="rounded-2xl border border-white/5 bg-edge-surface/80 p-4 shadow-glow"
          >
            <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">{card.title}</p>
            <p className="mt-2 text-2xl font-semibold text-white">{card.value}</p>
            <p className="text-xs text-edge-muted">{card.sub}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Signaux live</h2>
          <p className="text-sm text-edge-muted">
            {performanceData?.label ?? "Performances calculées en temps réel"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={leagueFilter}
            onChange={(e) => setLeagueFilter(e.target.value)}
            className="rounded-lg border border-white/10 bg-edge-surface px-3 py-1.5 text-xs text-white focus:border-edge-green/50 focus:outline-none"
          >
            <option value="all">Toutes les ligues</option>
            {leagues.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
          <span className="rounded-full border border-edge-green/30 bg-edge-green/10 px-3 py-1 text-xs text-edge-green">
            {signalsLoading ? "Synchronisation..." : "À jour"}
          </span>
        </div>
      </div>

      {signalsError && (
        <div className="rounded-xl border border-edge-red/40 bg-edge-red/10 p-4 text-sm text-edge-red">
          Impossible de charger les signaux: {signalsError}
        </div>
      )}

      <div className="grid gap-6">
        {signalsLoading && (
          <div className="rounded-2xl border border-white/5 bg-edge-card p-6 text-sm text-edge-muted">
            Chargement des signaux en cours...
          </div>
        )}
        {!signalsLoading && totalSignals === 0 && (
          <div className="rounded-2xl border border-white/5 bg-edge-card p-6 text-sm text-edge-muted">
            Aucun signal disponible pour le moment.
          </div>
        )}
        {!signalsLoading &&
          Array.isArray(sorted) &&
          sorted.map((signal) => <BetCard key={signal?.id ?? signal?.match} signal={signal} bankroll={bankroll} />)}
      </div>
    </section>
  );
}
