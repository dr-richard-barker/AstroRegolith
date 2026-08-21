#!/usr/bin/env python3
"""Write MANIFEST.tsv and CHECKSUMS.sha256 — the provenance record for the archive.

MANIFEST.tsv lists every non-generated input the repository depends on: what it is,
where it came from, when it was retrieved, how big it is, its SHA-256, its licence,
and whether it is redistributed here or re-fetched by the pipeline. That last column
matters for Zenodo: a 36 MB expression table is listed but not shipped.

CHECKSUMS.sha256 covers everything actually committed under the data and results
directories, in the format `sha256sum -c` expects.

Re-run after `scripts/run_all.sh`; both files are committed.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, RESULTS, ROOT, SITE_DATA, log  # noqa: E402

TODAY = dt.date.today().isoformat()
OSDR = "https://osdr.nasa.gov/bio/repo/data/studies/OSD-476"
AWG = "https://github.com/dr-richard-barker/Lunar_regolith_AWG"

# Inputs the pipeline consumes. Everything else in results/ and public/data/ is
# generated from these and is covered by CHECKSUMS.sha256 rather than listed here.
INPUTS = [
    ("data/awg/plantcv_shoot_traits.csv", "PlantCV shoot morphometrics re-scored from the OSD-476 plate scans", AWG, "CC-BY-4.0", "yes"),
    ("data/awg/broad_lunar_model_deseq2.csv", "Broad Lunar linear model: all Apollo samples pooled vs JSC-1A (DESeq2)", AWG, "CC-BY-4.0", "yes"),
    ("data/awg/osd476_nfcore_counts.csv", "nf-core/rnaseq counts for the OSD-476 assay (dupRadar run 1)", AWG, "CC-BY-4.0", "yes"),
    ("data/awg/simulant_endpoint.csv", "CoSE Lunar Large Chamber probe: endpoint readings, 8 substrates", AWG, "CC-BY-4.0", "yes"),
    ("data/awg/simulant_timeseries.csv", "CoSE Lunar Large Chamber probe: full time series", AWG, "CC-BY-4.0", "yes"),
    ("data/awg/simulant_catalogue.csv", "Exolith LHS-1 specification (mineralogy, chemistry, physical properties)", "https://exolithsimulants.com/collections/regolith-simulants/products/lhs-1-lunar-highlands-simulant", "manufacturer spec sheet, factual data", "yes"),
    ("data/awg/ce5_farside_soil_composition.csv", "Chang'e-5 lunar soil bulk chemistry (XRF + INAA)", "https://doi.org/10.1093/nsr/nwab188", "cite the source publication", "yes"),
    ("data/awg/osdr_substrate_isa_template.xlsx", "OSDR ISA configuration template for a ground regolith substrate study", AWG, "CC-BY-4.0", "yes"),
    ("data/awg/plate_measurements_full.xlsx", "Plate measurements accompanying the shoot-analysis series", AWG, "CC-BY-4.0", "yes"),
    ("data/awg/shoot_series/", "20 P1-P4 plate photographs behind the PlantCV traits", AWG, "CC-BY-4.0", "yes"),
    ("data/osdr/OSD-476-ISA.zip", "OSD-476 ISA-Tab archive: sample table, morphometric assay, RNA-seq assay", OSDR, "NASA open data", "yes"),
    ("data/osdr/sample_table.csv", "GLDS-476 RNA-seq sample table (GSM -> condition)", OSDR, "NASA open data", "yes"),
    ("data/osdr/contrasts.csv", "GLDS-476 differential-expression contrast definitions", OSDR, "NASA open data", "yes"),
    ("data/osdr/raw_large/vst_counts_rRNArm.csv", "GLDS-476 variance-stabilised counts, rRNA removed (7.9 MB)", OSDR, "NASA open data", "no — re-fetched by scripts/01_fetch_osdr.py"),
    ("data/osdr/raw_large/normalized_counts_rRNArm.csv", "GLDS-476 normalised counts, rRNA removed (7.3 MB)", OSDR, "NASA open data", "no — re-fetched by scripts/01_fetch_osdr.py"),
    ("data/osdr/raw_large/differential_expression_rRNArm.csv", "GLDS-476 differential expression, all contrasts + annotation (36 MB)", OSDR, "NASA open data", "no — re-fetched by scripts/01_fetch_osdr.py"),
    ("data/osdr/raw_large/osd-670/", "OSD-670 morphometric photographs, full resolution (~20 MB)", "https://osdr.nasa.gov/bio/repo/data/studies/OSD-670", "NASA open data", "no — downscaled copies are in public/images/osd-670/"),
    ("data/go_terms.json", "GO term names cached from the EBI QuickGO service", "https://www.ebi.ac.uk/QuickGO/", "EMBL-EBI terms of use", "yes"),
    ("public/images/awg-shoot-series/", "Web-sized copies of the AWG plate photographs (long edge 1600 px)", AWG, "CC-BY-4.0", "yes"),
    ("public/images/osd-670/", "Web-sized copies of the OSD-670 photographs (long edge 1600 px)", "https://osdr.nasa.gov/bio/repo/data/studies/OSD-670", "NASA open data", "yes"),
]

# Directories whose committed contents are checksummed.
CHECKSUM_ROOTS = ["data/awg", "data/osdr", "results", "public/data", "public/images",
                  "manuscript/figures", "manuscript/supplementary", "legacy"]
SKIP_DIRS = {"raw_large", "__pycache__", ".fetch"}
# Deliberately excluded: it carries the build date, so its checksum changes on
# every run by design. Everything else in the tree is byte-reproducible.
SKIP_FILES = {"public/data/manifest.json"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(rel: str) -> tuple:
    """(size, sha256) for a file, or (total size, 'directory: N files') for a folder."""
    p = ROOT / rel
    if rel.endswith("/"):
        if not p.is_dir():
            return ("", "not present")
        files = sorted(f for f in p.rglob("*") if f.is_file())
        return (str(sum(f.stat().st_size for f in files)), f"directory: {len(files)} files")
    if not p.is_file():
        return ("", "not present — re-fetch with scripts/run_all.sh")
    return (str(p.stat().st_size), sha256(p))


def main() -> int:
    rows = ["\t".join(["path", "description", "source", "licence", "redistributed_here",
                       "bytes", "sha256", "retrieved"])]
    missing = 0
    for rel, desc, src, lic, redist in INPUTS:
        size, digest = describe(rel)
        if digest.startswith("not present"):
            missing += 1
        rows.append("\t".join([rel, desc, src, lic, redist, size, digest, TODAY]))
    (ROOT / "MANIFEST.tsv").write_text("\n".join(rows) + "\n")
    log(f"  MANIFEST.tsv: {len(INPUTS)} inputs"
        + (f" ({missing} not present locally — expected for re-fetchable files)" if missing else ""))

    lines, count = [], 0
    for root in CHECKSUM_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            rel = str(f.relative_to(ROOT))
            if (not f.is_file() or rel in SKIP_FILES
                    or any(part in SKIP_DIRS for part in f.parts)):
                continue
            lines.append(f"{sha256(f)}  {f.relative_to(ROOT)}")
            count += 1
    (ROOT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n")
    log(f"  CHECKSUMS.sha256: {count} committed files")
    log("  verify with:  sha256sum -c CHECKSUMS.sha256   (macOS: shasum -a 256 -c)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
