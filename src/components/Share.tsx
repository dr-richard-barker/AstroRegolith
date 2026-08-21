import React, { useState } from 'react';
import {
  Smartphone, Camera, UploadCloud, Download, Ruler, CheckCircle2, ExternalLink,
  Github, ShieldCheck, ListChecks,
} from 'lucide-react';
import { buildEc5Template, templateCsv, download, TEMPLATE_FIELDS } from '../lib/form-template';
import { EC5_REGOLITH_SLUG, EC5_PROJECT_CONFIGURED } from '../api/epicollect';

const STEPS = [
  {
    icon: Smartphone,
    title: 'Install Epicollect5 and add the project',
    body: (
      <>
        Epicollect5 is a free, open data-collection app from Imperial College London. Install it,
        search for the AstroRegolith project by name (or scan its QR code from the project page),
        and it downloads the form to your phone. It works offline in a greenhouse or a chamber and
        uploads when you get signal.
      </>
    ),
    links: [
      { label: 'Epicollect5 (iOS)', url: 'https://apps.apple.com/app/epicollect5/id1183858199' },
      { label: 'Epicollect5 (Android)', url: 'https://play.google.com/store/apps/details?id=uk.ac.imperial.epicollect.five' },
    ],
  },
  {
    icon: Camera,
    title: 'Photograph the plant next to a calibration marker',
    body: (
      <>
        Put a marker — the AstroBotany ArUco card, a colour chart, or at minimum a ruler — in the
        frame beside the plant. That single habit is what turns a phone snapshot into a
        measurement: the marker fixes millimetres per pixel and a colour reference, so anyone can
        recover real leaf area and real colour from your photo years later. Take a second photo of
        the dry substrate and the vessel; regolith work is very hard to reproduce from text alone.
      </>
    ),
  },
  {
    icon: ListChecks,
    title: 'Fill in the substrate fields, especially the boring ones',
    body: (
      <>
        Simulant name, supplier <em>batch</em>, blend ratio, particle size, and whether you rinsed
        or autoclaved it. Simulant composition varies between production runs, and leaching changes
        the ionic stress a root actually sees — two labs reporting "LHS-1" can be running different
        experiments. Record days after sowing and leaf count too: those two fields match OSD-476's
        own metadata, so your series lands on the same axes as the Apollo plants.
      </>
    ),
  },
  {
    icon: UploadCloud,
    title: 'Submit — and it appears here',
    body: (
      <>
        Epicollect5 stores your entries and photos. This site reads that project through
        Epicollect5's open, CORS-enabled API and shows your entries in the Database tab, running
        marker detection in <em>your reader's</em> browser. Nothing is uploaded to us, there is no
        server and no account here, and you keep control of the project — you can export or delete
        your data in Epicollect5 at any time.
      </>
    ),
  },
];

