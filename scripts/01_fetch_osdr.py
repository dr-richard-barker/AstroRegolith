#!/usr/bin/env python3
"""Catalogue the regolith-relevant NASA OSDR studies and pull OSD-476's tables.

Two outputs:

  public/data/osdr_regolith_catalog.json   the study cards the site's OSDR tab renders
  data/osdr/                               OSD-476 metadata + expression tables

The study set is *seeded* from a curated accession list (search relevance alone
misses the historic Apollo-era LSDA studies) and then *extended* by a live search
so a newly deposited regolith study is picked up by the monthly refresh workflow.
Each study is re-read from the files API, so counts in the catalogue are measured,
never asserted.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import (DATA, OSDR_STUDY_URL, SITE_DATA, download, log,  # noqa: E402
                         osdr_download_url, osdr_files, osdr_meta, osdr_search,
                         write_json)


def _one(v) -> str:
    """OSDR returns scalars or lists for the same field depending on the study."""
    if isinstance(v, list):
        return " · ".join(str(x) for x in v if x)
    return str(v or "")

IMG_EXT = ("jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif")

# Curated seed set. `why` is shown on the study card so a reader knows why a
# study is in a *regolith* database — several are proxies rather than regolith
# proper, and saying so is more useful than quietly including them.
SEED = {
    "OSD-476": "Arabidopsis grown in Apollo 11/12/17 regolith vs JSC-1A simulant — RNA-seq + per-plant morphometrics. The reference study for this database.",
    "OSD-670": "Radish and lettuce grown in CI asteroid regolith simulant as an in-situ growth medium.",
    "OSD-581": "Italian ryegrass (Lolium multiflorum) on Martian regolith simulant — proteomics.",
    "OSD-855": "Apollo 17 Challenge System: seed germination (cabbage, brussels sprout, radish) in contact with lunar material.",
    "OSD-856": "Dose-response of lettuce growth to varying amounts of simulated lunar soil (batch #005).",
    "OSD-877": "Elemental content of seedlings and liverwort tissue exposed to Apollo 15 lunar material.",
    "OSD-883": "Vegetable seedlings grown in contact with Apollo 14 lunar surface material.",
    "OSD-305": "Serratia liquefaciens under simulated Martian conditions — a microbial counterpart to the plant studies.",
    "OSD-22": "Arabidopsis root transcriptome under high magnesium — a terrestrial proxy for the ionic stress regolith imposes.",
}
SEARCH_TERMS = ["regolith", "lunar regolith", "Martian regolith simulant",
                "lunar simulant", "JSC-1A", "asteroid regolith", "lunar soil"]
REGOLITH_RE = ("regolith", "lunar", "apollo", "simulant", "martian", "asteroid", "moon")

# The OSD-476 tables the analysis needs. Large files are re-fetchable and kept
# out of git (see .gitignore); the compact ones are versioned.
OSD476_FILES = {
    "OSD-476_metadata_OSD-476-ISA.zip": ("OSD-476-ISA.zip", False),
    "GLDS-476_rna_seq_SampleTable_GLbulkRNAseq.csv": ("sample_table.csv", False),
    "GLDS-476_rna_seq_contrasts_GLbulkRNAseq.csv": ("contrasts.csv", False),
    "GLDS-476_rna_seq_VST_Counts_rRNArm_GLbulkRNAseq.csv": ("vst_counts_rRNArm.csv", True),
    "GLDS-476_rna_seq_Normalized_Counts_rRNArm_GLbulkRNAseq.csv": ("normalized_counts_rRNArm.csv", True),
    "GLDS-476_rna_seq_differential_expression_rRNArm_GLbulkRNAseq.csv": ("differential_expression_rRNArm.csv", True),
}


def study_card(acc: str, why: str) -> dict:
    """Measure a study from the files API; describe it from the biodata API."""
    study = next(iter(osdr_files(acc).get("studies", {}).values()), {})
    files = study.get("study_files", [])
    imgs = [f for f in files
            if f.get("file_name", "").lower().rsplit(".", 1)[-1] in IMG_EXT]
    m = osdr_meta(acc)
    released = m.get("study public release date")
    return {
        "accession": acc,
        "title": _one(m.get("study title")),
        "publication": _one(m.get("study publication title")),
        "organism": _one(m.get("organism")),
        "material": _one(m.get("material type")),
        "factors": _one(m.get("study factor name")),
        "measurements": _one(m.get("study assay measurement type")),
        "technology": _one(m.get("study assay technology type")),
        "authors": _one(m.get("study publication author list")),
        "released": (dt.datetime.utcfromtimestamp(released).date().isoformat()
                     if isinstance(released, (int, float)) and released else ""),
        "description": _one(m.get("study description"))[:1200],
        "why_regolith": why,
        "files": len(files),
        "images": len(imgs),
        "image_mb": round(sum(f.get("file_size", 0) for f in imgs) / 1048576, 1),
        "categories": sorted({f.get("category", "") for f in files if f.get("category")}),
        "url": OSDR_STUDY_URL.format(acc=acc),
    }


def main() -> int:
    found = dict(SEED)
    for term in SEARCH_TERMS:
        for s in osdr_search(term):
            acc = s.get("Accession") or s.get("Study Identifier") or ""
            title = s.get("Study Title") or ""
            if (acc.startswith("OSD-") and acc not in found
                    and any(k in title.lower() for k in REGOLITH_RE)):
                found[acc] = f"Discovered by search on '{term}'. Needs curation."
                log(f"  + new study from search: {acc} — {title[:70]}")

    catalog = []
    for acc, why in sorted(found.items(), key=lambda kv: int(kv[0].split("-")[1])):
        try:
            catalog.append(study_card(acc, why))
            log(f"  ✓ {acc}  files={catalog[-1]['files']:<4} images={catalog[-1]['images']}")
        except Exception as e:                                   # noqa: BLE001
            log(f"  ! {acc} skipped: {e}")

    write_json(SITE_DATA / "osdr_regolith_catalog.json", {
        "source": "NASA Open Science Data Repository (OSDR)",
        "api": "https://osdr.nasa.gov/osdr/data",
        "accessed": dt.date.today().isoformat(),
        "note": ("Baked at build time: the OSDR API restricts CORS to osdr.nasa.gov, "
                 "so a browser on github.io cannot query it directly."),
        "studies": catalog,
    })

    small, large = DATA / "osdr", DATA / "osdr" / "raw_large"
    for remote, (local, is_large) in OSD476_FILES.items():
        dest = (large if is_large else small) / local
        download(osdr_download_url("OSD-476", remote), dest)
        log(f"  ✓ OSD-476/{local}  ({dest.stat().st_size / 1048576:.1f} MB)")

    log(f"\n{len(catalog)} regolith studies catalogued → public/data/osdr_regolith_catalog.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
