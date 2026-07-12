import { useMemo, useRef, useState } from "react";
import { formatCompact, formatMoney } from "../lib/format";

export function StatTile(props: { label: string; value: string; delta?: string }) {
  return (
    <div className="stat">
      <div className="label">{props.label}</div>
      <div className="value">{props.value}</div>
      {props.delta ? <div className="delta muted">{props.delta}</div> : null}
    </div>
  );
}

/**
 * Horizontal category bars. Single-hue ink marks (magnitude, one series —
 * no legend needed), direct value labels, per-row hover emphasis.
 */
export function CategoryBars(props: { data: { category: string; amount: number }[] }) {
  const max = Math.max(...props.data.map((d) => d.amount), 1);
  return (
    <div role="img" aria-label="Spend by category">
      {props.data.map((d) => (
        <div className="barrow" key={d.category} title={`${d.category}: ${formatMoney(d.amount)}`}>
          <span className="name">{d.category}</span>
          <span className="track">
            <span className="fill" style={{ width: `${(d.amount / max) * 100}%` }} />
          </span>
          <span className="val">{formatCompact(d.amount)}</span>
        </div>
      ))}
    </div>
  );
}

/**
 * Single-series trend line: 2px line, subtle area, crosshair hover with a
 * tooltip naming the month and value. Recessive hairline grid.
 */
export function TrendLine(props: { data: { date: string; amount: number }[] }) {
  const W = 560;
  const H = 180;
  const PAD = { top: 12, right: 8, bottom: 22, left: 56 };
  const [hover, setHover] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const { points, min, max } = useMemo(() => {
    const values = props.data.map((d) => d.amount);
    const lo = Math.min(...values) * 0.95;
    const hi = Math.max(...values) * 1.02;
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const pts = props.data.map((d, i) => ({
      x: PAD.left + (i / Math.max(props.data.length - 1, 1)) * innerW,
      y: PAD.top + (1 - (d.amount - lo) / Math.max(hi - lo, 1)) * innerH,
      ...d,
    }));
    return { points: pts, min: lo, max: hi };
  }, [props.data]);

  if (points.length === 0) return <div className="empty">No trend data</div>;

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const area = `${path} L${points[points.length - 1].x},${H - PAD.bottom} L${points[0].x},${H - PAD.bottom} Z`;

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    let bestDist = Infinity;
    points.forEach((p, i) => {
      const d = Math.abs(p.x - x);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    });
    setHover(best);
  }

  const hp = hover !== null ? points[hover] : null;
  const monthOf = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", { month: "short" });

  return (
    <div className="chart-wrap">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "auto", display: "block" }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label="Monthly spend trend"
      >
        {/* recessive grid: three hairlines */}
        {[0.25, 0.5, 0.75].map((t) => {
          const y = PAD.top + t * (H - PAD.top - PAD.bottom);
          return (
            <line key={t} x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} stroke="var(--rule)" strokeWidth="1" />
          );
        })}
        {/* y extents, mono, muted */}
        <text x={PAD.left - 6} y={PAD.top + 4} textAnchor="end" fontSize="10" fill="var(--muted)" fontFamily="var(--font-mono)">
          {formatCompact(max)}
        </text>
        <text x={PAD.left - 6} y={H - PAD.bottom} textAnchor="end" fontSize="10" fill="var(--muted)" fontFamily="var(--font-mono)">
          {formatCompact(min)}
        </text>
        {/* x labels: first, middle, last */}
        {[0, Math.floor((points.length - 1) / 2), points.length - 1].map((i) => (
          <text key={i} x={points[i].x} y={H - 6} textAnchor="middle" fontSize="10" fill="var(--muted)" fontFamily="var(--font-mono)">
            {monthOf(points[i].date)}
          </text>
        ))}
        <path d={area} fill="var(--mark-soft)" />
        <path d={path} fill="none" stroke="var(--mark)" strokeWidth="2" strokeLinejoin="round" />
        {/* endpoint dot + direct label (selective labeling, not every point) */}
        <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r="4" fill="var(--mark)" stroke="var(--panel)" strokeWidth="2" />
        {hp ? (
          <g>
            <line x1={hp.x} x2={hp.x} y1={PAD.top} y2={H - PAD.bottom} stroke="var(--muted)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx={hp.x} cy={hp.y} r="4.5" fill="var(--mark)" stroke="var(--panel)" strokeWidth="2" />
          </g>
        ) : null}
      </svg>
      {hp ? (
        <div className="chart-tip" style={{ left: `${(hp.x / W) * 100}%`, top: `${(hp.y / H) * 100}%` }}>
          {monthOf(hp.date)} · {formatMoney(hp.amount)}
        </div>
      ) : null}
    </div>
  );
}
