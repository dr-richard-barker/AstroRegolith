#!/usr/bin/env python3
"""The JSON the Curation view reads.

Follows `09_export_site_data.py`: everything the site displays is written here
from `data/ares/`, so a figure on the page cannot disagree with a committed
table.

Only the regolith slice of the photograph index travels to `public/data/` — the
full index is 33 MB and derivable. The coverage summary is a small aggregate and
goes across whole, because the page states its numbers.

Output: public/data/curation.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, SITE_DATA, log, write_json  # noqa: E402

ARES = DATA / "ares"

COMPENDIUM_URL = "https://curator.jsc.nasa.gov/lunar/lsc/{generic}.pdf"
SAMPLE_PAGE = "https://curator.jsc.nasa.gov/lunar/samplecatalog/index.cfm"
LUNAR_API = "https://curator.jsc.nasa.gov/rest/lunarapi/samples"


def _load(name: str):
    p = ARES / name
    if not p.exists():
        raise SystemExit(f"{p} missing — run scripts/14_fetch_ares_curation.py first")
    return json.loads(p.read_text())


def main() -> int:
    SITE_DATA.mkdir(parents=True, exist_ok=True)

    regoliths = _load("osd476_regoliths.json")
    photos = _load("osd476_photos.json")
    summary = _load("coverage_summary.json")
    simulants = _load("simulants.json")
    a3d = _load("a3d_lunar.json")
    prov = _load("pds_index_provenance.json")

    compendium = None
    if (ARES / "compendium_index.json").exists():
        compendium = _load("compendium_index.json")

    a3d_by_generic: dict = {}
    for r in a3d:
        a3d_by_generic.setdefault(r["generic"], []).append(r)

    out_regoliths = []
    for generic, blob in sorted(regoliths.items()):
        d = blob["detail"]
        shots = photos.get(generic, [])
        out_regoliths.append({
            "generic": generic,
            "mission": d.get("MISSION"),
            "sampleType": d.get("SAMPLETYPE"),
            "sampleSubtype": d.get("SAMPLESUBTYPE"),
            "originalWeightG": d.get("ORIGINALWEIGHT"),
            "pristinityPct": d.get("PRISTINITY"),
            "pristinityDate": d.get("PRISTINITYDATE"),
            "station": d.get("STATION"),
            "landmark": d.get("LANDMARK"),
            "bagNumber": d.get("BAGNUMBER"),
            "description": d.get("GENERICDESCRIPTION"),
            "hasThinSection": bool(d.get("HASTHINSECTION")),
            "nThinSections": len(blob.get("thin_sections") or []),
            "displaySamples": d.get("DISPLAYSAMPLENUMBER"),
            "osd476Splits": blob.get("osd476_splits") or [],
            "photos": [
                {
                    "photo": p["photo"],
                    "type": p["photo_type"],
                    "description": p["photo_description"],
                    "width": p["width"],
                    "height": p["height"],
                    "fileSize": p.get("file_size", ""),
                    "jpegUrl": p["jpeg_url"],
                    "tifUrl": p["tif_url"],
                }
                for p in shots
            ],
            "nPhotos": len(shots),
            # None when the compendium was not consulted: unknown, not absent.
            "hasCompendium": (generic in compendium) if compendium is not None else None,
            "compendiumUrl": COMPENDIUM_URL.format(generic=generic),
            "a3d": a3d_by_generic.get(generic, []),
        })

    payload = {
        "regoliths": out_regoliths,
        "simulants": [
            {
                "name": s["simulant"],
                "nameAsPublished": s["name_as_published"],
                "wasCorrected": s["was_corrected"],
                "surface": s["representative_surface"],
                "bench": s.get("local_bench"),
                "micro": s.get("local_micro"),
                "benchSourceUrl": s.get("simulant_photo_full"),
                "microSourceUrl": s.get("microscope_photo_full"),
            }
            for s in simulants["simulants"]
        ],
        "simulantCorrections": simulants.get("corrections", []),
        "simulantStock": simulants.get("stock", []),
        "coverage": summary,
        "pdsIndexProvenance": prov,
        "sources": {
            "lunarApi": LUNAR_API,
            "samplePage": SAMPLE_PAGE,
            "pdsArchive": "https://asc-pds-apollo.s3.us-west-2.amazonaws.com",
            "simulantTable": "https://ares.jsc.nasa.gov/projects/simulants/development-lab.html",
            "astromaterials3d": "https://ares.jsc.nasa.gov/astromaterials3d/",
            "compendium": "https://curator.jsc.nasa.gov/lunar/lsc/",
        },
    }

    if len(payload["regoliths"]) != 3:
        raise SystemExit(f"expected 3 OSD-476 regoliths, exported "
                         f"{len(payload['regoliths'])}")
    if not payload["simulants"]:
        raise SystemExit("no simulants exported")

    dest = write_json(SITE_DATA / "curation.json", payload)
    log(f"  curation.json — {len(payload['regoliths'])} regoliths, "
        f"{len(payload['simulants'])} simulants, "
        f"{sum(r['nPhotos'] for r in out_regoliths)} photographs, "
        f"{dest.stat().st_size / 1024:.0f} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
