// Loader for the pre-baked datasets in `public/data/`.
//
// Why baked and not fetched live: the NASA OSDR API answers
// `Access-Control-Allow-Origin: osdr.nasa.gov`, the OSDR biodata API sends no
// CORS header, and NASA PSI runs the same GeoDE backend — so a browser on
// github.io cannot call any of them. `scripts/01_fetch_osdr.py`,
// `02_fetch_psi.py` and `09_export_site_data.py` harvest them offline and write
// the JSON this module reads. Every number the site shows therefore has a
// committed table behind it.

const cache = new Map<string, Promise<any>>();

export function loadData<T = any>(name: string): Promise<T> {
  const url = `${import.meta.env.BASE_URL}data/${name}.json`;
  if (!cache.has(url)) {
    cache.set(url, fetch(url).then(r => {
      if (!r.ok) throw new Error(`${name}.json — HTTP ${r.status}`);
      return r.json();
    }).catch(e => { cache.delete(url); throw e; }));
  }
  return cache.get(url)! as Promise<T>;
}

/** Columnar JSON ({col: values[]}) back to row objects. */
export function rows<T = Record<string, any>>(col: Record<string, any[]> | undefined): T[] {
  if (!col) return [];
  const keys = Object.keys(col);
  const n = keys.length ? col[keys[0]].length : 0;
  const out: any[] = new Array(n);
  for (let i = 0; i < n; i++) {
    const o: any = {};
    for (const k of keys) o[k] = col[k][i];
    out[i] = o;
  }
  return out;
}

// ---- shapes of the baked files (only the fields the UI reads) ----

export interface OsdrStudy {
  accession: string; title: string; publication: string; organism: string;
  material: string; factors: string; measurements: string; technology: string;
  authors: string; released: string; description: string; why_regolith: string;
  files: number; images: number; image_mb: number; categories: string[]; url: string;
}
export interface OsdrCatalog {
  source: string; api: string; accessed: string; note: string; studies: OsdrStudy[];
}

export interface PsiStudy {
  accession: string; title: string; acronym: string; research_area: string;
  sub_area: string; project_type: string; platform: string; keywords: string[];
  start: string; end: string; relevance: string; url: string;
}
export interface PsiCatalog {
  source: string; api: string; accessed: string; caveat: string;
  curated: PsiStudy[]; other_hits: PsiStudy[];
}

export interface LinkRow {
  gsm: string; treatment: string; substrate: string; replicate: number | null;
  plate: string | null; join_confidence: 'exact' | 'plate_mean' | 'unlinked';
  n_plants: number; plant_ids: string;
  age_at_harvest_days: number | null; n_leaves_at_harvest: number | null;
  dev_stage_at_harvest: string;
  leaf_first_day: number | null; leaf_final: number | null;
  leaf_rate_per_day: number | null; leaf_auc: number | null;
  area_mm2_first: number | null; area_mm2_last: number | null;
  rgr_area_per_day: number | null; solidity_last: number | null;
  height_mm_last: number | null; longest_path_mm_last: number | null;
  qc_leaf_area_spearman: number; qc_leaf_area_p: number;
  qc_solidity_out_of_range: boolean;
}
export interface Phenotypes {
  study: string; note: string; time_axis: string;
  leaf_counts: Record<string, any[]>;
  plantcv_traits: Record<string, any[]>;
  linkage: LinkRow[];
  sowing_date_check: { gsm: string; candidate_sowing_dates: string }[];
}

export interface GeneRow {
  gene: string; SYMBOL: string; GENENAME: string;
  analysis?: string; covariate?: string; spearman_rho?: number;
  primary?: number; within_lunar?: number; fdr?: number; p_value?: number;
  mean_vst?: number; n_samples?: number;
}
export interface GrowthGenes {
  method: string; fdr_threshold: number;
  covariates: { covariate: string; covariate_description: string }[];
  summary: { analysis: string; covariate: string; genes_tested: number; genes_fdr05: number; max_abs_rho: number }[];
  overlap_with_published: { published_degs_any_apollo_vs_jsc1a: number; growth_correlated_robust: number; overlap: number; growth_only: number; contrasts_used: string }[];
  robust: GeneRow[];
  top_per_set: GeneRow[];
  examples: { gene: string; label: string; gsm: string; substrate: string; leaf_rate_per_day: number; leaf_final: number; vst: number; spearman_rho: number }[];
}

