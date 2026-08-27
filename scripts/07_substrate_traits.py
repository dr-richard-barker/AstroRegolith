#!/usr/bin/env python3
"""Tidy the substrate-characterisation data into analysis-ready tables.

Three independent descriptions of what a regolith substrate *is*, which together
let an experiment designer compare a simulant against the real thing:

  probe        CoSE Lunar Large Chamber soil-probe runs (unpublished): water
               content, electrical conductivity, pH and N/P/K logged every ~16 min
               while water was added to 15 mL of each substrate. 8 substrates.
  simulant     Exolith LHS-1 lunar-highlands simulant spec sheet: mineralogy,
               bulk oxide chemistry, and physical properties (particle size,
               bulk/grain density, void ratio, porosity, angle of repose).
  lunar truth  Chang'e-5 lunar soil bulk chemistry (XRF + INAA) from Li et al.,
               National Science Review 9(2):nwab188 — the reference the simulant
               is trying to approximate.

Also tidies the Broad Lunar linear model (all Apollo samples pooled vs JSC-1A).

Units are carried through exactly as the sources report them; where a source does
not state a unit (the probe's N/P/K), the column says so rather than inventing one.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, RESULTS, log  # noqa: E402

A, T = DATA / "awg", RESULTS / "tables"

# The raw "Time" column is in SECONDS, despite reading like minutes at a glance.
# Three independent checks agree: consecutive readings are 16.0 apart against a
# documented "readings every 15 s"; the water-addition steps fall 176-448 apart
# against "5 mL added at ~5 min intervals"; and the longest run is 1606, i.e. 27
# minutes to wet 15 mL of substrate. Read as minutes it would be a 26.8-hour run
# taking a reading every 16 minutes.
PROBE_COLS = {
    "Time": ("time_s", "seconds from the start of the run"),
    "Water Content": ("water_content_pct", "% volumetric, probe-reported"),
    "EC": ("ec_us_cm", "µS/cm, probe-reported"),
    "pH": ("ph", "pH units"),
    "Nitrogen": ("nitrogen", "probe-reported index; the probe's datasheet gives no unit"),
    "Phosphorus": ("phosphorus", "probe-reported index; the probe's datasheet gives no unit"),
    "Potassium": ("potassium", "probe-reported index; the probe's datasheet gives no unit"),
}


# The two probe exports label the same substrates slightly differently; normalise
# so the endpoint and time-series tables join.
SUBSTRATE_ALIAS = {
    "Perlite": "Perlite (Small particle)",
    "Vermiculite": "Vermiculite (old powder)",
    "Pottinng soil": "Potting soil",
    "Vermiculite (old powder)": "Vermiculite (old powder)",
}


def tidy_probe(path: Path, first_col: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.rename(columns={df.columns[0]: "substrate"})
    df = df[df["substrate"].notna() & (df["substrate"].astype(str).str.strip() != "")]
    df["substrate"] = (df["substrate"].str.strip()
                       .map(lambda v: SUBSTRATE_ALIAS.get(v, v)))
    keep = {"substrate": "substrate"}
    keep.update({src: dst for src, (dst, _) in PROBE_COLS.items() if src in df.columns})
    extra = [c for c in ("Total water added (ml)", "Total water added", "protocol ") if c in df.columns]
    out = df[list(keep) + extra].rename(columns=keep)
    out = out.rename(columns={"Total water added (ml)": "water_added_ml",
                              "Total water added": "water_added_ml", "protocol ": "protocol"})
    for c in out.columns:
        if c not in ("substrate", "protocol"):
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.dropna(subset=["time_s"]).reset_index(drop=True)


def parse_lhs1(path: Path) -> tuple:
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    source_url = rows[0][0] if rows and rows[0] else ""
    mineral, chem, phys = [], [], []
    for r in rows[3:]:
        r = (r + [""] * 9)[:9]
        if r[0].strip() and r[1].strip():
            mineral.append({"component": r[0].strip(), "wt_pct": pd.to_numeric(r[1], errors="coerce")})
        if r[3].strip() and r[4].strip() and not r[3].startswith(("*", "**")):
            chem.append({"oxide": r[3].strip(), "wt_pct": pd.to_numeric(r[4], errors="coerce")})
        if r[6].strip() and r[7].strip() and not r[6].lower().startswith("note"):
            phys.append({"property": r[6].strip(), "value": r[7].strip()})
    for d in (mineral, chem, phys):
        for x in d:
            x["simulant"] = "LHS-1 (Exolith lunar highlands simulant)"
            x["source"] = source_url
    return pd.DataFrame(mineral), pd.DataFrame(chem), pd.DataFrame(phys)


def parse_ce5(path: Path) -> pd.DataFrame:
    """XRF oxides and INAA elements for Chang'e-5 soil, with their uncertainties."""
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    ref = rows[0][1] if len(rows) > 1 and len(rows[0]) > 1 else ""
    out, method = [], ""
    i = 0
    while i < len(rows):
        head = (rows[i][0] or "").strip()
        if head in ("XRF", "INAA"):
            method = head
        elif head == "Element" and method:
            names = [c.strip() for c in rows[i][1:]]
            vals = rows[i + 1][1:] if i + 1 < len(rows) else []
            uncs = rows[i + 2][1:] if i + 2 < len(rows) and "ncertaint" in (rows[i + 2][0] or "") else []
            unit = (rows[i + 1][0] or "").strip() if i + 1 < len(rows) else ""
            for j, n in enumerate(names):
                if not n or n in ("Total", "Mg#"):
                    continue
                v = pd.to_numeric(vals[j], errors="coerce") if j < len(vals) else None
                if pd.isna(v):
                    continue
                out.append({
                    "sample": "Chang'e-5 lunar soil", "method": method, "analyte": n,
                    "value": float(v), "unit": unit,
                    "uncertainty_k2": pd.to_numeric(uncs[j], errors="coerce") if j < len(uncs) else None,
                    "reference": ref,
                })
            i += 2
        i += 1
    return pd.DataFrame(out)


