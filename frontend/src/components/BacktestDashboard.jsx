import useApi from "../hooks/useApi.js";

const formatPct = (value, digits = 1) => `${Number(value ?? 0).toFixed(digits)}%`;

const LineChart = ({ points = [] }) => {
  if (!points.length) {
    return <div className="text-xs text-edge-muted">Aucune donnée disponible.</div>;
  }
  const values = points.map((point) => point[1]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = 100 / Math.max(points.length - 1, 1);
  const path = points
    .map((point, index) => {
      const x = index * step;
      const y = 100 - ((point[1] - min) / range) * 100;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 100" className="h-32 w-full">
      <path d={path} fill="none" stroke="#35f39f" strokeWidth="2" />
      <line x1="0" y1="100" x2="100" y2="100" stroke="#1f2937" strokeWidth="1" />
    </svg>
  );
};

const BarChart = ({ data = [] }) => {
  if (!data.length) {
    return <div className="text-xs text-edge-muted">Aucune donnée disponible.</div>;
  }
  const max = Math.max(...data.map((item) => item.count));
  return (
    <div className="flex items-end gap-2">
      {data.map((item, index) => {
        const height = max ? (item.count / max) * 100 : 0;
        return (
          <div key={index} className="flex w-6 flex-col items-center gap-2">
            <div
              className="w-4 rounded-t-lg bg-edge-green"
              style={{ height: `${height}%` }}
            />
            <span className="text-[10px] text-edge-muted">{item.count}</span>
          </div>
        );
      })}
    </div>
  );
};

const CalibrationChart = ({ data = [] }) => {
  if (!data.length) {
    return <div className="text-xs text-edge-muted">Aucune donnée disponible.</div>;
  }
  return (
    <svg viewBox="0 0 100 100" className="h-32 w-full">
      <line x1="0" y1="100" x2="100" y2="0" stroke="#1f2937" strokeWidth="1" />
      {data.map((point) => {
        const x = point.predicted * 100;
        const y = 100 - point.observed * 100;
        return (
          <circle key={point.bin} cx={x} cy={y} r="3" fill="#35f39f" />
        );
      })}
    </svg>
  );
};

export default function BacktestDashboard() {
  const { data, loading, error, refetch } = useApi("/api/backtest");

  const summary = data?.summary ?? {};
  const strategies = data?.strategies ?? {};
  const equity = data?.equity_curves?.quarter_kelly ?? [];
  const edgeDistribution = data?.edge_distribution ?? [];
  const calibration = data?.calibration ?? {};
  const roiByLeague = data?.roi_by_league ?? [];
  const roiByMarket = data?.roi_by_market ?? [];
  const params = summary?.best_params ?? {};

  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Backtest historique</h2>
          <p className="text-sm text-edge-muted">
            Analyse sur {summary?.matches ?? 0} matchs, optimisation 2021-2022 & validation 2023.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-full border border-edge-green/40 px-4 py-2 text-xs text-edge-green hover:bg-edge-green/10"
        >
          Relancer
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-edge-red/40 bg-edge-red/10 p-4 text-sm text-edge-red">
          Impossible de charger le backtest: {error}
        </div>
      )}

      {loading && (
        <div className="rounded-2xl border border-white/5 bg-edge-card p-6 text-sm text-edge-muted">
          Backtest en cours, cela peut prendre quelques instants...
        </div>
      )}

      {!loading && data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-2xl border border-white/5 bg-edge-surface/80 p-4 shadow-glow">
              <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">ROI train</p>
              <p className="mt-2 text-2xl font-semibold text-white">{formatPct(summary?.train?.roi, 2)}</p>
              <p className="text-xs text-edge-muted">Saisons {summary?.split?.train_seasons?.join(", ") || "-"}</p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-edge-surface/80 p-4 shadow-glow">
              <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">ROI test</p>
              <p className="mt-2 text-2xl font-semibold text-white">{formatPct(summary?.test?.roi, 2)}</p>
              <p className="text-xs text-edge-muted">Quarter Kelly · {summary?.split?.test_seasons?.join(", ") || "-"}</p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-edge-surface/80 p-4 shadow-glow">
              <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">Max drawdown</p>
              <p className="mt-2 text-2xl font-semibold text-white">{formatPct(summary?.test?.max_drawdown, 2)}</p>
              <p className="text-xs text-edge-muted">Risque historique</p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-edge-surface/80 p-4 shadow-glow">
              <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">Sharpe</p>
              <p className="mt-2 text-2xl font-semibold text-white">{Number(summary?.test?.sharpe ?? 0).toFixed(2)}</p>
              <p className="text-xs text-edge-muted">Ratio rendement / risque</p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-edge-surface/80 p-4 shadow-glow">
              <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">CLV moyen</p>
              <p className="mt-2 text-2xl font-semibold text-white">{formatPct(summary?.avg_clv, 2)}</p>
              <p className="text-xs text-edge-muted">Vs moyenne marché</p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-edge-surface/80 p-4 shadow-glow">
              <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">Bets test</p>
              <p className="mt-2 text-2xl font-semibold text-white">{summary?.test?.bets ?? 0}</p>
              <p className="text-xs text-edge-muted">Échantillon out-of-sample</p>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
            <div className="rounded-2xl border border-white/5 bg-edge-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">Equity curve</h3>
                  <p className="text-xs text-edge-muted">Quarter Kelly (test)</p>
                </div>
                <span className="rounded-full border border-edge-green/30 bg-edge-green/10 px-3 py-1 text-xs text-edge-green">
                  {summary?.test?.bets ?? 0} paris
                </span>
              </div>
              <LineChart points={equity} />
            </div>

            <div className="rounded-2xl border border-white/5 bg-edge-card p-6">
              <h3 className="text-lg font-semibold">Paramètres optimisés</h3>
              <ul className="mt-4 space-y-2 text-sm text-edge-muted">
                <li>Shrinkage K: <span className="text-white">{params?.shrinkage_k ?? "-"}</span></li>
                <li>Blend modèle: <span className="text-white">{formatPct((params?.blend_model_weight ?? 0) * 100, 0)}</span></li>
                <li>Home field adv: <span className="text-white">{Number(params?.hfa ?? 0).toFixed(2)}</span></li>
                <li>Seuil edge: <span className="text-white">{formatPct((params?.edge_threshold ?? 0) * 100, 2)}</span></li>
              </ul>
              <div className="mt-4 space-y-2 text-xs text-edge-muted">
                <p>Kelly: ROI {formatPct(strategies?.kelly?.roi, 2)} / Drawdown {formatPct(strategies?.kelly?.max_drawdown, 2)}</p>
                <p>Quarter Kelly: ROI {formatPct(strategies?.quarter_kelly?.roi, 2)} / Drawdown {formatPct(strategies?.quarter_kelly?.max_drawdown, 2)}</p>
                <p>Flat: ROI {formatPct(strategies?.flat?.roi, 2)} / Drawdown {formatPct(strategies?.flat?.max_drawdown, 2)}</p>
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="rounded-2xl border border-white/5 bg-edge-card p-6">
              <h3 className="text-lg font-semibold">Distribution des edges</h3>
              <BarChart data={edgeDistribution} />
            </div>
            <div className="rounded-2xl border border-white/5 bg-edge-card p-6">
              <h3 className="text-lg font-semibold">Calibration 1X2</h3>
              <CalibrationChart data={calibration?.h2h ?? []} />
            </div>
            <div className="rounded-2xl border border-white/5 bg-edge-card p-6">
              <h3 className="text-lg font-semibold">Calibration Totaux</h3>
              <CalibrationChart data={calibration?.totals ?? []} />
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-white/5 bg-edge-card p-6">
              <h3 className="text-lg font-semibold">ROI par ligue</h3>
              <div className="mt-4 space-y-3">
                {roiByLeague.map((item) => (
                  <div key={item.label} className="flex items-center justify-between text-sm">
                    <span className="text-edge-muted">{item.label}</span>
                    <span className="text-white">{formatPct(item.roi, 2)} ({item.bets} bets)</span>
                  </div>
                ))}
                {!roiByLeague.length && <p className="text-xs text-edge-muted">Aucune donnée.</p>}
              </div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-edge-card p-6">
              <h3 className="text-lg font-semibold">ROI par marché</h3>
              <div className="mt-4 space-y-3">
                {roiByMarket.map((item) => (
                  <div key={item.label} className="flex items-center justify-between text-sm">
                    <span className="text-edge-muted">{item.label}</span>
                    <span className="text-white">{formatPct(item.roi, 2)} ({item.bets} bets)</span>
                  </div>
                ))}
                {!roiByMarket.length && <p className="text-xs text-edge-muted">Aucune donnée.</p>}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
