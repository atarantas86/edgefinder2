import BetCard from "./BetCard.jsx";
import useApi from "../hooks/useApi.js";

const getAverage = (items, key) => {
  if (!Array.isArray(items) || items.length === 0) return 0;
  const total = items.reduce((acc, item) => acc + Number(item?.[key] ?? 0), 0);
  return total / items.length;
};

export default function Dashboard() {
  const {
    data: signalsData,
    loading: signalsLoading,
    error: signalsError
  } = useApi("/api/signals");
  const { data: performanceData } = useApi("/api/performance");

  const signals = signalsData?.signals ?? signalsData ?? [];
  const totalSignals = Array.isArray(signals) ? signals.length : 0;
  const avgEdge = getAverage(signals, "edge");
  const avgConfidence = getAverage(signals, "confidence");

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
        <span className="rounded-full border border-edge-green/30 bg-edge-green/10 px-3 py-1 text-xs text-edge-green">
          {signalsLoading ? "Synchronisation..." : "À jour"}
        </span>
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
          Array.isArray(signals) &&
          signals.map((signal) => <BetCard key={signal?.id ?? signal?.match} signal={signal} />)}
      </div>
    </section>
  );
}
