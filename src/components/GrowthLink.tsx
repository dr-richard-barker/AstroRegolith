import React, { useMemo, useState } from 'react';
import { Link2, Search, AlertTriangle, Sprout } from 'lucide-react';
import { loadData, rows, type Phenotypes, type GrowthGenes, type LinkRow } from '../lib/sitedata';
import { loadRegistry, resolve, type SubstrateRegistry } from '../lib/substrates';
import { SubstrateChip } from './SubstrateChip';
import {
  LineChart, Scatter, Loading, LoadError, useData, groupBy, meanSem,
  SUBSTRATE_COLOUR, SUBSTRATE_LABEL, SUBSTRATE_ORDER, type Series,
} from './charts';

/**
 * The core of the database: every sequenced plant joined to how it actually grew.
 *
 * The join is possible because the OSD-476 ISA-Tab keys each RNA-seq sample to a
 * plate and to a per-plant leaf-count trajectory, and each plate carried exactly
 * one Apollo 11, one Apollo 12 and one Apollo 17 plant.
 */
export const GrowthLink: React.FC = () => {
  const ph = useData<Phenotypes>(() => loadData('phenotypes'));
  const gg = useData<GrowthGenes>(() => loadData('growth_genes'));
  const [tab, setTab] = useState<'growth' | 'join' | 'genes'>('growth');

  if (ph.error) return <LoadError error={ph.error} />;
  if (!ph.data) return <Loading what="the phenotype linkage" />;

  const link = ph.data.linkage;
  const linked = link.filter(l => l.join_confidence !== 'unlinked');
  const rho = linked[0]?.qc_leaf_area_spearman;

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Phenotype ↔ Expression</div>
        <h1>Growth-anchored transcriptomics</h1>
        <p>
          OSD-476 deposited a leaf-count trajectory and a plate assignment for each sequenced
          plant. That makes it possible to ask which genes track <em>how well an individual
          plant grew</em>, rather than only which regolith it grew in — a covariate that varies
          widely inside every treatment group.
        </p>
      </div>

      <SubstrateProvenanceStrip />

      <div className="stat-row" style={{ marginBottom: 16 }}>
        <Stat k="RNA-seq samples" v={link.length} />
        <Stat k="Joined to a plant" v={linked.length} accent />
        <Stat k="One-to-one joins" v={link.filter(l => l.join_confidence === 'exact').length} teal />
        <Stat k="Leaf ↔ area agreement" v={rho != null ? `ρ ${rho.toFixed(2)}` : '—'} />
      </div>

      <div className="row wrap" style={{ gap: 8, marginBottom: 16 }}>
        {([['growth', 'Growth trajectories'], ['join', 'How the join works'], ['genes', 'Growth-correlated genes']] as const).map(([id, label]) => (
          <button key={id} className={`btn btn-sm ${tab === id ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      {tab === 'growth' && <Growth ph={ph.data} />}
      {tab === 'join' && <JoinTable ph={ph.data} />}
      {tab === 'genes' && (gg.error ? <LoadError error={gg.error} /> : !gg.data ? <Loading what="the gene results" /> : <Genes gg={gg.data} />)}
    </div>
  );
};

const Growth: React.FC<{ ph: Phenotypes }> = ({ ph }) => {
  const leaves = useMemo(() => rows(ph.leaf_counts), [ph]);
  const traits = useMemo(() => rows(ph.plantcv_traits), [ph]);
  const link = ph.linkage.filter(l => l.join_confidence !== 'unlinked');

  const series = (data: any[], value: string): Series[] =>
    groupBy(data, (r: any) => r.substrate, SUBSTRATE_ORDER).map(([sub, rs]) => {
      const byDay = groupBy(rs, (r: any) => String(r.day));
      const pts = byDay.map(([d, g]) => ({ day: Number(d), ...meanSem(g.map((r: any) => r[value])) }))
        .sort((a, b) => a.day - b.day);
      return {
        name: `${SUBSTRATE_LABEL[sub] || sub} (n=${Math.max(...pts.map(p => p.n))})`,
        colour: SUBSTRATE_COLOUR[sub] || 'var(--accent)',
        points: pts.map(p => ({ x: p.day, y: p.mean })),
        band: pts.map(p => ({ x: p.day, lo: p.mean - p.sem, hi: p.mean + p.sem })),
      };
    });

  return (
    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))' }}>
      <div className="card pad">
        <div className="card-title"><Sprout size={16} /> Leaf emergence (OSDR ISA-Tab)</div>
        <LineChart series={series(leaves, 'n_leaves')} xLabel="days from first plate scan" yLabel="leaves visible" />
        <p className="muted" style={{ fontSize: '.78rem', marginBottom: 0 }}>
          Mean ± s.e.m. per substrate. Apollo plants take 2–8 days longer to put out a first true leaf
          and never catch up.
        </p>
      </div>

      <div className="card pad">
        <div className="card-title"><Sprout size={16} /> Rosette expansion (PlantCV)</div>
        <LineChart series={series(traits, 'area_mm2')} logY xLabel="days from first plate scan" yLabel="rosette area (mm²)" />
        <p className="muted" style={{ fontSize: '.78rem', marginBottom: 0 }}>
          Re-scored from the same plate scans, so this is an independent measurement rather than a
          restatement of the leaf counts. The dip after day 2 is the thinning to one seedling per
          well that the study protocol records for days 6–8.
        </p>
      </div>

      <div className="card pad">
        <div className="card-title"><Link2 size={16} /> The two phenotype layers agree</div>
        <Scatter
          logX
          points={link.map(l => ({
            x: l.area_mm2_last ?? NaN, y: l.leaf_final ?? NaN,
            colour: SUBSTRATE_COLOUR[l.substrate], label: `${l.gsm} · ${SUBSTRATE_LABEL[l.substrate]}`,
          }))}
          legend={SUBSTRATE_ORDER.map(s => ({ name: SUBSTRATE_LABEL[s], colour: SUBSTRATE_COLOUR[s] }))}
          xLabel="rosette area, last morphometric day (mm²)" yLabel="leaf count, last imaged day"
        />
        <p className="muted" style={{ fontSize: '.78rem', marginBottom: 0 }}>
          Spearman ρ = {link[0]?.qc_leaf_area_spearman.toFixed(2)} (p ={' '}
          {link[0]?.qc_leaf_area_p.toExponential(1)}, n = {link.length}). Hover a point for its sample.
        </p>
      </div>

      <div className="card pad">
        <div className="card-title"><Link2 size={16} /> Growth spans every substrate</div>
        <Scatter
          zeroLines
          points={link.map(l => ({
            x: l.leaf_rate_per_day ?? NaN, y: l.rgr_area_per_day ?? NaN,
            colour: SUBSTRATE_COLOUR[l.substrate], label: l.gsm,
          }))}
          legend={SUBSTRATE_ORDER.map(s => ({ name: SUBSTRATE_LABEL[s], colour: SUBSTRATE_COLOUR[s] }))}
          xLabel="leaf rate (leaves day⁻¹)" yLabel="rosette relative growth rate (day⁻¹)"
        />
        <p className="muted" style={{ fontSize: '.78rem', marginBottom: 0 }}>
          Apollo plants span most of the growth range on their own, which is what lets the
          within-lunar analysis separate growth from substrate.
        </p>
      </div>
    </div>
  );
};

const CONFIDENCE: Record<string, { label: string; cls: string; note: string }> = {
  exact: { label: 'exact', cls: 'pos', note: 'one plant, one transcriptome' },
  plate_mean: { label: 'plate mean', cls: 'info', note: 'mean of the 4 JSC-1A plants on the same plate' },
  unlinked: { label: 'unlinked', cls: 'neg', note: 'no morphometrics deposited for this sample' },
};

const JoinTable: React.FC<{ ph: Phenotypes }> = ({ ph }) => (
  <div className="grid" style={{ gap: 14 }}>
    <div className="card pad">
      <div className="card-title"><Link2 size={16} /> Sample → plant join</div>
      <div style={{ overflowX: 'auto' }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Sample</th><th>Substrate</th><th>Plate</th><th>Join</th><th>Plants</th>
              <th>First leaf<br /><span className="muted">day</span></th>
              <th>Final<br />leaves</th>
              <th>Leaf rate<br /><span className="muted">day⁻¹</span></th>
              <th>Area<br /><span className="muted">mm²</span></th>
              <th>Stage at harvest</th>
            </tr>
          </thead>
          <tbody>
            {ph.linkage.map(l => {
              const c = CONFIDENCE[l.join_confidence];
              return (
                <tr key={l.gsm}>
                  <td className="mono">{l.gsm}</td>
                  <td><span className="chip tag" style={{ color: SUBSTRATE_COLOUR[l.substrate], borderColor: SUBSTRATE_COLOUR[l.substrate] }}>{SUBSTRATE_LABEL[l.substrate] || l.substrate}</span></td>
                  <td className="mono">{l.plate ?? '—'}</td>
                  <td><span className={`badge ${c.cls}`} title={c.note}>{c.label}</span></td>
                  <td className="mono">{l.n_plants || '—'}</td>
                  <td className="mono">{fmt(l.leaf_first_day)}</td>
                  <td className="mono">{fmt(l.leaf_final)}</td>
                  <td className="mono">{fmt(l.leaf_rate_per_day, 2)}</td>
                  <td className="mono">{fmt(l.area_mm2_last, 2)}</td>
                  <td className="muted" style={{ fontSize: '.78rem' }}>{l.dev_stage_at_harvest}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{ fontSize: '.8rem', lineHeight: 1.6, marginBottom: 0 }}>
        Each plate carried one Apollo 11, one Apollo 12 and one Apollo 17 plant, so those twelve
        samples join one-to-one. The four JSC-1A samples with morphometrics share a plate with
        three other control plants and are joined to the plate mean. The last four JSC-1A
        replicates have no morphometrics in the deposited metadata and are excluded from the
        growth analysis rather than imputed.
      </p>
    </div>

    <div className="card pad" style={{ borderColor: 'var(--warn)' }}>
      <div className="card-title" style={{ color: 'var(--warn)' }}>
        <AlertTriangle size={16} style={{ color: 'var(--warn)' }} /> A discrepancy we did not smooth over
      </div>
      <p style={{ fontSize: '.85rem', lineHeight: 1.6, marginTop: 0 }}>{ph.time_axis}</p>
      <p className="muted" style={{ fontSize: '.8rem', lineHeight: 1.6 }}>
        Every plant shared a chamber, so one sowing date has to fit them all. For each sample the
        candidate harvest dates are the imaging days whose leaf count equals the deposited leaf
        count at collection; each implies a sowing date of <span className="mono">harvest − age</span>.
        The intersection across samples is empty — the Apollo samples (21 d) imply 2021-04-27 while
        JSC-1A replicate 3 (20 d) implies 2021-04-28. Growth is therefore reported on days from the
        first plate scan, which needs no inference.
      </p>
      <details>
        <summary className="muted" style={{ fontSize: '.8rem', cursor: 'pointer' }}>Per-sample candidate sowing dates</summary>
        <table className="admin-table" style={{ marginTop: 8 }}>
          <thead><tr><th>Sample</th><th>Candidate sowing dates</th></tr></thead>
          <tbody>{ph.sowing_date_check.map(r => (
            <tr key={r.gsm}><td className="mono">{r.gsm}</td><td className="mono">{r.candidate_sowing_dates}</td></tr>
          ))}</tbody>
        </table>
      </details>
    </div>
  </div>
);

const Genes: React.FC<{ gg: GrowthGenes }> = ({ gg }) => {
  const [cov, setCov] = useState(gg.covariates[0]?.covariate ?? '');
  const [q, setQ] = useState('');
  const ov = gg.overlap_with_published[0];

  const robust = useMemo(() => {
    const t = q.trim().toLowerCase();
    return gg.robust
      .filter(r => !t || `${r.gene} ${r.SYMBOL} ${r.GENENAME}`.toLowerCase().includes(t))
      .sort((a, b) => Math.abs(b.primary ?? 0) - Math.abs(a.primary ?? 0));
  }, [gg, q]);

  const examples = groupBy(gg.examples, e => e.gene);

  return (
    <div className="grid" style={{ gap: 14 }}>
      <div className="card pad">
        <div className="card-title">Method</div>
        <p style={{ fontSize: '.86rem', lineHeight: 1.6, margin: 0 }}>{gg.method}</p>
        <div className="row wrap" style={{ gap: 14, marginTop: 12 }}>
          <Stat k="Published DEGs" v={ov.published_degs_any_apollo_vs_jsc1a} />
          <Stat k="Robust growth genes" v={ov.growth_correlated_robust} teal />
          <Stat k="Overlap" v={ov.overlap} />
          <Stat k="Growth-only" v={ov.growth_only} accent />
        </div>
        <p className="muted" style={{ fontSize: '.78rem', marginTop: 10, marginBottom: 0 }}>
          “Published DEGs” = significant in any Apollo-versus-JSC-1A contrast in the GeneLab
          analysis ({ov.contrasts_used.split(';').length} contrasts). The growth-only genes are the
          ones the source contrast misses.
        </p>
      </div>

      <div className="card pad">
        <div className="card-title">Hits per covariate</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="admin-table">
            <thead><tr><th>Analysis</th><th>Covariate</th><th>Genes tested</th><th>FDR &lt; 5%</th><th>max |ρ|</th></tr></thead>
            <tbody>{gg.summary.map(s => (
              <tr key={`${s.analysis}-${s.covariate}`}>
                <td><span className={`badge ${s.analysis === 'primary' ? 'info' : 'pos'}`}>{s.analysis}</span></td>
                <td className="mono">{s.covariate}</td>
                <td className="mono">{s.genes_tested.toLocaleString()}</td>
                <td className="mono" style={{ fontWeight: 600 }}>{s.genes_fdr05.toLocaleString()}</td>
                <td className="mono">{s.max_abs_rho?.toFixed(2)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div className="field" style={{ marginTop: 12, marginBottom: 0, maxWidth: 460 }}>
          <label>Covariate definitions</label>
          <select className="select" value={cov} onChange={e => setCov(e.target.value)}>
            {gg.covariates.map(c => <option key={c.covariate} value={c.covariate}>{c.covariate}</option>)}
          </select>
          <p className="muted" style={{ fontSize: '.8rem', marginTop: 6 }}>
            {gg.covariates.find(c => c.covariate === cov)?.covariate_description}
          </p>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        {examples.map(([gene, pts]) => (
          <div className="card pad" key={gene}>
            <div className="card-title">{pts[0].label} <span className="mono muted" style={{ fontWeight: 400 }}>{gene}</span></div>
            <Scatter
              points={pts.map(p => ({ x: p.leaf_rate_per_day, y: p.vst, colour: SUBSTRATE_COLOUR[p.substrate], label: p.gsm }))}
              legend={SUBSTRATE_ORDER.map(s => ({ name: SUBSTRATE_LABEL[s], colour: SUBSTRATE_COLOUR[s] }))}
              xLabel="leaf rate (leaves day⁻¹)" yLabel="VST expression" height={220}
            />
            <p className="muted" style={{ fontSize: '.78rem', marginBottom: 0 }}>
              Spearman ρ = {pts[0].spearman_rho >= 0 ? '+' : ''}{pts[0].spearman_rho.toFixed(2)} across all 16 phenotyped plants.
            </p>
          </div>
        ))}
      </div>

      <div className="card pad">
        <div className="row sb wrap" style={{ gap: 10 }}>
          <div className="card-title" style={{ margin: 0 }}>Genes that replicate in both analyses ({gg.robust.length})</div>
          <span className="search" style={{ maxWidth: 280 }}>
            <Search size={16} />
            <input placeholder="AT1G66350, RGL, DELLA…" value={q} onChange={e => setQ(e.target.value)} />
          </span>
        </div>
        <div style={{ overflowX: 'auto', maxHeight: 460, marginTop: 10 }}>
          <table className="admin-table">
            <thead><tr><th>Gene</th><th>Symbol</th><th>Covariate</th><th>ρ all 16</th><th>ρ Apollo only</th><th>Description</th></tr></thead>
            <tbody>
              {robust.slice(0, 300).map((r, i) => (
                <tr key={`${r.gene}-${r.covariate}-${i}`}>
                  <td className="mono">
                    <a href={`https://www.arabidopsis.org/servlets/TairObject?type=locus&name=${r.gene}`} target="_blank" rel="noreferrer">{r.gene}</a>
                  </td>
                  <td style={{ fontWeight: 600 }}>{(r.SYMBOL || '').split('|')[0] || '—'}</td>
                  <td className="mono muted" style={{ fontSize: '.76rem' }}>{r.covariate}</td>
                  <td className="mono" style={{ color: (r.primary ?? 0) > 0 ? 'var(--ok)' : 'var(--danger)' }}>{sign(r.primary)}</td>
                  <td className="mono" style={{ color: (r.within_lunar ?? 0) > 0 ? 'var(--ok)' : 'var(--danger)' }}>{sign(r.within_lunar)}</td>
                  <td className="muted" style={{ fontSize: '.76rem', maxWidth: 380 }}>{r.GENENAME || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {robust.length > 300 && <p className="muted" style={{ fontSize: '.78rem' }}>Showing the 300 strongest of {robust.length} matches.</p>}
      </div>
    </div>
  );
};

const fmt = (v: number | null | undefined, dp = 0) => v == null || !isFinite(v) ? '—' : v.toFixed(dp);
const sign = (v: number | null | undefined) => v == null ? '—' : `${v > 0 ? '+' : ''}${v.toFixed(2)}`;

const Stat: React.FC<{ k: string; v: React.ReactNode; accent?: boolean; teal?: boolean }> = ({ k, v, accent, teal }) => (
  <div className="stat" style={{ minWidth: 130 }}>
    <div className="k">{k}</div>
    <div className={`v ${accent ? 'accent' : ''} ${teal ? 'teal' : ''}`}>{v}</div>
  </div>
);

/**
 * The four treatment groups, resolved to the material behind each one.
 *
 * `A11` is a chart label; `10084` is 3,830 g of Apollo 11 soil collected in a
 * rock box, 60% of it still unallocated fifty years later. This strip closes
 * that gap, so the substrate axis of the analysis is traceable to the curated
 * sample rather than to a four-character code.
 */
const SubstrateProvenanceStrip: React.FC = () => {
  const { data: registry } = useData<SubstrateRegistry>(loadRegistry);
  if (!registry) return null;

  return (
    <div className="card pad" style={{ marginBottom: 16 }}>
      <div className="card-title"><Sprout size={16} /> What the four groups grew in</div>
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: 10 }}>
        {SUBSTRATE_ORDER.map(code => (
          <SubstrateChip key={code} name={code} substrate={resolve(registry, code)} />
        ))}
      </div>
      <p className="muted" style={{ fontSize: '.78rem', lineHeight: 1.6, marginTop: 12, marginBottom: 0 }}>
        The three Apollo soils are named to the split in OSD-476's own deposit, so they key
        directly to NASA's curation database. The Curation view carries the full record and
        NASA's photographs — where they exist: 70051 has none.
      </p>
    </div>
  );
};
