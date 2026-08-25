#!/usr/bin/env python3
"""Push OSD-476 observations (and their plate photographs) into Epicollect5.

Epicollect5's *documented* API is read-only, but the endpoint its mobile app uses
to submit entries is reachable and, for a PUBLIC project, needs no authentication
at all (ProjectPermissions::hasPermission only checks a user/role when the
project isPrivate). This script uses it:

    POST https://five.epicollect.net/api/upload/{project_slug}
      multipart/form-data
        data = json({"type": "entry", ...})                      # the answers
        data = json({"type": "file_entry", ...}) + name=<file>   # each photo

Contract read from epicollect5-server (master): routes/api_external.php,
Http/Validation/Entries/Upload/RuleUpload.php, .../RuleAnswers.php,
.../InputRules/*.php, Http/Middleware/ProjectPermissions.php, and
tests/.../PublicRoutes/Media/UploadAppControllerPhotoLocalTest.php.
It is undocumented and can change; nothing here is officially supported.

EVERY answer is either taken from a source or left blank. Sources:
  [P]   Paul, Elardo & Ferl 2022, Commun Biol 5:382, doi:10.1038/s42003-022-03334-8
        (Methods, read from PMC9098553)
  [ISA] the OSD-476 ISA archive in data/osdr/OSD-476-ISA.zip
  [T]   this repository's own tables in results/tables/
  [IMG] direct inspection of the plate photographs
Anything the sources do not state is left empty on purpose - see NOT_STATED.

Usage:
  python3 tools/ec5_push_entries.py build --granularity plant-final
  python3 tools/ec5_push_entries.py build --granularity plant-date -o entries.json
  python3 tools/ec5_push_entries.py push  --granularity plant-final --dry-run
  python3 tools/ec5_push_entries.py push  --granularity plant-final --limit 1
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "https://five.epicollect.net"
SLUG = "regolith-collaboration"

# Images live in the mirror the app already reads; raw.githubusercontent is CORS-open.
IMG_BASE = ("https://raw.githubusercontent.com/dr-richard-barker/"
            "image-analysis-software-and-R-codes/master/NASA_OSDR/OSD-476/images")

# Fields the published record does not contain. Left blank rather than guessed.
NOT_STATED = ("Light, photoperiod, temperature, humidity, CO2, substrate pH/EC and the sowing "
              "date are not reported in the paper or the OSD-476 ISA archive, so are left blank.")

# --- substrate facts, all from [P] "Lunar regolith materials" ----------------
SUBSTRATE = {
    "A11": dict(cls="Lunar regolith (returned sample)",
                name="Apollo 11 regolith, sample 10084",
                supplier="NASA JSC Apollo Sample Curator (AARB allocation); "
                         "4 x 1 g subsamples 10084-2075/2076/2077/2078",
                pretreat="Other"),
    "A12": dict(cls="Lunar regolith (returned sample)",
                name="Apollo 12 regolith, sample 12070",
                supplier="NASA JSC Apollo Sample Curator (AARB allocation); "
                         "4 x 1 g subsamples 12070-105/99/106/109",
                pretreat="Other"),
    "A17": dict(cls="Lunar regolith (returned sample)",
                name="Apollo 17 regolith, sample 70051",
                supplier="NASA JSC Apollo Sample Curator (AARB allocation); "
                         "4 x 1 g subsamples 70051-159/160/161/162",
                pretreat="None"),
    "JSC1A": dict(cls="Lunar simulant",
                  name="JSC-1A lunar simulant",
                  supplier="Orbitec JSC-1A Lunar",
                  pretreat="None"),
}
# [P]: Apollo 11 and 12 "were hydrophobic and initially failed to wet using the
# subsurface irrigation procedure ... therefore actively stirred with nutrient
# solution to overcome the hydrophobicity". Apollo 17 and JSC-1A wetted by capillarity.
STIR_NOTE = "Hydrophobic on first wetting; stirred with nutrient solution to wet it (Methods)."


# config/epicollect/limits.php -> entry_answer_limits
ANSWER_LIMITS = {"text": 255, "phone": 255, "integer": 255, "decimal": 255,
                 "textarea": 1000, "date": 25, "time": 25}


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def load_form() -> tuple[dict, str, str]:
    """Live form structure -> (question -> input dict), form ref, project version."""
    proj = fetch_json(f"{BASE}/api/export/project/{SLUG}")
    form = proj["data"]["project"]["forms"][0]
    version = fetch_json(f"{BASE}/api/project-version/{SLUG}")["data"]["attributes"]["structure_last_updated"]
    return {i["question"]: i for i in form["inputs"]}, form["ref"], version


def existing_entries() -> dict:
    """title -> ec5_uuid for entries already in the project.

    Re-using the uuid of a matching entry makes a re-run an edit. Without it the
    upload would be rejected: "Sample / experiment ID" is unique per form, so a
    second entry carrying the same ID cannot be created.
    """
    try:
        d = fetch_json(f"{BASE}/api/export/entries/{SLUG}?per_page=500")
    except Exception:
        return {}
    return {e.get("title"): e["ec5_uuid"] for e in d.get("data", {}).get("entries", [])}


def answer_refs(inp: dict) -> dict:
    return {a["answer"]: a["answer_ref"] for a in inp["possible_answers"]}


# ---------------------------------------------------------------------------
def build_rows(granularity: str) -> list[dict]:
    """One row per observation, from this repository's own tables."""
    leaf = list(csv.DictReader(open(REPO / "results/tables/leaf_counts_long.csv")))
    pcv = list(csv.DictReader(open(REPO / "results/tables/plantcv_traits_long.csv")))

    if granularity in {"plant-final", "plant-date"}:
        rows = leaf
        if granularity == "plant-final":
            # Per plate, the latest date that has BOTH a leaf count and a plate scan,
            # so every entry carries a photograph taken on its own observation date.
            # The scans rotate between plates, so this is not one date for all four.
            pick = {}
            for r in rows:
                if plate_image(r["plate"], r["date"]):
                    pick[r["plate"]] = max(pick.get(r["plate"], ""), r["date"])
            rows = [r for r in rows if pick.get(r["plate"]) == r["date"]]
        return [dict(kind="leaf", plate=r["plate"], substrate=r["substrate"], date=r["date"],
                     n_leaves=r["n_leaves"], day=r["day"], gsm=r["gsm"],
                     plant_id=f'{r["plate"]}-{r["substrate"]}') for r in rows]

    if granularity == "plantcv":
        return [dict(kind="pcv", plate=r["plate"], substrate=r["substrate"], date=r["date"],
                     area=r["area_mm2"], day=r["day"], plant_id=r["plant_id"],
                     contour=r["contour_id"], gsm="") for r in pcv]

    raise SystemExit(f"unknown granularity {granularity}")


