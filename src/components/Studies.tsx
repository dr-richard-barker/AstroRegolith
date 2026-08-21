import React, { useMemo, useState } from 'react';
import { Library, ExternalLink, Images, FileText, AlertTriangle, Atom } from 'lucide-react';
import { loadData, type OsdrCatalog, type PsiCatalog, type OsdrStudy, type PsiStudy } from '../lib/sitedata';
import { Loading, LoadError, useData } from './charts';

/** The regolith slice of NASA's two open repositories, harvested offline. */
export const Studies: React.FC = () => {
  const osdr = useData<OsdrCatalog>(() => loadData('osdr_regolith_catalog'));
  const psi = useData<PsiCatalog>(() => loadData('psi_regolith_catalog'));
  const [repo, setRepo] = useState<'osdr' | 'psi'>('osdr');
  const [q, setQ] = useState('');

  if (osdr.error) return <LoadError error={osdr.error} />;
  if (!osdr.data) return <Loading what="the study catalogue" />;

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Repositories</div>
        <h1>Regolith studies at NASA</h1>
        <p>
          Every regolith-relevant dataset we could find in the NASA Open Science Data Repository
          and the Physical Sciences Informatics system, with a note on why each one belongs in a
          regolith database. Both APIs restrict cross-origin requests, so this catalogue is
          harvested by <span className="mono">scripts/01_fetch_osdr.py</span> and{' '}
          <span className="mono">scripts/02_fetch_psi.py</span> and re-checked monthly.
        </p>
      </div>

      <div className="row wrap" style={{ gap: 8, marginBottom: 14 }}>
        <button className={`btn btn-sm ${repo === 'osdr' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setRepo('osdr')}>
          <Library size={14} /> OSDR — biology ({osdr.data.studies.length})
        </button>
        <button className={`btn btn-sm ${repo === 'psi' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setRepo('psi')}>
          <Atom size={14} /> PSI — physical sciences ({psi.data?.curated.length ?? '…'})
        </button>
        <span className="search" style={{ maxWidth: 300 }}>
          <input placeholder="Filter by title, organism, keyword…" value={q} onChange={e => setQ(e.target.value)} />
        </span>
      </div>

      {repo === 'osdr' ? <OsdrList cat={osdr.data} q={q} /> : (
        psi.error ? <LoadError error={psi.error} /> :
        !psi.data ? <Loading what="the PSI catalogue" /> : <PsiList cat={psi.data} q={q} />
      )}
    </div>
  );
};

const match = (q: string, ...fields: (string | undefined)[]) =>
  !q.trim() || fields.filter(Boolean).join(' ').toLowerCase().includes(q.trim().toLowerCase());

const OsdrList: React.FC<{ cat: OsdrCatalog; q: string }> = ({ cat, q }) => {
  const shown = useMemo(
    () => cat.studies.filter(s => match(q, s.title, s.organism, s.why_regolith, s.accession, s.factors)),
    [cat, q]);
  const withImages = cat.studies.filter(s => s.images > 0);
  return (
    <div>
      <div className="stat-row" style={{ marginBottom: 16 }}>
        <Stat k="Studies" v={cat.studies.length} />
        <Stat k="With imagery" v={withImages.length} accent />
        <Stat k="Images available" v={withImages.reduce((a, s) => a + s.images, 0)} teal />
        <Stat k="Catalogue read" v={cat.accessed} small />
      </div>
      <div className="grid" style={{ gap: 12 }}>
        {shown.map(s => <OsdrCard key={s.accession} s={s} />)}
        {!shown.length && <div className="empty">No study matches “{q}”.</div>}
      </div>
    </div>
  );
};

