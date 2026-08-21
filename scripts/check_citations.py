#!/usr/bin/env python3
"""Cross-check the manuscript's \\cite keys against references.bib.

Fails if the manuscript cites a key the bibliography does not define — the error
LaTeX reports as a bare "[?]" and which is easy to miss in a long build log.
Uncited entries are reported but do not fail the run; a few are expected while
drafting.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import ROOT, log  # noqa: E402

TEX = ROOT / "manuscript" / "manuscript_npj.tex"
BIB = ROOT / "manuscript" / "references.bib"


def main() -> int:
    tex, bib = TEX.read_text(), BIB.read_text()
    cited = set()
    for m in re.finditer(r"\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", tex):
        cited |= {k.strip() for k in m.group(1).split(",") if k.strip()}
    defined = set(re.findall(r"@\w+\{([^,]+),", bib))

    missing = sorted(cited - defined)
    unused = sorted(defined - cited)
    log(f"  {len(cited)} distinct citations in the manuscript, {len(defined)} bib entries")
    if missing:
        log(f"  ✗ cited but not in references.bib: {', '.join(missing)}")
    if unused:
        log(f"  · in references.bib but uncited: {', '.join(unused)}")
    if not missing:
        log("  ✓ every citation resolves")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
