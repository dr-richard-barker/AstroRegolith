#!/usr/bin/env python3
"""NASA curation provenance for the regoliths OSD-476 actually grew plants in.

OSD-476's `i_Investigation.txt` names its substrate to the split:

    "4 x 1 g samples of regolith from Apollo 11 (10084-2075, 2076, 2077, 2078),
     Apollo 12 (12070-105, 99, 106, 109) and Apollo 17 (70051-159, 160, 161,
     162). All lunar samples were of particle size less than 1 mm."

10084, 12070 and 70051 are verbatim primary keys in NASA's Apollo Sample and
Photo Database, so this database's plants join to the curation record of the
exact soil they grew in — mass, pristinity, collection landmark, thin sections,
photographs — on an exact key rather than on a mission name.

This step also builds the coverage table over all 2,511 Apollo and Luna samples,
which is what turns "70051 has no photograph" from an anecdote into a measured
result.

Unlike OSDR and PSI, the curation API answers `Access-Control-Allow-Origin: *`,
so the site *could* call it live. It is baked anyway, for the same reason every
other number here is baked: a figure that reads a committed table cannot drift.
The site's live-lookup box is an explicitly labelled extra on top.

Outputs: data/ares/*.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, log, write_json  # noqa: E402

# The client lives in its own repository so sibling projects can use it. A
# sibling checkout is accepted so the pipeline runs before it is pip-installed.
_SIBLING = Path(__file__).resolve().parents[2] / "ares-curation" / "src"
if _SIBLING.exists():
    sys.path.insert(0, str(_SIBLING))

try:
    from ares_curation import a3d, compendium, coverage, lunar, pds
except ImportError:  # noqa: BLE001 - re-raised with an actionable message
    raise SystemExit(
        "ares-curation is not importable.\n"
        "  pip install ares-curation\n"
        "or clone it beside this repository:\n"
        "  git clone https://github.com/dr-richard-barker/ares-curation ../ares-curation"
    )

OUT = DATA / "ares"

# Fetching the compendium index means one request to a host whose robots.txt
# disallows automated access; see ares_curation/compendium.py. Left on because
# the coverage table's compendium column is a published result, and the cost is
# a single GET of one index page with no PDFs mirrored. Set to False to report
# compendium coverage as unknown instead.
INCLUDE_COMPENDIUM = True


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    log("NASA lunar curation API ...")
    missions = lunar.listmissions()
    samples = lunar.all_samples()
    stats = lunar.check_invariants(samples, missions)
    log(f"  {stats['n_samples']} samples across {stats['n_missions']} missions")
    write_json(OUT / "lunar_samples.json", samples)

    log("OSD-476 regolith provenance ...")
    regoliths = {}
    for generic, meta in lunar.OSD476_REGOLITHS.items():
        detail = lunar.sampledetails(generic)
        if detail is None:
            raise SystemExit(f"OSD-476 regolith {generic} not found in the curation API")
        regoliths[generic] = {
            "detail": detail,
            "thin_sections": lunar.samplethinsections(generic),
            "displays": lunar.sampledisplays(generic),
            "osd476_splits": meta["splits"],
        }
        log(f"  {generic} {detail['MISSION']:9} {detail['SAMPLETYPE']}/"
            f"{detail['SAMPLESUBTYPE']}  {detail['ORIGINALWEIGHT']} g  "
            f"pristinity {detail['PRISTINITY']}%")
    write_json(OUT / "osd476_regoliths.json", regoliths)

    log("PDS Apollo sample photographs ...")
    photos, prov = pds.photo_index()
    log(f"  {sum(len(v) for v in photos.values())} photographs for {len(photos)} samples")
    for p in prov:
        if not p["rows_match_label"]:
            log(f"  ! {p['volume']}: parsed {p['parsed_rows']} rows, label declares "
                f"{p['declared_rows']} (bytes reconcile: {p['bytes_accounted_for']})")
    write_json(OUT / "pds_index_provenance.json", prov)
    # Only the regolith slice is committed; the full 33 MB index is derivable.
    write_json(OUT / "osd476_photos.json",
               {g: photos.get(g, []) for g in lunar.OSD476_REGOLITHS})

    log("Astromaterials 3D ...")
    a3d_lunar = a3d.lunar()
    write_json(OUT / "a3d_lunar.json", a3d_lunar)
    log(f"  {len(a3d_lunar)} lunar samples have a 3D scan")

    comp = None
    if INCLUDE_COMPENDIUM:
        log("Lunar Sample Compendium index (one request) ...")
        comp = compendium.index(allow_restricted=True)
        log(f"  {len(comp)} samples have a compendium entry")
        write_json(OUT / "compendium_index.json", comp)
    else:
        log(f"Lunar Sample Compendium SKIPPED — {compendium.ROBOTS_NOTICE}")

    log("coverage ...")
    rows = coverage.build(
        samples, photos, comp,
        a3d_generics={r["generic"] for r in a3d_lunar},
        osd476=set(lunar.OSD476_REGOLITHS),
    )
    summary = coverage.summarise(rows)
    write_json(OUT / "coverage_summary.json", summary)
    coverage.write_csv(rows, OUT / "apollo_curation_coverage.csv")

    log(f"  photographed {summary['n_with_pds_photos']}/{summary['n_samples']}; "
        f"soils {summary['n_soil_photographed']}/{summary['n_soil_samples']}")
    for g, v in sorted(summary["osd476"].items()):
        log(f"  OSD-476 {g} ({v['mission']}): {v['n_pds_photos']} photographs, "
            f"compendium={v['has_compendium']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