def plate_image(plate: str, date: str) -> str | None:
    """The plate scan for this plate and date, if the mirror has one."""
    if not hasattr(plate_image, "_index"):
        url = ("https://api.github.com/repos/dr-richard-barker/"
               "image-analysis-software-and-R-codes/contents/NASA_OSDR/OSD-476/images?ref=master")
        plate_image._index = [f["name"] for f in fetch_json(url)]
    stamp = date.replace("-", "")[2:]                    # 2021-05-10 -> 210510
    for n in plate_image._index:
        if f"_{stamp}-{plate}_" in n:
            return n
    return None


def build_entries(rows: list[dict], form_ref: str, version: str,
                  existing: dict | None = None) -> list[dict]:
    existing = existing or {}
    out = []
    for r in rows:
        s = SUBSTRATE[r["substrate"]]
        img = plate_image(r["plate"], r["date"])
        sample_id = f'OSD-476 {r["plant_id"]} {r["date"]}'

        a: dict[str, object] = {
            "Sample / experiment ID": sample_id,                                    # unique per form
            "Contributor name": "Imported by the AstroRegolith database (not an original observation)",
            "Institution / group": "University of Florida Space Plants Lab (original study)",   # [P], [IMG]
            "Date of observation": f'{r["date"]}T00:00:00.000',                     # [T]
            "DOI or citation (optional)":
                "Paul, Elardo & Ferl 2022, Commun Biol 5:382, doi:10.1038/s42003-022-03334-8; "
                "data NASA OSDR OSD-476",
            "Species (Latin binomial)": "Arabidopsis thaliana",                     # [P]
            "Genotype / ecotype / cultivar": "Columbia-0 (Col-0), TAIR CS70000",    # [P]
            "Substrate class": s["cls"],                                            # [P]
            "Substrate name / source": s["name"],                                   # [P]
            "Supplier / batch or lot": s["supplier"],                               # [P]
            "Amendment": ["Nutrient solution"],                                     # [P] 0.125x MS via Rockwool
            "Amendment details":
                "0.125x strength Murashige & Skoog nutrient solution, pH 5.7, delivered by subsurface "
                "irrigation through a Rockwool plug capped with a 13 mm nylon 0.45 um filter.",   # [P]
            # Strings::containsHtml rejects any < or > anywhere in an entry too (ec5_220),
            # so the paper's "<1 mm" has to be spelled out.
            "Particle size (µm, mean or range)": "up to 1000 (all samples under 1 mm)",  # [P]
            "Substrate mass or volume per vessel": "900 mg",                        # [P]
            "Substrate pre-treatment": s["pretreat"],                               # [P]
            "Environment": "Ground control (1g)",                                   # [P]
            "Vessel / hardware":
                "Nunc 48-well sterile culture plate (cat. 150687); well 12.5 mm diameter x 15 mm deep; "
                "Rockwool plug subsurface irrigation; plates held in vented terrarium boxes.",     # [P]
            "Watering regime":
                "Bottom-watered daily: plates stood in trays of nutrient solution until the substrate "
                "wetted from below through the Rockwool plug, then allowed to drain.",            # [P]
            "Nutrient solution": "0.125x Murashige & Skoog, pH 5.7",                # [P]
            "Germinated?": "Yes",                                                   # [P] 48-60 h after planting
            "Camera / lens (optional)": "Canon EOS 5D Mark IV, RGB colour space",   # [ISA]
            "Calibration marker in frame?": "No",                                   # [IMG] no marker/ruler/colour card
            "Marker type / notes":
                "No in-frame marker; morphometric scale came from the OSDR image-analysis assay's "
                "linear_scale (m/px). A grey standard image accompanies the deposit.",
            "Licence for this contribution": "CC0 (public domain)",                 # NASA open data
        }

        if r["substrate"] != "JSC1A":
            a["Blend ratio (% regolith by volume)"] = "100"                          # neat returned regolith

        if r["kind"] == "leaf":
            a["Leaf count"] = r["n_leaves"]                                          # [T]/[ISA]
            a["Measurement type"] = "Leaf count"
            a["Measurement value"] = r["n_leaves"]
            a["Measurement unit"] = "count"
        else:
            a["Measurement type"] = "Rosette / canopy area"                          # [T] PlantCV
            a["Measurement value"] = r["area"]
            a["Measurement unit"] = "mm²"

        notes = [
            f'Plant {r["plant_id"]} on plate {r["plate"]}, substrate {r["substrate"]}.',
            f'Imaging day {r["day"]} counted from the first plate scan (2021-05-02) - NOT days after '
            f'sowing; no sowing date is published for this study.',
        ]
        if r.get("gsm"):
            notes.append(f'Transcriptome sample {r["gsm"]}.')
        if r["substrate"] in {"A11", "A12"}:
            notes.append(STIR_NOTE)
        if img:
            notes.append("Photograph is the whole 48-well plate, carrying Apollo 11, 12, 17 and "
                         "JSC-1A wells together; this entry describes one well on it. Downscaled "
                         f"to Epicollect5's 1024 px limit; original at {IMG_BASE}/{img}")
        notes.append(NOT_STATED)
        a["Phenotype notes"] = f'PlantCV/GeneLab scoring for {r["plant_id"]}.'
        a["General notes / issues"] = " ".join(notes)

        # Deterministic, like the form's input refs: a re-run edits the same entry
        # instead of creating a duplicate (and q01's form-level uniqueness would
        # reject a duplicate anyway).
        eid = existing.get(sample_id) or str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"astroregolith:{SLUG}:{sample_id}"))
        already = sample_id in existing
        if img:
            # The ENTRY must carry the stored filename in the photo question's answer -
            # RulePhotoInput requires /\.(jpg|jpeg|png)$/ there. The file_entry upload
            # only stores the bytes; it does not fill the answer in. Epicollect5's own
            # naming is {entry_uuid}_{unix}.jpg, which is 51 chars and fits the 52-char
            # entry_answer_limits['photo'] cap.
            a["Photo of the plant"] = f"{eid}_{int(time.time())}.jpg"

        out.append({"uuid": eid, "sample_id": sample_id, "answers": a, "already": already,
                    "photo": img, "stored_as": a.get("Photo of the plant"),
                    "form_ref": form_ref, "version": version})
    return out


