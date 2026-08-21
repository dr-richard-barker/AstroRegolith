import React, { useMemo, useState } from 'react';
import { Dna, Search, ExternalLink, GitCompare } from 'lucide-react';
import { loadData, rows, type Transcriptomics as TxData, type Enrichment } from '../lib/sitedata';
import { Scatter, BarRow, Loading, LoadError, useData, PALETTE } from './charts';

/** OSD-476 expression: the published source contrasts plus the pooled Broad Lunar model. */
export const Transcriptomics: React.FC = () => {
  const tx = useData<TxData>(() => loadData('transcriptomics'));
  const en = useData<Enrichment>(() => loadData('enrichment'));
  const [tab, setTab] = useState<'broad' | 'contrasts' | 'go'>('broad');

  if (tx.error) return <LoadError error={tx.error} />;
  if (!tx.data) return <Loading what="the expression tables" />;

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Transcriptomics</div>
        <h1>Arabidopsis in Apollo regolith</h1>
        <p>
          Differential expression for OSD-476, both ways it has been modelled: site by site as
          GeneLab processed it, and with every Apollo sample pooled against the JSC-1A simulant —
          the Broad Lunar model, which trades site resolution for power.
        </p>
      </div>

      <div className="row wrap" style={{ gap: 8, marginBottom: 16 }}>
        {([['broad', 'Broad Lunar model'], ['contrasts', 'Site contrasts'], ['go', 'Functional enrichment']] as const).map(([id, label]) => (
          <button key={id} className={`btn btn-sm ${tab === id ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      {tab === 'broad' && <BroadLunar tx={tx.data} />}
      {tab === 'contrasts' && <Contrasts tx={tx.data} />}
      {tab === 'go' && (en.error ? <LoadError error={en.error} /> : !en.data ? <Loading what="enrichment" /> : <GoTerms en={en.data} />)}
    </div>
  );
};

const BroadLunar: React.FC<{ tx: TxData }> = ({ tx }) => {
  const [q, setQ] = useState('');
  const all = useMemo(() => rows<{ gene: string; symbol: string; log2fc_lunar_vs_simulant: number; padj: number }>(
    tx.broad_lunar_model.data), [tx]);

  // Plot every significant gene plus a deterministic thinning of the rest, so the
  // volcano stays honest about its shape without drawing 21 000 SVG circles.
  const points = useMemo(() => {
    const sig = all.filter(g => g.padj != null && g.padj < 0.05);
    const bg = all.filter(g => !(g.padj != null && g.padj < 0.05)).filter((_, i) => i % 4 === 0);
    const pt = (g: any, colour: string) => ({
      x: g.log2fc_lunar_vs_simulant,
      y: -Math.log10(Math.max(g.padj ?? 1, 1e-300)),
      colour, r: 1.8, label: `${g.symbol || g.gene} · log2FC ${g.log2fc_lunar_vs_simulant?.toFixed(2)}`,
    });
    return [...bg.map(g => pt(g, 'var(--line)')), ...sig.map(g => pt(g, 'var(--accent)'))]
      .filter(p => isFinite(p.x) && isFinite(p.y));
  }, [all]);

  const hits = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return [];
    return all.filter(g => `${g.gene} ${g.symbol || ''}`.toLowerCase().includes(t))
      .sort((a, b) => (a.padj ?? 1) - (b.padj ?? 1)).slice(0, 60);
  }, [all, q]);

  return (
    <div className="grid" style={{ gap: 14 }}>
      <div className="card pad">
        <div className="card-title"><Dna size={16} /> All Apollo regolith vs JSC-1A simulant</div>
        <Scatter points={points} zeroLines height={320}
                 xLabel="log₂ fold change (lunar / simulant)" yLabel="−log₁₀ adjusted p" />
        <div className="row wrap" style={{ gap: 14, marginTop: 8 }}>
          <span className="badge info">{tx.broad_lunar_model.n_genes.toLocaleString()} genes</span>
          <span className="badge pos">{tx.broad_lunar_model.n_sig.toLocaleString()} at adj. p &lt; 0.05</span>
        </div>
        <p className="muted" style={{ fontSize: '.8rem', lineHeight: 1.6, marginBottom: 0 }}>
          {tx.broad_lunar_model.description} Non-significant genes are thinned 4× for rendering;
          every significant gene is drawn and every gene is searchable below.
        </p>
      </div>

      <div className="card pad">
        <div className="row sb wrap" style={{ gap: 10 }}>
          <div className="card-title" style={{ margin: 0 }}><Search size={16} /> Look up a gene</div>
          <span className="search" style={{ maxWidth: 320 }}>
            <Search size={16} />
            <input placeholder="AT1G66350, RGL1, GA20OX…" value={q} onChange={e => setQ(e.target.value)} />
          </span>
        </div>
        {!q.trim() ? (
          <p className="muted" style={{ fontSize: '.84rem', marginBottom: 0 }}>
            Search all {tx.broad_lunar_model.n_genes.toLocaleString()} genes by AGI locus or symbol.
          </p>
        ) : hits.length === 0 ? (
          <div className="empty">No gene matches “{q}”.</div>
        ) : (
          <div style={{ overflowX: 'auto', maxHeight: 400, marginTop: 10 }}>
            <table className="admin-table">
              <thead><tr><th>Gene</th><th>Symbol</th><th>log₂ FC</th><th>adj. p</th><th /></tr></thead>
              <tbody>{hits.map(g => (
                <tr key={g.gene}>
                  <td className="mono">{g.gene}</td>
                  <td style={{ fontWeight: 600 }}>{g.symbol || '—'}</td>
                  <td className="mono" style={{ color: g.log2fc_lunar_vs_simulant > 0 ? 'var(--ok)' : 'var(--danger)' }}>
                    {g.log2fc_lunar_vs_simulant > 0 ? '+' : ''}{g.log2fc_lunar_vs_simulant?.toFixed(2)}
                  </td>
                  <td className="mono">{g.padj == null ? '—' : g.padj < 1e-4 ? g.padj.toExponential(1) : g.padj.toFixed(4)}</td>
                  <td>
                    <a className="btn btn-xs btn-ghost" target="_blank" rel="noreferrer"
                       href={`https://www.arabidopsis.org/servlets/TairObject?type=locus&name=${g.gene}`}>
                      TAIR <ExternalLink size={11} />
                    </a>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const Contrasts: React.FC<{ tx: TxData }> = ({ tx }) => {
  const [sel, setSel] = useState(tx.contrast_summary[0]?.contrast ?? '');
  const top = tx.top_genes_per_contrast[sel] || [];
  return (
    <div className="grid" style={{ gap: 14 }}>
      <div className="card pad">
        <div className="card-title"><GitCompare size={16} /> Significant genes per contrast</div>
        <BarRow items={tx.contrast_summary.map((c, i) => ({
          label: c.contrast.replace(/[()]/g, ''), value: c.n_sig, colour: PALETTE[i % PALETTE.length],
          note: `${c.n_up} up / ${c.n_down} down`,
        }))} />
        <p className="muted" style={{ fontSize: '.8rem', marginTop: 10, marginBottom: 0 }}>
          From {tx.source}. Each pair appears in both directions, as GeneLab deposits them.
        </p>
      </div>

      <div className="card pad">
        <div className="field" style={{ maxWidth: 480 }}>
          <label>Contrast</label>
          <select className="select" value={sel} onChange={e => setSel(e.target.value)}>
            {tx.contrast_summary.map(c => <option key={c.contrast} value={c.contrast}>{c.contrast}</option>)}
          </select>
        </div>
        <div style={{ overflowX: 'auto', maxHeight: 460 }}>
          <table className="admin-table">
            <thead><tr><th>Gene</th><th>Symbol</th><th>log₂ FC</th><th>adj. p</th><th>Description</th></tr></thead>
            <tbody>{top.map(g => (
              <tr key={g.gene}>
                <td className="mono">
                  <a href={`https://www.arabidopsis.org/servlets/TairObject?type=locus&name=${g.gene}`} target="_blank" rel="noreferrer">{g.gene}</a>
                </td>
                <td style={{ fontWeight: 600 }}>{(g.symbol || '').split('|')[0] || '—'}</td>
                <td className="mono" style={{ color: g.log2fc > 0 ? 'var(--ok)' : 'var(--danger)' }}>
                  {g.log2fc > 0 ? '+' : ''}{g.log2fc?.toFixed(2)}
                </td>
                <td className="mono">{g.adj_p < 1e-4 ? g.adj_p.toExponential(1) : g.adj_p?.toFixed(4)}</td>
                <td className="muted" style={{ fontSize: '.76rem', maxWidth: 400 }}>{g.name}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="muted" style={{ fontSize: '.78rem', marginBottom: 0 }}>
          The {tx.top_n} largest absolute fold changes among significant genes. The full
          differential-expression table is 36 MB and stays at OSDR —{' '}
          <span className="mono">scripts/01_fetch_osdr.py</span> pulls it on demand.
        </p>
      </div>
    </div>
  );
};

const GoTerms: React.FC<{ en: Enrichment }> = ({ en }) => {
  const sets = useMemo(() => [...new Set(en.terms.map(t => t.gene_set))].sort(), [en]);
  const [sel, setSel] = useState(sets.find(s => s.startsWith('robust')) ?? sets[0] ?? '');
  const shown = en.terms.filter(t => t.gene_set === sel).sort((a, b) => a.p_value - b.p_value).slice(0, 20);
  return (
    <div className="grid" style={{ gap: 14 }}>
      <div className="card pad">
        <div className="card-title">Method</div>
        <p style={{ fontSize: '.86rem', lineHeight: 1.6, margin: 0 }}>{en.method}</p>
        <p className="muted" style={{ fontSize: '.8rem', marginBottom: 0 }}>Showing {en.shown}.</p>
      </div>
      <div className="card pad">
        <div className="field" style={{ maxWidth: 480 }}>
          <label>Gene set — <span className="mono">analysis | covariate | direction</span></label>
          <select className="select" value={sel} onChange={e => setSel(e.target.value)}>
            {sets.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <BarRow unit="×" items={shown.map(t => ({
          label: t.go_name || t.go_id, value: t.fold_enrichment,
          colour: t.fdr < 0.05 ? 'var(--accent)' : 'var(--line)',
          note: `${t.overlap}/${t.genes_in_term} · q ${t.fdr < 0.001 ? t.fdr.toExponential(0) : t.fdr.toFixed(3)}`,
        }))} />
        <p className="muted" style={{ fontSize: '.78rem', marginTop: 10, marginBottom: 0 }}>
          Solid bars pass FDR 5%; faded bars are shown for context because a GO-slim background of
          ~1 900 terms makes Benjamini-Hochberg strict at this sample size.
        </p>
      </div>
    </div>
  );
};
