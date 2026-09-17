// Resolving "what the plant grew in" to one identified material.
//
// The repository writes substrates eight different ways — `A11` in a chart,
// "Apollo 11 regolith" in an OSDR factor, "Lunar simulant" in a probe trace,
// `JSC-1A` in NASA's simulant table, `10084` in NASA's curation database, and
// free text in a contribution form. `scripts/17_build_substrate_registry.py`
// maps them onto one `substrate_id`; this reads that table.
//
// The point of the registry is that it distinguishes *identified* from
// *unidentified*. `resolution` is:
//
//   deposit-stated   the depositing study named the sample (the Apollo soils)
//   exact            this repository uses it under a name that matches a source
//   catalogue-only   reference data; nothing here uses it
//   unresolved       named too vaguely to key to any material — see `evidence`
//
// Nothing resolves by guessing. A substrate recorded only as "Lunar simulant"
// stays unresolved, because several ARES simulants fit that label equally well
// and picking one would invent a provenance the record does not support.

import { loadData } from './sitedata';

export interface SubstrateRow {
  substrate_id: string;
  label: string;
  short: string;
  kind: 'apollo_soil' | 'lunar_simulant' | 'mars_simulant' | 'terrestrial_medium' | string;
  apollo_generic: string;
  ares_simulant: string;
  name_as_published: string;
  surface: string;
  mission: string;
  landmark: string;
  original_weight_g: number | string;
  pristinity_pct: number | string;
  particle_size: string;
  n_photos: number;
  has_compendium: boolean | string;
  resolution: 'deposit-stated' | 'exact' | 'catalogue-only' | 'unresolved' | string;
  evidence: string;
  aliases: string;
}

export interface SubstrateRegistry {
  note: string;
  substrates: SubstrateRow[];
  alias_index: Record<string, string>;
}

export const loadRegistry = () => loadData<SubstrateRegistry>('substrates_registry');

/** The substrate a name refers to, or null when nothing claims that name. */
export function resolve(reg: SubstrateRegistry, name: string): SubstrateRow | null {
  const id = reg.alias_index[name.trim()];
  if (!id) return null;
  return reg.substrates.find(s => s.substrate_id === id) ?? null;
}

export const isIdentified = (s: SubstrateRow | null): boolean =>
  !!s && s.resolution !== 'unresolved';

/** How much of what this database measured can be traced to a named material. */
export function traceability(reg: SubstrateRegistry, names: string[]) {
  const rows = names.map(n => resolve(reg, n));
  const planetary = rows.filter(
    r => r && (r.kind === 'lunar_simulant' || r.kind === 'mars_simulant' || r.kind === 'apollo_soil'),
  ) as SubstrateRow[];
  return {
    total: names.length,
    unmatched: rows.filter(r => r === null).length,
    planetary: planetary.length,
    planetaryIdentified: planetary.filter(isIdentified).length,
    unresolved: planetary.filter(r => !isIdentified(r)),
  };
}

/** Where a substrate can be read about, for the links under a chip. */
export function links(s: SubstrateRow) {
  const out: { label: string; href: string }[] = [];
  if (s.apollo_generic) {
    out.push({
      label: `Sample ${s.apollo_generic}`,
      href: 'https://curator.jsc.nasa.gov/lunar/samplecatalog/index.cfm',
    });
    if (s.has_compendium === true || s.has_compendium === 'True') {
      out.push({
        label: 'Compendium',
        href: `https://curator.jsc.nasa.gov/lunar/lsc/${s.apollo_generic}.pdf`,
      });
    }
  }
  if (s.ares_simulant) {
    out.push({
      label: 'ARES simulant lab',
      href: 'https://ares.jsc.nasa.gov/projects/simulants/development-lab.html',
    });
  }
  return out;
}
