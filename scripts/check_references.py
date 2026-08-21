#!/usr/bin/env python3
"""Build and verify `manuscript/references.bib` from Crossref — never from memory.

Every entry starts as a DOI and a cite key. The script resolves each DOI through
the Crossref REST API and writes the BibTeX from the *returned* metadata, so
authors, titles, journals, volumes, pages and years cannot be misremembered. A
DOI that does not resolve is reported and left out of the .bib rather than
guessed at, and the run exits non-zero so CI catches it.

  python3 scripts/check_references.py            build/refresh references.bib
  python3 scripts/check_references.py --check     verify only, write nothing

Sources with no DOI (a simulant spec sheet, a data repository record) are held
in NON_DOI below with the URL that has to be checked by hand; they are written
into the .bib as @misc and listed in the report as unverifiable by this script.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import ROOT, get_json, log  # noqa: E402

BIB = ROOT / "manuscript" / "references.bib"
CROSSREF = "https://api.crossref.org/works/"
MAILTO = "dr.richard.barker@gmail.com"        # Crossref's polite pool

# cite key -> DOI. Add a reference by adding its DOI here, never by writing BibTeX.
DOIS = {
    "paul2022apollo": "10.1038/s42003-022-03334-8",
    "li2022change5": "10.1093/nsr/nwab188",
    "gehan2017plantcv": "10.7717/peerj.4088",
    "love2014deseq2": "10.1186/s13059-014-0550-8",
    "benjamini1995fdr": "10.1111/j.2517-6161.1995.tb02031.x",
    "aanensen2014epicollect": "10.12688/f1000research.4702.1",
    "berrios2021genelab": "10.1093/nar/gkaa887",
    "wu2020grf4della": "10.1126/science.aaz2046",
    "colebrook2014ga": "10.1242/jeb.089938",
    "sananmishra2016della": "10.1016/j.molp.2015.09.011",
    "achard2006della": "10.1126/science.1118642",
    "wu2009spl": "10.1016/j.cell.2009.06.031",
    "porco2016dao1": "10.1073/pnas.1604375113",
    "werner2003ckx": "10.1105/tpc.014928",
    "nakano2017pyk10": "10.1111/tpj.13377",
    "hedden2020ga": "10.1093/pcp/pcaa092",
    "sun2011della": "10.1016/j.cub.2011.02.036",
}

# No DOI exists for these. The URL is what a reader must be sent to; the script
# cannot verify them, and says so.
NON_DOI = {
    "osdr476": {
        "type": "misc",
        "title": "Plants grown in Apollo lunar regolith present stress-associated transcriptomes that inform prospects for lunar exploration",
        "author": "Paul, Anna-Lisa and Elardo, Stephen M. and Ferl, Robert J.",
        "howpublished": "NASA Open Science Data Repository, OSD-476 (GLDS-476 / LSDS-12)",
        "url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-476",
        "year": "2022",
    },
    "osdr670": {
        "type": "misc",
        "title": "CI Asteroid Regolith as an In Situ Plant Growth Medium for Space Crop Production",
        "author": "Russell, Steven J. and Fieber-Beyer, Sherry K. and Yurkonis, Kathryn A.",
        "howpublished": "NASA Open Science Data Repository, OSD-670",
        "url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-670",
        "year": "2024",
    },
    "exolithlhs1": {
        "type": "misc",
        "title": "{LHS-1} Lunar Highlands Simulant: specification sheet",
        "author": "{Exolith Lab, University of Central Florida}",
        "howpublished": "Exolith Lab simulant catalogue",
        "url": "https://exolithsimulants.com/collections/regolith-simulants/products/lhs-1-lunar-highlands-simulant",
        "year": "2021",
    },
    "nasapsi": {
        "type": "misc",
        "title": "Physical Sciences Informatics ({PSI}) system",
        "author": "{NASA Biological and Physical Sciences Division}",
        "howpublished": "NASA PSI data repository",
        "url": "https://psi.nasa.gov/physci/repo/",
        "year": "2026",
    },
    "astroregolith": {
        "type": "misc",
        "title": "{AstroRegolith}: an open database and reanalysis of plant growth in regolith",
        "author": "Barker, Richard J.",
        "howpublished": "GitHub repository",
        "url": "https://github.com/dr-richard-barker/AstroRegolith",
        "year": "2026",
    },
}

TYPE_MAP = {"journal-article": "article", "proceedings-article": "inproceedings",
            "book-chapter": "incollection", "posted-content": "misc", "book": "book"}


TAGS = re.compile(r"<[^>]+>")


def escape(s: str) -> str:
    """Crossref titles carry JATS markup (<i>, <sub>, …) — strip it, then escape
    the characters LaTeX would otherwise treat as commands."""
    s = TAGS.sub("", s)
    s = " ".join(s.split())
    return (s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
             .replace("#", r"\#").replace("$", r"\$"))


def entry_from_crossref(key: str, doi: str) -> tuple:
    """Return (bibtex, summary) built entirely from what Crossref returns."""
    d = get_json(f"{CROSSREF}{urllib.parse.quote(doi)}?mailto={MAILTO}")["message"]
    authors = " and ".join(
        f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
        for a in d.get("author", []) if a.get("family")
    ) or d.get("publisher", "")
    parts = (d.get("published-print") or d.get("published-online")
             or d.get("issued") or {}).get("date-parts", [[None]])
    year = parts[0][0] if parts and parts[0] else ""
    fields = {
        "author": authors,
        "title": (d.get("title") or [""])[0],
        "journal": (d.get("container-title") or [""])[0],
        "year": str(year or ""),
        "volume": d.get("volume", ""),
        "number": d.get("issue", ""),
        "pages": d.get("page", ""),
        "doi": d.get("DOI", doi),
        "publisher": d.get("publisher", ""),
    }
    kind = TYPE_MAP.get(d.get("type", ""), "article")
    if kind != "article":
        fields.pop("journal", None)
        fields["howpublished"] = (d.get("container-title") or [d.get("publisher", "")])[0]
    body = "\n".join(f"  {k:<12} = {{{escape(str(v))}}}," for k, v in fields.items() if v)
    return f"@{kind}{{{key},\n{body}\n}}\n", f"{fields['title'][:74]} ({fields['year']})"


def entry_from_manual(key: str, spec: dict) -> str:
    kind = spec.pop("type", "misc")
    body = "\n".join(f"  {k:<12} = {{{escape(str(v))}}}," for k, v in spec.items() if v)
    spec["type"] = kind
    return f"@{kind}{{{key},\n{body}\n}}\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only; do not write")
    args = ap.parse_args()

    entries, failed = {}, []
    for key, doi in DOIS.items():
        try:
            bib, summary = entry_from_crossref(key, doi)
            entries[key] = bib
            log(f"  ✓ {key:<22} {doi:<34} {summary}")
        except Exception as e:                                    # noqa: BLE001
            failed.append((key, doi, str(e)[:90]))
            log(f"  ✗ {key:<22} {doi:<34} UNRESOLVED — {str(e)[:60]}")

    for key, spec in NON_DOI.items():
        entries[key] = entry_from_manual(key, dict(spec))
        log(f"  · {key:<22} {'(no DOI)':<34} manual entry — verify {spec['url']}")

    if failed:
        log(f"\n  {len(failed)} DOI(s) did not resolve. They are NOT in references.bib; "
            f"fix or remove them before submission:")
        for key, doi, err in failed:
            log(f"    {key}: {doi} — {err}")

    if not args.check:
        header = (
            "% references.bib — generated by scripts/check_references.py\n"
            "%\n"
            "% Every @article below is written from metadata returned by the Crossref API\n"
            "% for its DOI, not from memory. Re-run the script to refresh or to verify.\n"
            "% @misc entries have no DOI and must be checked by hand; their URLs are in\n"
            "% the NON_DOI table of that script.\n\n"
        )
        BIB.parent.mkdir(parents=True, exist_ok=True)
        BIB.write_text(header + "\n".join(entries[k] for k in sorted(entries)))
        log(f"\n  {len(entries)} entries → {BIB}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
