#!/usr/bin/env python3
"""Pull the primary data files out of the original `Lunar_regolith_AWG` repo.

Only the *data* comes across. The GitBook scaffolding (`.gitbook/`, `SUMMARY.md`),
the AWG action-plan page and the Google-Docs project-management links are not
mirrored — see `legacy/PROVENANCE.md` for what was kept and what was dropped.

Files land in `data/awg/`. Provenance for each is recorded in `MANIFEST.tsv`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, download, log  # noqa: E402

RAW = "https://raw.githubusercontent.com/dr-richard-barker/Lunar_regolith_AWG/main/"

# repo path -> local name under data/awg/
FILES = {
    # PlantCV shoot morphometrics re-scored from the OSD-476 plate scans.
    "regolith_results_merged_v2.csv": "plantcv_shoot_traits.csv",
    # Broad Lunar model: all Apollo samples pooled vs JSC-1A simulant (DESeq2).
    "Broad Lunar Soil Model- regolith vs Earth.csv": "broad_lunar_model_deseq2.csv",
    # nf-core/rnaseq counts for the OSD-476 assay (dupRadar run 1).
    "dupradar_run1_osd476_allCounts_Regolith.csv": "osd476_nfcore_counts.csv",
    # CoSE Lunar Large Chamber regolith-probe measurements.
    "Regolith_simulant/Regolith_Combine_Data_Table.csv": "simulant_endpoint.csv",
    "Regolith_simulant/Regolith_Time_series_Raw.csv": "simulant_timeseries.csv",
    "Regolith_simulant/Exollith_simulant_web_description.csv": "simulant_catalogue.csv",
    "Regolith_simulant/Change dark side soil.csv": "ce5_farside_soil_composition.csv",
    # OSDR ISA configuration template for a ground regolith substrate study.
    "Ground_plant_regolith_substrate_study_OSDR_template.xlsx": "osdr_substrate_isa_template.xlsx",
}

# The P1-P4 shoot-analysis image series (the images the PlantCV traits came from).
PLATE_IMAGES = {
    "P1": ["P1-210502", "P1-210504", "P1-210506", "P1-210508", "P1-210510"],
    "P2": ["P2-02", "P2-04", "P2-06", "P2-08", "P2-10"],
    "P3": ["P3-02", "P3-04", "P3-06", "P3-08", "P3-10"],
    "P4": ["P4-02", "P4-04", "P4-06", "P4-08", "P4-10"],
}


def main() -> int:
    out = DATA / "awg"
    for remote, local in FILES.items():
        download(RAW + remote.replace(" ", "%20"), out / local)
        log(f"  ✓ {local}")

    img_out = out / "shoot_series"
    for plate, stems in PLATE_IMAGES.items():
        for stem in stems:
            download(f"{RAW}shoot_analysis_data-package/{plate}/{stem}.jpg",
                     img_out / f"{stem}.jpg")
    log(f"  ✓ {sum(len(v) for v in PLATE_IMAGES.values())} shoot-series images")

    download(RAW + "shoot_analysis_data-package/plate-measurements-full.xlsx",
             out / "plate_measurements_full.xlsx")
    log("  ✓ plate_measurements_full.xlsx")
    log(f"AWG source data → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
