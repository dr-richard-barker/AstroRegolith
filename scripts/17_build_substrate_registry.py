#!/usr/bin/env python3
"""The substrate registry — one dimension table the whole database keys into.

Before this step, "what the plant grew in" was written eight different ways
across the repository and none of them joined:

    phenotypes / charts     A11, A12, A17, JSC1A
    OSD-476 factor values   "Apollo 11 regolith", "JSC-1A lunar simulant"
    probe series            "Lunar simulant", "Martian Regolith Simulant", ...
    LHS-1 specification     "LHS-1 (Exolith lunar highlands simulant)"
    ARES simulant table     JSC-1A, LHS-1, BP-1, NU-LHT-2M, ...
    ARES simulant stock     "JSC-1/1A", "GreenSpar < 90 um", "NU-LHT Series"
    NASA curation API       10084, 12070, 70051
    Epicollect5 form        free text typed by a contributor

This builds the table that maps all of them onto one identifier, so a bar in a
growth chart can resolve to the curated soil it grew in, with its mass,
pristinity, collection landmark and NASA's photograph of it.

### The rule this file exists to enforce

**A mapping is only written when there is evidence for it, and the evidence is
recorded in the row.** Where a substrate cannot be identified, it is registered
as unresolved with the reason, never guessed from a similar-looking name. The
site's own "Plan an experiment" view tells contributors that simulant name,
supplier and batch are what decide reusability; the probe series in this very
repository records none of them, and the registry says so rather than quietly
inventing a product for it.

Outputs: data/substrates/registry.csv and public/data/substrates_registry.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, SITE_DATA, log, write_json  # noqa: E402

ARES = DATA / "ares"
OUT = DATA / "substrates"

# --- the curated mappings -------------------------------------------------
# Each entry is a decision with a stated reason. Anything not here, and not
# generated from the ARES table below, ends up unresolved.

OSD476_EVIDENCE = (
    "OSD-476 i_Investigation.txt: \"4 x 1 g samples of regolith from Apollo 11 "
    "(10084-2075, 2076, 2077, 2078), Apollo 12 (12070-105, 99, 106, 109) and "
    "Apollo 17 (70051-159, 160, 161, 162)\""
)

#: Apollo soils: alias -> (generic, evidence)
APOLLO = {
    "10084": ("A11", ["A11", "Apollo 11 regolith"]),
    "12070": ("A12", ["A12", "Apollo 12 regolith"]),
    "70051": ("A17", ["A17", "Apollo 17 regolith"]),
}

#: Simulants whose local aliases are known. ares_name must exist in the ARES
#: table or the build fails, so a renamed simulant is caught rather than
#: silently dropped.
SIMULANT_ALIASES = {
    "JSC-1A": {
        "aliases": ["JSC1A", "JSC-1A lunar simulant"],
        "evidence": (
            "OSD-476 names its control \"the NASA lunar simulant JSC-1A (Orbitec "
            "JSC-1A Lunar)\"; exact name match to the ARES SDL table row JSC-1A"
        ),
    },
    "LHS-1": {
        "aliases": ["LHS-1 (Exolith lunar highlands simulant)"],
        "evidence": (
            "The specification table in substrates.json is titled LHS-1 and sourced "
            "from Exolith Lab; the ARES SDL row LHS-1 is likewise Lunar Highlands"
        ),
    },
}

#: Terrestrial growth media from the probe series. These are not simulants, so
#: they need no ARES link -- but they are a real substrate class and belong in
#: the registry so every probe trace resolves to something.
MEDIA = {
    "Perlite (Small particle)": "perlite",
    "Vermiculite (old powder)": "vermiculite",
    "Potting soil": "potting-soil",
    "Arcelite": "arcelite",
    "Potassium polyacrylate": "potassium-polyacrylate",
}

#: Substrates that cannot be identified from what the repository records.
#: `parent` groups readings that are the same material under two treatments.
UNRESOLVED = {
    "Lunar simulant": {
        "kind": "lunar_simulant",
        "why": (
            "The CoSE Lunar Large Chamber probe series records only the generic "
            "label \"Lunar simulant\" \u2014 no product name, supplier or batch \u2014 so "
            "it cannot be keyed to a row in the ARES simulant table. Several ARES "
            "lunar simulants would fit the label equally well."
        ),
    },
    "Stirred Lunar simulant": {
        "kind": "lunar_simulant",
        "parent": "Lunar simulant",
        "why": (
            "The same unidentified material as \"Lunar simulant\", stirred during the "
            "run; the product is unrecorded for both."
        ),
    },
    "Martian Regolith Simulant": {
        "kind": "mars_simulant",
        "why": (
            "Generic label with no product name or supplier. The ARES table lists "
            "three Mars simulants (JPL MMS, JSC MARS-1, JSC ROCKNEST) and nothing "
            "in this repository distinguishes which, if any, was used."
        ),
    },
}


def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def _load(name: str):
    p = ARES / name
    if not p.exists():
        raise SystemExit(f"{p} missing — run scripts/14_fetch_ares_curation.py first")
    return json.loads(p.read_text())


def build() -> list:
    ares = _load("simulants.json")
    regoliths = _load("osd476_regoliths.json")
    photos = _load("osd476_photos.json")
    compendium = _load("compendium_index.json") if (ARES / "compendium_index.json").exists() else None

    by_name = {s["simulant"]: s for s in ares["simulants"]}
    for name in SIMULANT_ALIASES:
        if name not in by_name:
            raise SystemExit(
                f"{name!r} is aliased here but is no longer in the ARES simulant "
                f"table ({sorted(by_name)}) — the mapping must be re-checked"
            )

    rows: list = []

    # --- Apollo soils -----------------------------------------------------
    for generic, (code, aliases) in APOLLO.items():
        blob = regoliths.get(generic)
        if blob is None:
            raise SystemExit(f"no curation record harvested for Apollo {generic}")
        d = blob["detail"]
        rows.append({
            "substrate_id": f"apollo-{generic}",
            "label": f"Apollo {d['MISSION'].split()[-1]} {generic}",
            "short": code,
            "kind": "apollo_soil",
            "apollo_generic": generic,
            "ares_simulant": "",
            "name_as_published": "",
            # No terrain classification is asserted for the returned soils:
            # ARES's "representative surface" column describes simulants, and
            # nothing harvested here classifies the real samples by terrain.
            # The mission and landmark below are NASA's own record.
            "surface": "",
            "mission": d.get("MISSION") or "",
            "landmark": d.get("LANDMARK") or "",
            "original_weight_g": d.get("ORIGINALWEIGHT") or "",
            "pristinity_pct": d.get("PRISTINITY") or "",
            "particle_size": d.get("SAMPLESUBTYPE") or "",
            "n_photos": len(photos.get(generic, [])),
            "has_compendium": (generic in compendium) if compendium is not None else "",
            "resolution": "deposit-stated",
            "evidence": OSD476_EVIDENCE,
            "aliases": "|".join(aliases),
        })

    # --- ARES simulants ---------------------------------------------------
    for name, s in sorted(by_name.items()):
        extra = SIMULANT_ALIASES.get(name, {})
        # The simulant's own name is an alias of itself, so a bare "JSC-1A"
        # from a contribution form resolves.
        aliases = [name] + list(extra.get("aliases", []))
        # `name_as_published` is deliberately NOT an alias. For CSM-LMT-1 the
        # published name is "CSM-LHT-1", which is a different, real simulant --
        # aliasing it here would make the string "CSM-LHT-1" resolve to the
        # wrong material, the precise error the correction exists to undo.
        surface = s["representative_surface"]
        kind = ("mars_simulant" if "Mars" in surface else "lunar_simulant")
        rows.append({
            "substrate_id": f"sim-{slug(name)}",
            "label": name,
            "short": name,
            "kind": kind,
            "apollo_generic": "",
            "ares_simulant": name,
            "name_as_published": s["name_as_published"] if s["was_corrected"] else "",
            "surface": surface,
            "mission": "", "landmark": "", "original_weight_g": "",
            "pristinity_pct": "", "particle_size": "",
            "n_photos": sum(1 for k in ("local_bench", "local_micro") if s.get(k)),
            "has_compendium": "",
            # "exact" only when this repository actually uses the simulant
            # under a local name; otherwise it is catalogue reference data.
            "resolution": "exact" if extra.get("aliases") else "catalogue-only",
            "evidence": extra.get(
                "evidence",
                "Row in the NASA ARES Simulant Development Lab table; no use of "
                "this simulant is recorded in this repository.",
            ),
            "aliases": "|".join(aliases),
        })

    # --- terrestrial media ------------------------------------------------
    for label, key in MEDIA.items():
        rows.append({
            "substrate_id": f"medium-{key}",
            "label": label, "short": label, "kind": "terrestrial_medium",
            "apollo_generic": "", "ares_simulant": "", "name_as_published": "",
            "surface": "Terrestrial",
            "mission": "", "landmark": "", "original_weight_g": "",
            "pristinity_pct": "", "particle_size": "", "n_photos": 0,
            "has_compendium": "",
            "resolution": "exact",
            "evidence": "Named terrestrial growth medium in the CoSE Lunar Large "
                        "Chamber probe series; not a planetary simulant.",
            "aliases": label,
        })

    # --- unresolved -------------------------------------------------------
    for label, meta in UNRESOLVED.items():
        rows.append({
            "substrate_id": f"unresolved-{slug(label)}",
            "label": label, "short": label, "kind": meta["kind"],
            "apollo_generic": "", "ares_simulant": "", "name_as_published": "",
            "surface": "",
            "mission": "", "landmark": "", "original_weight_g": "",
            "pristinity_pct": "", "particle_size": "", "n_photos": 0,
            "has_compendium": "",
            "resolution": "unresolved",
            "evidence": meta["why"],
            "aliases": label,
        })

    return rows


def check(rows: list) -> dict:
    """Assert the registry is usable before anything is written."""
    if not rows:
        raise SystemExit("registry built zero rows")

    ids = [r["substrate_id"] for r in rows]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"duplicate substrate_id: {dupes}")

    # An alias must resolve to exactly one substrate, or lookups are ambiguous.
    owner: dict = {}
    for r in rows:
        for a in filter(None, r["aliases"].split("|")):
            if a in owner:
                raise SystemExit(
                    f"alias {a!r} claimed by both {owner[a]} and {r['substrate_id']}"
                )
            owner[a] = r["substrate_id"]

    # Every substrate the analysis actually uses must resolve to a real sample.
    for code in ("A11", "A12", "A17", "JSC1A"):
        if code not in owner:
            raise SystemExit(f"the analysis uses {code!r} but nothing in the registry claims it")
    for code in ("A11", "A12", "A17"):
        r = next(x for x in rows if x["substrate_id"] == owner[code])
        if not r["apollo_generic"]:
            raise SystemExit(f"{code} resolved to {r['substrate_id']} with no Apollo sample number")

    # And every substrate string the *site data* contains must resolve too, so
    # adding one to a probe run or a phenotype table fails this build until it
    # has been registered with its evidence. Silent non-resolution would let a
    # substrate back into the database with no provenance at all, which is the
    # thing the registry exists to prevent.
    orphans = sorted(used_substrate_strings() - set(owner))
    if orphans:
        raise SystemExit(
            "these substrates appear in the site data but nothing in the registry "
            f"claims them: {orphans}\n"
            "Add each to APOLLO, SIMULANT_ALIASES, MEDIA or UNRESOLVED in this "
            "file, with the evidence for the mapping -- or the reason there is none."
        )

    return {"n": len(rows), "aliases": owner, "n_used": len(used_substrate_strings())}


def used_substrate_strings() -> set:
    """Every substrate name the built site data actually contains."""
    used: set = set()

    pheno = SITE_DATA / "phenotypes.json"
    if pheno.exists():
        s = pheno.read_text()
        used |= set(re.findall(r'"substrate": "([^"]+)"', s))
        used |= set(re.findall(r'"treatment": "([^"]+)"', s))

    subs = SITE_DATA / "substrates.json"
    if subs.exists():
        d = json.loads(subs.read_text())
        used |= {r["substrate"] for r in d.get("probe", {}).get("endpoint", [])}
        for r in d.get("simulant_lhs1", {}).get("mineralogy", []):
            if r.get("simulant"):
                used |= {r["simulant"]}

    return {u for u in used if u.strip()}


def main() -> int:
    rows = build()
    stats = check(rows)
    OUT.mkdir(parents=True, exist_ok=True)

    import csv as _csv
    fields = list(rows[0])
    with (OUT / "registry.csv").open("w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in sorted(rows, key=lambda x: x["substrate_id"]):
            w.writerow(r)

    write_json(SITE_DATA / "substrates_registry.json", {
        "note": "One row per substrate. `aliases` maps every name used across "
                "this repository onto it; `resolution` says how firmly the "
                "identification is known.",
        "substrates": sorted(rows, key=lambda x: x["substrate_id"]),
        "alias_index": stats["aliases"],
    })

    by_res: dict = {}
    for r in rows:
        by_res[r["resolution"]] = by_res.get(r["resolution"], 0) + 1
    log(f"  registry.csv — {stats['n']} substrates, "
        f"{len(stats['aliases'])} aliases")
    for k, v in sorted(by_res.items()):
        log(f"    {k:16} {v}")
    for r in rows:
        if r["resolution"] == "unresolved":
            log(f"    ! unresolved: {r['label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
