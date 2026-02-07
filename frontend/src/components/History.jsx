import useApi from "../hooks/useApi.js";

const formatPercent = (value) => `${Number(value ?? 0).toFixed(1)}%`;
const formatOdds = (value) => Number(value ?? 0).toFixed(2);

export default function History() {
  const { data: historyData, loading, error } = useApi("/api/history");
  const { data: performanceData } = useApi("/api/performance");
  const history = historyData?.history ?? historyData ?? [];

  const stats = [
    { label: "ROI", value: formatPercent(performanceData?.roi) },
    { label: "Yield", value: formatPercent(performanceData?.yield) },
    { label: "Win rate", value: formatPercent(performanceData?.winRate) }
  ];

  return (
    <section className="rounded-2xl border border-white/5 bg-edge-surface/80 p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Historique des paris</h2>
          <p className="text-sm text-edge-muted">Suivi des paris clôturés.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {stats.map((stat) => (
            <div key={stat.label} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
              <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">{stat.label}</p>
              <p className="text-sm font-semibold text-white">{stat.value}</p>
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-edge-red/40 bg-edge-red/10 p-4 text-sm text-edge-red">
          Impossible de charger l'historique: {error}
        </div>
      )}

      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-[0.2em] text-edge-muted">
            <tr>
              <th className="pb-3 pr-4">Match</th>
              <th className="pb-3 pr-4">Market</th>
              <th className="pb-3 pr-4">Cote</th>
              <th className="pb-3 pr-4">Résultat</th>
              <th className="pb-3 pr-4">P/L</th>
              <th className="pb-3">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {loading && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-edge-muted">
                  Chargement des données...
                </td>
              </tr>
            )}
            {!loading && Array.isArray(history) && history.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-edge-muted">
                  Aucun pari clôturé pour l'instant.
                </td>
              </tr>
            )}
            {!loading &&
              Array.isArray(history) &&
              history.map((item) => (
                <tr key={item?.id ?? `${item?.match}-${item?.date}`}>
                  <td className="py-4 pr-4 font-medium text-white">{item?.match ?? "—"}</td>
                  <td className="py-4 pr-4 text-edge-muted">{item?.market ?? "—"}</td>
                  <td className="py-4 pr-4 font-mono text-white">{formatOdds(item?.odds)}</td>
                  <td className="py-4 pr-4">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
                        item?.result === "win"
                          ? "bg-edge-green/15 text-edge-green"
                          : item?.result === "loss"
                            ? "bg-edge-red/15 text-edge-red"
                            : "bg-edge-orange/15 text-edge-orange"
                      }`}
                    >
                      {item?.result ?? "pending"}
                    </span>
                  </td>
                  <td className="py-4 pr-4 font-mono text-white">
                    {formatPercent(item?.profit)}
                  </td>
                  <td className="py-4 text-edge-muted">{item?.date ?? "—"}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
