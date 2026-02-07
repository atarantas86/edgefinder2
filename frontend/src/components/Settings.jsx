import { useState } from "react";

const Slider = ({ label, value, min, max, step, unit, onChange }) => (
  <div className="rounded-xl border border-white/5 bg-edge-card p-4">
    <div className="flex items-center justify-between">
      <p className="text-xs uppercase tracking-[0.2em] text-edge-muted">{label}</p>
      <p className="font-mono text-sm text-white">
        {value}
        {unit}
      </p>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(event) => onChange(Number(event.target.value))}
      className="mt-3 w-full accent-edge-green"
    />
  </div>
);

export default function Settings({ bankroll, setBankroll }) {
  const [edgeMin, setEdgeMin] = useState(1);
  const [kelly, setKelly] = useState(40);

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-white/5 bg-edge-surface/80 p-6">
      <div>
        <h2 className="text-xl font-semibold">Paramètres</h2>
        <p className="text-sm text-edge-muted">Ajustez vos règles de staking.</p>
      </div>

      <Slider
        label="Bankroll"
        value={bankroll}
        min={500}
        max={10000}
        step={100}
        unit="€"
        onChange={setBankroll}
      />
      <Slider
        label="Edge minimum"
        value={edgeMin}
        min={1}
        max={10}
        step={0.5}
        unit="%"
        onChange={setEdgeMin}
      />
      <Slider
        label="Kelly fraction"
        value={kelly}
        min={10}
        max={100}
        step={5}
        unit="%"
        onChange={setKelly}
      />

      <div className="rounded-xl border border-edge-green/20 bg-edge-green/10 p-4 text-sm">
        <p className="font-semibold text-edge-green">Prévisualisation</p>
        <p className="mt-1 text-edge-muted">
          Bankroll: <span className="text-white">{bankroll}€</span> · Edge min: {edgeMin}% · Kelly:
          {kelly}%
        </p>
      </div>
    </section>
  );
}
