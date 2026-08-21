// Tiny promise wrapper over IndexedDB for locally-uploaded image sources and RSML traces.
// Three stores:
// - "sources": metadata for an uploaded batch, keyed by id.
// - "images": compressed image blobs, keyed by `${sourceId}::${filename}`.
// - "rsml": raw RSML XML strings, keyed by `${projectSlug}::${filename}`.

const DB_NAME = 'astrobotany-local';
const VERSION = 2;

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('sources')) db.createObjectStore('sources', { keyPath: 'id' });
      if (!db.objectStoreNames.contains('images')) db.createObjectStore('images');
      if (!db.objectStoreNames.contains('rsml')) db.createObjectStore('rsml');
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest): Promise<T> {
  return open().then(db => new Promise<T>((resolve, reject) => {
    const t = db.transaction(store, mode);
    const req = fn(t.objectStore(store));
    req.onsuccess = () => resolve(req.result as T);
    req.onerror = () => reject(req.error);
    t.oncomplete = () => db.close();
  }));
}

export const idbPut = (store: string, value: any, key?: IDBValidKey) =>
  tx<void>(store, 'readwrite', s => (key !== undefined ? s.put(value, key) : s.put(value)));
export const idbGet = <T>(store: string, key: IDBValidKey) => tx<T>(store, 'readonly', s => s.get(key));
export const idbGetAll = <T>(store: string) => tx<T[]>(store, 'readonly', s => s.getAll());
export const idbDelete = (store: string, key: IDBValidKey) => tx<void>(store, 'readwrite', s => s.delete(key));

// Delete a source record + all of its image blobs.
export async function idbDeleteSource(id: string): Promise<void> {
  const db = await open();
  await new Promise<void>((resolve, reject) => {
    const t = db.transaction(['sources', 'images'], 'readwrite');
    t.objectStore('sources').delete(id);
    const imgs = t.objectStore('images');
    const cursor = imgs.openKeyCursor();
    cursor.onsuccess = () => {
      const c = cursor.result;
      if (c) { if (String(c.key).startsWith(id + '::')) imgs.delete(c.key); c.continue(); }
    };
    t.oncomplete = () => { db.close(); resolve(); };
    t.onerror = () => reject(t.error);
  });
}

// RSML storage helpers
export async function saveRsml(projectSlug: string, filename: string, content: string): Promise<void> {
  await idbPut('rsml', content, `${projectSlug}::${filename}`);
}

export async function getProjectRsmls(projectSlug: string): Promise<{ filename: string; content: string }[]> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction('rsml', 'readonly');
    const store = t.objectStore('rsml');
    const results: { filename: string; content: string }[] = [];
    const range = IDBKeyRange.bound(projectSlug + '::', projectSlug + '::\uffff');
    const req = store.openCursor(range);
    req.onsuccess = () => {
      const cursor = req.result;
      if (cursor) {
        const key = String(cursor.key);
        results.push({
          filename: key.substring(projectSlug.length + 2),
          content: cursor.value as string
        });
        cursor.continue();
      } else {
        resolve(results);
      }
    };
    req.onerror = () => reject(req.error);
  });
}

export async function deleteProjectRsmls(projectSlug: string): Promise<void> {
  const db = await open();
  return new Promise<void>((resolve, reject) => {
    const t = db.transaction('rsml', 'readwrite');
    const store = t.objectStore('rsml');
    const range = IDBKeyRange.bound(projectSlug + '::', projectSlug + '::\uffff');
    const req = store.openCursor(range);
    req.onsuccess = () => {
      const cursor = req.result;
      if (cursor) {
        store.delete(cursor.key);
        cursor.continue();
      } else {
        resolve();
      }
    };
    req.onerror = () => reject(t.error);
  });
}

export async function getAllRsmls(): Promise<{ key: string; filename: string; content: string }[]> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction('rsml', 'readonly');
    const store = t.objectStore('rsml');
    const results: { key: string; filename: string; content: string }[] = [];
    const req = store.openCursor();
    req.onsuccess = () => {
      const cursor = req.result;
      if (cursor) {
        const k = String(cursor.key);
        results.push({
          key: k,
          filename: k.split('::')[1] || k,
          content: cursor.value as string
        });
        cursor.continue();
      } else {
        resolve(results);
      }
    };
    req.onerror = () => reject(req.error);
  });
}
