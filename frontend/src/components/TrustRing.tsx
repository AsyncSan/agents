/**
 * SVG ring visualization for trust scores.
 * Color-coded: red (<0.4), amber (0.4-0.7), green (>0.7).
 */

interface TrustRingProps {
  score: number | null;
  size?: number;
}

export function TrustRing({ score, size = 36 }: TrustRingProps) {
  if (score === null || score === undefined) {
    return (
      <div
        className="flex items-center justify-center text-[10px] text-[#64748b]"
        style={{ width: size, height: size }}
      >
        N/A
      </div>
    );
  }

  const pct = Math.round(score * 100);
  const radius = (size - 4) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score);
  const center = size / 2;

  // Color based on score
  const color =
    score >= 0.7
      ? "#34d399" // emerald-400
      : score >= 0.4
        ? "#fbbf24" // amber-400
        : "#f87171"; // red-400

  const bgColor =
    score >= 0.7
      ? "rgba(52, 211, 153, 0.1)"
      : score >= 0.4
        ? "rgba(251, 191, 36, 0.1)"
        : "rgba(248, 113, 113, 0.1)";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill={bgColor}
          stroke="rgba(255,255,255,0.04)"
          strokeWidth={2.5}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={2.5}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            transition: "stroke-dashoffset 0.6s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center font-medium"
        style={{ fontSize: size * 0.28, color }}
      >
        {pct}
      </span>
    </div>
  );
}
