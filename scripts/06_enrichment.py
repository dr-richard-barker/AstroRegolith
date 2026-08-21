#!/usr/bin/env python3
"""GO-slim enrichment of the growth-correlated genes.

Annotation comes from the `GOSLIM_IDS` column that OSDR ships inside
`GLDS-476_rna_seq_differential_expression_*.csv` — the same annotation the
published analysis used, so no external mapping is introduced and no gene list
is hand-curated. Term *names* are resolved from the EBI QuickGO REST service and
cached in `data/go_terms.json`, so a re-run works offline.

Test: one-sided hypergeometric (over-representation) of each GO-slim term in the
growth-correlated set against the background of every gene that was tested and
carries at least one slim annotation, with Benjamini-Hochberg control.

Outputs
  results/enrichment/goslim_enrichment.csv   term x gene-set results
  data/go_terms.json                         GO id -> name/aspect cache
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, RESULTS, get_json, log, write_json  # noqa: E402

T, E = RESULTS / "tables", RESULTS / "enrichment"
DE = DATA / "osdr" / "raw_large" / "differential_expression_rRNArm.csv"
GO_CACHE = DATA / "go_terms.json"
QUICKGO = "https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/"
FDR, MIN_TERM = 0.05, 5


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    ranked = np.minimum.accumulate((p[order] * n / np.arange(1, n + 1))[::-1])[::-1]
    adj = np.empty(n)
    adj[order] = np.clip(ranked, 0, 1)
    return adj


def go_names(ids: list) -> dict:
    cache = json.loads(GO_CACHE.read_text()) if GO_CACHE.exists() else {}
    missing = sorted(set(ids) - set(cache))
    for i in range(0, len(missing), 100):                # QuickGO caps the batch
        chunk = missing[i:i + 100]
        try:
            d = get_json(QUICKGO + urllib.parse.quote(",".join(chunk)))
        except Exception as e:                            # noqa: BLE001
            log(f"  ! QuickGO lookup failed ({e}) — {len(chunk)} terms stay unnamed")
            break
        for r in d.get("results", []):
            cache[r["id"]] = {"name": r.get("name", ""), "aspect": r.get("aspect", "")}
        log(f"  · resolved {min(i + 100, len(missing))}/{len(missing)} GO term names")
    write_json(GO_CACHE, cache)
    return cache


def main() -> int:
    E.mkdir(parents=True, exist_ok=True)
    ann = pd.read_csv(DE, usecols=["TAIR", "SYMBOL", "GOSLIM_IDS"])
    term_genes = defaultdict(set)
    gene_terms = {}
    for tair, slim in zip(ann["TAIR"], ann["GOSLIM_IDS"]):
        if isinstance(slim, str) and slim.strip():
            terms = {t for t in slim.split("|") if t.startswith("GO:")}
            gene_terms[tair] = terms
            for t in terms:
                term_genes[t].add(tair)

    res = pd.read_csv(T / "growth_correlated_genes.csv.gz")
    tested = set(res["gene"])
    background = tested & set(gene_terms)
    log(f"  background: {len(background)} tested genes carry a GO-slim annotation "
        f"(of {len(tested)} tested)")

    # Gene sets to test: per analysis x covariate, split by direction, plus the
    # robust set that survived both analyses.
    sets = {}
    sig = res[res["fdr"] < FDR]
    for (analysis, cov), d in sig.groupby(["analysis", "covariate"]):
        for label, sel in (("up", d["spearman_rho"] > 0), ("down", d["spearman_rho"] < 0)):
            g = set(d.loc[sel, "gene"]) & background
            if len(g) >= 10:
                sets[f"{analysis}|{cov}|{label}"] = g
    robust = pd.read_csv(T / "growth_genes_robust.csv")
    for label, sel in (("up", robust["primary"] > 0), ("down", robust["primary"] < 0)):
        g = set(robust.loc[sel, "gene"]) & background
        if len(g) >= 10:
            sets[f"robust|any|{label}"] = g

    all_terms = sorted({t for t in term_genes if len(term_genes[t] & background) >= MIN_TERM})
    names = go_names(all_terms)

    rows = []
    N = len(background)
    for label, genes in sets.items():
        K = len(genes)
        pvals, recs = [], []
        for t in all_terms:
            in_term = term_genes[t] & background
            hits = len(in_term & genes)
            if hits == 0:
                continue
            # P(X >= hits) for X ~ Hypergeometric(N, len(in_term), K)
            p = stats.hypergeom.sf(hits - 1, N, len(in_term), K)
            pvals.append(p)
            meta = names.get(t, {})
            recs.append({
                "gene_set": label, "analysis": label.split("|")[0],
                "covariate": label.split("|")[1], "direction": label.split("|")[2],
                "go_id": t, "go_name": meta.get("name", ""), "go_aspect": meta.get("aspect", ""),
                "genes_in_set": K, "genes_in_term": len(in_term), "overlap": hits,
                "fold_enrichment": (hits / K) / (len(in_term) / N),
                "p_value": p,
                "example_genes": ";".join(sorted(in_term & genes)[:8]),
            })
        if not recs:
            continue
        for rec, q in zip(recs, bh(np.array(pvals))):
            rec["fdr"] = float(q)
        rows.extend(recs)
        n_sig = sum(r["fdr"] < FDR for r in recs)
        log(f"  {label:<40} {K:>4} genes → {n_sig} enriched GO-slim terms (FDR<{FDR})")

    out = pd.DataFrame(rows).sort_values(["gene_set", "fdr", "p_value"])
    out.to_csv(E / "goslim_enrichment.csv", index=False)
    log(f"\n  {len(out)} term x set tests → {E / 'goslim_enrichment.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
