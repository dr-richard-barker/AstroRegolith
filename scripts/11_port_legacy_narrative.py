#!/usr/bin/env python3
"""Port the written work from `Lunar_regolith_AWG` into `legacy/` and `results/`.

What is dropped, deliberately:
  .gitbook/                       ~200 PNGs, mostly duplicate "(1)" copies
  SUMMARY.md                      a GitBook table of contents
  README.md                       the AWG action-plan page and its Google-Docs
                                  project-management links
  future-work-.../not-sure-how-you-can-help.md   collaborator recruitment
  every {% embed %} / {% @github-files %} shortcode, and every docs.google.com
  edit link, wherever they appear

What is kept: the science. Each page is rewritten from GitBook-flavoured
Markdown into plain CommonMark, its figures re-pointed at `results/figures/`,
and a provenance header added. Figures are ported only where a kept page
actually references them, so the orphaned and duplicated assets do not travel.

Run once; `legacy/` is committed. Re-running is idempotent.
"""
from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import ROOT, download, log, write_json  # noqa: E402

RAW = "https://raw.githubusercontent.com/dr-richard-barker/Lunar_regolith_AWG/main/"
LEGACY = ROOT / "legacy"
FIGS = LEGACY / "figures"

# source path -> (destination, title). Order is the reading order.
PAGES = [
    ("README (1).md", "01-abstract.md", "Reanalysis of Arabidopsis response to lunar regolith"),
    ("the-lunar-green-revolution-introduction.md", "02-introduction.md", "The Lunar Green Revolution: introduction"),
    ("the-green-lunar-revolution-methods.md", "03-methods.md", "The Lunar Green Revolution: methods"),
    ("results/README.md", "04-results-overview.md", "Results: the broad lunar soil stress-response model"),
    ("results/regolith-image-reanalysis-stats.md", "05-results-image-reanalysis.md", "Results: shoot image reanalysis"),
    ("results/regolith-exploratory-data-analysis-gpt4-automated.md", "06-results-exploratory.md", "Results: exploratory data analysis"),
    ("results/regolith_simulant.md", "07-results-simulant.md", "Results: regolith simulant assessment"),
    ("results/broad-lunar-model-provides-evidence-for-della-potential-stabilisation.md", "08-results-della.md", "Results: evidence for DELLA stabilisation"),
    ("lunar-green-revolution-conclusion.md", "09-conclusion.md", "The Lunar Green Revolution: conclusion"),
    ("future-work-digital-doubles/README.md", "10-future-work.md", "Future work: digital doubles"),
    ("future-work-digital-doubles/regolith-stress-might-resemble-some-terrestrial-stressors.md", "11-future-terrestrial-analogues.md", "Future work: terrestrial stress analogues"),
    ("future-work-digital-doubles/microrna-anaylsis.md", "12-future-microrna.md", "Future work: microRNA analysis"),
    ("references.md", "13-references.md", "References"),
    ("Original_insights/readme.md", "14-original-insights.md", "Original insights from the Apollo regolith study"),
    ("using-the-config-file-for-regolith-research-planning.md", "15-experiment-planning.md", "Using an ISA config file to plan regolith research"),
    ("student-lessons-the-shackleton-crater-rim-garden.md", "16-lesson-shackleton-garden.md", "Student lesson: the Shackleton crater rim garden"),
    ("exploration-lesson-plan.md", "17-lesson-exploration.md", "Exploration lesson plan"),
    ("Student_images_and_data/readme.md", "18-student-data-sharing.md", "Sharing student images and data"),
]

DROPPED = {
    "README.md": "the AWG action-plan page — project management and Google-Docs links only",
    "SUMMARY.md": "GitBook table of contents, replaced by legacy/README.md",
    ".gitbook/": "~200 GitBook assets, mostly duplicate '(1)' copies; referenced figures are ported to legacy/figures/",
    "future-work-digital-doubles/not-sure-how-you-can-help.md": "collaborator recruitment for the AWG review",
    "results/README.md § slide links": "Google Slides and Sheets edit links inside otherwise-kept pages",
}

