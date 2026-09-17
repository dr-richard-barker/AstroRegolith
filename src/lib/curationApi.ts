// The one NASA API this site can call from the browser.
//
// Every other dataset here is baked into `public/data/` because the
// repositories refuse cross-origin requests: OSDR answers
// `Access-Control-Allow-Origin: osdr.nasa.gov`, its biodata API sends no CORS
// header at all, and PSI runs the same GeoDE backend.
//
// NASA's Apollo curation API is different — it answers
// `Access-Control-Allow-Origin: *`, so a page on github.io may call it
// directly. That makes a live lookup possible for any of the 2,511 samples,
// rather than only the three this database bakes.
//
// This is deliberately an *extra*. Nothing the site states as a result comes
// from here: every displayed figure is read from a committed table, so a
// number on a page cannot drift with a remote change. A failure here degrades
// one lookup box and nothing else.
//
// API documentation: https://curator.jsc.nasa.gov/lunar/api/index.cfm

const BASE = 'https://curator.jsc.nasa.gov/rest/lunarapi/samples';
const TIMEOUT_MS = 12_000;

/** One row of the curation API's `sampledetails` response. */
export interface LunarSample {
  GENERIC: string;
  SAMPLEID: number | null;
  MISSION: string;
  STATION: string | null;
  LANDMARK: string | null;
  BAGNUMBER: string | null;
  ORIGINALWEIGHT: number | null;
  SAMPLETYPE: string | null;
  SAMPLESUBTYPE: string | null;
  PRISTINITY: number | null;
  PRISTINITYDATE: string | null;
  HASTHINSECTION: boolean | null;
  HASDISPLAYSAMPLE: boolean | null;
  DISPLAYSAMPLENUMBER: string | null;
  GENERICDESCRIPTION: string | null;
}

async function getJson(url: string): Promise<unknown> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { signal: ctrl.signal, headers: { Accept: 'application/json' } });
    if (!r.ok) throw new Error(`NASA curation API returned HTTP ${r.status}`);
    return await r.json();
  } catch (e: any) {
    if (e?.name === 'AbortError') throw new Error('NASA curation API timed out');
    // A network or CORS failure is surfaced, never swallowed into a default.
    throw new Error(e?.message || 'could not reach the NASA curation API');
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Look up one Apollo sample by its generic number.
 *
 * Resolves to `null` when the collection holds no such sample — distinct from
 * throwing, which means the lookup itself failed.
 */
export async function lookupSample(generic: string): Promise<LunarSample | null> {
  const id = generic.trim();
  if (!/^\d{4,5}$/.test(id)) {
    throw new Error('An Apollo sample number is four or five digits, e.g. 10084.');
  }
  const d = await getJson(`${BASE}/sampledetails/${encodeURIComponent(id)}`);
  if (!Array.isArray(d)) throw new Error('unexpected response from the curation API');
  return (d[0] as LunarSample) ?? null;
}

/** Every sample from one mission, e.g. `samplesByMission('Apollo 17')`. */
export async function samplesByMission(mission: string): Promise<LunarSample[]> {
  const d = await getJson(`${BASE}/samplesbymission/${encodeURIComponent(mission)}`);
  if (!Array.isArray(d)) throw new Error('unexpected response from the curation API');
  return d as LunarSample[];
}
