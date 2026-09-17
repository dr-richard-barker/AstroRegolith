import React, { useMemo, useState } from 'react';
import { Gem, Camera, ExternalLink, AlertTriangle, Search, BookOpen, Boxes } from 'lucide-react';
import { loadData } from '../lib/sitedata';
import { BarRow, Loading, LoadError, useData } from './charts';
import { lookupSample, type LunarSample } from '../lib/curationApi';
import type { CurationData } from '../lib/sitedata';

const fmt = (n: number | null | undefined, unit = '') =>
  n === null || n === undefined ? '—' : `${n.toLocaleString()}${unit}`;

/** Curation provenance for the material OSD-476 actually grew plants in. */
export const Curation: React.FC = () => {
  const { data, error } = useData<CurationData>(() => loadData('curation'));
  const [open, setOpen] = useState<string | null>(null);

  if (error) return <LoadError error={error} />;
  if (!data) return <Loading what="NASA curation records" />;

  const cov = data.coverage;
  const pctAll = (100 * cov.n_with_pds_photos) / cov.n_samples;
  const pctSoil = (100 * cov.n_soil_photographed) / cov.n_soil_samples;

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Curation</div>
        <h1>Where the regolith came from</h1>
        <p>
          OSD-476 did not grow plants in "Apollo regolith" in general. Its deposited
          metadata names the material to the split — Apollo 11 <span className="mono">10084</span>,
          Apollo 12 <span className="mono">12070</span> and Apollo 17 <span className="mono">70051</span>,
          all sieved below 1&nbsp;mm — and those are primary keys in NASA's Apollo Sample
          and Photo Database. So every plant on this site can be traced to the curation
          record of the exact soil it grew in.
        </p>
      </div>

      {/* --- the three regoliths --------------------------------------- */}
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', marginBottom: 16 }}>
        {data.regoliths.map(r => (
          <div className="card pad" key={r.generic}>
            <div className="card-title">
              <Gem size={16} /> {r.generic}
              <span className="tag" style={{ marginLeft: 'auto' }}>{r.mission}</span>
            </div>

            <div className="kv" style={{ fontSize: '.85rem' }}>
              <div>Type</div><div>{r.sampleType} · {r.sampleSubtype}</div>
              <div>Returned mass</div><div>{fmt(r.originalWeightG, ' g')}</div>
              <div>Pristinity</div>
              <div>
                {fmt(r.pristinityPct, '%')}
                {r.pristinityDate && (
                  <span className="muted"> · assessed {String(r.pristinityDate).split(' 00:')[0]}</span>
                )}
              </div>
              <div>Collected at</div>
              {/* 10084 has no landmark or station recorded, only the rock box it
                  came home in, so fall back to that rather than printing
                  "not recorded" beside a value that is in fact recorded. */}
              <div>
                {r.landmark || r.station
                  ? <>{r.landmark || r.station}{r.bagNumber ? <span className="muted"> · {r.bagNumber}</span> : null}</>
                  : r.bagNumber
                    ? <>{r.bagNumber} <span className="muted">(container only)</span></>
                    : <span className="muted">not recorded</span>}
              </div>
              <div>Thin sections</div><div>{fmt(r.nThinSections)}</div>
              <div>OSD-476 splits</div>
              <div className="mono">{r.osd476Splits.map(s => `,${s}`).join(' ')}</div>
            </div>

            <div className="hr" />

            {r.nPhotos > 0 ? (
              <>
                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <strong style={{ fontSize: '.85rem' }}>
                    <Camera size={13} /> {r.nPhotos} NASA photograph{r.nPhotos === 1 ? '' : 's'}
                  </strong>
                  <button className="btn btn-xs btn-ghost"
                          onClick={() => setOpen(open === r.generic ? null : r.generic)}>
                    {open === r.generic ? 'hide' : 'show'}
                  </button>
                </div>
                {open === r.generic && (
                  <div style={{ marginTop: 10, display: 'grid', gap: 10 }}>
                    {r.photos.slice(0, 8).map(p => (
                      <figure key={p.photo} style={{ margin: 0 }}>
                        {p.jpegUrl && (
                          <img src={p.jpegUrl} alt={p.description || p.photo} loading="lazy"
                               style={{ width: '100%', borderRadius: 6, background: 'var(--card-2)' }} />
                        )}
                        <figcaption className="muted" style={{ fontSize: '.72rem', marginTop: 4, lineHeight: 1.5 }}>
                          <span className="mono">{p.photo}</span> · {p.type}
                          {p.description ? <> — {p.description}</> : null}
                          {/* The dimensions in the PDS index describe the archival
                              TIFF, not the JPEG shown here, which is a reduced
                              derivative — so say which is which rather than
                              printing the scan size under a smaller image. */}
                          <br />
                          Archival scan {p.width}×{p.height} px.{' '}
                          {p.tifUrl && (
                            <a href={p.tifUrl} target="_blank" rel="noopener">
                              Original TIFF{p.fileSize ? ` (${p.fileSize})` : ' (very large)'}
                            </a>
                          )}
                        </figcaption>
                      </figure>
                    ))}
                    {r.nPhotos > 8 && (
                      <p className="muted" style={{ fontSize: '.75rem', margin: 0 }}>
                        {r.nPhotos - 8} more in the PDS archive.
                      </p>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="row" style={{ gap: 8, alignItems: 'flex-start' }}>
                <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2, color: 'var(--warn)' }} />
                <div style={{ fontSize: '.82rem', lineHeight: 1.6 }}>
                  <strong>No photograph exists.</strong> {r.generic} has no entry in the PDS
                  Apollo sample photograph archive
                  {r.hasCompendium === false && <> and no Lunar Sample Compendium entry</>}
                  {r.hasCompendium === null && <> (compendium coverage not checked)</>}.
                  {' '}It is the only one of the three that cannot be seen.
                </div>
              </div>
            )}

            <div className="row wrap" style={{ gap: 6, marginTop: 12 }}>
              {r.hasCompendium && (
                <a className="btn btn-xs btn-ghost" href={r.compendiumUrl} target="_blank" rel="noopener">
                  <BookOpen size={12} /> Compendium <ExternalLink size={10} />
                </a>
              )}
              {r.a3d.map(s => (
                <a key={s.key} className="btn btn-xs btn-ghost" href={s.viewer_url} target="_blank" rel="noopener">
                  <Boxes size={12} /> 3D scan {s.display_name} <ExternalLink size={10} />
                </a>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* --- the coverage gap ------------------------------------------- */}
      <div className="card pad" style={{ marginBottom: 16 }}>
        <div className="card-title"><AlertTriangle size={16} /> What the archives do and do not hold</div>
        <p style={{ fontSize: '.86rem', lineHeight: 1.7 }}>
          Joining NASA's sample API, its photograph archive, the Lunar Sample Compendium and
          Astromaterials 3D on the sample number gives a coverage figure for all{' '}
          <strong>{fmt(cov.n_samples)}</strong> Apollo and Luna samples. They do not cover the
          same material, and the material most relevant to growing plants is the least
          documented: <strong>soils are photographed at {pctSoil.toFixed(0)}%</strong> against{' '}
          {pctAll.toFixed(0)}% for the collection as a whole.
        </p>
        <BarRow
          unit=" samples"
          max={cov.n_samples}
          items={[
            { label: `Photographed (PDS)`, value: cov.n_with_pds_photos, colour: 'var(--accent)' },
            { label: `Thin section available`, value: cov.n_with_thin_section, colour: 'var(--accent2)' },
            ...(cov.n_with_compendium != null
              ? [{ label: 'Compendium entry', value: cov.n_with_compendium, colour: '#b7791f' }]
              : []),
            { label: `3D scanned`, value: cov.n_with_3d_scan, colour: '#9c6ea0' },
            { label: `Soils photographed (of ${cov.n_soil_samples})`, value: cov.n_soil_photographed, colour: '#c2483f' },
          ]}
        />
        <p className="muted" style={{ fontSize: '.78rem', lineHeight: 1.6, marginBottom: 0 }}>
          The Luna 16/20/24 samples ({Object.entries(cov.by_mission)
            .filter(([m]) => m.startsWith('Luna'))
            .reduce((s, [, v]) => s + v.n, 0)} in total) have no photographs here because the
          PDS Apollo volumes do not cover them — an archive boundary rather than a gap. The
          full per-sample table is in{' '}
          <span className="mono">data/ares/apollo_curation_coverage.csv</span>.
        </p>
      </div>

      <SimulantGallery data={data} />
      <LiveLookup />

      <p className="muted" style={{ fontSize: '.75rem', lineHeight: 1.7, marginTop: 20 }}>
        Sources: NASA JSC Astromaterials Acquisition and Curation Office (
        <a href={data.sources.samplePage} target="_blank" rel="noopener">Apollo Sample and Photo Database</a>),
        NASA PDS Imaging Node (<a href={data.sources.pdsArchive} target="_blank" rel="noopener">Apollo Mission
        Lunar Sample Photographs</a>), the{' '}
        <a href={data.sources.simulantTable} target="_blank" rel="noopener">ARES Simulant Development Lab</a> and{' '}
        <a href={data.sources.astromaterials3d} target="_blank" rel="noopener">Astromaterials 3D</a>. Harvested
        by <span className="mono">ares-curation</span>; every number on this page is read from a
        table committed to this repository.
      </p>
    </div>
  );
};

/** NASA's own photographs of the simulants, including the JSC-1A control. */
const SimulantGallery: React.FC<{ data: CurationData }> = ({ data }) => {
  const [surface, setSurface] = useState<string>('all');
  const surfaces = useMemo(
    () => ['all', ...Array.from(new Set(data.simulants.map(s => s.surface)))],
    [data],
  );
  const shown = data.simulants.filter(s => surface === 'all' || s.surface === surface);
  const correction = data.simulantCorrections[0];

  return (
    <div className="card pad" style={{ marginBottom: 16 }}>
      <div className="card-title"><Camera size={16} /> What the simulants look like</div>
      <p style={{ fontSize: '.86rem', lineHeight: 1.7 }}>
        The Substrates view says what a simulant is made of. This is what it looks like — NASA's
        bench and microscope photographs of the sixteen simulants its Simulant Development Lab
        keeps, including <strong>JSC-1A</strong>, the control OSD-476 grew its comparison plants in.
      </p>

      <div className="row wrap" style={{ gap: 6, marginBottom: 12 }}>
        {surfaces.map(s => (
          <button key={s} className={`btn btn-sm ${surface === s ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setSurface(s)}>
            {s === 'all' ? `All ${data.simulants.length}` : s}
          </button>
        ))}
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14 }}>
        {shown.map(s => (
          <figure key={s.name} style={{ margin: 0 }}>
            <div className="row" style={{ gap: 4 }}>
              {s.bench && <img src={`${import.meta.env.BASE_URL}${s.bench}`} alt={`${s.name} bulk sample`}
                               loading="lazy" style={{ width: '50%', borderRadius: 5, background: 'var(--card-2)' }} />}
              {s.micro && <img src={`${import.meta.env.BASE_URL}${s.micro}`} alt={`${s.name} under the microscope`}
                               loading="lazy" style={{ width: '50%', borderRadius: 5, background: 'var(--card-2)' }} />}
            </div>
            <figcaption style={{ fontSize: '.78rem', marginTop: 5, lineHeight: 1.5 }}>
              <strong>{s.name}</strong>
              {s.name === 'JSC-1A' && <span className="chip" style={{ marginLeft: 5 }}>OSD-476 control</span>}
              <br />
              <span className="muted">{s.surface}</span>
              {s.wasCorrected && (
                <>
                  <br />
                  <span className="muted" style={{ fontSize: '.72rem' }}>
                    published as “{s.nameAsPublished}” — see note below
                  </span>
                </>
              )}
            </figcaption>
          </figure>
        ))}
      </div>

      {correction && (
        <p className="muted" style={{ fontSize: '.76rem', lineHeight: 1.6, marginTop: 14, marginBottom: 0 }}>
          <strong>Correction applied.</strong> NASA's published table names this row{' '}
          “{correction.name_as_published}”, repeating the row above it, while its photographs are
          all <span className="mono">{correction.image_stem}.jpg</span> and its Representative
          Planetary Surface reads “{correction.surface}”. We show it as{' '}
          <strong>{correction.corrected_to}</strong> and keep the published name on the record.
        </p>
      )}
    </div>
  );
};

/**
 * A live query against NASA's curation API.
 *
 * Every other dataset on this site is baked, because OSDR and PSI refuse
 * cross-origin browser requests. This API answers `Access-Control-Allow-Origin: *`,
 * so it is the one source here a visitor's browser can query directly — for any
 * of the 2,511 samples, not just the three this database bakes.
 */
const LiveLookup: React.FC = () => {
  const [q, setQ] = useState('');
  const [state, setState] = useState<{ busy: boolean; row?: LunarSample | null; err?: string }>({ busy: false });

  const go = async (e: React.FormEvent) => {
    e.preventDefault();
    const generic = q.trim();
    if (!generic) return;
    setState({ busy: true });
    try {
      setState({ busy: false, row: await lookupSample(generic) });
    } catch (err: any) {
      setState({ busy: false, err: err?.message || 'lookup failed' });
    }
  };

  return (
    <div className="card pad">
      <div className="card-title"><Search size={16} /> Look up any Apollo sample</div>
      <p style={{ fontSize: '.86rem', lineHeight: 1.7 }}>
        This queries NASA live. It is the only thing on this site that does: OSDR and PSI both
        refuse cross-origin browser requests, but the curation API allows them, so any of the
        2,511 samples can be read here rather than only the three baked above.
      </p>

      <form className="row wrap" style={{ gap: 6 }} onSubmit={go}>
        <input className="input mono" value={q} onChange={e => setQ(e.target.value)}
               placeholder="e.g. 10084, 15555, 70051" aria-label="Apollo sample number"
               style={{ maxWidth: 220 }} />
        <button className="btn btn-sm btn-primary" type="submit" disabled={state.busy}>
          {state.busy ? 'looking up…' : 'Look up'}
        </button>
      </form>

      {state.err && (
        <p className="muted" style={{ fontSize: '.8rem', marginTop: 10, marginBottom: 0 }}>
          {state.err}
        </p>
      )}

      {state.row === null && !state.err && (
        <p className="muted" style={{ fontSize: '.8rem', marginTop: 10, marginBottom: 0 }}>
          No sample with that number is in the collection.
        </p>
      )}

      {state.row && (
        <div className="kv" style={{ fontSize: '.85rem', marginTop: 12 }}>
          <div>Sample</div><div className="mono">{state.row.GENERIC}</div>
          <div>Mission</div><div>{state.row.MISSION}</div>
          <div>Type</div><div>{state.row.SAMPLETYPE} · {state.row.SAMPLESUBTYPE || '—'}</div>
          <div>Returned mass</div><div>{fmt(state.row.ORIGINALWEIGHT, ' g')}</div>
          <div>Pristinity</div><div>{fmt(state.row.PRISTINITY, '%')}</div>
          <div>Collected at</div>
          <div>{state.row.LANDMARK || state.row.STATION || <span className="muted">not recorded</span>}</div>
          {state.row.GENERICDESCRIPTION && (
            <>
              <div>Description</div><div>{state.row.GENERICDESCRIPTION}</div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