export const Share: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const copy = (t: string) => { navigator.clipboard?.writeText(t); setCopied(true); setTimeout(() => setCopied(false), 1600); };

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Contribute</div>
        <h1>Share your regolith experiment</h1>
        <p>
          Most regolith plant-growth work never leaves the lab notebook it was written in. If you
          are already photographing your plants, four extra minutes with a free app turns those
          photos into a citable, measurable, comparable record — and into part of a shared dataset
          that a single lab could not build alone.
        </p>
      </div>

      {!EC5_PROJECT_CONFIGURED && (
        <div className="card pad" style={{ borderColor: 'var(--warn)', marginBottom: 16 }}>
          <div className="card-title" style={{ color: 'var(--warn)' }}>
            <ShieldCheck size={16} style={{ color: 'var(--warn)' }} /> The collection project is not live yet
          </div>
          <p style={{ fontSize: '.86rem', lineHeight: 1.6, margin: 0 }}>
            Creating an Epicollect5 project needs an account, so it is the maintainer's to make.
            The form below is ready to build: sign in at{' '}
            <a href="https://five.epicollect.net" target="_blank" rel="noreferrer">five.epicollect.net</a>,
            create a public project, add these questions, then set{' '}
            <span className="mono">EC5_REGOLITH_SLUG</span> in{' '}
            <span className="mono">src/api/epicollect.ts</span> to the new project slug. Everything
            else on this page already works.
          </p>
        </div>
      )}

      <div className="grid" style={{ gap: 14, marginBottom: 18 }}>
        {STEPS.map((s, i) => (
          <div className="card pad" key={s.title}>
            <div className="row" style={{ gap: 12, alignItems: 'flex-start' }}>
              <span className="land-ico" style={{ margin: 0, flexShrink: 0 }}><s.icon size={19} /></span>
              <div style={{ minWidth: 0 }}>
                <h3 style={{ margin: '2px 0 6px', fontSize: '1rem' }}>
                  <span className="mono" style={{ color: 'var(--accent2)', marginRight: 8 }}>{i + 1}</span>
                  {s.title}
                </h3>
                <p style={{ margin: 0, fontSize: '.87rem', lineHeight: 1.65, color: 'var(--muted)' }}>{s.body}</p>
                {s.links && (
                  <div className="row wrap" style={{ gap: 8, marginTop: 10 }}>
                    {s.links.map(l => (
                      <a key={l.url} className="btn btn-xs btn-ghost" href={l.url} target="_blank" rel="noreferrer">
                        {l.label} <ExternalLink size={11} />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', marginBottom: 18 }}>
        <div className="card pad">
          <div className="card-title"><Download size={16} /> The regolith form, ready to build</div>
          <p style={{ fontSize: '.86rem', lineHeight: 1.6 }}>
            {TEMPLATE_FIELDS.length} questions covering identity, substrate provenance, growth
            environment, phenotype and imaging. Download the JSON for Epicollect5's project
            structure, or the CSV as a checklist for the form builder.
          </p>
          <div className="row wrap" style={{ gap: 8 }}>
            <button className="btn btn-sm btn-primary" onClick={() => download(
              'astroregolith_epicollect5_form.json',
              JSON.stringify(buildEc5Template(), null, 2), 'application/json')}>
              <Download size={13} /> Form JSON
            </button>
            <button className="btn btn-sm btn-ghost" onClick={() => download(
              'astroregolith_form_checklist.csv', templateCsv(), 'text/csv')}>
              <Download size={13} /> Checklist CSV
            </button>
            {EC5_PROJECT_CONFIGURED && (
              <button className="btn btn-sm btn-ghost" onClick={() => copy(EC5_REGOLITH_SLUG)}>
                {copied ? <CheckCircle2 size={13} /> : null} {copied ? 'Copied' : `Copy slug: ${EC5_REGOLITH_SLUG}`}
              </button>
            )}
          </div>
        </div>

        <div className="card pad">
          <div className="card-title"><Github size={16} /> Prefer git to a phone?</div>
          <p style={{ fontSize: '.86rem', lineHeight: 1.6 }}>
            Commit your images to a public GitHub folder with a <span className="mono">metadata.csv</span>{' '}
            beside them — one row per image, joined by a <span className="mono">filename</span> column —
            then add that folder as a source in the Contribute tab. GitHub serves raw files
            CORS-open, so marker detection runs on them in the browser exactly as it does for
            Epicollect5 entries. Use the same column names as the form questions above and the two
            routes stay interchangeable.
          </p>
          <p className="muted" style={{ fontSize: '.8rem', marginBottom: 0 }}>
            <span className="mono">tools/generate_sidecar.py</span> builds the sidecar from a folder;
            <span className="mono"> tools/validate_sidecar.py</span> checks it before you push.
          </p>
        </div>
      </div>

      <div className="card pad" style={{ marginBottom: 18 }}>
        <div className="card-title"><Ruler size={16} /> Why the marker matters more than the camera</div>
        <p style={{ fontSize: '.87rem', lineHeight: 1.65, marginBottom: 0 }}>
          A rosette photographed at an unknown distance with unknown white balance is an anecdote.
          The same rosette photographed beside a marker of known size and known colour is a
          measurement in mm² with a colour correction — and it stays one when the phone, the lab
          and the lighting all change. That is the whole reason this database asks for a card in the
          frame, and it is why images contributed here can be pooled with the OSD-476 plate scans
          instead of merely sitting next to them.
        </p>
      </div>

      <div className="card pad">
        <div className="card-title"><ListChecks size={16} /> Form questions</div>
        <div style={{ overflowX: 'auto', maxHeight: 420 }}>
          <table className="admin-table">
            <thead><tr><th>#</th><th>Question</th><th>Type</th><th>Required</th><th>Options / notes</th></tr></thead>
            <tbody>
              {TEMPLATE_FIELDS.map((f, i) => (
                <tr key={f.question}>
                  <td className="mono muted">{i + 1}</td>
                  <td style={{ fontWeight: f.required ? 600 : 400 }}>{f.question}</td>
                  <td><span className="chip tag">{f.type}</span></td>
                  <td>{f.required ? <span className="badge pos">required</span> : ''}</td>
                  <td className="muted" style={{ fontSize: '.76rem', maxWidth: 420 }}>
                    {(f.options || []).join(' · ')}{f.options && f.help ? ' — ' : ''}{f.help || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
