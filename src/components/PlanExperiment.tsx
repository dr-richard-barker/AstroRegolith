import React, { useMemo, useState } from 'react';
import { ClipboardList, Calculator, AlertTriangle, FileSpreadsheet, Beaker, TrendingDown } from 'lucide-react';
import { loadData, type Phenotypes, type Substrates as SubstrateData, type LinkRow } from '../lib/sitedata';
import { Loading, LoadError, useData, BarRow, SUBSTRATE_COLOUR, SUBSTRATE_LABEL, SUBSTRATE_ORDER, meanSem } from './charts';

/**
 * Design guidance grounded in this repository's own numbers.
 *
 * The power calculator uses the observed OSD-476 means and spreads rather than a
 * textbook effect size, so the sample sizes it reports are the ones that study's
 * variance actually implies.
 */
export const PlanExperiment: React.FC = () => {
  const ph = useData<Phenotypes>(() => loadData('phenotypes'));
  const sub = useData<SubstrateData>(() => loadData('substrates'));

  if (ph.error) return <LoadError error={ph.error} />;
  if (!ph.data) return <Loading what="the design data" />;

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Plan</div>
        <h1>Designing a regolith experiment</h1>
        <p>
          What the datasets in this repository imply for a new study: how large an effect you should
          expect, how many plants you need to see it, which metadata decides whether anyone can reuse
          your result, and the specific mistakes visible in the record so far.
        </p>
      </div>

      <Power link={ph.data.linkage} />
      <Pitfalls />
      <SubstrateChoice sub={sub.data} />
      <Metadata />
    </div>
  );
};

// ---------------------------------------------------------------- power

/** Two-sample t-test power by the normal approximation, two-sided.
 *  Floored at 2: a t-test needs at least two observations per group however
 *  large the effect, and the approximation happily returns 1 for a huge d. */
function nPerGroup(delta: number, sd: number, power = 0.8): number {
  if (!isFinite(delta) || delta === 0 || !isFinite(sd) || sd <= 0) return NaN;
  const zA = 1.959963985, zB = power === 0.9 ? 1.2815516 : 0.8416212;   // 0.975 / power quantiles
  return Math.max(2, Math.ceil(2 * ((zA + zB) * sd / Math.abs(delta)) ** 2));
}

const TRAITS = [
  { key: 'leaf_final', label: 'Final leaf count', unit: '' },
  { key: 'leaf_rate_per_day', label: 'Leaf rate', unit: ' leaves/day' },
  { key: 'leaf_first_day', label: 'Days to first true leaf', unit: ' days' },
  { key: 'area_mm2_last', label: 'Rosette area', unit: ' mm²' },
] as const;

