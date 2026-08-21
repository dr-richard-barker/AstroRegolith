#!/usr/bin/env python3
"""Build tidy phenotype tables for OSD-476 from two independent sources.

  1. The OSDR ISA-Tab archive (`data/osdr/OSD-476-ISA.zip`)
       s_OSD-476.txt ................ 20 RNA-seq samples: treatment, growth medium,
                                      age at harvest, leaf count and developmental
                                      stage AT HARVEST — a terminal phenotype for
                                      every sequenced plant.
       a_..._image-analysis_... ..... 16 of those samples additionally carry a
                                      12-timepoint leaf-count trajectory, the plate
                                      they grew on (P1-P4), and the plate-scan files.
  2. PlantCV shoot morphometrics re-scored from the plate scans
     (`data/awg/plantcv_shoot_traits.csv`) — 16 shape traits per plant per day.

Outputs (all in `results/tables/`)
  sample_metadata.csv       20 rows, one per RNA-seq sample
  leaf_counts_long.csv      192 rows, gsm x date
  plantcv_traits_long.csv   one row per plant x day, in millimetres
  phenotype_summary.csv     one row per sequenced plant: the growth covariates
                            script 05 regresses expression against

Scale: the PlantCV table carries `linear_scale` (m/px) and `area_scale` (m^2/px).
This script asserts area_scale == linear_scale^2 before converting to mm/mm^2, so
a change in the upstream file cannot silently corrupt the units.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, RESULTS, log  # noqa: E402

ISA = DATA / "osdr" / "OSD-476-ISA.zip"
PLANTCV = DATA / "awg" / "plantcv_shoot_traits.csv"
OUT = RESULTS / "tables"

MORPH = "a_OSD-476_morphometric-analysis_image-analysis_imagej.txt"
SAMPLES = "s_OSD-476.txt"

# Treatment label -> the short substrate code the PlantCV table uses.
SUBSTRATE = {
    "JSC-1A lunar simulant": "JSC1A",
    "Apollo 11 regolith": "A11",
    "Apollo 12 regolith": "A12",
    "Apollo 17 regolith": "A17",
}
LEAF_RE = re.compile(r"Number of Leaves (\d{2})/(\d{2})/(\d{4})")
# ISA-Tab puts a bare `Unit` column immediately after the value it qualifies, so
# csv.DictReader collapses the several `Unit` columns into one. The unit for
# `Quantity of Growth Medium` is read positionally instead.
GROWTH_MEDIUM_UNIT = ""
PLATE_RE = re.compile(r"_(\d{6})-\s*(P\d)\.tiff", re.I)


def read_isa(member: str) -> list:
    with zipfile.ZipFile(ISA) as z:
        text = z.read(member).decode("utf-8", "replace")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def num(v, cast=float):
    try:
        return cast(str(v).strip())
    except (TypeError, ValueError):
        return None


def isa_unit_for(member: str, param: str) -> str:
    """The `Unit` column that immediately follows `param` in an ISA-Tab header.

    DictReader cannot be used here: ISA-Tab repeats the bare column name `Unit`
    after each value it qualifies, and a dict keeps only the last one.
    """
    with zipfile.ZipFile(ISA) as z:
        lines = z.read(member).decode("utf-8", "replace").splitlines()
    header = lines[0].split("\t")
    row = lines[1].split("\t") if len(lines) > 1 else []
    for i, col in enumerate(header):
        if col == f"Parameter Value[{param}]" and i + 1 < len(header) and header[i + 1] == "Unit":
            return row[i + 1] if i + 1 < len(row) else ""
    return ""


def build_samples() -> pd.DataFrame:
    global GROWTH_MEDIUM_UNIT
    GROWTH_MEDIUM_UNIT = isa_unit_for(SAMPLES, "Quantity of Growth Medium")
    rows = []
    for r in read_isa(SAMPLES):
        src = r["Source Name"]
        rows.append({
            "gsm": r["Sample Name"],
            "source_name": src,
            "treatment": r["Factor Value[Treatment]"],
            "substrate": SUBSTRATE.get(r["Factor Value[Treatment]"], "?"),
            "replicate": num(src.rsplit("replicate", 1)[-1], int) if "replicate" in src else None,
            "genotype": r.get("Characteristics[Genotype]", ""),
            "cultivar": r.get("Characteristics[cultivar]", ""),
            "growth_medium": r.get("Parameter Value[Growth Medium]", ""),
            "growth_medium_quantity": num(r.get("Parameter Value[Quantity of Growth Medium]")),
            "growth_medium_unit": GROWTH_MEDIUM_UNIT,
            "growth_time_days": num(r.get("Parameter Value[Growth Time]"), int),
            "age_at_harvest_days": num(r.get("Parameter Value[Age at sample harvest]"), int),
            "n_leaves_at_harvest": num(r.get("Parameter Value[Number of Leaves at Time of Sample Collection]"), int),
            "dev_stage_at_harvest": r.get("Parameter Value[Developmental stage at time of sample collection]", ""),
            "thinning_note": r.get("Parameter Value[Number of seeds sown per well]", ""),
        })
    return pd.DataFrame(rows)


def build_leaf_counts() -> pd.DataFrame:
    morph = read_isa(MORPH)
    leaf_cols = [c for c in morph[0] if LEAF_RE.search(c)]
    rows = []
    for r in morph:
        gsm = r["Sample Name"]
        plate = ""
        for c, v in r.items():
            if c.startswith("Parameter Value[Image file") and (m := PLATE_RE.search(v or "")):
                plate = m.group(2).upper()
                break
        for c in leaf_cols:
            mm, dd, yyyy = LEAF_RE.search(c).groups()
            n = num(r[c], int)
            if n is None:
                continue
            rows.append({"gsm": gsm, "plate": plate,
                         "date": dt.date(int(yyyy), int(mm), int(dd)).isoformat(),
                         "n_leaves": n})
    return pd.DataFrame(rows)


def build_plantcv() -> pd.DataFrame:
    # keep_default_na=False: the group column literally contains the string
    # "None" for unassignable contours, which pandas would otherwise read as NaN
    # and silently keep in the analysis.
    df = pd.read_csv(PLANTCV, encoding="utf-8-sig", keep_default_na=False)
    dropped = int((df["Group"] == "None").sum())
    df = df[df["Group"] != "None"].copy()          # unassignable contours, QC drop
    for c in ("area", "convex_hull_area", "solidity", "perimeter", "width", "height",
              "longest_path", "convex_hull_vertices", "ellipse_major_axis",
              "ellipse_minor_axis", "ellipse_eccentricity", "linear_scale", "area_scale"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    lin, area = df["linear_scale"].astype(float), df["area_scale"].astype(float)
    if not ((lin ** 2 - area).abs() < 1e-14).all():
        raise SystemExit("area_scale is no longer linear_scale^2 — unit conversion unsafe")
    mm_per_px = lin * 1000.0                       # metres -> millimetres
    mm2_per_px = area * 1e6

    parts = df["sample_name"].str.extract(r"^(?P<plate>P\d)-(?P<substrate>[A-Za-z0-9]+)(?:-(?P<rep>\d+))?$")

    # Take the date from the image filename (GLDS-476_image-analysis_YYMMDD-Pn.tiff)
    # rather than the `Age` column, then check the two agree — `Age` is the day of
    # the month, which is only unambiguous because the series sits inside one month.
    stamp = df["image_name"].str.extract(r"_(\d{2})(\d{2})(\d{2})-")
    img_date = ("20" + stamp[0] + "-" + stamp[1] + "-" + stamp[2])
    if not (stamp[2] == df["Age"].astype(str).str.zfill(2)).all():
        raise SystemExit("`Age` disagrees with the date in `image_name` — check the source table")
    out = pd.DataFrame({
        "plant_id": df["sample_name"],
        "contour_id": df["samples"],
        "plate": parts["plate"],
        "substrate": df["Group"],
        "plate_replicate": pd.to_numeric(parts["rep"], errors="coerce"),
        "date": img_date,
        "image_name": df["image_name"],
        "area_mm2": df["area"] * mm2_per_px,
        "convex_hull_area_mm2": df["convex_hull_area"] * mm2_per_px,
        "solidity": df["solidity"],
        "perimeter_mm": df["perimeter"] * mm_per_px,
        "width_mm": df["width"] * mm_per_px,
        "height_mm": df["height"] * mm_per_px,
        "longest_path_mm": df["longest_path"] * mm_per_px,
        "ellipse_major_axis_mm": df["ellipse_major_axis"] * mm_per_px,
        "ellipse_minor_axis_mm": df["ellipse_minor_axis"] * mm_per_px,
        "ellipse_eccentricity": df["ellipse_eccentricity"],
        "convex_hull_vertices": df["convex_hull_vertices"],
        "area_px": df["area"],
    })
    log(f"  PlantCV: {len(out)} rows kept, {dropped} 'None'-group contours dropped at QC")
    return out.sort_values(["date", "plate", "substrate", "plant_id"]).reset_index(drop=True)


FIRST_IMAGE = dt.date(2021, 5, 2)     # the earliest plate scan in the study


def check_sowing_consistency(samples: pd.DataFrame, leaves: pd.DataFrame) -> dict:
    """Test whether the deposited metadata implies one sowing date. It does not.

    Every plant shared a plate and a chamber, so one sowing date must fit them
    all. For each sample the candidate harvest dates are the imaging dates whose
    leaf count equals the ISA's `Number of Leaves at Time of Sample Collection`;
    each implies a sowing date of `harvest - age at harvest`. Intersecting those
    sets across samples comes back **empty**: the lunar samples (age 21 d) imply
    2021-04-27 while JSC-1A replicate 3 (age 20 d, 8 leaves only on the final
    scan) implies 2021-04-28.

    We therefore do not publish a sowing date. Growth is expressed on the
    unambiguous axis the images themselves provide — days from the first plate
    scan (2021-05-02) — and `age_at_harvest_days` is carried through verbatim
    from the ISA. The discrepancy is reported here so it travels with the data
    rather than being silently smoothed over.
    """
    by_gsm = {g: dict(zip(d["date"], d["n_leaves"])) for g, d in leaves.groupby("gsm")}
    per_sample, inter = {}, None
    for _, r in samples.iterrows():
        series = by_gsm.get(r["gsm"])
        if not series or pd.isna(r["n_leaves_at_harvest"]) or pd.isna(r["age_at_harvest_days"]):
            continue
        age = int(r["age_at_harvest_days"])
        sow = {(dt.date.fromisoformat(d) - dt.timedelta(days=age)).isoformat()
               for d, n in series.items() if n == int(r["n_leaves_at_harvest"])}
        per_sample[r["gsm"]] = sorted(sow)
        inter = sow if inter is None else (inter & sow)

    consistent = sorted(inter or [])
    log(f"  sowing-date check: {len(consistent)} date(s) fit all {len(per_sample)} "
        f"phenotyped samples{' — ' + consistent[0] if len(consistent) == 1 else ''}")
    if len(consistent) != 1:
        log("    → no sowing date published; growth axis is days from the first "
            "plate scan (2021-05-02). See results/tables/sowing_date_check.csv")
    return {"consistent_dates": consistent, "per_sample": per_sample}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    samples, leaves, traits = build_samples(), build_leaf_counts(), build_plantcv()

    if len(samples) != 20:
        raise SystemExit(f"expected 20 RNA-seq samples, got {len(samples)}")
    if leaves["gsm"].nunique() != 16:
        raise SystemExit(f"expected 16 samples with morphometrics, got {leaves['gsm'].nunique()}")

    check = check_sowing_consistency(samples, leaves)
    pd.DataFrame([{"gsm": g, "candidate_sowing_dates": " ".join(v)}
                  for g, v in sorted(check["per_sample"].items())]
                 ).to_csv(OUT / "sowing_date_check.csv", index=False)

    samples = samples.merge(leaves[["gsm", "plate"]].drop_duplicates(), on="gsm", how="left")
    samples["phenotyped"] = samples["gsm"].isin(check["per_sample"])

    # Shared, assumption-free time axis: days from the first plate scan.
    for df in (leaves, traits):
        df["day"] = [(dt.date.fromisoformat(d) - FIRST_IMAGE).days for d in df["date"]]
    leaves = leaves.merge(samples[["gsm", "treatment", "substrate"]], on="gsm", how="left")

    samples.to_csv(OUT / "sample_metadata.csv", index=False)
    leaves.to_csv(OUT / "leaf_counts_long.csv", index=False)
    traits.to_csv(OUT / "plantcv_traits_long.csv", index=False)

    log(f"\n  sample_metadata.csv     {len(samples)} rows")
    log(f"  leaf_counts_long.csv    {len(leaves)} rows ({leaves['gsm'].nunique()} plants x "
        f"{leaves['date'].nunique()} dates)")
    log(f"  plantcv_traits_long.csv {len(traits)} rows ({traits['plant_id'].nunique()} plants x "
        f"{traits['date'].nunique()} dates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
