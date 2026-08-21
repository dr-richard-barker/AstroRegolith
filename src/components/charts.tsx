// Small SVG chart primitives shared by the regolith dashboards.
//
// Deliberately dependency-free: the site already ships React + Tailwind and a
// charting library would be a bigger download than the datasets it draws. Every
// colour comes from the CoSE CSS variables so light/dark themes just work.

import React, { useMemo, useState } from 'react';

export const SUBSTRATE_COLOUR: Record<string, string> = {
  JSC1A: 'var(--accent2)', A11: 'var(--danger)', A12: 'var(--warn)', A17: 'var(--accent)',
};
export const SUBSTRATE_LABEL: Record<string, string> = {
  JSC1A: 'JSC-1A simulant', A11: 'Apollo 11', A12: 'Apollo 12', A17: 'Apollo 17',
};
export const SUBSTRATE_ORDER = ['JSC1A', 'A11', 'A12', 'A17'];
export const PALETTE = ['#3b6ea5', '#3fb6a8', '#b7791f', '#c2483f', '#8aa9cf', '#7bccc0', '#9c6ea0', '#5a6473'];

const PAD = { l: 52, r: 12, t: 10, b: 34 };

export interface Series { name: string; colour: string; points: { x: number; y: number }[]; band?: { x: number; lo: number; hi: number }[]; }

function scales(w: number, h: number, xs: number[], ys: number[], logY?: boolean) {
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const raw = logY ? ys.filter(v => v > 0).map(Math.log10) : ys;
  let ymin = Math.min(...raw), ymax = Math.max(...raw);
  if (ymin === ymax) { ymin -= 1; ymax += 1; }
  const padY = (ymax - ymin) * 0.08;
  ymin -= padY; ymax += padY;
  const X = (v: number) => PAD.l + ((v - xmin) / (xmax - xmin || 1)) * (w - PAD.l - PAD.r);
  const Y = (v: number) => {
    const t = logY ? Math.log10(Math.max(v, 1e-12)) : v;
    return h - PAD.b - ((t - ymin) / (ymax - ymin || 1)) * (h - PAD.t - PAD.b);
  };
  return { X, Y, xmin, xmax, ymin, ymax };
}

function ticks(min: number, max: number, n = 5): number[] {
  const span = max - min;
  if (!isFinite(span) || span <= 0) return [min];
  const step = Math.pow(10, Math.floor(Math.log10(span / n)));
  const err = (span / n) / step;
  const mult = err >= 7.5 ? 10 : err >= 3 ? 5 : err >= 1.5 ? 2 : 1;
  const s = step * mult;
  const out: number[] = [];
  for (let v = Math.ceil(min / s) * s; v <= max + 1e-9; v += s) out.push(Number(v.toFixed(10)));
  return out;
}

const fmt = (v: number) => Math.abs(v) >= 1000 || (Math.abs(v) < 0.01 && v !== 0)
  ? v.toExponential(1) : String(Number(v.toFixed(3)));

function Axes({ w, h, xTicks, yTicks, X, Y, xLabel, yLabel, logY }: any) {
  return (
    <g>
      {yTicks.map((t: number) => (
        <g key={`y${t}`}>
          <line x1={PAD.l} x2={w - PAD.r} y1={Y(logY ? Math.pow(10, t) : t)} y2={Y(logY ? Math.pow(10, t) : t)}
                stroke="var(--line)" strokeWidth={1} />
          <text x={PAD.l - 6} y={Y(logY ? Math.pow(10, t) : t) + 3} textAnchor="end"
                fontSize={9} fill="var(--muted)">{logY ? `1e${t}` : fmt(t)}</text>
        </g>
      ))}
      {xTicks.map((t: number) => (
        <text key={`x${t}`} x={X(t)} y={h - PAD.b + 14} textAnchor="middle" fontSize={9} fill="var(--muted)">{fmt(t)}</text>
      ))}
      <line x1={PAD.l} x2={w - PAD.r} y1={h - PAD.b} y2={h - PAD.b} stroke="var(--muted)" strokeWidth={1} />
      {xLabel && <text x={(PAD.l + w - PAD.r) / 2} y={h - 3} textAnchor="middle" fontSize={9.5} fill="var(--muted)">{xLabel}</text>}
      {yLabel && <text transform={`translate(11,${(PAD.t + h - PAD.b) / 2}) rotate(-90)`} textAnchor="middle" fontSize={9.5} fill="var(--muted)">{yLabel}</text>}
    </g>
  );
}

