#!/usr/bin/env python3
"""Build and push the Regolith Collaboration form structure to Epicollect5.

Epicollect5 has no public write API. The Form Builder saves through one internal
endpoint, which this script speaks directly:

    POST https://five.epicollect.net/api/internal/formbuilder/{project_slug}
    body = base64( gzip( json({"data": <project definition>}) ) )

That wire format, and every validation rule enforced below, was read from the
Epicollect5 server source (github.com/epicollect5/epicollect5-server, master):
  routes/api_internal.php                                     - the endpoint + role guard
  app/Http/Controllers/Api/Project/FormBuilderController.php  - gzip+base64 body, HTML/emoji screens
  app/Http/Validation/Project/RuleInput.php                   - per-input rules
  app/Http/Validation/Project/RuleForm.php                    - form name/slug/jump rules
  app/Http/Validation/Project/RuleProjectDefinition.php       - counts, titles, refs
  app/Http/Validation/ValidationBase.php                      - required-key + ref-shape checks
  config/epicollect/{limits,strings}.php                      - the numbers and enums

The endpoint requires a logged-in web session with a project role of at least
MANAGER, so this script never handles credentials: you log in yourself in a
browser and hand it the two session cookies (see --help).

Usage
-----
  python3 ec5_formbuilder.py check                 # build + validate, touch nothing
  python3 ec5_formbuilder.py definition -o out.json
  python3 ec5_formbuilder.py console -o ec5_formbuilder_console.js
  python3 ec5_formbuilder.py push --cookies cookies.json
  python3 ec5_formbuilder.py push --playwright     # log in yourself, script drives the save
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "ec5_regolith_schema.json"
BASE_URL = "https://five.epicollect.net"

# ---------------------------------------------------------------------------
# Constants mirrored from config/epicollect/{limits,strings}.php
# ---------------------------------------------------------------------------
INPUT_TYPES = {
    "text", "decimal", "integer", "date", "time", "dropdown", "radio", "checkbox",
    "searchsingle", "searchmultiple", "textarea", "location", "photo", "audio",
    "video", "barcode", "branch", "group", "readme", "phone",
}
DATETIME_FORMATS = {
    "dd/MM/YYYY", "MM/dd/YYYY", "YYYY/MM/dd", "MM/YYYY", "dd/MM",
    "HH:mm:ss", "hh:mm:ss", "HH:mm", "hh:mm", "mm:ss",
}
UNIQUENESS = {"none", "form", "hierarchy"}

QUESTION_LIMIT = 255
README_QUESTION_LIMIT = 1000
ANSWER_LENGTH_LIMIT = 250
ANSWER_REF_LENGTH = 13          # strlen() must equal this exactly
POSSIBLE_ANSWERS_LIMIT = 300
INPUTS_MAX = 300
FORMS_MAX = 5
TITLES_MAX = 3
FORM_NAME_MAXLENGTH = 50
MAP_KEY_LENGTH = 20

# Types whose 'default' must be "" (not null): RuleInput compares default !== ''
# before validating it, so null trips ec5_339 on these.
EMPTY_STRING_DEFAULT = {
    "integer", "decimal", "dropdown", "checkbox", "radio", "searchsingle", "searchmultiple",
}
NUMERIC_TYPES = {"integer", "decimal"}
CHOICE_TYPES = {"dropdown", "checkbox", "radio", "searchsingle", "searchmultiple"}

# The Form Builder client (epicollect5/epicollect5-formbuilder, js/app_modules/config/consts.js)
# is stricter than the server, and its import validator rejects the whole file with one
# generic "invalid file" toast. These lists are from that file.
MEDIA_TYPES = {"audio", "photo", "video", "location"}          # no required/uniqueness option
REQUIRED_ALLOWED = {"text", "textarea", "date", "time", "integer", "decimal", "barcode",
                    "phone", "radio", "checkbox", "dropdown", "searchmultiple", "searchsingle"}
UNIQUENESS_ALLOWED = {"text", "textarea", "date", "time", "integer", "decimal", "barcode", "phone"}
VERIFY_ALLOWED = {"text", "textarea", "integer", "decimal", "barcode", "phone"}
INPUT_REF_LENGTH = 60          # consts.REGEX.input_ref = ^[a-zA-Z0-9-_]{60}$

# Key order used by the Form Builder's own "download form" export.
EXPORT_KEY_ORDER = [
    "ref", "type", "question", "is_title", "is_required", "uniqueness", "regex", "default",
    "verify", "max", "min", "datetime_format", "set_to_current_datetime",
    "possible_answers", "jumps", "branch", "group",
]

# Strings::containsEmoji() ranges, rejected anywhere in the definition (ec5_323)
EMOJI_RANGES = [
    (0x1F600, 0x1F64F), (0x1F300, 0x1F5FF), (0x1F680, 0x1F6FF),
    (0x2600, 0x26FF), (0x2700, 0x27BF), (0x1F1E6, 0x1F1FF), (0x1F910, 0x1F95E),
]

# Every key RuleInput declares: all must be present or the input fails ec5_60.
INPUT_KEY_ORDER = [
    "max", "min", "ref", "type", "group", "jumps", "regex", "branch", "verify",
    "default", "is_title", "question", "uniqueness", "is_required",
    "datetime_format", "possible_answers", "set_to_current_datetime",
]


# ---------------------------------------------------------------------------
# Deterministic refs
# ---------------------------------------------------------------------------
def ref13(*parts: str) -> str:
    """13 hex chars, matching Epicollect5's ^[a-zA-Z0-9]{13}$ ref shape.

    Deterministic on purpose: entry data is keyed by input ref, so re-running
    this script must reproduce the same refs or existing entries are orphaned.
    """
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:13]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_inputs(schema: dict) -> list[dict]:
    form_ref = schema["form"]["ref"]
    out = []
    for spec in schema["inputs"]:
        t = spec["type"]
        key = spec["key"]
        input_ref = f"{form_ref}_{ref13(form_ref, key)}"

        answers = []
        for opt in spec.get("options", []):
            label = opt if isinstance(opt, str) else opt["label"]
            seed = opt if isinstance(opt, str) else opt.get("id", label)
            answers.append({"answer": label, "answer_ref": ref13(input_ref, str(seed))})

        numeric = t in NUMERIC_TYPES
        item = {
            "max": (str(spec["max"]) if spec.get("max") is not None else "") if numeric else None,
            "min": (str(spec["min"]) if spec.get("min") is not None else "") if numeric else None,
            "ref": input_ref,
            "type": t,
            "group": [],
            "jumps": list(spec.get("jumps", [])),
            "regex": "" if numeric else None,
            "branch": [],
            "verify": bool(spec.get("verify", False)),
            "default": "" if t in EMPTY_STRING_DEFAULT else None,
            "is_title": bool(spec.get("is_title", False)),
            "question": spec["question"],
            "uniqueness": spec.get("uniqueness", "none"),
            "is_required": bool(spec.get("required", False)),
            "datetime_format": spec.get(
                "datetime_format",
                "dd/MM/YYYY" if t == "date" else ("HH:mm" if t == "time" else None),
            ),
            "possible_answers": answers,
            "set_to_current_datetime": bool(spec.get("set_to_current_datetime", False)),
        }
        out.append({k: item[k] for k in INPUT_KEY_ORDER})
    return out


def build_definition(schema: dict, current: dict) -> dict:
    """Graft the 46 inputs onto the project definition fetched from the server.

    Everything outside forms[0] is left exactly as the server returned it, so no
    project setting is silently rewritten.
    """
    definition = json.loads(json.dumps(current))     # deep copy
    project = definition["project"]
    forms = project.get("forms") or []
    if not forms:
        raise SystemExit("project has no forms; create one in the Form Builder first")

    target_ref = schema["form"]["ref"]
    idx = next((i for i, f in enumerate(forms) if f["ref"] == target_ref), None)
    if idx is None:
        raise SystemExit(
            f"form ref {target_ref} not found in project (have: "
            f"{[f['ref'] for f in forms]}). Update ec5_regolith_schema.json."
        )

    forms[idx]["name"] = schema["form"]["name"]
    # The server re-derives the slug from the name (Str::slug), but send a
    # matching one so the payload is self-consistent.
    forms[idx]["slug"] = re.sub(r"[^a-z0-9]+", "-", schema["form"]["name"].lower()).strip("-")
    forms[idx]["type"] = "hierarchy"
    forms[idx]["inputs"] = build_inputs(schema)
    return definition


# ---------------------------------------------------------------------------
# Preflight: every server-side rule, checked locally
# ---------------------------------------------------------------------------
def preflight(definition: dict, project_ref: str) -> list[str]:
    errs: list[str] = []
    blob = json.dumps(definition, ensure_ascii=False)

    if "<" in blob or ">" in blob:
        errs.append("ec5_220: definition contains '<' or '>' (Strings::containsHtml rejects both)")
    for ch in blob:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in EMOJI_RANGES):
            errs.append(f"ec5_323: emoji-range character U+{cp:04X} ({ch!r}) in definition")
            break

    project = definition.get("project", {})
    if project.get("ref") != project_ref:
        errs.append(f"ec5_321: project ref mismatch ({project.get('ref')} != {project_ref})")
    name = project.get("name", "")
    if not re.fullmatch(r"[A-Za-z0-9_\s]*", name) or not (3 <= len(name) <= 100):
        errs.append(f"ec5_63: project name {name!r} must be 3-100 chars, alphanumeric/underscore/space")
    if not (3 <= len(project.get("small_description") or "") <= 100):
        errs.append("ec5_63: small_description must be 3-100 chars")
    if project.get("access") not in {"public", "private"}:
        errs.append("ec5_63: access must be public|private")
    if project.get("visibility") not in {"listed", "hidden"}:
        errs.append("ec5_63: visibility must be listed|hidden")
    if project.get("status") not in {"active", "trashed", "locked"}:
        errs.append("ec5_63: status must be active|trashed|locked")
    if not isinstance(project.get("entries_limits"), list):
        errs.append("ec5_63: entries_limits must be present and an array")

    forms = project.get("forms", [])
    if not forms:
        errs.append("ec5_66: project has no forms")
    if len(forms) > FORMS_MAX:
        errs.append(f"ec5_263: {len(forms)} forms exceeds the {FORMS_MAX} allowed")

    for form in forms:
        fname = form.get("name", "")
        if not re.fullmatch(r"[a-zA-Z0-9_\- ]+", fname):
            errs.append(f"ec5_29: form name {fname!r} allows only letters, digits, space, '-', '_'")
        if len(fname) > FORM_NAME_MAXLENGTH:
            errs.append(f"ec5_44: form name longer than {FORM_NAME_MAXLENGTH} chars")
        if not re.fullmatch(r"[a-zA-Z0-9\-]+", form.get("slug", "")):
            errs.append(f"ec5_29: form slug {form.get('slug')!r} allows only letters, digits and '-'")
        if form.get("type") != "hierarchy":
            errs.append("ec5_29: form type must be 'hierarchy'")
        if not re.fullmatch(rf"{re.escape(project_ref)}_[a-zA-Z0-9]{{13}}", form.get("ref", "")):
            errs.append(f"ec5_243: form ref {form.get('ref')!r} must be <project_ref>_<13 alnum>")

        inputs = form.get("inputs") or []
        if not inputs:
            errs.append(f"ec5_68: form {fname!r} has no inputs")
        if len(inputs) > INPUTS_MAX:
            errs.append(f"ec5_262: {len(inputs)} inputs exceeds the {INPUTS_MAX} allowed")
        if sum(1 for i in inputs if i.get("is_title")) > TITLES_MAX:
            errs.append(f"ec5_211: more than {TITLES_MAX} inputs flagged is_title")

        seen_refs, positions = set(), {i["ref"]: n for n, i in enumerate(inputs) if "ref" in i}
        for n, inp in enumerate(inputs):
            where = f"input #{n + 1} ({inp.get('question', '?')[:40]!r})"
            missing = [k for k in INPUT_KEY_ORDER if k not in inp]
            if missing:
                errs.append(f"ec5_60: {where} missing keys {missing}")
                continue
            if not re.fullmatch(rf"{re.escape(form.get('ref', ''))}_[a-zA-Z0-9]{{13}}", inp["ref"]):
                errs.append(f"ec5_243: {where} ref {inp['ref']!r} must be <form_ref>_<13 alnum>")
            if inp["ref"] in seen_refs:
                errs.append(f"ec5_224: {where} duplicate ref {inp['ref']!r}")
            seen_refs.add(inp["ref"])

            t = inp["type"]
            if t not in INPUT_TYPES:
                errs.append(f"ec5_29: {where} unknown type {t!r}")
            if inp["uniqueness"] not in UNIQUENESS:
                errs.append(f"ec5_29: {where} uniqueness must be one of {sorted(UNIQUENESS)}")
            limit = README_QUESTION_LIMIT if t == "readme" else QUESTION_LIMIT
            if len(inp["question"]) > limit:
                errs.append(f"ec5_244: {where} question longer than {limit} chars")
            if not inp["question"]:
                errs.append(f"ec5_21: {where} question is required")
            if inp["datetime_format"] is not None and inp["datetime_format"] not in DATETIME_FORMATS:
                errs.append(
                    f"ec5_29: {where} datetime_format {inp['datetime_format']!r} not in "
                    f"{sorted(DATETIME_FORMATS)} (note: 'dd/MM/yyyy' lowercase is NOT valid)"
                )
            if t in {"date", "time"} and not inp["datetime_format"]:
                errs.append(f"ec5_29: {where} type {t} needs a datetime_format")
            for bound in ("min", "max"):
                v = inp[bound]
                if v not in (None, "") and not re.fullmatch(r"-?\d+(\.\d+)?", str(v)):
                    errs.append(f"ec5_27: {where} {bound}={v!r} must be numeric")
            if inp["min"] not in (None, "") and inp["max"] not in (None, ""):
                if float(inp["max"]) <= float(inp["min"]):
                    errs.append(f"ec5_28: {where} max must be greater than min")

            if t in CHOICE_TYPES:
                pa = inp["possible_answers"]
                if not pa:
                    errs.append(f"ec5_336/337/338: {where} {t} needs at least one possible answer")
                if len(pa) > POSSIBLE_ANSWERS_LIMIT:
                    errs.append(f"ec5_340: {where} more than {POSSIBLE_ANSWERS_LIMIT} answers")
                refs = set()
                for a in pa:
                    if len(a["answer_ref"]) != ANSWER_REF_LENGTH:
                        errs.append(
                            f"ec5_355: {where} answer_ref {a['answer_ref']!r} is "
                            f"{len(a['answer_ref'])} chars, must be exactly {ANSWER_REF_LENGTH}"
                        )
                    if len(a["answer"]) > ANSWER_LENGTH_LIMIT:
                        errs.append(f"ec5_341: {where} answer longer than {ANSWER_LENGTH_LIMIT} chars")
                    if a["answer_ref"] in refs:
                        errs.append(f"{where} duplicate answer_ref {a['answer_ref']!r}")
                    refs.add(a["answer_ref"])
                if inp["default"] != "" and inp["default"] not in refs:
                    errs.append(f"ec5_339: {where} default must be '' or a valid answer_ref")
            elif inp["possible_answers"]:
                errs.append(f"{where} type {t} must have an empty possible_answers list")

            if t == "integer" and inp["default"] not in ("", "0") and inp["default"] is not None:
                try:
                    int(inp["default"])
                except (TypeError, ValueError):
                    errs.append(f"ec5_339: {where} integer default must be '' or an integer")
            if t in EMPTY_STRING_DEFAULT and inp["default"] is None:
                errs.append(f"ec5_339: {where} type {t} needs default '' (null trips the check)")

            # Form Builder client rules - stricter than the server, and the reason an
            # otherwise-valid file is rejected by drag-and-drop with a generic error.
            if len(inp["ref"]) != INPUT_REF_LENGTH or inp["ref"].count("_") != 2:
                errs.append(
                    f"{where} ref must be exactly {INPUT_REF_LENGTH} chars in 3 underscore-separated "
                    f"parts (got {len(inp['ref'])}); the Form Builder import rejects anything else"
                )
            if inp["is_required"] and t not in REQUIRED_ALLOWED:
                errs.append(
                    f"{where} type {t} cannot be required - Epicollect5 has no required option on "
                    f"{'media' if t in MEDIA_TYPES else 'this'} type"
                )
            if inp["uniqueness"] != "none" and t not in UNIQUENESS_ALLOWED:
                errs.append(f"{where} type {t} must have uniqueness 'none'")
            if inp["verify"] and t not in VERIFY_ALLOWED:
                errs.append(f"{where} type {t} does not support verify")
            if inp["set_to_current_datetime"] and t not in {"date", "time"}:
                errs.append(f"{where} set_to_current_datetime is only valid on date/time")
            if t in MEDIA_TYPES and inp["possible_answers"]:
                errs.append(f"ec5_398: {where} media types cannot have possible answers")

            for jump in inp["jumps"]:
                if set(jump) - {"to", "when", "answer_ref"}:
                    errs.append(f"ec5_207: {where} jump has keys outside to/when/answer_ref")
                if not jump.get("to") or not jump.get("when"):
                    errs.append(f"ec5_207: {where} jump needs non-empty 'to' and 'when'")
                if t not in CHOICE_TYPES and jump.get("when") != "ALL":
                    errs.append(f"ec5_207: {where} type {t} only supports when='ALL'")
                if jump.get("when") not in {"ALL", "NO_ANSWER_GIVEN"}:
                    valid = {a["answer_ref"] for a in inp["possible_answers"]}
                    if jump.get("answer_ref") not in valid:
                        errs.append(f"ec5_265: {where} jump answer_ref is not one of this input's answers")
                if jump.get("to") != "END":
                    dest = positions.get(jump.get("to"))
                    if dest is None or dest < n + 2:
                        errs.append(
                            f"ec5_264: {where} jump target must be 'END' or an input at least "
                            f"two positions later (got position {dest})"
                        )
    return errs


def build_form_file(schema: dict) -> dict:
    """The single-form file the Form Builder's drag-and-drop import accepts.

    Shape confirmed against a real Form Builder export
    (<project-slug>__<form-slug>.form.epicollect.json) and against
    import-form-validation.js: data.id is the FORM ref, data.type is "form",
    and every input carries exactly the 17 keys below - the client rejects
    extra ones (utils.hasSameProps).
    """
    form_ref = schema["form"]["ref"]
    name = schema["form"]["name"]
    return {
        "data": {
            "id": form_ref,
            "type": "form",
            "form": {
                "ref": form_ref,
                "name": name,
                "slug": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
                "type": "hierarchy",
                "inputs": [{k: i[k] for k in EXPORT_KEY_ORDER} for i in build_inputs(schema)],
            },
        }
    }


# ---------------------------------------------------------------------------
# Wire format
# ---------------------------------------------------------------------------
def encode_body(definition: dict) -> bytes:
    """json -> gzip -> base64, matching the Form Builder's btoa(pako.gzip(...))."""
    raw = json.dumps({"data": definition}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(raw, mtime=0))


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------
def load_cookies(path: str) -> dict:
    """Accepts {"name": "value"} or a browser cookie-export array of objects."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, list):
        data = {c["name"]: c["value"] for c in data}
    missing = [c for c in ("epicollect5_session", "XSRF-TOKEN") if c not in data]
    if missing:
        raise SystemExit(f"cookie file is missing {missing}")
    return data


def push_requests(schema: dict, cookies: dict, dry_run: bool) -> None:
    import urllib.parse

    import requests

    slug = schema["project"]["slug"]
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/project/{slug}/formbuilder",
        # The site sends the XSRF-TOKEN cookie back URL-decoded in this header
        # (see /js/site.js: $.ajaxSetup({headers:{'X-XSRF-TOKEN': ...}})).
        "X-XSRF-TOKEN": urllib.parse.unquote(cookies["XSRF-TOKEN"]),
    })

    url = f"{BASE_URL}/api/internal/formbuilder/{slug}"
    got = session.get(url, headers={"Accept": "application/json"})
    if got.status_code != 200:
        raise SystemExit(
            f"GET {url} returned {got.status_code}. Cookies are probably stale, or the "
            f"account is not a MANAGER on this project.\n{got.text[:400]}"
        )
    current = got.json().get("data")
    if not current or "project" not in current:
        raise SystemExit(f"unexpected GET payload: {got.text[:400]}")

    definition = build_definition(schema, current)
    errs = preflight(definition, schema["project"]["ref"])
    if errs:
        print("preflight failed:", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        raise SystemExit(1)

    body = encode_body(definition)
    print(f"built {len(definition['project']['forms'][0]['inputs'])} inputs, "
          f"body {len(body)} bytes (gzip+base64)")
    if dry_run:
        print("--dry-run: not posting")
        return

    res = session.post(url, data=body, headers={"Content-Type": "text/plain;charset=UTF-8"})
    if res.status_code != 200:
        print(f"POST failed with {res.status_code}", file=sys.stderr)
        print(res.text[:2000], file=sys.stderr)
        raise SystemExit(1)
    saved = res.json().get("data", {}).get("project", {}).get("forms", [{}])[0]
    print(f"saved: form {saved.get('name')!r} now has {len(saved.get('inputs', []))} inputs")


def push_playwright(schema: dict, dry_run: bool) -> None:
    """Open a real browser, let the user log in by hand, then run the save in-page.

    Nothing here types or stores credentials - the login happens in the browser
    window, driven by the person sitting in front of it.
    """
    from playwright.sync_api import sync_playwright

    slug = schema["project"]["slug"]
    console_js = (HERE / "ec5_formbuilder_console.js").read_text()
    if dry_run:
        console_js = console_js.replace("const DRY_RUN = false;", "const DRY_RUN = true;")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/login")
        print("Log in to Epicollect5 in the browser window, then press Enter here...")
        input()
        page.goto(f"{BASE_URL}/project/{slug}/formbuilder", wait_until="domcontentloaded")
        # The snippet defines window.ec5Sync and immediately starts it, parking the
        # promise on window.__ec5Sync - so inject, then await that promise.
        page.add_script_tag(content=console_js)
        result = page.evaluate("() => window.__ec5Sync")
        print(json.dumps(result, indent=2)[:2000])
        browser.close()


# ---------------------------------------------------------------------------
# Console snippet generation (keeps Artifact A and Artifact B in lockstep)
# ---------------------------------------------------------------------------
def render_console(schema: dict, template: Path) -> str:
    text = template.read_text()
    payload = json.dumps(schema, ensure_ascii=False, indent=2)
    return re.sub(
        r"(/\* SCHEMA:START \*/\n).*?(\n\s*/\* SCHEMA:END \*/)",
        lambda m: m.group(1) + "const SCHEMA = " + payload + ";" + m.group(2),
        text,
        flags=re.S,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "definition", "body", "form", "console", "push"])
    ap.add_argument("-o", "--out")
    ap.add_argument("--schema", default=str(SCHEMA_PATH))
    ap.add_argument("--cookies", help='JSON file with the epicollect5_session and XSRF-TOKEN cookies')
    ap.add_argument("--playwright", action="store_true", help="log in interactively instead of using cookies")
    ap.add_argument("--dry-run", action="store_true", help="build and validate, but do not POST")
    ap.add_argument("--current", help="offline: a saved project definition to graft onto (skips the GET)")
    args = ap.parse_args()

    schema = json.loads(Path(args.schema).read_text())

    if args.command == "push":
        if args.playwright:
            push_playwright(schema, args.dry_run)
        else:
            if not args.cookies:
                ap.error("push needs --cookies FILE (or --playwright)")
            push_requests(schema, load_cookies(args.cookies), args.dry_run)
        return

    if args.command == "console":
        js = render_console(schema, HERE / "ec5_formbuilder_console.js")
        Path(args.out or (HERE / "ec5_formbuilder_console.js")).write_text(js)
        print(f"wrote {args.out or 'ec5_formbuilder_console.js'}")
        return

    # check / definition / body work offline against a stub project shell.
    if args.current:
        current = json.loads(Path(args.current).read_text())
        current = current.get("data", current)
    else:
        import urllib.request
        with urllib.request.urlopen(f"{BASE_URL}/api/export/project/{schema['project']['slug']}") as r:
            current = json.load(r)["data"]

    definition = build_definition(schema, current)
    errs = preflight(definition, schema["project"]["ref"])
    for e in errs:
        print("  -", e, file=sys.stderr)

    inputs = definition["project"]["forms"][0]["inputs"]
    print(f"{len(inputs)} inputs; {sum(1 for i in inputs if i['is_title'])} title(s); "
          f"{sum(len(i['possible_answers']) for i in inputs)} possible answers; "
          f"{len(errs)} preflight error(s)")
    print("EC5_AUTO export column names (first 5):")
    for n, i in enumerate(inputs[:5], start=1):
        q = re.sub(r"[^A-Za-z0-9_]", "", re.sub(r" +", "_", f"{n}_{i['question'].strip()}"))
        print(f"  {i['ref'].rsplit('_', 1)[1]}  {q[:MAP_KEY_LENGTH]}")

    if args.command == "form":
        if errs:
            raise SystemExit("preflight failed - form file not written")
        form_file = build_form_file(schema)
        out = args.out or str(
            HERE / f"{schema['project']['slug']}__{form_file['data']['form']['slug']}.form.epicollect.json"
        )
        Path(out).write_text(json.dumps(form_file, ensure_ascii=False, indent=4) + "\n")
        print(f"\nwrote {out}")
        print("Drag it onto the Form Builder's drop zone, then press 'Save project'.")
    elif args.command == "definition":
        text = json.dumps({"data": definition}, ensure_ascii=False, indent=2)
        Path(args.out).write_text(text) if args.out else print(text)
    elif args.command == "body":
        body = encode_body(definition)
        Path(args.out).write_bytes(body) if args.out else print(body.decode())

    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