const OsdrCard: React.FC<{ s: OsdrStudy }> = ({ s }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="card pad">
      <div className="row sb wrap" style={{ gap: 10, alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <div className="row wrap" style={{ gap: 6, marginBottom: 5 }}>
            <span className="badge info mono">{s.accession}</span>
            {s.images > 0 && <span className="badge pos"><Images size={11} /> {s.images} images · {s.image_mb} MB</span>}
            <span className="chip tag">{s.files} files</span>
            {s.released && <span className="chip tag">released {s.released}</span>}
          </div>
          <h3 style={{ margin: '0 0 4px', fontSize: '.98rem', lineHeight: 1.35 }}>{s.title}</h3>
          <div className="muted" style={{ fontSize: '.82rem', fontStyle: 'italic' }}>{s.organism || '—'}</div>
        </div>
        <a className="btn btn-sm btn-ghost" href={s.url} target="_blank" rel="noreferrer">
          Open at OSDR <ExternalLink size={13} />
        </a>
      </div>

      <p style={{ margin: '11px 0 0', fontSize: '.85rem', lineHeight: 1.55 }}>
        <span style={{ fontWeight: 600, color: 'var(--accent2)' }}>Why it is here — </span>{s.why_regolith}
      </p>

      {(s.factors || s.measurements) && (
        <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
          {s.factors && <span className="chip tag">factors: {s.factors}</span>}
          {s.measurements && <span className="chip tag">measures: {s.measurements}</span>}
          {s.material && <span className="chip tag">material: {s.material}</span>}
        </div>
      )}

      {s.description && (
        <>
          <button className="btn btn-xs btn-ghost" style={{ marginTop: 10 }} onClick={() => setOpen(o => !o)}>
            <FileText size={12} /> {open ? 'Hide' : 'Study description'}
          </button>
          {open && <p className="muted" style={{ fontSize: '.82rem', lineHeight: 1.6, marginTop: 8 }}>{s.description}</p>}
        </>
      )}
    </div>
  );
};

const PsiList: React.FC<{ cat: PsiCatalog; q: string }> = ({ cat, q }) => {
  const [showOther, setShowOther] = useState(false);
  const curated = cat.curated.filter(s => match(q, s.title, s.relevance, s.accession, s.keywords.join(' ')));
  const other = cat.other_hits.filter(s => match(q, s.title, s.accession, s.keywords.join(' ')));
  return (
    <div>
      <div className="card pad" style={{ borderColor: 'var(--warn)', marginBottom: 16 }}>
        <div className="card-title" style={{ color: 'var(--warn)' }}>
          <AlertTriangle size={16} style={{ color: 'var(--warn)' }} /> What PSI does and does not hold
        </div>
        <p style={{ margin: 0, fontSize: '.86rem', lineHeight: 1.6 }}>{cat.caveat}</p>
      </div>
      <div className="grid" style={{ gap: 12 }}>
        {curated.map(s => <PsiCard key={s.accession} s={s} />)}
        {!curated.length && <div className="empty">No curated PSI investigation matches “{q}”.</div>}
      </div>
      <button className="btn btn-sm btn-ghost" style={{ marginTop: 14 }} onClick={() => setShowOther(o => !o)}>
        {showOther ? 'Hide' : 'Show'} the other {cat.other_hits.length} search hits
      </button>
      {showOther && (
        <div className="card pad" style={{ marginTop: 10 }}>
          <p className="muted" style={{ fontSize: '.8rem', marginTop: 0 }}>
            Returned by the same searches but not curated as regolith-relevant. Listed so the
            search is reproducible and nothing is quietly discarded.
          </p>
          <table className="admin-table">
            <thead><tr><th>Accession</th><th>Research area</th><th>Title</th></tr></thead>
            <tbody>
              {other.map(s => (
                <tr key={s.accession}>
                  <td className="mono"><a href={s.url} target="_blank" rel="noreferrer">{s.accession}</a></td>
                  <td className="muted">{s.research_area}</td>
                  <td>{s.title}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const PsiCard: React.FC<{ s: PsiStudy }> = ({ s }) => (
  <div className="card pad">
    <div className="row sb wrap" style={{ gap: 10, alignItems: 'flex-start' }}>
      <div style={{ minWidth: 0 }}>
        <div className="row wrap" style={{ gap: 6, marginBottom: 5 }}>
          <span className="badge info mono">{s.accession}</span>
          {s.acronym && <span className="chip tag">{s.acronym}</span>}
          <span className="chip tag">{s.research_area}</span>
          <span className="chip tag">{s.project_type}</span>
        </div>
        <h3 style={{ margin: '0 0 4px', fontSize: '.98rem', lineHeight: 1.35 }}>{s.title}</h3>
        {s.platform && <div className="muted" style={{ fontSize: '.82rem' }}>{s.platform}</div>}
      </div>
      <a className="btn btn-sm btn-ghost" href={s.url} target="_blank" rel="noreferrer">
        Open at PSI <ExternalLink size={13} />
      </a>
    </div>
    <p style={{ margin: '11px 0 0', fontSize: '.85rem', lineHeight: 1.55 }}>
      <span style={{ fontWeight: 600, color: 'var(--accent2)' }}>Why it is here — </span>{s.relevance}
    </p>
    {s.keywords.length > 0 && (
      <div className="row wrap" style={{ gap: 5, marginTop: 9 }}>
        {s.keywords.slice(0, 8).map(k => <span key={k} className="chip tag">{k}</span>)}
      </div>
    )}
  </div>
);

const Stat: React.FC<{ k: string; v: React.ReactNode; accent?: boolean; teal?: boolean; small?: boolean }> =
  ({ k, v, accent, teal, small }) => (
    <div className="stat">
      <div className="k">{k}</div>
      <div className={`v ${accent ? 'accent' : ''} ${teal ? 'teal' : ''}`} style={small ? { fontSize: '1rem' } : undefined}>{v}</div>
    </div>
  );