# ---------------------------------------------------------------------------
def to_payload(entry: dict, questions: dict) -> tuple[dict, list[str]]:
    """Answers keyed by question text -> the Epicollect5 entry payload."""
    answers, problems = {}, []
    for question, inp in questions.items():
        value = entry["answers"].get(question, None)
        t = inp["type"]
        if value is None:
            value = {} if t == "location" else ([] if t == "checkbox" else "")
        elif t in {"dropdown", "radio"}:
            refs = answer_refs(inp)
            if value not in refs:
                problems.append(f'{entry["sample_id"]}: "{value}" is not an option of "{question}"')
                value = ""
            else:
                value = refs[value]
        elif t == "checkbox":
            refs = answer_refs(inp)
            missing = [v for v in value if v not in refs]
            if missing:
                problems.append(f'{entry["sample_id"]}: {missing} not options of "{question}"')
            value = [refs[v] for v in value if v in refs]
        if inp["is_required"] and value in ("", [], {}):
            problems.append(f'{entry["sample_id"]}: REQUIRED question "{question}" has no answer')
        # ec5_220: the entry endpoint screens the whole payload for < and > as well.
        if isinstance(value, str) and ("<" in value or ">" in value):
            problems.append(f'{entry["sample_id"]}: "{question}" contains < or > (ec5_220)')
        # ec5_214: config/epicollect/limits.php entry_answer_limits
        cap = ANSWER_LIMITS.get(t)
        if cap and isinstance(value, str) and len(value) > cap:
            problems.append(f'{entry["sample_id"]}: "{question}" is {len(value)} chars, '
                            f'over the {cap}-char limit for {t} answers (ec5_214)')
        answers[inp["ref"]] = {"answer": value, "was_jumped": False}

    return {
        "type": "entry",
        "id": entry["uuid"],
        "attributes": {"form": {"ref": entry["form_ref"], "type": "hierarchy"}},
        "relationships": {"parent": {}, "branch": {}},
        "entry": {
            "entry_uuid": entry["uuid"],
            "created_at": entry["answers"]["Date of observation"],
            "device_id": "",
            "platform": "AstroRegolith import",
            "title": entry["sample_id"],
            "answers": answers,
            "project_version": entry["version"],
        },
    }, problems