EMBED = re.compile(r"\{%\s*embed\s+url=\"([^\"]+)\"\s*%\}(.*?)\{%\s*endembed\s*%\}", re.S)
EMBED_SOLO = re.compile(r"\{%\s*embed\s+url=\"([^\"]+)\"\s*%\}")
GH_BLOCK = re.compile(r"\{%\s*@github-files/github-code-block\s+url=\"([^\"]+)\"\s*%\}")
ANY_TAG = re.compile(r"\{%.*?%\}", re.S)
GOOGLE = re.compile(r"\[([^\]]*)\]\(https://docs\.google\.com/[^)]*\)")
GOOGLE_BARE = re.compile(r"^\s*<?https://docs\.google\.com/\S*?>?\s*$", re.M)
GOOGLE_INLINE = re.compile(r"<https://docs\.google\.com/[^>]*>")
IMG = re.compile(r"!\[([^\]]*)\]\((?:\.\./)*\.gitbook/assets/([^)]+)\)")
FIGURE = re.compile(r"<figure><img src=\"(?:\.\./)*\.gitbook/assets/([^\"]+)\"[^>]*>"
                    r"(?:<figcaption>(.*?)</figcaption>)?</figure>", re.S)
STRIP_MD_ESCAPES = re.compile(r"\\([_*])")


def slugify(name: str) -> str:
    """Filesystem-safe name that stays unique.

    GitBook names duplicates `image (3) (1).png`. Those parenthesised numbers are
    the only thing distinguishing several assets, so they must survive into the
    slug — collapsing them (to `-alt`, say) silently overwrites one figure with
    another and leaves pages pointing at the wrong image.
    """
    stem = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")
    return f"awg-{stem}{Path(name).suffix.lower()}"


