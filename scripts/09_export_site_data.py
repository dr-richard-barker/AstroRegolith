#!/usr/bin/env python3
"""Bake every table the static site renders into `public/data/*.json`.

The site is a Vite/React SPA on GitHub Pages with no backend, and neither NASA
API allows cross-origin browser calls, so all of its numbers arrive as JSON
committed alongside the code. Keeping that translation in one script means the
site can never show a figure the tables do not support.

Large tables are emitted columnar and rounded — the same information, roughly a
third of the bytes of an array-of-objects, and far friendlier to gzip.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, RESULTS, ROOT, SITE_DATA, log, write_json  # noqa: E402

T, E = RESULTS / "tables", RESULTS / "enrichment"
DE = DATA / "osdr" / "raw_large" / "differential_expression_rRNArm.csv"
TOP_PER_CONTRAST = 300


# Columns holding a probability. Rounding these to a fixed number of decimals
# collapses everything below the last place to exactly 0, which then reads as
# "-log10(p) = infinity" downstream. They are rounded to significant figures.
P_COLUMNS = re.compile(r"(^|_)(p_value|pvalue|p|padj|fdr|adj_p|q_value)$", re.I)


def sigfig(v: float, digits: int = 4) -> float:
    """Round to `digits` significant figures, preserving very small magnitudes."""
    if v is None or not np.isfinite(v) or v == 0:
        return 0.0 if v == 0 else v
    return float(f"%.{digits}g" % v)


def _round_col(name: str, values, decimals: int):
    if P_COLUMNS.search(name):
        return [None if pd.isna(v) else sigfig(float(v)) for v in values]
    return [None if pd.isna(v) else round(float(v), decimals) for v in values]


def records(df: pd.DataFrame, round_to: int = 4) -> list:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_bool_dtype(out[c]):
            out[c] = _round_col(c, out[c], round_to)
    return out.replace({np.nan: None}).to_dict("records")


def columnar(df: pd.DataFrame, rounding: dict) -> dict:
    out = {}
    for c in df.columns:
        col = df[c]
        if c in rounding or P_COLUMNS.search(c):
            out[c] = _round_col(c, col, rounding.get(c, 4))
        else:
            out[c] = [None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in col]
    return out


def export_phenotypes():
    leaves = pd.read_csv(T / "leaf_counts_long.csv")
    traits = pd.read_csv(T / "plantcv_traits_long.csv")
    link = pd.read_csv(T / "sample_phenotype_expression_map.csv")
    check = pd.read_csv(T / "sowing_date_check.csv")
    write_json(SITE_DATA / "phenotypes.json", {
        "study": "OSD-476",
        "note": ("Leaf counts come from the OSDR ISA-Tab morphometric assay; rosette "
                 "shape traits are PlantCV re-scores of the same plate scans. They are "
                 "independent measurements of the same 16 sequenced plants."),
        "time_axis": ("`day` counts from the first plate scan, 2021-05-02. No sowing "
                      "date is published: the deposited ages and leaf counts admit no "
                      "single sowing date (see sowing_date_check)."),
        "leaf_counts": columnar(leaves, {"n_leaves": 0, "day": 0}),
        "plantcv_traits": columnar(traits, {
            "area_mm2": 4, "convex_hull_area_mm2": 4, "solidity": 4, "perimeter_mm": 3,
            "width_mm": 3, "height_mm": 3, "longest_path_mm": 3,
            "ellipse_major_axis_mm": 3, "ellipse_minor_axis_mm": 3,
            "ellipse_eccentricity": 4, "day": 0}),
        "linkage": records(link),
        "sowing_date_check": records(check),
    })
    log(f"  phenotypes.json  ({len(leaves)} leaf rows, {len(traits)} trait rows, "
        f"{len(link)} samples)")


def export_transcriptomics():
    bl = pd.read_csv(T / "broad_lunar_model.csv")
    bl = bl.dropna(subset=["log2fc_lunar_vs_simulant"])
    bl["symbol"] = bl["symbol"].fillna("")

    head = pd.read_csv(DE, nrows=0).columns
    contrasts = sorted({c.replace("Adj.p.value_", "") for c in head
                        if c.startswith("Adj.p.value_")})
    use = ["TAIR", "SYMBOL", "GENENAME"] + \
          [f"{p}{c}" for c in contrasts for p in ("Log2fc_", "Adj.p.value_")]
    de = pd.read_csv(DE, usecols=use)

    summary, tops = [], {}
    for c in contrasts:
        l2, ap = de[f"Log2fc_{c}"], de[f"Adj.p.value_{c}"]
        sig = ap < 0.05
        summary.append({"contrast": c, "n_tested": int(ap.notna().sum()),
                        "n_sig": int(sig.sum()),
                        "n_up": int((sig & (l2 > 0)).sum()),
                        "n_down": int((sig & (l2 < 0)).sum())})
        d = de.loc[sig, ["TAIR", "SYMBOL", "GENENAME"]].copy()
        d["log2fc"], d["adj_p"] = l2[sig], ap[sig]
        d = d.reindex(d["log2fc"].abs().sort_values(ascending=False).index).head(TOP_PER_CONTRAST)
        d["GENENAME"] = d["GENENAME"].fillna("").str.slice(0, 160)
        tops[c] = records(d.rename(columns={"TAIR": "gene", "SYMBOL": "symbol",
                                            "GENENAME": "name"}).fillna(""), 4)

    write_json(SITE_DATA / "transcriptomics.json", {
        "study": "OSD-476",
        "source": "GLDS-476 GeneLab RNA-seq differential expression (rRNA-removed)",
        "contrast_summary": summary,
        "top_genes_per_contrast": tops,
        "top_n": TOP_PER_CONTRAST,
        "broad_lunar_model": {
            "description": ("All Apollo samples pooled against JSC-1A simulant in one "
                            "linear model, rather than site-by-site — the Broad Lunar "
                            "model. Re-tidied from the original analysis."),
            "n_genes": len(bl), "n_sig": int((bl["padj"] < 0.05).sum()),
            "data": columnar(bl, {"log2fc_lunar_vs_simulant": 3, "padj": 6}),
        },
    })
    log(f"  transcriptomics.json  ({len(contrasts)} contrasts, "
        f"{len(bl)} Broad-Lunar genes)")


def export_growth_genes():
    res = pd.read_csv(T / "growth_correlated_genes.csv.gz")
    ann = pd.read_csv(T / "gene_annotation.csv").set_index("gene")
    res = res.join(ann, on="gene")
    robust = pd.read_csv(T / "growth_genes_robust.csv")
    ex = pd.read_csv(T / "expression_examples.csv")
    ov = pd.read_csv(T / "growth_gene_overlap.csv")

    res["SYMBOL"] = res["SYMBOL"].fillna("")
    res["GENENAME"] = res["GENENAME"].fillna("").str.slice(0, 160)
    top = (res[res["fdr"] < 0.05]
           .sort_values("p_value")
           .groupby(["analysis", "covariate"], as_index=False)
           .head(150))

    robust["SYMBOL"] = robust["SYMBOL"].fillna("")
    robust["GENENAME"] = robust["GENENAME"].fillna("").str.slice(0, 160)

    write_json(SITE_DATA / "growth_genes.json", {
        "method": ("Spearman correlation of VST expression against each growth "
                   "covariate, Benjamini-Hochberg FDR. `primary` uses all 16 "
                   "phenotyped plants; `within_lunar` uses the 12 Apollo plants only, "
                   "where substrate no longer tracks growth. `robust` = significant in "
                   "both with a consistent sign."),
        "fdr_threshold": 0.05,
        "covariates": (pd.read_csv(T / "growth_covariates.csv")
                       .rename(columns={"description": "covariate_description"})
                       .to_dict("records")),
        "summary": records(pd.read_csv(E / "growth_gene_sets.csv")),
        "overlap_with_published": records(ov, 0),
        "robust": records(robust),
        "top_per_set": records(top),
        "examples": records(ex),
    })
    log(f"  growth_genes.json  ({len(robust)} robust, {len(top)} top rows)")


def export_substrates():
    write_json(SITE_DATA / "substrates.json", {
        "probe": {
            "description": ("CoSE Lunar Large Chamber soil probe: 15 mL of substrate in "
                            "an acrylic pouch, 5 mL water added at ~5 min intervals, "
                            "readings every 15 s. Unpublished."),
            "units": records(pd.read_csv(T / "substrate_probe_units.csv")),
            "endpoint": records(pd.read_csv(T / "substrate_probe_endpoint.csv")),
            "timeseries": columnar(pd.read_csv(T / "substrate_probe_timeseries.csv"),
                                   {"time_min": 2, "water_content_pct": 2, "ec_us_cm": 1,
                                    "ph": 2, "nitrogen": 1, "phosphorus": 1,
                                    "potassium": 1, "water_added_ml": 1}),
        },
        "simulant_lhs1": {
            "mineralogy": records(pd.read_csv(T / "simulant_lhs1_mineralogy.csv")),
            "chemistry": records(pd.read_csv(T / "simulant_lhs1_chemistry.csv")),
            "physical": records(pd.read_csv(T / "simulant_lhs1_physical.csv")),
        },
        "lunar_soil_ce5": records(pd.read_csv(T / "lunar_soil_ce5_composition.csv")),
        "chemistry_comparison": records(pd.read_csv(T / "substrate_chemistry_comparison.csv")),
    })
    log("  substrates.json")


def export_enrichment():
    e = pd.read_csv(E / "goslim_enrichment.csv")
    e = e[e["p_value"] < 0.01].copy()
    e["go_name"] = e["go_name"].fillna("")
    write_json(SITE_DATA / "enrichment.json", {
        "method": ("One-sided hypergeometric over-representation of GO-slim terms "
                   "(the GOSLIM_IDS annotation OSDR ships with GLDS-476) against the "
                   "background of tested, annotated genes; Benjamini-Hochberg FDR."),
        "shown": "terms with raw p < 0.01; `fdr` carries the corrected value",
        "terms": records(e),
    })
    log(f"  enrichment.json  ({len(e)} terms at p<0.01)")


def export_manifest():
    def n(path, key=None):
        d = pd.read_csv(path)
        return int(len(d) if key is None else d[key].nunique())

    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:                                            # noqa: BLE001
        commit = ""

    write_json(SITE_DATA / "manifest.json", {
        "built": dt.date.today().isoformat(),
        "commit": commit,
        "counts": {
            "osdr_studies": len(pd.read_json(SITE_DATA / "osdr_regolith_catalog.json")["studies"]),
            "rnaseq_samples": n(T / "sample_metadata.csv"),
            "phenotyped_samples": int(pd.read_csv(T / "sample_metadata.csv")["phenotyped"].sum()),
            "plantcv_plants": n(T / "plantcv_traits_long.csv", "plant_id"),
            "leaf_count_observations": n(T / "leaf_counts_long.csv"),
            "genes_tested": n(T / "growth_correlated_genes.csv.gz", "gene"),
            "robust_growth_genes": n(T / "growth_genes_robust.csv", "gene"),
            "broad_lunar_genes": n(T / "broad_lunar_model.csv"),
        },
        "provenance": [
            {"name": "NASA OSDR", "url": "https://osdr.nasa.gov/bio/repo/",
             "note": "study catalogue, OSD-476 ISA-Tab and expression tables"},
            {"name": "NASA PSI", "url": "https://psi.nasa.gov/physci/repo/",
             "note": "physical-science investigations on regolith mechanics and ISRU"},
            {"name": "Lunar_regolith_AWG",
             "url": "https://github.com/dr-richard-barker/Lunar_regolith_AWG",
             "note": "PlantCV shoot traits, Broad Lunar model, substrate probe runs"},
            {"name": "Exolith Lab", "url": "https://exolithsimulants.com/",
             "note": "LHS-1 simulant specification"},
        ],
    })
    log("  manifest.json")


def main() -> int:
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    export_phenotypes()
    export_transcriptomics()
    export_growth_genes()
    export_substrates()
    export_enrichment()
    export_manifest()
    total = sum(p.stat().st_size for p in SITE_DATA.glob("*.json"))
    log(f"\n  {len(list(SITE_DATA.glob('*.json')))} JSON files, "
        f"{total / 1048576:.1f} MB uncompressed → {SITE_DATA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