export const LineChart: React.FC<{
  series: Series[]; height?: number; xLabel?: string; yLabel?: string; logY?: boolean;
}> = ({ series, height = 240, xLabel, yLabel, logY }) => {
  const w = 560, h = height;
  const xs = series.flatMap(s => s.points.map(p => p.x));
  const ys = series.flatMap(s => s.points.map(p => p.y)).concat(series.flatMap(s => s.band?.flatMap(b => [b.lo, b.hi]) || []));
  if (!xs.length) return <div className="empty">No data</div>;
  const { X, Y, xmin, xmax, ymin, ymax } = scales(w, h, xs, ys, logY);
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 'auto' }} role="img">
        <Axes w={w} h={h} X={X} Y={Y} logY={logY} xLabel={xLabel} yLabel={yLabel}
              xTicks={ticks(xmin, xmax)} yTicks={ticks(ymin, ymax)} />
        {series.map(s => (
          <g key={s.name}>
            {s.band && s.band.length > 1 && (
              <path fill={s.colour} opacity={0.16}
                    d={`M${s.band.map(b => `${X(b.x)},${Y(b.hi)}`).join('L')}L${[...s.band].reverse().map(b => `${X(b.x)},${Y(b.lo)}`).join('L')}Z`} />
            )}
            <path fill="none" stroke={s.colour} strokeWidth={1.8} strokeLinejoin="round"
                  d={`M${s.points.map(p => `${X(p.x)},${Y(p.y)}`).join('L')}`} />
            {s.points.map((p, i) => <circle key={i} cx={X(p.x)} cy={Y(p.y)} r={2.6} fill={s.colour} />)}
          </g>
        ))}
      </svg>
      <Legend items={series.map(s => ({ name: s.name, colour: s.colour }))} />
    </div>
  );
};

export const Scatter: React.FC<{
  points: { x: number; y: number; colour?: string; label?: string; r?: number }[];
  height?: number; xLabel?: string; yLabel?: string; logX?: boolean; logY?: boolean;
  legend?: { name: string; colour: string }[]; zeroLines?: boolean; identity?: boolean;
}> = ({ points, height = 260, xLabel, yLabel, logX, logY, legend, zeroLines, identity }) => {
  const w = 560, h = height;
  const [hover, setHover] = useState<number | null>(null);
  const pts = points.filter(p => isFinite(p.x) && isFinite(p.y) && (!logX || p.x > 0) && (!logY || p.y > 0));
  if (!pts.length) return <div className="empty">No data</div>;
  const xsRaw = pts.map(p => (logX ? Math.log10(p.x) : p.x));
  const { X: X0, xmin, xmax } = scales(w, h, xsRaw, [0, 1]);
  const { Y, ymin, ymax } = scales(w, h, [0, 1], pts.map(p => p.y), logY);
  const X = (v: number) => X0(logX ? Math.log10(v) : v);
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 'auto' }}
           onMouseLeave={() => setHover(null)}>
        <Axes w={w} h={h} X={X0} Y={Y} logY={logY} xLabel={xLabel} yLabel={yLabel}
              xTicks={ticks(xmin, xmax)} yTicks={ticks(ymin, ymax)} />
        {zeroLines && ymin < 0 && ymax > 0 && <line x1={PAD.l} x2={w - PAD.r} y1={Y(0)} y2={Y(0)} stroke="var(--muted)" strokeDasharray="3 3" strokeWidth={0.8} />}
        {zeroLines && xmin < 0 && xmax > 0 && <line y1={PAD.t} y2={h - PAD.b} x1={X(0)} x2={X(0)} stroke="var(--muted)" strokeDasharray="3 3" strokeWidth={0.8} />}
        {identity && <line x1={X0(Math.max(xmin, ymin))} y1={Y(Math.max(xmin, ymin))} x2={X0(Math.min(xmax, ymax))} y2={Y(Math.min(xmax, ymax))} stroke="var(--muted)" strokeDasharray="2 3" strokeWidth={0.8} />}
        {pts.map((p, i) => (
          <circle key={i} cx={X(p.x)} cy={Y(p.y)} r={p.r ?? (hover === i ? 5.5 : 3.6)}
                  fill={p.colour || 'var(--accent)'} stroke="var(--card)" strokeWidth={0.7}
                  onMouseEnter={() => setHover(i)} style={{ cursor: p.label ? 'pointer' : 'default' }} />
        ))}
        {hover != null && pts[hover]?.label && (
          <text x={Math.min(X(pts[hover].x) + 8, w - PAD.r - 4)} y={Y(pts[hover].y) - 8}
                fontSize={10} fill="var(--fg)" textAnchor={X(pts[hover].x) > w * 0.7 ? 'end' : 'start'}>
            {pts[hover].label}
          </text>
        )}
      </svg>
      {legend && <Legend items={legend} />}
    </div>
  );
};