export interface Transcriptomics {
  study: string; source: string; top_n: number;
  contrast_summary: { contrast: string; n_tested: number; n_sig: number; n_up: number; n_down: number }[];
  top_genes_per_contrast: Record<string, { gene: string; symbol: string; name: string; log2fc: number; adj_p: number }[]>;
  broad_lunar_model: {
    description: string; n_genes: number; n_sig: number;
    data: Record<string, any[]>;
  };
}

export interface Substrates {
  probe: {
    description: string;
    units: { column: string; source_column: string; unit_note: string }[];
    endpoint: Record<string, any>[];
    timeseries: Record<string, any[]>;
  };
  simulant_lhs1: {
    mineralogy: { component: string; wt_pct: number; simulant: string; source: string }[];
    chemistry: { oxide: string; wt_pct: number; simulant: string; source: string }[];
    physical: { property: string; value: string; simulant: string; source: string }[];
  };
  lunar_soil_ce5: { sample: string; method: string; analyte: string; value: number; unit: string; uncertainty_k2: number | null; reference: string }[];
  chemistry_comparison: { oxide: string; lhs1_wt_pct: number | null; ce5_wt_pct: number | null; difference_wt_pct: number | null }[];
}

export interface Enrichment {
  method: string; shown: string;
  terms: {
    gene_set: string; analysis: string; covariate: string; direction: string;
    go_id: string; go_name: string; go_aspect: string;
    genes_in_set: number; genes_in_term: number; overlap: number;
    fold_enrichment: number; p_value: number; fdr: number; example_genes: string;
  }[];
}

export interface Manifest {
  built: string; commit: string;
  counts: Record<string, number>;
  provenance: { name: string; url: string; note: string }[];
}

/**
 * NASA curation provenance for the material OSD-476 grew plants in, plus the
 * ARES simulant photographs and the coverage of NASA's own archives.
 * Written by `scripts/16_export_curation_site_data.py`.
 */
export interface CurationData {
  regoliths: {
    generic: string; mission: string;
    sampleType: string; sampleSubtype: string;
    originalWeightG: number | null; pristinityPct: number | null; pristinityDate: string | null;
    station: string | null; landmark: string | null; bagNumber: string | null;
    description: string | null;
    hasThinSection: boolean; nThinSections: number;
    displaySamples: string | null;
    osd476Splits: string[];
    photos: {
      photo: string; type: string; description: string;
      width: string; height: string; fileSize: string;
      jpegUrl: string; tifUrl: string;
    }[];
    nPhotos: number;
    /** null means the compendium was not consulted — unknown, not absent. */
    hasCompendium: boolean | null;
    compendiumUrl: string;
    a3d: { key: string; display_name: string; classification: string; viewer_url: string }[];
  }[];
  simulants: {
    name: string; nameAsPublished: string; wasCorrected: boolean; surface: string;
    bench: string | null; micro: string | null;
    benchSourceUrl: string; microSourceUrl: string;
  }[];
  simulantCorrections: {
    name_as_published: string; image_stem: string; surface: string; corrected_to: string;
  }[];
  simulantStock: { simulant: string; analog: string }[];
  coverage: {
    n_samples: number; n_with_pds_photos: number; n_pds_photo_records: number;
    n_with_thin_section: number; n_with_3d_scan: number; n_with_display: number;
    n_soil_samples: number; n_soil_photographed: number;
    compendium_consulted: boolean; n_with_compendium: number | null;
    by_mission: Record<string, { n: number; photographed: number }>;
    osd476: Record<string, {
      mission: string; has_pds_photos: boolean; n_pds_photos: number;
      has_compendium: boolean | null; has_thin_section: boolean;
    }>;
  };
  pdsIndexProvenance: {
    volume: string; index: string; layout: string;
    declared_rows: number | null; parsed_rows: number;
    rows_match_label: boolean | null; bytes_accounted_for: boolean | null;
  }[];
  sources: Record<string, string>;
}