def rewrite(text: str, wanted: set) -> str:
    """GitBook-flavoured Markdown -> plain CommonMark."""
    def keep_figure(m):
        asset = urllib.parse.unquote(m.group(1))
        wanted.add(asset)
        cap = re.sub(r"<[^>]+>", "", m.group(2) or "").strip()
        out = f"![{cap}](figures/{slugify(asset)})"
        return f"{out}\n\n*{cap}*" if cap else out

    text = FIGURE.sub(keep_figure, text)
    text = IMG.sub(lambda m: (wanted.add(urllib.parse.unquote(m.group(2))),
                              f"![{m.group(1)}](figures/{slugify(urllib.parse.unquote(m.group(2)))})")[1], text)

    # {% embed %}…{% endembed %} keeps its inner caption, becomes a plain link.
    text = EMBED.sub(lambda m: f"{re.sub(ANY_TAG, '', m.group(2)).strip()}\n\n<{m.group(1)}>", text)
    text = EMBED_SOLO.sub(lambda m: f"<{m.group(1)}>", text)
    text = GH_BLOCK.sub(lambda m: f"Code: <{m.group(1)}>", text)
    text = ANY_TAG.sub("", text)

    # Google Docs/Sheets/Slides were the project-management layer, and several are
    # private to the original collaboration. Drop every form of the link — inline,
    # bare, and the autolink an {% embed %} just turned into — while keeping the
    # sentence around it readable.
    text = GOOGLE.sub(lambda m: m.group(1) or "", text)
    text = GOOGLE_INLINE.sub("", text)
    text = GOOGLE_BARE.sub("", text)
    # A sentence whose only content was the dropped link leaves a dangling stub.
    text = re.sub(r"^\s*(?:Link to|Here is a link to|Access|Watch)\b[^\n]{0,80}\.?\s*$",
                  "", text, flags=re.M | re.I)
    text = STRIP_MD_ESCAPES.sub(r"\1", text)
    text = re.sub(r"&#x20;", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def main() -> int:
    LEGACY.mkdir(parents=True, exist_ok=True)
    wanted: set = set()
    written = []

    for src, dst, title in PAGES:
        url = RAW + urllib.parse.quote(src)
        tmp = LEGACY / ".fetch" / dst          # unique per destination; several
        #                                        source pages are all named README.md
        try:
            download(url, tmp)
        except Exception as e:                                   # noqa: BLE001
            log(f"  ! {src} could not be fetched ({e}) — skipped")
            continue
        body = rewrite(tmp.read_text(encoding="utf-8", errors="replace"), wanted)
        header = (
            f"# {title}\n\n"
            f"> Ported verbatim (minus GitBook markup) from `{src}` in\n"
            f"> [Lunar_regolith_AWG](https://github.com/dr-richard-barker/Lunar_regolith_AWG).\n"
            f"> This is the original written record. The analysis that supersedes parts of it\n"
            f"> lives in `results/` and is reproducible from `scripts/`.\n\n---\n\n"
        )
        # The ported page carries its own H1; drop the source's leading one.
        body = re.sub(r"\A#\s+.*?\n", "", body).lstrip()
        (LEGACY / dst).write_text(header + body)
        written.append((dst, title, src))
        log(f"  ✓ {dst}")

    FIGS.mkdir(parents=True, exist_ok=True)
    ported = []
    for asset in sorted(wanted):
        try:
            download(RAW + ".gitbook/assets/" + urllib.parse.quote(asset), FIGS / slugify(asset))
            ported.append(asset)
        except Exception as e:                                   # noqa: BLE001
            log(f"  ! figure {asset} unavailable ({e})")
    log(f"  ✓ {len(ported)} referenced figures ported (orphans and duplicates left behind)")

    index = ["# Legacy: the original Lunar_regolith_AWG write-up", "",
             "The written record this database grew out of, ported here so it stays citable and",
             "so the newer analysis in `results/` can be compared against what it replaced.",
             "GitBook markup, the AWG action-plan page and the Google-Docs project-management",
             "layer are not reproduced — see `PROVENANCE.md` for exactly what was dropped and why.",
             "", "## Contents", ""]
    index += [f"{i + 1}. [{t}]({d})" for i, (d, t, _) in enumerate(written)]
    (LEGACY / "README.md").write_text("\n".join(index) + "\n")

    prov = ["# Provenance of `legacy/`", "",
            "Source: <https://github.com/dr-richard-barker/Lunar_regolith_AWG> (branch `main`).",
            "Ported by `scripts/11_port_legacy_narrative.py`.", "",
            "## Kept", "", "| Source path | Ported to |", "| --- | --- |"]
    prov += [f"| `{s}` | [`legacy/{d}`]({d}) |" for d, _, s in written]
    prov += ["", "## Dropped", "", "| Source path | Why |", "| --- | --- |"]
    prov += [f"| `{k}` | {v} |" for k, v in DROPPED.items()]
    prov += ["", "## Figures", "",
             f"{len(ported)} of the repository's GitBook assets are referenced by a kept page and "
             "were ported to `legacy/figures/` under descriptive names. The remainder were "
             "duplicates (`image (3) (1) (1).png` and similar) or orphaned, and were not copied.",
             "", "## Data", "",
             "The primary data files moved to `data/awg/` (see `MANIFEST.tsv`) and are the input "
             "to the reproducible analysis in `scripts/`, not to this narrative."]
    (LEGACY / "PROVENANCE.md").write_text("\n".join(prov) + "\n")

    write_json(LEGACY / "ported.json",
               {"source": "https://github.com/dr-richard-barker/Lunar_regolith_AWG",
                "pages": [{"source": s, "file": d, "title": t} for d, t, s in written],
                "figures": ported, "dropped": DROPPED})
    log(f"\n  {len(written)} pages → legacy/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
