#!/usr/bin/env python3
"""Bundle the regolith image sets the gallery serves from this repository.

Two sets are bundled rather than linked:

  awg-shoot-series  the 20 P1-P4 plate photographs behind the PlantCV shoot
                    traits, so the gallery images and the phenotype table are
                    the same pixels.
  osd-670           NASA OSD-670 morphometric photography (radish, lettuce and
                    pepper in CI asteroid-regolith simulant). OSDR does not
                    allow cross-origin browser requests, so these cannot be
                    read live from a static site.

Both are re-encoded to a long edge of 1600 px, which is well above what the
marker detector needs and roughly a tenth of the original bytes. The full-
resolution originals stay at their source; every entry records the URL.

OSD-476's own plate scans are *not* bundled — they are already mirrored, with a
metadata sidecar, in `image-analysis-software-and-R-codes`, and the app reads
that folder straight from GitHub.

Outputs: public/images/<set>/*.jpg and public/data/bundled_images.json
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image

# Five of OSD-670's "supplemental" files are HEIC images deposited with a .jpeg
# extension. Registering the HEIF opener makes Pillow read them by content
# rather than by filename; without it they fail to open at all.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF = True
except ImportError:                                       # optional dependency
    HEIF = False

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import (DATA, OSDR_STUDY_URL, ROOT, SITE_DATA, download, log,  # noqa: E402
                         osdr_download_url, osdr_files, write_json)

IMAGES = ROOT / "public" / "images"
LONG_EDGE, QUALITY = 1600, 82

# OSD-670 filename -> the metadata the gallery shows. Parsed from the deposit's
# own naming (ExpA/ExpB, block, crop), which the study description defines.
CROPS = {"radish": "Raphanus sativus", "lettuce": "Lactuca sativa", "pepper": "Capsicum annuum"}


def is_heic(path: Path) -> bool:
    with open(path, "rb") as f:
        return b"ftypheic" in f.read(32) or b"ftypmif1" in f.read(0)


def shrink(src: Path, dst: Path) -> tuple:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, LONG_EDGE / max(w, h))
        if scale < 1.0:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return (w, h), im.size


def bundle_awg() -> list:
    src_dir = DATA / "awg" / "shoot_series"
    out, entries = IMAGES / "awg-shoot-series", []
    for src in sorted(src_dir.glob("*.jpg")):
        m = re.match(r"^(P\d)-(\d+)$", src.stem)
        if not m:
            continue
        plate, day = m.group(1), m.group(2)
        # P1 is dated YYMMDD, P2-P4 use the day of month alone; both resolve to May 2021.
        date = f"2021-05-{day[-2:]}"
        dst = out / f"{src.stem}.jpg"
        orig, new = shrink(src, dst)
        entries.append({
            "filename": f"{src.stem}.jpg",
            "title": f"Plate {plate} · {date}",
            "date_taken": date,
            "species": "Arabidopsis thaliana",
            "genotype": "Col-0",
            "treatment": "Apollo 11/12/17 regolith and JSC-1A simulant on one plate",
            "plate": plate,
            "osd_accession": "OSD-476",
            "notes": ("Shoot-analysis plate photograph. The PlantCV traits in "
                      "results/tables/plantcv_traits_long.csv were scored from this image."),
            "source_url": "https://github.com/dr-richard-barker/Lunar_regolith_AWG",
            "original_size": f"{orig[0]}x{orig[1]}",
            "bundled_size": f"{new[0]}x{new[1]}",
        })
    log(f"  awg-shoot-series: {len(entries)} images")
    return entries


def bundle_osd670() -> list:
    files = osdr_files("OSD-670")["studies"]["OSD-670"]["study_files"]
    raw = DATA / "osdr" / "raw_large" / "osd-670"
    out, entries = IMAGES / "osd-670", []
    for f in sorted(files, key=lambda x: x["file_name"]):
        name = f["file_name"]
        if not name.lower().endswith((".jpg", ".jpeg")):
            continue                                   # skip the one large TIFF
        src = download(osdr_download_url("OSD-670", name), raw / name)
        heic = is_heic(src)
        if heic and not HEIF:
            log(f"  ! {name} is HEIC despite its .jpeg extension and pillow-heif is "
                f"not installed — skipped (pip install pillow-heif)")
            continue
        dst = out / (re.sub(r"[^A-Za-z0-9_.-]", "_", name).rsplit(".", 1)[0] + ".jpg")
        orig, new = shrink(src, dst)
        low = name.lower()
        species = next((v for k, v in CROPS.items() if k in low), "")
        exp = "Experiment A" if "expa" in low else "Experiment B" if "expb" in low else ""
        block = (m.group(1) if (m := re.search(r"b(?:lock)?[-_]?(\d)", low)) else "")
        entries.append({
            "filename": dst.name,
            "title": " · ".join(x for x in [exp, f"block {block}" if block else "", species] if x) or name,
            "species": species,
            "treatment": "CI asteroid regolith simulant, peat-moss and perlite blends",
            "osd_accession": "OSD-670",
            "notes": ("NASA OSD-670 morphometric photography. Downscaled for the web; the "
                      "full-resolution original is at OSDR."
                      + (" Deposited as .jpeg but actually HEIC; re-encoded here." if heic else "")),
            "source_url": OSDR_STUDY_URL.format(acc="OSD-670"),
            "original_size": f"{orig[0]}x{orig[1]}",
            "bundled_size": f"{new[0]}x{new[1]}",
        })
    log(f"  osd-670: {len(entries)} images")
    return entries


def main() -> int:
    sets = [
        {
            "id": "awg-shoot-series",
            "name": "OSD-476 shoot series — Apollo regolith plates",
            "reference": {
                "text": ("Paul, Elardo & Ferl (2022). Plants grown in Apollo lunar regolith present "
                         "stress-associated transcriptomes that inform prospects for lunar exploration. "
                         "Communications Biology 5:382."),
                "url": "https://doi.org/10.1038/s42003-022-03334-8",
            },
            "provenance": {
                "organism": "Arabidopsis thaliana (Col-0)",
                "conditions": "Apollo 11 / 12 / 17 regolith vs JSC-1A simulant, one plant of each per plate",
                "description": ("20 plate photographs across 5 imaging days. Every PlantCV shoot trait in "
                                "this repository was scored from these images, and each plate ties to the "
                                "RNA-seq samples grown on it."),
                "source": "Lunar_regolith_AWG",
            },
            "entries": bundle_awg(),
        },
        {
            "id": "osd-670",
            "name": "OSD-670 — crops in CI asteroid regolith simulant",
            "reference": {
                "text": ("Russell, Fieber-Beyer & Yurkonis. CI Asteroid Regolith as an In Situ Plant "
                         "Growth Medium for Space Crop Production. NASA OSDR OSD-670."),
                "url": OSDR_STUDY_URL.format(acc="OSD-670"),
            },
            "provenance": {
                "organism": "Raphanus sativus · Lactuca sativa · Capsicum annuum",
                "conditions": "CI asteroid regolith simulant blended with peat moss or perlite, 55 days after planting",
                "description": ("Morphometric photographs of three crop species across simulant blends. "
                                "Bundled because the OSDR file API is not readable from a browser on "
                                "another origin."),
                "source": "NASA OSDR OSD-670",
            },
            "entries": bundle_osd670(),
        },
    ]
    write_json(SITE_DATA / "bundled_images.json", {
        "note": ("Images served from this repository. Re-encoded to a long edge of "
                 f"{LONG_EDGE} px at quality {QUALITY}; originals remain at the source URL "
                 "recorded on each entry."),
        "base": "images/",
        "sets": sets,
    })
    mb = sum(p.stat().st_size for p in IMAGES.rglob("*.jpg")) / 1048576
    log(f"\n  {sum(len(s['entries']) for s in sets)} images, {mb:.1f} MB → public/images/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
