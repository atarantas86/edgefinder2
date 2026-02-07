export default function ConfidenceRing({ value = 0 }) {
  const size = 56;
  const stroke = 6;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const normalized = Math.min(Math.max(value, 0), 100);
  const offset = circumference - (normalized / 100) * circumference;

  return (
    <div className="relative flex h-14 w-14 items-center justify-center">
      <svg height={size} width={size} className="-rotate-90">
        <circle
          stroke="rgba(255,255,255,0.08)"
          fill="transparent"
          strokeWidth={stroke}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          stroke="currentColor"
          fill="transparent"
          strokeWidth={stroke}
          strokeLinecap="round"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={offset}
          className="text-edge-green transition-all duration-500"
        />
      </svg>
      <span className="absolute text-xs font-semibold text-white">{normalized}%</span>
    </div>
  );
}
