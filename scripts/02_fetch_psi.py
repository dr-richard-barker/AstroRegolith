#!/usr/bin/env python3
"""Catalogue the regolith-relevant NASA Physical Sciences Informatics investigations.

PSI (psi.nasa.gov) runs the same GeoDE backend as OSDR — the search endpoint is
`/geode-py/ws/repo/search`, found by reading the PSI web app's own bundle. Like
OSDR it is not callable from a browser on another origin, so the result is baked
into `public/data/psi_regolith_catalog.json`.

An honest caveat travels with the output and is shown on the site: **PSI holds no
plant-in-regolith data.** Its regolith content is granular mechanics (STRATA-1),
regolith-derived cement/ISRU, and dust behaviour. Those matter for designing a
regolith growth experiment — particle packing, dust transport, binder chemistry —
but they are physics investigations, not biology.
"""
from __future__ import annotations

import datetime as dt
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import PSI_API, PSI_STUDY_URL, SITE_DATA, get_json, log, write_json  # noqa: E402

# Curated: `relevance` says what a regolith plant scientist would actually take
# from each. Search alone over-returns (any "grain"/"soil" token scores) so the
# script reports every hit but only promotes these to the curated list.
CURATED = {
    "PSI-110": "Regolith mechanics in microgravity (STRATA-1): how granular beds of asteroid/lunar-analogue material segregate and pack over long durations. Bears on substrate settling and root penetration resistance in low gravity.",
    "PSI-84": "Cement solidified in microgravity (MICS): hydration and pore structure of a regolith-derived binder. The ISRU counterpart to growing in regolith — the same feedstock, a different use.",
    "PSI-83": "MICS on a variable-gravity platform — the gravity-level dependence of the same binder chemistry.",
    "PSI-174": "Micromechanical modelling of microgravity-solidified cement, giving pore-network parameters for regolith-derived material.",
    "PSI-47": "Dust and aerosol measurement: particulate behaviour in a closed cabin — relevant to regolith dust load in a plant-growth habitat.",
    "PSI-187": "Plant Water Management: capillary water delivery to plant roots in microgravity. Not regolith, but the irrigation physics any regolith substrate has to work with.",
}
SEARCH_TERMS = ["regolith", "lunar", "dust", "granular", "regolith simulant",
                "soil", "particle", "plant"]


def search(term: str, size: int = 30) -> list:
    url = f"{PSI_API}/search?term={urllib.parse.quote(term)}&size={size}"
    return [h.get("_source", {}) for h in get_json(url).get("hits", {}).get("hits", [])]


def card(src: dict, relevance: str = "") -> dict:
    acc = src.get("Accession", "")
    return {
        "accession": acc,
        "title": src.get("Title", ""),
        "acronym": src.get("Acronym", ""),
        "research_area": src.get("Research Area", ""),
        "sub_area": src.get("SubResearch Area", ""),
        "project_type": src.get("Project Type", ""),
        "platform": src.get("Flight Platform", ""),
        "keywords": [k.strip() for k in (src.get("Keywords") or "").split("  ") if k.strip()],
        "start": src.get("Investigation Start Date", ""),
        "end": src.get("Investigation End Date", ""),
        "relevance": relevance,
        "url": PSI_STUDY_URL.format(acc=acc),
    }


def main() -> int:
    seen: dict = {}
    for term in SEARCH_TERMS:
        for s in search(term):
            acc = s.get("Accession")
            if acc and acc not in seen:
                seen[acc] = s
        log(f"  · searched '{term}'")

    missing = [a for a in CURATED if a not in seen]
    for acc in missing:                       # curated hit that search missed today
        log(f"  ! curated {acc} not returned by search — fetching directly")
        hits = search(acc, size=5)
        for s in hits:
            if s.get("Accession") == acc:
                seen[acc] = s

    curated = [card(seen[a], CURATED[a]) for a in CURATED if a in seen]
    curated.sort(key=lambda c: int(c["accession"].split("-")[1]))
    others = sorted((card(s) for a, s in seen.items() if a not in CURATED),
                    key=lambda c: int(c["accession"].split("-")[1]))

    write_json(SITE_DATA / "psi_regolith_catalog.json", {
        "source": "NASA Physical Sciences Informatics (PSI)",
        "api": f"{PSI_API}/search",
        "accessed": dt.date.today().isoformat(),
        "caveat": ("PSI holds no plant-in-regolith data. Its regolith-relevant content is "
                   "granular mechanics, regolith-derived cement/ISRU and dust behaviour — "
                   "physics investigations that constrain how a regolith growth substrate "
                   "behaves, not biology. Listed here so an experiment designer can find "
                   "the substrate physics, with that limitation stated up front."),
        "curated": curated,
        "other_hits": others,
    })
    log(f"\n{len(curated)} curated + {len(others)} other PSI investigations "
        f"→ public/data/psi_regolith_catalog.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