const Power: React.FC<{ link: LinkRow[] }> = ({ link }) => {
  const [trait, setTrait] = useState<string>('leaf_final');
  const [power, setPower] = useState(0.8);
  const linked = link.filter(l => l.join_confidence !== 'unlinked');
  const t = TRAITS.find(x => x.key === trait)!;

  const stats = useMemo(() => SUBSTRATE_ORDER.map(s => {
    const vals = linked.filter(l => l.substrate === s).map(l => Number((l as any)[trait])).filter(isFinite);
    const m = meanSem(vals);
    return { substrate: s, ...m, sd: m.sem * Math.sqrt(Math.max(m.n, 1)) };
  }), [linked, trait]);

  const ctrl = stats.find(s => s.substrate === 'JSC1A')!;
  const rows = stats.filter(s => s.substrate !== 'JSC1A').map(s => {
    const pooled = Math.sqrt(((ctrl.sd ** 2) + (s.sd ** 2)) / 2);
    const delta = s.mean - ctrl.mean;
    // `nRequired`, not `n` — `n` is the observed count and must not be shadowed.
    return { ...s, delta, pooled, nRequired: nPerGroup(delta, pooled, power) };
  });

  return (
    <div className="card pad" style={{ marginBottom: 16 }}>
      <div className="card-title"><Calculator size={16} /> How many plants do you need?</div>
      <p style={{ fontSize: '.87rem', lineHeight: 1.65 }}>
        Effect sizes and spreads measured from the {linked.length} phenotyped OSD-476 plants, not
        assumed. Pick a trait to see what it took to separate each Apollo regolith from the JSC-1A
        simulant, and how many plants per group a replication would need.
      </p>

      <div className="row wrap" style={{ gap: 8, marginBottom: 12 }}>
        {TRAITS.map(x => (
          <button key={x.key} className={`btn btn-sm ${trait === x.key ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setTrait(x.key)}>{x.label}</button>
        ))}
        <span style={{ flex: 1 }} />
        {[0.8, 0.9].map(p => (
          <button key={p} className={`btn btn-sm ${power === p ? 'btn-teal' : 'btn-ghost'}`} onClick={() => setPower(p)}>
            {p * 100}% power
          </button>
        ))}
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Substrate</th><th>n observed</th><th>Mean{t.unit}</th><th>SD</th>
              <th>Δ vs JSC-1A</th><th>Cohen's d</th><th>n / group for {power * 100}% power</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><span className="chip tag" style={{ color: SUBSTRATE_COLOUR.JSC1A, borderColor: SUBSTRATE_COLOUR.JSC1A }}>{SUBSTRATE_LABEL.JSC1A}</span></td>
              <td className="mono">{ctrl.n}</td>
              <td className="mono">{fx(ctrl.mean)}</td>
              <td className="mono">{fx(ctrl.sd)}</td>
              <td className="muted">reference</td><td className="muted">—</td><td className="muted">—</td>
            </tr>
            {rows.map(r => (
              <tr key={r.substrate}>
                <td><span className="chip tag" style={{ color: SUBSTRATE_COLOUR[r.substrate], borderColor: SUBSTRATE_COLOUR[r.substrate] }}>{SUBSTRATE_LABEL[r.substrate]}</span></td>
                <td className="mono">{r.n}</td>
                <td className="mono">{fx(r.mean)}</td>
                <td className="mono">{fx(r.sd)}</td>
                <td className="mono" style={{ color: r.delta < 0 ? 'var(--danger)' : 'var(--ok)' }}>{r.delta > 0 ? '+' : ''}{fx(r.delta)}</td>
                <td className="mono">{fx(Math.abs(r.delta) / r.pooled, 2)}</td>
                <td className="mono" style={{ fontWeight: 700 }}>{isFinite(r.nRequired) ? r.nRequired : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="muted" style={{ fontSize: '.79rem', lineHeight: 1.6, marginBottom: 0, marginTop: 10 }}>
        Two-sided two-sample t-test, α = 0.05, normal approximation, floored at 2 per group. With
        only four plants per substrate these standard deviations are themselves poorly estimated,
        so read the sample sizes as an order of magnitude, not a specification. The honest summary:
        regolith-versus-simulant is a large effect that a handful of plants will find, whereas
        distinguishing <em>one Apollo site from another</em> — where the means differ by less than
        a within-group standard deviation on most traits — is a far bigger experiment. Budget for
        the question you are actually asking.
      </p>
    </div>
  );
};

// ---------------------------------------------------------------- pitfalls

const PITFALLS = [
  {
    icon: AlertTriangle,
    title: 'Record the sowing date',
    body: (
      <>
        OSD-476 deposited an age at harvest but no sowing date, and the deposited ages and leaf
        counts admit no single consistent sowing date — the Apollo samples imply 2021-04-27 and one
        JSC-1A replicate implies 2021-04-28. Every growth curve in this database therefore runs on
        "days from the first plate scan" instead of plant age. One extra metadata field would have
        prevented that permanently.
      </>
    ),
  },
  {
    icon: TrendingDown,
    title: 'Thinning is a treatment, not housekeeping',
    body: (
      <>
        OSD-476 sowed 2–4 seeds per well and thinned to one on day 6 or 8. Rosette area drops
        between the day-2 and day-4 scans as a result, and the Apollo plants recover from it far
        more slowly than the simulant controls. If you thin, log the date per vessel — otherwise a
        handling event is indistinguishable from a substrate effect.
      </>
    ),
  },
  {
    icon: Beaker,
    title: 'Name the simulant batch, not just the simulant',
    body: (
      <>
        Simulant composition changes between production runs — the LHS-1 spec sheet in this
        repository is itself versioned "before 06/2021" and "6/2021–current". Two labs reporting
        "LHS-1" may not be comparable. Record supplier, batch or lot, and whether you rinsed,
        autoclaved or dry-heat sterilised it, because leaching in particular changes the ionic
        stress the root sees.
      </>
    ),
  },
  {
    icon: ClipboardList,
    title: 'Phenotype every sequenced plant',
    body: (
      <>
        Four of the twenty OSD-476 RNA-seq samples have no morphometrics at all, so they cannot
        enter any growth-anchored analysis — a 20% loss of an irreplaceable Apollo dataset for want
        of a photograph. If a plant is going into a sequencer, image it first.
      </>
    ),
  },
  {
    icon: AlertTriangle,
    title: 'Report the zeroes',
    body: (
      <>
        One Apollo 11 plant (GSM5691020) never produced a true leaf. That zero is one of the most
        informative points in the dataset and it survives only because the deposit recorded it
        rather than dropping a "failed" replicate. Germination failure and death are results.
      </>
    ),
  },
];

const Pitfalls: React.FC = () => (
  <div className="card pad" style={{ marginBottom: 16 }}>
    <div className="card-title"><AlertTriangle size={16} /> Five things the existing record gets wrong</div>
    <p style={{ fontSize: '.87rem', lineHeight: 1.65 }}>
      Each of these is visible in the data assembled here, and each cost real analytical power.
      They are cheap to avoid on the way in and impossible to fix afterwards.
    </p>
    <div className="grid" style={{ gap: 12 }}>
      {PITFALLS.map(p => (
        <div key={p.title} className="row" style={{ gap: 12, alignItems: 'flex-start' }}>
          <span className="land-ico" style={{ margin: 0, flexShrink: 0, width: 32, height: 32 }}><p.icon size={16} /></span>
          <div>
            <h4 style={{ margin: '4px 0 5px', fontSize: '.92rem' }}>{p.title}</h4>
            <p style={{ margin: 0, fontSize: '.85rem', lineHeight: 1.65, color: 'var(--muted)' }}>{p.body}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ---------------------------------------------------------------- substrate choice

const SubstrateChoice: React.FC<{ sub: SubstrateData | null }> = ({ sub }) => {
  if (!sub) return null;
  const comp = sub.chemistry_comparison.filter(c => c.difference_wt_pct != null)
    .sort((a, b) => Math.abs(b.difference_wt_pct!) - Math.abs(a.difference_wt_pct!));
  return (
    <div className="card pad" style={{ marginBottom: 16 }}>
      <div className="card-title"><Beaker size={16} /> Choosing a substrate commits you to a terrain</div>
      <p style={{ fontSize: '.87rem', lineHeight: 1.65 }}>
        LHS-1 is a lunar <em>highlands</em> simulant; Chang'e-5 returned <em>mare</em> soil. The
        differences below are systematic geology, not manufacturing tolerance. Before you pick a
        simulant, decide which lunar terrain your question is about — and say so in your methods.
      </p>
      <BarRow unit=" wt%" items={comp.map(c => ({
        label: c.oxide, value: c.difference_wt_pct!,
        colour: c.difference_wt_pct! > 0 ? 'var(--accent2)' : 'var(--danger)',
        note: c.difference_wt_pct! > 0 ? 'higher in LHS-1' : 'higher in real soil',
      }))} />
      <p className="muted" style={{ fontSize: '.79rem', marginTop: 10, marginBottom: 0 }}>
        Iron and titanium are the largest gaps, and both bear directly on the ionic and oxidative
        stress that Apollo-grown plants showed. A highlands simulant will systematically understate
        them relative to mare regolith.
      </p>
    </div>
  );
};

// ---------------------------------------------------------------- metadata

const Metadata: React.FC = () => (
  <div className="card pad">
    <div className="card-title"><FileSpreadsheet size={16} /> Metadata that makes your study reusable</div>
    <p style={{ fontSize: '.87rem', lineHeight: 1.65 }}>
      NASA OSDR describes studies in ISA-Tab: an investigation file, a sample file with one row per
      biological sample and its factor values, and an assay file per measurement type. Deciding the
      factor names before you start is what lets an analysis like the one on this site exist at all
      — OSD-476's growth-anchored reanalysis is possible <em>only</em> because its assay file
      recorded a plate and a leaf count against each sequenced sample.
    </p>
    <dl className="kv" style={{ marginBottom: 14 }}>
      <dt>Factor value</dt><dd>the thing you varied — <span className="mono">Treatment: Apollo 11 regolith</span></dd>
      <dt>Characteristics</dt><dd>fixed properties — organism, genotype, cultivar, seed source</dd>
      <dt>Parameter value</dt><dd>protocol settings — growth medium, light cycle, temperature, quantity</dd>
      <dt>Assay linkage</dt><dd>the column that ties one sample to one image, plate or sequencing run</dd>
    </dl>
    <p style={{ fontSize: '.87rem', lineHeight: 1.65, marginBottom: 0 }}>
      A ground regolith substrate study template is included in this repository at{' '}
      <span className="mono">data/awg/osdr_substrate_isa_template.xlsx</span>, and the Contribute
      page's Epicollect5 form is shaped so a phone-collected series exports into the same
      vocabulary. Whichever route you take, the single most valuable habit is to give every
      sequenced plant an imaging identifier and every image a sample identifier — the join is worth
      more than either dataset alone.
    </p>
  </div>
);

const fx = (v: number, dp = 1) => (v == null || !isFinite(v) ? '—' : v.toFixed(dp));
