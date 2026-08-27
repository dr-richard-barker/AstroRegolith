import React, { useMemo, useState } from 'react';
import { Layers, Droplets, Zap, FlaskConical, Mountain, ExternalLink } from 'lucide-react';
import { loadData, rows, type Substrates as SubstrateData } from '../lib/sitedata';
import { LineChart, BarRow, Loading, LoadError, useData, groupBy, PALETTE, type Series } from './charts';

const METRICS = [
  { key: 'water_content_pct', label: 'Water content', unit: '%', icon: Droplets },
  { key: 'ec_us_cm', label: 'Electrical conductivity', unit: 'µS/cm', icon: Zap },
  { key: 'ph', label: 'pH', unit: '', icon: FlaskConical },
  { key: 'nitrogen', label: 'Nitrogen', unit: '', icon: Layers },
  { key: 'phosphorus', label: 'Phosphorus', unit: '', icon: Layers },
  { key: 'potassium', label: 'Potassium', unit: '', icon: Layers },
] as const;

/** What a regolith substrate actually is: probe behaviour, mineralogy, chemistry. */
export const Substrates: React.FC = () => {
  const { data, error } = useData<SubstrateData>(() => loadData('substrates'));
  const [metric, setMetric] = useState<string>('water_content_pct');

  const ts = useMemo(() => rows(data?.probe.timeseries), [data]);
  const series: Series[] = useMemo(() => groupBy(ts, (r: any) => r.substrate)
    .map(([name, rs], i) => ({
      name, colour: PALETTE[i % PALETTE.length],
      // time_s is seconds from the start of the run; plot it in minutes.
      points: rs.map((r: any) => ({ x: r.time_s / 60, y: r[metric] }))
        .filter((p: any) => isFinite(p.x) && isFinite(p.y))
        .sort((a: any, b: any) => a.x - b.x),
    })).filter(s => s.points.length > 1), [ts, metric]);

  if (error) return <LoadError error={error} />;
  if (!data) return <Loading what="substrate characterisation" />;

  const m = METRICS.find(x => x.key === metric)!;
  const unitNote = data.probe.units.find(u => u.column === metric)?.unit_note;
  const comp = data.chemistry_comparison.filter(c => c.lhs1_wt_pct != null && c.ce5_wt_pct != null);
  const maxOxide = Math.max(...comp.flatMap(c => [c.lhs1_wt_pct!, c.ce5_wt_pct!]));

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Substrates</div>
        <h1>What you are actually growing in</h1>
        <p>
          Three independent descriptions of a regolith substrate — how it behaves when watered,
          what it is made of, and how far a simulant sits from real lunar soil. Choosing a
          substrate fixes all three before a single seed is sown.
        </p>
      </div>

      <div className="card pad" style={{ marginBottom: 16 }}>
        <div className="card-title"><m.icon size={16} /> Probe response while watering</div>
        <div className="row wrap" style={{ gap: 6, marginBottom: 12 }}>
          {METRICS.map(x => (
            <button key={x.key} className={`btn btn-sm ${metric === x.key ? 'btn-primary' : 'btn-ghost'}`}
                    onClick={() => setMetric(x.key)}>{x.label}</button>
          ))}
        </div>
        <LineChart series={series} xLabel="minutes" yLabel={m.unit ? `${m.label} (${m.unit.trim()})` : m.label} height={210} />
        <p className="muted" style={{ fontSize: '.8rem', lineHeight: 1.6, marginBottom: 0 }}>
          {data.probe.description}{unitNote ? ` Units: ${unitNote}.` : ''}
        </p>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', marginBottom: 16 }}>
        <div className="card pad">
          <div className="card-title"><Mountain size={16} /> Simulant vs real lunar soil</div>
          <BarRow unit=" wt%" max={maxOxide}
                  items={comp.flatMap(c => [
                    { label: `${c.oxide} · LHS-1`, value: c.lhs1_wt_pct!, colour: 'var(--accent2)' },
                    { label: `${c.oxide} · Chang'e-5`, value: c.ce5_wt_pct!, colour: 'var(--accent)' },
                  ])} />
          <p className="muted" style={{ fontSize: '.8rem', lineHeight: 1.6, marginTop: 10, marginBottom: 0 }}>
            LHS-1 is a <em>highlands</em> simulant and Chang'e-5 returned <em>mare</em> soil, so the
            gaps are systematic rather than manufacturing error: LHS-1 carries{' '}
            {fmtDiff(comp.find(c => c.oxide === 'Al2O3'))} more Al₂O₃ and{' '}
            {fmtDiff(comp.find(c => c.oxide === 'FeO'))} less FeO. A simulant choice is a choice
            about which lunar terrain you are modelling.
          </p>
        </div>

        <div className="card pad">
          <div className="card-title"><Layers size={16} /> LHS-1 mineralogy</div>
          <BarRow unit=" wt%" items={data.simulant_lhs1.mineralogy.map((r, i) => ({
            label: r.component, value: r.wt_pct, colour: PALETTE[i % PALETTE.length],
          }))} />
          <div className="hr" />
          <div className="card-title" style={{ fontSize: '.85rem' }}>Physical properties</div>
          <dl className="kv">
            {data.simulant_lhs1.physical.map(p => (
              <React.Fragment key={p.property}><dt>{p.property}</dt><dd>{p.value}</dd></React.Fragment>
            ))}
          </dl>
          {data.simulant_lhs1.mineralogy[0]?.source && (
            <a className="btn btn-xs btn-ghost" style={{ marginTop: 10 }}
               href={data.simulant_lhs1.mineralogy[0].source} target="_blank" rel="noreferrer">
              Exolith spec sheet <ExternalLink size={12} />
            </a>
          )}
        </div>
      </div>

      <div className="card pad" style={{ marginBottom: 16 }}>
        <div className="card-title"><Droplets size={16} /> Endpoint readings</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Substrate</th><th>Run (min)</th><th>Water (%)</th><th>EC (µS/cm)</th>
                <th>pH</th><th>N</th><th>P</th><th>K</th><th>Water added (mL)</th>
              </tr>
            </thead>
            <tbody>
              {data.probe.endpoint.map(r => (
                <tr key={r.substrate}>
                  <td style={{ fontWeight: 600 }}>{r.substrate}</td>
                  <td className="mono">{num(r.time_s / 60, 1)}</td>
                  <td className="mono">{num(r.water_content_pct, 1)}</td>
                  <td className="mono">{num(r.ec_us_cm, 0)}</td>
                  <td className="mono">{num(r.ph, 1)}</td>
                  <td className="mono">{num(r.nitrogen, 0)}</td>
                  <td className="mono">{num(r.phosphorus, 0)}</td>
                  <td className="mono">{num(r.potassium, 0)}</td>
                  <td className="mono">{num(r.water_added_ml, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted" style={{ fontSize: '.8rem', marginBottom: 0 }}>
          N, P and K are the probe's own indices — its datasheet gives no unit, so none is invented
          here. Compare substrates against each other, not against a soil-test laboratory value.
        </p>
      </div>

      <div className="card pad">
        <div className="card-title"><Mountain size={16} /> Chang'e-5 lunar soil composition</div>
        <div style={{ overflowX: 'auto', maxHeight: 380 }}>
          <table className="admin-table">
            <thead><tr><th>Method</th><th>Analyte</th><th>Value</th><th>Unit</th><th>Uncertainty (k=2)</th></tr></thead>
            <tbody>
              {data.lunar_soil_ce5.map(r => (
                <tr key={`${r.method}-${r.analyte}`}>
                  <td><span className="chip tag">{r.method}</span></td>
                  <td style={{ fontWeight: 600 }}>{r.analyte}</td>
                  <td className="mono">{r.value}</td>
                  <td className="muted">{r.unit}</td>
                  <td className="mono muted">{r.uncertainty_k2 ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data.lunar_soil_ce5[0]?.reference && (
          <a className="btn btn-xs btn-ghost" style={{ marginTop: 10 }} href={data.lunar_soil_ce5[0].reference} target="_blank" rel="noreferrer">
            Source publication <ExternalLink size={12} />
          </a>
        )}
      </div>
    </div>
  );
};

const num = (v: any, dp: number) => v == null || !isFinite(Number(v)) ? '—' : Number(v).toFixed(dp);
const fmtDiff = (c?: { difference_wt_pct: number | null }) =>
  c?.difference_wt_pct == null ? '—' : `${Math.abs(c.difference_wt_pct).toFixed(1)} wt%`;
