#!/usr/bin/env python3
"""Join every OSD-476 RNA-seq sample to the growth of the plant it came from.

This is the linkage the database is built around. It works because the OSDR
ISA-Tab keys each sequenced sample to a plate (P1-P4) and to a per-plant leaf
count, and because the plate layout puts exactly one Apollo 11, one Apollo 12
and one Apollo 17 plant on each plate:

  Apollo 11 / 12 / 17   4 plants x 4 plates, 1 sequenced sample per plate-substrate
                        -> `exact`      a one-to-one plant<->transcriptome join
  JSC-1A simulant       16 plants (4 per plate) against 4 phenotyped samples
                        -> `plate_mean` the sample is joined to the mean of the
                                        four control plants on its own plate
  JSC-1A replicates 5-8 no plate and no morphometrics in the ISA
                        -> `unlinked`   excluded from growth-anchored analysis

Two phenotype layers are carried through: the ISA's own leaf-count trajectory
(12 timepoints, 2021-05-06..05-18) and the PlantCV shape traits re-scored from
the plate scans (5 timepoints, 2021-05-02..05-10). They come from different
measurements of the same plants, so agreement between them is a check, not a
tautology - `qc_leaf_area_spearman` reports it.

Output: results/tables/sample_phenotype_expression_map.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import RESULTS, log  # noqa: E402

T = RESULTS / "tables"
LUNAR = ("A11", "A12", "A17")


# numpy renamed trapz -> trapezoid in 2.0; support both without a deprecation warning.
_trapz = getattr(np, "trapezoid", None) or np.trapz


def slope(x, y):
    """OLS slope, or NaN when the series cannot support one."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 2 or np.ptp(x[ok]) == 0:
        return np.nan
    return float(np.polyfit(x[ok], y[ok], 1)[0])


def leaf_covariates(g: pd.DataFrame) -> dict:
    g = g.sort_values("day")
    emerged = g.loc[g["n_leaves"] > 0, "day"]
    return {
        "leaf_first_day": float(emerged.iloc[0]) if len(emerged) else np.nan,
        "leaf_final": float(g["n_leaves"].iloc[-1]),
        "leaf_rate_per_day": slope(g["day"], g["n_leaves"]),
        "leaf_auc": float(_trapz(g["n_leaves"], g["day"])),
    }


def shape_covariates(g: pd.DataFrame) -> dict:
    """Rosette shape at the first and last morphometric day, plus relative growth."""
    g = g.groupby("day", as_index=False).mean(numeric_only=True).sort_values("day")
    first, last = g.iloc[0], g.iloc[-1]
    span = float(last["day"] - first["day"])
    rgr = (np.log(last["area_mm2"]) - np.log(first["area_mm2"])) / span if span else np.nan
    return {
        "area_mm2_first": float(first["area_mm2"]),
        "area_mm2_last": float(last["area_mm2"]),
        "rgr_area_per_day": float(rgr),
        "solidity_last": float(last["solidity"]),
        "height_mm_last": float(last["height_mm"]),
        "longest_path_mm_last": float(last["longest_path_mm"]),
        "ellipse_eccentricity_last": float(last["ellipse_eccentricity"]),
        "area_slope_mm2_per_day": slope(g["day"], g["area_mm2"]),
    }


def main() -> int:
    samples = pd.read_csv(T / "sample_metadata.csv")
    leaves = pd.read_csv(T / "leaf_counts_long.csv")
    traits = pd.read_csv(T / "plantcv_traits_long.csv")

    leaf_cov = {g: leaf_covariates(d) for g, d in leaves.groupby("gsm")}

    rows = []
    for _, s in samples.iterrows():
        gsm, sub, plate = s["gsm"], s["substrate"], s["plate"]
        row = {
            "gsm": gsm, "treatment": s["treatment"], "substrate": sub,
            "replicate": s["replicate"], "plate": plate,
            "age_at_harvest_days": s["age_at_harvest_days"],
            "n_leaves_at_harvest": s["n_leaves_at_harvest"],
            "dev_stage_at_harvest": s["dev_stage_at_harvest"],
        }
        if not s["phenotyped"] or pd.isna(plate):
            rows.append({**row, "join_confidence": "unlinked", "n_plants": 0,
                         "plant_ids": ""})
            continue

        row.update(leaf_cov.get(gsm, {}))
        plants = traits[(traits["plate"] == plate) & (traits["substrate"] == sub)]
        ids = sorted(plants["plant_id"].unique())
        row["join_confidence"] = "exact" if sub in LUNAR else "plate_mean"
        row["n_plants"] = len(ids)
        row["plant_ids"] = ";".join(ids)
        if len(ids):
            row.update(shape_covariates(plants))
        rows.append(row)

    out = pd.DataFrame(rows)

    # --- assertions: the join must hold, or the analysis downstream is meaningless
    exact = out[out["join_confidence"] == "exact"]
    if len(exact) != 12:
        raise SystemExit(f"expected 12 exact (Apollo) joins, got {len(exact)}")
    if not (exact["n_plants"] == 1).all():
        raise SystemExit("an Apollo sample matched more than one plant — plate layout changed")
    pm = out[out["join_confidence"] == "plate_mean"]
    if len(pm) != 4 or not (pm["n_plants"] == 4).all():
        raise SystemExit(f"expected 4 JSC-1A plate-mean joins over 4 plants each, got "
                         f"{len(pm)} / {sorted(pm['n_plants'].unique())}")
    if len(out[out["join_confidence"] == "unlinked"]) != 4:
        raise SystemExit("expected 4 unlinked JSC-1A replicates (5-8)")
    if out["gsm"].nunique() != len(out) != 20:
        raise SystemExit("sample table is no longer 20 unique GSMs")

    # --- QC: do the two independent phenotype layers agree?
    linked = out[out["join_confidence"] != "unlinked"]
    rho, p = stats.spearmanr(linked["leaf_final"], linked["area_mm2_last"])
    log(f"  QC  leaf count vs PlantCV rosette area: Spearman rho={rho:.3f}, p={p:.2g} "
        f"(n={len(linked)}) — independent measurements of the same plants")

    # Solidity is area / convex-hull area and cannot exceed 1. A handful of the
    # upstream PlantCV rows do, on the smallest/most distorted plants where the
    # hull fit is unreliable. Flag rather than silently propagate.
    bad = linked[linked["solidity_last"] > 1.0]
    if len(bad):
        log(f"  QC  {len(bad)} sample(s) carry solidity > 1 from the upstream PlantCV "
            f"table ({', '.join(bad['gsm'])}) — flagged, not corrected")
    out["qc_solidity_out_of_range"] = out["solidity_last"] > 1.0

    out["qc_leaf_area_spearman"] = round(float(rho), 4)
    out["qc_leaf_area_p"] = float(p)
    out.to_csv(T / "sample_phenotype_expression_map.csv", index=False)

    log(f"\n  {len(exact)} exact + {len(pm)} plate-mean + "
        f"{len(out) - len(exact) - len(pm)} unlinked = {len(out)} RNA-seq samples")
    log(f"  → {T / 'sample_phenotype_expression_map.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
