#!/usr/bin/env python3
"""Growth-anchored transcriptomics: regress OSD-476 expression on measured growth.

The published analysis of OSD-476 contrasts regolith *sources* (Apollo 11 vs 12
vs 17 vs JSC-1A). Because the ISA links each sequenced plant to its own growth
trajectory, we can instead ask which genes track how well the individual plant
actually grew - a continuous covariate that varies substantially *within* every
regolith source.

Two analyses, deliberately:

  primary     all 16 phenotyped samples. Powerful, but growth and substrate are
              confounded (every JSC-1A plant outgrew every Apollo plant), so a
              hit here may only be re-describing the treatment contrast.
  within_lunar  the 12 Apollo samples alone. Growth still spans 0-6 leaves and
              0.14-16 mm^2 here, but substrate is no longer simulant-vs-lunar.
              A gene significant in BOTH is tracking growth itself.

Spearman is used throughout: n is small, the covariates are not normal, and
rank correlation is robust to the one near-dead plant (GSM5691020, 0 leaves).

Outputs
  results/tables/growth_correlated_genes.csv.gz  every gene x covariate result
  results/tables/gene_annotation.csv             gene -> symbol, description
  results/tables/growth_covariates.csv           covariate -> definition
  results/tables/growth_genes_robust.csv         significant in both analyses
  results/tables/growth_gene_overlap.csv         growth hits vs the published DEGs
  results/enrichment/growth_gene_sets.csv        hit counts per covariate/analysis

The full result is 282 000 rows. Gene symbols and descriptions live in a separate
annotation table rather than being repeated on each of a gene's twelve rows, and
the table is gzipped -- pandas reads it with the same `read_csv` call. Together
that turns 61 MB into a few megabytes, which matters for a repository meant to be
cloned and archived.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, RESULTS, log  # noqa: E402

T, E = RESULTS / "tables", RESULTS / "enrichment"
VST = DATA / "osdr" / "raw_large" / "vst_counts_rRNArm.csv"
DE = DATA / "osdr" / "raw_large" / "differential_expression_rRNArm.csv"

# Growth covariates, each a defensible summary of the same underlying trajectory.
COVARIATES = {
    "leaf_final": "leaf count on the last imaging day (2021-05-18)",
    "leaf_rate_per_day": "OLS slope of leaf count over the 12 imaged days",
    "leaf_first_day": "days from first plate scan to first true leaf (higher = slower)",
    "leaf_auc": "area under the leaf-count curve",
    "log10_area_mm2_last": "log10 rosette area on the last morphometric day (2021-05-10)",
    "rgr_area_per_day": "relative growth rate of rosette area",
}
FDR = 0.05


def bh(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (NaNs pass through)."""
    p = np.asarray(p, float)
    out = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    q, n = p[ok], ok.sum()
    if n == 0:
        return out
    order = np.argsort(q)
    ranked = q[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adj = np.empty(n)
    adj[order] = np.clip(ranked, 0, 1)
    out[ok] = adj
    return out


def spearman_matrix(expr: pd.DataFrame, x: pd.Series):
    """Spearman rho and p of every gene (rows of `expr`) against `x`."""
    ok = np.isfinite(x.values)
    xr = stats.rankdata(x.values[ok])
    yr = np.apply_along_axis(stats.rankdata, 1, expr.values[:, ok])
    xc = xr - xr.mean()
    yc = yr - yr.mean(axis=1, keepdims=True)
    denom = np.sqrt((yc ** 2).sum(axis=1) * (xc ** 2).sum())
    # A gene whose values are all tied inside this subset has zero rank spread;
    # rho is undefined there, so exclude it from the product rather than let the
    # division produce an inf that then poisons the t statistic.
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        rho = np.where(denom > 0, (yc @ xc) / np.where(denom > 0, denom, 1.0), np.nan)
    n = int(ok.sum())
    # t approximation, the same one scipy uses for spearmanr with n > 3
    with np.errstate(invalid="ignore", divide="ignore"):
        t = rho * np.sqrt((n - 2) / np.clip(1 - rho ** 2, 1e-300, None))
    p = 2 * stats.t.sf(np.abs(t), n - 2)
    p = np.where(np.isfinite(rho), p, np.nan)
    return rho, p, n


def main() -> int:
    E.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(T / "sample_phenotype_expression_map.csv")
    m = m[m["join_confidence"] != "unlinked"].copy()
    m["log10_area_mm2_last"] = np.log10(m["area_mm2_last"])

    vst = pd.read_csv(VST, index_col=0)
    vst = vst[m["gsm"].tolist()]
    keep = vst.var(axis=1) > 0
    vst = vst[keep]
    log(f"  {int(keep.sum())} of {len(keep)} genes retained (non-zero VST variance) "
        f"across {vst.shape[1]} phenotyped samples")

    ann = pd.read_csv(DE, usecols=["TAIR", "SYMBOL", "GENENAME"], index_col="TAIR")

    frames = []
    for analysis, sub in (("primary", m), ("within_lunar", m[m["substrate"] != "JSC1A"])):
        expr = vst[sub["gsm"].tolist()]
        for cov, desc in COVARIATES.items():
            rho, p, n = spearman_matrix(expr, sub[cov])
            frames.append(pd.DataFrame({
                "gene": expr.index, "analysis": analysis, "covariate": cov,
                "n_samples": n, "mean_vst": expr.mean(axis=1).values,
                "spearman_rho": rho, "p_value": p, "fdr": bh(p),
            }))
            sig = int((bh(p) < FDR).sum())
            log(f"  {analysis:<13} {cov:<22} n={n:<3} genes FDR<{FDR}: {sig}")

    res = pd.concat(frames, ignore_index=True)
    res = res.sort_values(["analysis", "covariate", "fdr", "p_value"])
    # mtime=0: gzip stamps the current time into its header by default, so an
    # otherwise identical re-run would produce different bytes and break the
    # checksum manifest. Pinning it keeps the pipeline byte-reproducible.
    res.to_csv(T / "growth_correlated_genes.csv.gz", index=False,
               compression={"method": "gzip", "mtime": 0})
    ann.reset_index().rename(columns={"TAIR": "gene"}).to_csv(
        T / "gene_annotation.csv", index=False)
    pd.DataFrame([{"covariate": k, "description": v} for k, v in COVARIATES.items()]
                 ).to_csv(T / "growth_covariates.csv", index=False)

    # Genes significant in BOTH analyses for the same covariate and with the same
    # sign: growth-tracking rather than substrate-tracking.
    sig = res[res["fdr"] < FDR]
    wide = sig.pivot_table(index=["gene", "covariate"], columns="analysis",
                           values="spearman_rho")
    robust = wide.dropna()
    robust = robust[np.sign(robust["primary"]) == np.sign(robust["within_lunar"])]
    robust = robust.reset_index().join(ann, on="gene")   # small enough to annotate inline
    robust.to_csv(T / "growth_genes_robust.csv", index=False)
    log(f"\n  {len(robust)} gene x covariate pairs significant in BOTH analyses "
        f"with a consistent sign ({robust['gene'].nunique()} distinct genes)")

    summary = (res.assign(sig=res["fdr"] < FDR)
               .groupby(["analysis", "covariate"], as_index=False)
               .agg(genes_tested=("gene", "size"), genes_fdr05=("sig", "sum"),
                    max_abs_rho=("spearman_rho", lambda s: float(np.nanmax(np.abs(s))))))
    summary.to_csv(E / "growth_gene_sets.csv", index=False)

    # How much does growth-anchoring add over the published source contrasts?
    de_cols = [c for c in pd.read_csv(DE, nrows=0).columns
               if c.startswith("Adj.p.value_") and "JSC-1A" in c and c.startswith("Adj.p.value_(Apollo")]
    de = pd.read_csv(DE, usecols=["TAIR"] + de_cols, index_col="TAIR")
    published = set(de.index[(de < 0.05).any(axis=1)])
    growth = set(robust["gene"])
    pd.DataFrame([{
        "published_degs_any_apollo_vs_jsc1a": len(published),
        "growth_correlated_robust": len(growth),
        "overlap": len(growth & published),
        "growth_only": len(growth - published),
        "contrasts_used": "; ".join(c.replace("Adj.p.value_", "") for c in de_cols),
    }]).to_csv(T / "growth_gene_overlap.csv", index=False)
    log(f"  vs published DEGs (any Apollo v JSC-1A, adj.p<0.05, n={len(published)}): "
        f"{len(growth & published)} overlap, {len(growth - published)} growth-only")

    # Per-sample expression for a few named example genes, so figure 3c plots the
    # same numbers the tables report. Selection is deterministic: the strongest
    # positive and negative robust correlations with leaf rate that carry a symbol.
    lr = robust[(robust["covariate"] == "leaf_rate_per_day") & robust["SYMBOL"].notna()]
    picks = pd.concat([lr.nlargest(2, "primary"), lr.nsmallest(1, "primary")])
    rows = []
    for _, g in picks.iterrows():
        for gsm, v in vst.loc[g["gene"], m["gsm"]].items():
            r = m[m["gsm"] == gsm].iloc[0]
            rows.append({"gene": g["gene"], "label": str(g["SYMBOL"]).split("|")[0],
                         "gsm": gsm, "substrate": r["substrate"],
                         "leaf_rate_per_day": r["leaf_rate_per_day"],
                         "leaf_final": r["leaf_final"], "vst": float(v),
                         "spearman_rho": g["primary"]})
    pd.DataFrame(rows).to_csv(T / "expression_examples.csv", index=False)
    log(f"  example genes for figure 3c: "
        f"{', '.join(str(x).split('|')[0] for x in picks['SYMBOL'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
