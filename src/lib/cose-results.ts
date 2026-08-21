// Shared analysis-results store for the CoSE image ecosystem.
//
// The AstroBotany database, AstroRoot, and Leaf Pigment & Size apps are all
// served from the SAME origin (dr-richard-barker.github.io), and IndexedDB is
// scoped to the origin (not the path), so they share this store. A tool writes
// its tailored metrics keyed by the image ref the database handed it; the
// database reads them back — a serverless round-trip.
//
// KEEP THIS FILE IDENTICAL (DB name, store name, record shape) across all three
// repos, or they won't see each other's results.

const DB_NAME = 'cose-analysis';
const STORE = 'results';

export interface AnalysisResult {
  id: string;            // `${ref}::${tool}`
  ref: string;           // image ref handed off by the database (slug::uuid, or a URL)
  imageUrl: string;
  tool: string;          // machine id, e.g. 'astroroot' | 'leaf-pigment-size'
  toolName: string;      // display name
  metrics: Record<string, string | number>;
  generatedAt: string;   // ISO
}

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'id' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function putResult(r: Omit<AnalysisResult, 'id'>): Promise<void> {
  const db = await open();
  const rec: AnalysisResult = { ...r, id: `${r.ref}::${r.tool}` };
  await new Promise<void>((resolve, reject) => {
    const t = db.transaction(STORE, 'readwrite');
    t.objectStore(STORE).put(rec);
    t.oncomplete = () => { db.close(); resolve(); };
    t.onerror = () => reject(t.error);
  });
}

async function getAll(): Promise<AnalysisResult[]> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const req = db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
    req.onsuccess = () => { db.close(); resolve(req.result as AnalysisResult[]); };
    req.onerror = () => reject(req.error);
  });
}

export async function getResults(ref: string): Promise<AnalysisResult[]> {
  return (await getAll()).filter(r => r.ref === ref).sort((a, b) => (b.generatedAt > a.generatedAt ? 1 : -1));
}
export const allResults = getAll;