def main() -> int:
    T.mkdir(parents=True, exist_ok=True)

    end = tidy_probe(A / "simulant_endpoint.csv", "substrate")
    ts = tidy_probe(A / "simulant_timeseries.csv", "substrate")
    end.to_csv(T / "substrate_probe_endpoint.csv", index=False)
    ts.to_csv(T / "substrate_probe_timeseries.csv", index=False)
    pd.DataFrame([{"column": d, "source_column": s, "unit_note": u}
                  for s, (d, u) in PROBE_COLS.items()]
                 ).to_csv(T / "substrate_probe_units.csv", index=False)
    log(f"  probe: {len(end)} substrates (endpoint), {len(ts)} readings across "
        f"{ts['substrate'].nunique()} substrates (time series)")

    mineral, chem, phys = parse_lhs1(A / "simulant_catalogue.csv")
    mineral.to_csv(T / "simulant_lhs1_mineralogy.csv", index=False)
    chem.to_csv(T / "simulant_lhs1_chemistry.csv", index=False)
    phys.to_csv(T / "simulant_lhs1_physical.csv", index=False)
    log(f"  LHS-1 spec: {len(mineral)} minerals, {len(chem)} oxides, "
        f"{len(phys)} physical properties")

    ce5 = parse_ce5(A / "ce5_farside_soil_composition.csv")
    ce5.to_csv(T / "lunar_soil_ce5_composition.csv", index=False)
    log(f"  Chang'e-5 soil: {len(ce5)} analytes "
        f"({', '.join(sorted(ce5['method'].unique()))})")

    # Side-by-side of the oxides both LHS-1 and Chang'e-5 report.
    ce5_ox = ce5[(ce5["method"] == "XRF")][["analyte", "value"]].rename(
        columns={"analyte": "oxide", "value": "ce5_wt_pct"})
    # LOI and the column total are bookkeeping rows, not oxides to compare.
    oxides = chem[~chem["oxide"].str.startswith(("LOI", "Total"))]
    comp = oxides[["oxide", "wt_pct"]].rename(columns={"wt_pct": "lhs1_wt_pct"}).merge(
        ce5_ox, on="oxide", how="outer")
    comp["difference_wt_pct"] = comp["lhs1_wt_pct"] - comp["ce5_wt_pct"]
    comp.to_csv(T / "substrate_chemistry_comparison.csv", index=False)
    log(f"  simulant vs lunar soil: {comp['oxide'].nunique()} oxides compared")

    bl = pd.read_csv(A / "broad_lunar_model_deseq2.csv", encoding="utf-8-sig")
    bl = bl.rename(columns={
        "Row-names": "gene", "Symbol": "symbol",
        "Moon-Earth___log2FoldChange": "log2fc_lunar_vs_simulant",
        "Moon-Earth___padj": "padj"}).drop(columns=[c for c in bl.columns if c == "data"],
                                           errors="ignore")
    bl = bl[bl["gene"].notna()][["gene", "symbol", "log2fc_lunar_vs_simulant", "padj"]]
    bl.to_csv(T / "broad_lunar_model.csv", index=False)
    sig = bl["padj"] < 0.05
    up = int((sig & (bl["log2fc_lunar_vs_simulant"] > 0)).sum())
    log(f"  Broad Lunar model: {len(bl)} genes, {int(sig.sum())} with padj<0.05 "
        f"({up} up and {int(sig.sum()) - up} down in lunar regolith)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
