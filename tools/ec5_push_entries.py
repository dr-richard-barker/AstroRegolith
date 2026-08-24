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
NOT_STATED = ("Light source, light spectrum, light intensity, photoperiod, temperature, "
              "relative humidity, CO2, substrate pH, substrate EC and the SOWING DATE are "
              "not reported in Paul, Elardo & Ferl 2022 or in the OSD-476 ISA archive - the "
              "paper says only 'growth lights in a secured plant growth room'. Left blank.")

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
STIR_NOTE = ("Hydrophobic on first wetting; actively stirred with nutrient solution to "
             "overcome hydrophobicity before sowing (Paul et al. 2022, Methods).")


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def load_form() -> tuple[dict, str, str]:
    """Live form structure -> (question -> input dict), form ref, project version."""
    proj = fetch_json(f"{BASE}/api/export/project/{SLUG}")
    form = proj["data"]["project"]["forms"][0]
    version = fetch_json(f"{BASE}/api/project-version/{SLUG}")["data"]["attributes"]["structure_last_updated"]
    return {i["question"]: i for i in form["inputs"]}, form["ref"], version


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
            last = max(r["date"] for r in rows)
            rows = [r for r in rows if r["date"] == last]
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


def build_entries(rows: list[dict], form_ref: str, version: str) -> list[dict]:
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
            "Particle size (µm, mean or range)": "<1000 (all samples <1 mm)",        # [P]
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
                "No in-frame marker. Scale for the morphometrics came from the OSDR image-analysis "
                "assay's linear_scale (m/px); a separate grey standard image accompanies the deposit.",
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
            notes.append("Photograph is the whole 48-well plate, which carries Apollo 11, 12, 17 and "
                         "JSC-1A wells together; this entry describes one well on it.")
        notes.append(NOT_STATED)
        a["Phenotype notes"] = f'PlantCV/GeneLab scoring for {r["plant_id"]}.'
        a["General notes / issues"] = " ".join(notes)

        out.append({"uuid": str(uuid.uuid4()), "sample_id": sample_id, "answers": a,
                    "photo": img, "form_ref": form_ref, "version": version})
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
            "name": entry["photo"],
            "type": "photo",
            "input_ref": questions["Photo of the plant"]["ref"],
            "project_version": entry["version"],
        },
    }


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
    entries = build_entries(rows, form_ref, version)
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
        code, text = post_multipart(url, json.dumps(p, ensure_ascii=False))
        print(f'{e["sample_id"]}: entry {code} {text[:120]}')
        if code != 200:
            raise SystemExit("stopping on first failure")
        if e["photo"]:
            with urllib.request.urlopen(f'{IMG_BASE}/{e["photo"]}') as r:
                blob = r.read()
            code, text = post_multipart(url, json.dumps(file_payload(e, questions), ensure_ascii=False),
                                        (e["photo"], blob))
            print(f'  photo {e["photo"]}: {code} {text[:120]}')


if __name__ == "__main__":
    main()
