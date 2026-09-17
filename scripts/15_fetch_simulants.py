#!/usr/bin/env python3
"""The ARES Simulant Development Lab table, and its photographs.

The Substrates view already carries the LHS-1 specification, the eight-substrate
probe series and the LHS-1 vs Chang'e-5 oxide comparison — all numbers, no
pictures. This adds NASA's own bench and microscope photographs of sixteen
simulants, which is what lets JSC-1A finally be seen next to the Apollo material
it was the control for in OSD-476.

The published table contains a copy-paste error: the row whose photographs are
all `CSM-LMT-1.jpg` and whose Representative Planetary Surface is "Lunar Mare"
is *named* `CSM-LHT-1`, duplicating the highlands row above it. The parser
corrects it and records the correction; both the corrected and the published
name are carried through to the site.

Photographs are re-encoded to a long edge of 1200 px, which keeps this set in
line with the ~200-330 kB per file of the other bundled sets; regolith texture
is noisy and compresses poorly, so 1600 px here cost three times as much for
detail the gallery never shows. The full-resolution original stays at NASA and
every entry records its URL.

Outputs: data/ares/simulants.json and public/images/simulants/*.jpg
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import DATA, ROOT, log, write_json  # noqa: E402

_SIBLING = Path(__file__).resolve().parents[2] / "ares-curation" / "src"
if _SIBLING.exists():
    sys.path.insert(0, str(_SIBLING))

try:
    from ares_curation import simulants
    from ares_curation.http import get_bytes
except ImportError:  # noqa: BLE001 - re-raised with an actionable message
    raise SystemExit(
        "ares-curation is not importable.\n"
        "  pip install ares-curation\n"
        "or clone it beside this repository:\n"
        "  git clone https://github.com/dr-richard-barker/ares-curation ../ares-curation"
    )

OUT = DATA / "ares"
IMAGES = ROOT / "public" / "images" / "simulants"
LONG_EDGE = 1200


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")


def bundle(url: str, dest: Path) -> bool:
    """Re-encode one photograph locally. Returns True if it was written now."""
    if dest.exists() and dest.stat().st_size > 0:
        return False
    blob = get_bytes(url, f"simulants/img/{dest.name}")
    img = Image.open(io.BytesIO(blob))
    img = img.convert("RGB")
    if max(img.size) > LONG_EDGE:
        scale = LONG_EDGE / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)),
                         Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=82, optimize=True)
    return True


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    log("ARES Simulant Development Lab ...")
    parsed = simulants.parse_simulants()
    parsed["stock"] = simulants.parse_stock()
    rows = parsed["simulants"]
    log(f"  {len(rows)} simulants, {len(parsed['stock'])} stock entries")

    for c in parsed["corrections"]:
        log(f"  ! corrected {c['name_as_published']!r} -> {c['corrected_to']!r} "
            f"(photo filenames and the {c['surface']!r} surface column agree "
            f"against the published name)")

    log("bundling photographs ...")
    written = reused = 0
    for r in rows:
        slug = _slug(r["simulant"])
        for key, suffix in (("simulant_photo_full", "bench"),
                            ("microscope_photo_full", "micro")):
            url = r.get(key)
            if not url:
                continue
            dest = IMAGES / f"{slug}-{suffix}.jpg"
            if bundle(url, dest):
                written += 1
            else:
                reused += 1
            r[f"local_{suffix}"] = f"images/simulants/{dest.name}"

    log(f"  {written} written, {reused} already present -> {IMAGES}")

    if not any(r.get("local_bench") for r in rows):
        raise SystemExit("no simulant photographs were bundled — refusing to "
                         "write a catalogue with no imagery")

    write_json(OUT / "simulants.json", parsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