def file_payload(entry: dict, questions: dict) -> dict:
    return {
        "type": "file_entry",
        "id": entry["uuid"],
        "attributes": {"form": {"ref": entry["form_ref"], "type": "hierarchy"}},
        "relationships": {"parent": {}, "branch": {}},
        "file_entry": {
            "entry_uuid": entry["uuid"],
            "name": entry["stored_as"],
            "type": "photo",
            "input_ref": questions["Photo of the plant"]["ref"],
            "project_version": entry["version"],
        },
    }


# RulePhotoApp: jpeg/jpg/png, max 5000 KB, and width AND height each max 1024 px.
MAX_EDGE = 1024


def prepare_photo(blob: bytes) -> bytes:
    """Downscale to Epicollect5's 1024 px limit. Full-resolution originals stay at source."""
    from io import BytesIO

    from PIL import Image

    im = Image.open(BytesIO(blob))
    if max(im.size) > MAX_EDGE:
        scale = MAX_EDGE / max(im.size)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    out = BytesIO()
    im.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue()


def post_multipart(url: str, data: str, file: tuple[str, bytes] | None = None) -> tuple[int, str]:
    boundary = "----ec5" + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="data"\r\n\r\n'
            f'{data}\r\n').encode()
    if file:
        name, blob = file
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="name"; '
                 f'filename="{name}"\r\nContent-Type: image/jpeg\r\n\r\n').encode()
        body += blob + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "push"])
    ap.add_argument("--granularity", default="plant-final",
                    choices=["plant-final", "plant-date", "plantcv"],
                    help="plant-final: 16 sequenced plants at the last imaging date (default). "
                         "plant-date: 192 leaf-count observations. plantcv: 133 rosette-area rows.")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    questions, form_ref, version = load_form()
    rows = build_rows(args.granularity)
    entries = build_entries(rows, form_ref, version, existing_entries())
    if args.limit:
        entries = entries[:args.limit]

    payloads, problems = [], []
    for e in entries:
        p, probs = to_payload(e, questions)
        payloads.append((e, p))
        problems += probs

    print(f"{len(entries)} entries at granularity '{args.granularity}'; "
          f"{sum(1 for e in entries if e['photo'])} with a photograph")
    if problems:
        seen, shown = set(), []
        for p in problems:
            key = p.split(": ", 1)[1]
            if key not in seen:
                seen.add(key)
                shown.append(p)
        print(f"\n{len(problems)} problem(s), {len(seen)} distinct:", file=sys.stderr)
        for p in shown:
            print("  -", p, file=sys.stderr)

    if args.command == "build":
        blob = json.dumps([p for _, p in payloads], ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(blob)
            print(f"wrote {args.out}")
        else:
            print(blob[:4000])
        sys.exit(1 if problems else 0)

    if problems:
        raise SystemExit("\nrefusing to push while any required answer is missing")
    if args.dry_run:
        print("--dry-run: nothing sent")
        return

    url = f"{BASE}/api/upload/{SLUG}"
    for e, p in payloads:
        if e["already"]:
            # Anonymous uploads cannot be edited afterwards (ec5_54), and the sample ID
            # is unique per form, so an entry that is already there is left alone.
            print(f'{e["sample_id"]}: already in the project, skipped')
            continue
        code, text = post_multipart(url, json.dumps(p, ensure_ascii=False))
        print(f'{e["sample_id"]}: entry {code} {text[:120]}')
        if code != 200:
            raise SystemExit("stopping on first failure")
        if e["photo"]:
            with urllib.request.urlopen(f'{IMG_BASE}/{e["photo"]}') as r:
                blob = prepare_photo(r.read())
            code, text = post_multipart(url, json.dumps(file_payload(e, questions), ensure_ascii=False),
                                        (e["stored_as"], blob))
            print(f'  photo {e["photo"]} -> {e["stored_as"]}: {code} {text[:90]}')


if __name__ == "__main__":
    main()
