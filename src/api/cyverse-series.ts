// CyVerse timelapse series source. Mirrors the GitHub folder structure but loads from
// a catalog.json hosted on GitHub Pages or any CORS-enabled endpoint.
//
// Structure:
//   https://example.com/catalog.json
//   └─ series[]: { name, path, frames, species, treatment, cadence, ... }
//
// Each series folder contains:
//   frames/                    # JPEG sequence
//   metadata.csv              # Frame table (filename, datetime, cadence, original_path, md5, ...)
//   timelapse.mp4            # Playable proxy video
//   manifest.json            # Series metadata
//   datapackage.json         # Frictionless metadata

import { parseSidecarText, parseFilenameMeta, metaFor, type MetaMap } from './github';
import type { Ec5Entry, EntryField } from '../types';

export interface CyVerseSeries {
  name: string;              // Display name
  path: string;              // Relative path in repo (e.g. "FlashLapse_Straight_growth")
  frames: number;            // Total frame count
  cadence_seconds?: number;  // Median interval between frames
  date_range?: { start: string; end: string; duration_hours: number };
  species?: string;
  treatment?: string;
  genotype?: string;
  irods_collection?: string; // Original iRODS path
}

export interface CyVerseCatalog {
  name: string;
  url: string;               // Base URL for series folders
  series: CyVerseSeries[];
  updated_at?: string;
}

export const cyverseId = (catalogUrl: string, seriesName: string) =>
  `cyverse:${catalogUrl}|${encodeURIComponent(seriesName)}`;

export const parseCyverseId = (id: string): { catalogUrl: string; seriesName: string } | null => {
  const m = id.match(/^cyverse:(.+)\|(.+)$/);
  if (!m) return null;
  return { catalogUrl: m[1], seriesName: decodeURIComponent(m[2]) };
};

// Load catalog.json from a remote URL
export async function fetchCatalog(catalogUrl: string, timeoutMs = 30000): Promise<CyVerseCatalog> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(catalogUrl, { signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.series || !Array.isArray(data.series)) throw new Error('Invalid catalog format');
    return data;
  } finally {
    clearTimeout(timeout);
  }
}

// Load a single series' metadata.csv and convert to entry-like objects
export async function fetchSeriesMetadata(seriesUrl: string): Promise<{ rows: Record<string, string>[]; meta: MetaMap }> {
  const csvUrl = new URL('metadata.csv', seriesUrl).href;
  const res = await fetch(csvUrl);
  if (!res.ok) throw new Error(`Failed to fetch ${csvUrl}`);
  const text = await res.text();

  const rows: Record<string, string>[] = [];
  const lines = text.trim().split('\n');
  if (lines.length < 1) throw new Error('Empty metadata.csv');

  const headers = lines[0].split(',').map(h => h.trim());
  for (const line of lines.slice(1)) {
    const values = line.split(',').map(v => v.trim());
    const row: Record<string, string> = {};
    for (let i = 0; i < headers.length; i++) {
      row[headers[i]] = values[i] || '';
    }
    rows.push(row);
  }

  // Convert to MetaMap (keyed by filename, as github.ts does)
  const meta: MetaMap = new Map();
  for (const row of rows) {
    const fn = row.filename?.toLowerCase() || '';
    if (fn) meta.set(fn, row);
  }

  return { rows, meta };
}

// Convert a series catalog entry + frame row into an Ec5Entry-like object
export function seriesFrameToEntry(
  series: CyVerseSeries,
  frameRow: Record<string, string>,
  frameIndex: number,
  catalogUrl: string,
  basePath: string
): Ec5Entry {
  const seriesUrl = new URL(series.path + '/', basePath).href;
  const frameUrl = new URL(`frames/${frameRow.filename || ''}`, seriesUrl).href;
  const videoUrl = new URL('timelapse.mp4', seriesUrl).href;

  const uuid = `${series.path}::${frameIndex}`;
  const catalogId = cyverseId(catalogUrl, series.name);

  const fields: EntryField[] = [];
  if (frameRow.datetime_utc) fields.push({ name: 'Captured', value: frameRow.datetime_utc });
  if (frameRow.treatment) fields.push({ name: 'Treatment', value: frameRow.treatment });
  if (frameRow.genotype) fields.push({ name: 'Genotype', value: frameRow.genotype });
  if (frameRow.cadence_seconds) fields.push({ name: 'Cadence', value: `${frameRow.cadence_seconds} sec` });
  if (frameRow.notes) fields.push({ name: 'Notes', value: frameRow.notes });

  return {
    uuid,
    project: catalogId,
    title: frameRow.filename || `Frame ${frameIndex + 1}`,
    createdAt: frameRow.datetime_utc || new Date().toISOString(),
    uploadedAt: new Date().toISOString(),
    photoUrl: frameUrl,
    thumbUrl: frameUrl,  // Same as full-res for now; could generate thumbnails
    videoUrl,           // Link to the full series video
    fields,
    species: series.species || frameRow.species || null,
    gps: null,
    marker: null,
  };
}