export const Legend: React.FC<{ items: { name: string; colour: string }[] }> = ({ items }) => (
  <div className="row wrap" style={{ gap: 12, marginTop: 6, fontSize: '.74rem', color: 'var(--muted)' }}>
    {items.map(i => (
      <span key={i.name} className="row" style={{ gap: 5 }}>
        <span style={{ width: 9, height: 9, borderRadius: 9, background: i.colour, display: 'inline-block' }} />{i.name}
      </span>
    ))}
  </div>
);

export const BarRow: React.FC<{
  items: { label: string; value: number; colour?: string; note?: string }[];
  unit?: string; max?: number;
}> = ({ items, unit, max }) => {
  const top = max ?? Math.max(...items.map(i => Math.abs(i.value)), 1);
  return (
    <div style={{ display: 'grid', gap: 5 }}>
      {items.map(i => (
        <div key={i.label} className="row" style={{ gap: 9, fontSize: '.79rem' }}>
          <span style={{ width: 150, flexShrink: 0, color: 'var(--muted)' }} title={i.label}>{i.label}</span>
          <span style={{ flex: 1, height: 13, background: 'var(--bg)', borderRadius: 4, overflow: 'hidden' }}>
            <span style={{ display: 'block', height: '100%', width: `${(Math.abs(i.value) / top) * 100}%`, background: i.colour || 'var(--accent)' }} />
          </span>
          <span className="mono" style={{ width: 74, textAlign: 'right' }}>
            {Number(i.value.toFixed(2))}{unit || ''}
          </span>
          {i.note && <span className="muted" style={{ width: 90, fontSize: '.72rem' }}>{i.note}</span>}
        </div>
      ))}
    </div>
  );
};

/** Group rows by a key, preserving a requested order. */
export function groupBy<T>(items: T[], key: (t: T) => string, order?: string[]): [string, T[]][] {
  const m = new Map<string, T[]>();
  for (const it of items) {
    const k = key(it);
    (m.get(k) || m.set(k, []).get(k)!).push(it);
  }
  const keys = order ? order.filter(k => m.has(k)).concat([...m.keys()].filter(k => !order.includes(k))) : [...m.keys()];
  return keys.map(k => [k, m.get(k)!]);
}

/** Mean and standard error of a numeric list. */
export function meanSem(vs: number[]) {
  const v = vs.filter(x => isFinite(x));
  if (!v.length) return { mean: NaN, sem: NaN, n: 0 };
  const mean = v.reduce((a, b) => a + b, 0) / v.length;
  if (v.length < 2) return { mean, sem: 0, n: v.length };
  const sd = Math.sqrt(v.reduce((a, b) => a + (b - mean) ** 2, 0) / (v.length - 1));
  return { mean, sem: sd / Math.sqrt(v.length), n: v.length };
}

export const Loading: React.FC<{ what: string }> = ({ what }) => (
  <div className="empty"><span className="pulse">Loading {what}…</span></div>
);

export const LoadError: React.FC<{ error: string }> = ({ error }) => (
  <div className="card pad" style={{ borderColor: 'var(--danger)', color: 'var(--danger)', fontSize: '.85rem' }}>
    Could not load the baked dataset: {error}
    <div className="muted" style={{ marginTop: 6 }}>Run <span className="mono">bash scripts/run_all.sh</span> to regenerate <span className="mono">public/data/</span>.</div>
  </div>
);

/** Standard hook for a baked dataset: {data, error}. */
export function useData<T>(loader: () => Promise<T>): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  React.useEffect(() => {
    let alive = true;
    loader().then(d => alive && setData(d)).catch(e => alive && setError(String(e?.message || e)));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { data, error };
}
