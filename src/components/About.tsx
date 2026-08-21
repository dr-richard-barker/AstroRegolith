import React from 'react';
import { Ruler, Cpu, Database, Github, Mountain, BookOpen, Scale } from 'lucide-react';
import { loadData, type Manifest } from '../lib/sitedata';
import { useData } from './charts';

const COUNT_LABELS: Record<string, string> = {
  osdr_studies: 'OSDR regolith studies catalogued',
  rnaseq_samples: 'OSD-476 RNA-seq samples',
  phenotyped_samples: 'samples joined to a growth trajectory',
  plantcv_plants: 'plants with PlantCV shape traits',
  leaf_count_observations: 'leaf-count observations',
  genes_tested: 'genes tested against growth',
  robust_growth_genes: 'genes correlated with growth in both analyses',
  broad_lunar_genes: 'genes in the Broad Lunar model',
};

export const About: React.FC = () => {
  const { data } = useData<Manifest>(() => loadData('manifest'));
  return (
    <div style={{ maxWidth: 780 }}>
      <div className="page-head">
        <div className="eyebrow">About</div>
        <h1>What this is</h1>
        <p>
          An open database for plant growth in regolith — lunar, Martian and asteroid. It gathers
          the imagery, the substrate measurements and the transcriptomes that already exist, joins
          them where they can be joined, and shows how to add to them.
        </p>
      </div>

      <div className="grid" style={{ gap: 16 }}>
        {data && (
          <div className="card pad">
            <div className="card-title"><Database /> What is in it</div>
            <dl className="kv">
              {Object.entries(data.counts).map(([k, v]) => (
                <React.Fragment key={k}>
                  <dt style={{ fontFamily: 'var(--mono)', fontSize: '.85rem' }}>{v.toLocaleString()}</dt>
                  <dd style={{ fontFamily: 'var(--font)' }}>{COUNT_LABELS[k] || k.replace(/_/g, ' ')}</dd>
                </React.Fragment>
              ))}
            </dl>
            <p className="muted" style={{ fontSize: '.78rem', marginBottom: 0 }}>
              Built {data.built}{data.commit ? ` from commit ${data.commit}` : ''}. Every figure on
              this site is rendered from a committed table, so it cannot drift from the numbers.
            </p>
          </div>
        )}

        <div className="card pad">
          <div className="card-title"><Mountain /> Why regolith needs its own database</div>
          <p style={{ fontSize: '.9rem', lineHeight: 1.65 }}>
            Regolith work is unusually hard to compare between labs. Simulant composition varies
            between production batches; a highlands simulant and a mare soil differ by nearly 20 wt%
            in iron; particle size drives water retention more than chemistry does; and most studies
            report a substrate by trade name alone. Meanwhile the only study with returned Apollo
            material grew each plant in 900&nbsp;mg of regolith across three landing sites, and will
            not be repeated. Pooling what exists, with enough metadata to know what is being pooled,
            is the only way this field gets statistical power.
          </p>
        </div>

        <div className="card pad">
          <div className="card-title"><Ruler /> The calibration marker</div>
          <p style={{ fontSize: '.9rem', lineHeight: 1.65 }}>
            The AstroBotany card carries four corner ArUco fiducials (dictionary{' '}
            <span className="mono">ARUCO_MIP_36h12</span>) around a 15-chip colour and grayscale
            reference, with a fixed <span className="mono">4.3&nbsp;cm</span> span between opposite
            corner centres. Detecting the four corners gives pixels-per-cm scale, in-plane rotation,
            and a sampling grid for the colour chips — which is what turns a phone photo of a
            stunted, reddening rosette into a measurement of area and pigmentation.
          </p>
        </div>

        <div className="card pad">
          <div className="card-title"><Cpu /> Analysis — in your browser</div>
          <p style={{ fontSize: '.9rem', lineHeight: 1.65 }}>
            Marker detection runs entirely client-side: a geometric contour detector locates the
            corner fiducials, with the <span className="mono">js-aruco2</span> decoder as a
            fallback, and the detected quad yields scale, rotation and a 3×4 affine colour
            correction. The engine is recycled from{' '}
            <a href="https://dr-richard-barker.github.io/Anthocyanin-Image-analysis/" target="_blank" rel="noreferrer">Anthocyanin-Image-analysis</a>.
            Results are cached in your browser and included in the exported manifest. Nothing is
            uploaded to a server.
          </p>
        </div>

        <div className="card pad">
          <div className="card-title"><Database /> Why the dashboards read baked JSON</div>
          <p style={{ fontSize: '.9rem', lineHeight: 1.65 }}>
            NASA OSDR answers <span className="mono">Access-Control-Allow-Origin: osdr.nasa.gov</span>,
            its biodata API sends no CORS header at all, and PSI runs the same backend — so a browser
            on github.io cannot query any of them. The scripts in{' '}
            <span className="mono">scripts/</span> harvest those APIs offline and write JSON into{' '}
            <span className="mono">public/data/</span>, which this site reads. Re-run{' '}
            <span className="mono">bash scripts/run_all.sh</span> to rebuild every table, figure and
            dashboard from the primary sources.
          </p>
        </div>

        {data && (
          <div className="card pad">
            <div className="card-title"><BookOpen /> Sources</div>
            <div className="grid" style={{ gap: 10 }}>
              {data.provenance.map(s => (
                <div key={s.name}>
                  <a href={s.url} target="_blank" rel="noreferrer" style={{ fontWeight: 600, fontSize: '.88rem' }}>{s.name} ↗</a>
                  <div className="muted" style={{ fontSize: '.8rem' }}>{s.note}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="card pad">
          <div className="card-title"><Scale /> Licence and citation</div>
          <p style={{ fontSize: '.9rem', lineHeight: 1.65, marginBottom: 0 }}>
            Code is MIT; data, figures and text are CC-BY-4.0. See{' '}
            <span className="mono">CITATION.cff</span> for how to cite this resource and{' '}
            <span className="mono">MANIFEST.tsv</span> for the provenance and licence of every
            bundled file. NASA OSDR and PSI data carry their own terms — cite the original
            investigators, not just this database.
          </p>
        </div>

        <div className="card pad">
          <div className="card-title"><Github /> Open source</div>
          <p style={{ fontSize: '.9rem', lineHeight: 1.65, marginBottom: 0 }}>
            Built for the Center of Space Exploration, forked from the architecture of{' '}
            <a href="https://github.com/dr-richard-barker/AstroBotany_calibration_image_sharing_and_analysis" target="_blank" rel="noreferrer">
              the AstroBotany calibration image database
            </a>. Sibling tools:{' '}
            <a href="https://dr-richard-barker.github.io/Anthocyanin-Image-analysis/" target="_blank" rel="noreferrer">Anthocyanin-Image-analysis</a>,{' '}
            <a href="https://dr-richard-barker.github.io/astroroot/" target="_blank" rel="noreferrer">AstroRoot</a>.
          </p>
        </div>
      </div>
    </div>
  );
};
