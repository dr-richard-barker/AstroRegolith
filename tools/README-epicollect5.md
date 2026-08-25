# Pushing the 46-question survey into Epicollect5

Deploys the standardised plant/regolith growth survey into the Epicollect5 project
**`regolith-collaboration`** (`ebfe222d5f7f4a7a967ab0cf2949375a`).

| File | Role |
| --- | --- |
| `ec5_regolith_schema.json` | The 46 questions, in a readable form. Single source of truth for everything below. |
| `regolith-collaboration__observation-form.form.epicollect.json` | **Drop-in file** — drag onto the Form Builder. The easiest route. |
| `ec5_formbuilder_console.js` | **Artifact A** — paste into the DevTools console on the Form Builder page. |
| `ec5_formbuilder.py` | **Artifact B** — build, validate, and emit/push from Python. Generates the other two. |
| `ec5_push_entries.py` | Push OSD-476 observations **and their photographs** into the project as entries. |

All three routes were verified to produce **identical inputs** from the same schema file.

## Route 1 — drag and drop (no console, no cookies)

The Form Builder's drop zone takes a single-form JSON file, the same format its own
"download form" button produces. That file is already generated:

```
tools/regolith-collaboration__observation-form.form.epicollect.json
```

1. Open `https://five.epicollect.net/project/regolith-collaboration/formbuilder`.
2. Drag the file onto the drop zone (or use the import button).
3. **Press "Save project".** The import only loads the questions into the editor —
   nothing is stored until you save.

Regenerate it after editing the schema with `python3 tools/ec5_formbuilder.py form`.

Two things worth knowing about this route. The import **replaces** the current form's
questions rather than appending, which is what we want here (the form is empty). And it
rewrites the file's form ref to whichever form tab is open — so drop it while the
*Observation Form* tab is selected, or the questions land in the wrong form.

If the drop is rejected you get a single generic "invalid file" toast with no detail.
`import-form-click-callback.js` bails on: a non-`.json` extension, any extra or missing
key on an input, an input ref that isn't exactly 60 characters in three
underscore-separated parts, more than 300 questions, more than 3 titles, a bad jump
destination, or any of the type restrictions in the validation report below. The
generated file satisfies all of them, and `ec5_formbuilder.py form` refuses to write a
file that wouldn't.

## Route 2 and 3 — direct to the API

Epicollect5's documented API is read-only. The Form Builder's *Save* button posts to one
internal endpoint, which both remaining artifacts speak directly:

```
POST https://five.epicollect.net/api/internal/formbuilder/{project_slug}
body: base64( gzip( json({"data": <project definition>}) ) )
auth: web session cookie + CSRF header, project role MANAGER or OWNER
```

The gzip+base64 body is not a workaround — it is the contract.
`FormBuilderController@store` calls
`json_decode(gzdecode(base64_decode(request()->getContent())))`, and the stock Form
Builder posts `btoa(pako.gzip(JSON.stringify(project_definition)))`.

**Browser console.** Log in, open the Form Builder, paste all of
`ec5_formbuilder_console.js` into DevTools → Console. It reads the CSRF token from the
page (`X-XSRF-TOKEN` from the `XSRF-TOKEN` cookie, the same header `/js/site.js`
installs, plus `X-CSRF-TOKEN` from the `<meta name="csrf-token">` tag), GETs the current
definition, swaps in the 46 inputs, preflights locally, and only then POSTs. Set
`DRY_RUN = true` at the top to build and validate without saving.

**Python.**

```bash
python3 tools/ec5_formbuilder.py check          # build + validate against the live project, change nothing
python3 tools/ec5_formbuilder.py form           # write the drag-and-drop file
```

To push, the script needs a logged-in session. It never handles credentials — you log
in yourself and hand it the cookies:

```bash
# DevTools -> Application -> Cookies -> five.epicollect.net
# copy the values of epicollect5_session and XSRF-TOKEN into cookies.json:
#   {"epicollect5_session": "...", "XSRF-TOKEN": "..."}
python3 tools/ec5_formbuilder.py push --cookies cookies.json --dry-run
python3 tools/ec5_formbuilder.py push --cookies cookies.json
```

Or drive a real browser and log in by hand, letting the script take over afterwards:

```bash
pip install playwright && playwright install chromium
python3 tools/ec5_formbuilder.py push --playwright
```

`cookies.json` is a live session — do not commit it.

**Re-running is safe.** Input and answer refs are `sha1(form_ref + key)[:13]`, so a
second run reproduces the same refs and updates the form in place. Random refs would
orphan any entries already collected against the old ones.

## Where these rules come from

Everything below was read from source rather than inferred — from
[`epicollect5/epicollect5-server`](https://github.com/epicollect5/epicollect5-server)
(`routes/api_internal.php`, `FormBuilderController.php`,
`Http/Validation/Project/Rule{Input,Form,ProjectDefinition,ProjectExtraDetails}.php`,
`ValidationBase.php`, `Libraries/Utilities/Strings.php`,
`Services/Mapping/ProjectMappingService.php`, `config/epicollect/{limits,strings}.php`)
and from
[`epicollect5/epicollect5-formbuilder`](https://github.com/epicollect5/epicollect5-formbuilder)
(`helpers/import-form-validation.js`, `config/consts.js`,
`event-handler-callbacks/{import-form,save-project}-click-callback.js`). The file
conventions were then checked against a real Form Builder export.

**The client is stricter than the server**, and that gap matters: the server will happily
store a form the Form Builder then refuses to import or edit. The generated files honour
the stricter of the two.

Because the endpoint is internal and undocumented, it can change without notice. If a
push starts failing, re-read those files before trusting this script.

## Validation report: the supplied schema vs. Epicollect5's real format

The question set is sound — all nine types (`text`, `textarea`, `dropdown`, `checkbox`,
`integer`, `decimal`, `date`, `location`, `photo`) are valid Epicollect5 types, and every
count is inside the limits (46 of 300 inputs; largest option list 8 of 300; longest
question 35 of 255 chars). The *encoding* needed ten corrections, all applied by the
builders:

| Supplied | Epicollect5 requires | Why it would have failed |
| --- | --- | --- |
| `q40` photo with `"required": true` | media types (`photo`, `audio`, `video`, `location`) **cannot be required** | `REQUIRED_ALLOWED_TYPES` excludes them, so the Form Builder rejects the import outright. The server would store it, leaving a form its own editor can't open. |
| `options[].id` = `"opt_sc_1"` | `possible_answers[].answer_ref`, **exactly 13** alphanumeric chars | `RuleInput::validatePossibleAnswers()` tests `strlen($ref) !== 13` → `ec5_355` |
| `options[].label` | `possible_answers[].answer` (≤ 250 chars) | key is not read; option list would import empty |
| `"default_to_current_date": true` | `set_to_current_datetime` (bool) **and** a `datetime_format` | unknown keys are silently dropped; `date` with no format → `ec5_29` |
| — | `datetime_format` must be `dd/MM/YYYY` — **uppercase** | `dd/MM/yyyy` is not in `config/epicollect/strings.php` → `ec5_29` |
| `min`/`max` as numbers, absent when unbounded | strings, `""` when unbounded on `integer`/`decimal`, `null` on every other type | `ifNotEmptyDefaultMinAndMax()` compares against `''`; `max` also carries `ec5_greater_than_field:min` |
| no `default` | `""` on `integer`, `decimal`, `dropdown`, `checkbox`; `null` elsewhere | those validators run `default !== ''` first, so `null` reaches the type check and trips `ec5_339` |
| partial input objects | **exactly 17 keys** on every input — no more, no fewer | server: `ValidationBase::validate($data, true)` → `ec5_60`. Client: `utils.hasSameProps()` rejects extra keys too. |
| `inputs` as a dict keyed by name, plus a name array under `forms[0]` | an ordered array of full input objects, each `ref` matching `^{project_ref}_{13}_{13}$` — **exactly 60 chars** | server `isValidRef()` → `ec5_243`; client `consts.REGEX.input_ref`. The `qNN_` keys exist nowhere in Epicollect5. |
| no `is_title` | at least one input should carry `is_title` (max 3 per form) | not enforced by either side, but with none the entry list has no readable label. `q01` is the title. |

Two content screens run over the whole definition before any of that:
`Strings::containsHtml()` rejects **any** `<` or `>` anywhere (`ec5_220`), and
`containsEmoji()` rejects seven Unicode blocks (`ec5_323`). The unit symbols in this
schema — `µ`, `·`, `⁻²`, `°C`, `CO₂`, `—` — all sit outside those blocks and are
preserved intact; verified by round-tripping the gzip+base64 body.

## Flagged for manual attention

1. **You cannot require a photo.** The spec asks for `q40 Photo of the plant` to be
   mandatory, and Epicollect5 simply has no such option on media questions — there is no
   required toggle in the UI for them. `q40` is therefore optional. If a photo must be
   present, the workaround is a required non-media question next to it, e.g. make
   `q42 Calibration marker in frame?` required (it is) and treat a missing photo as an
   invalid submission downstream. Same applies to `q41` and to `q20 Location`.

2. **The form gets renamed.** The live form is currently *Regolith Collaboration* (slug
   `regolith-collaboration`); the spec calls for *Observation Form*. The builders apply
   that rename, and the server re-derives the slug (`Str::slug`) to `observation-form`.
   To keep the current name, edit `form.name` in `ec5_regolith_schema.json` first.

3. **No jump logic is included** — the spec defines none. If you want it, add a `jumps`
   array to an input in the schema JSON (`{"to": "<input ref or END>", "when":
   "IS"|"IS_NOT"|"ALL"|"NO_ANSWER_GIVEN", "answer_ref": "..."}`); the preflight
   validates it. Constraints worth knowing first:
   - a jump target must be `END` or an input **at least two positions later**
     (`ec5_264`), so you can skip questions but not "jump" to the next one;
   - only choice types (`dropdown`, `checkbox`, `radio`, `searchsingle`,
     `searchmultiple`) may use `IS`/`IS_NOT`; everything else must use `ALL` (`ec5_207`);
   - inputs inside a group cannot have jumps at all (`ec5_320`).

   The natural candidates here are q12 *Amendment = None* → skip q13, q34
   *Germinated = No* → skip to q39, and q42 *Calibration marker = No* → skip q43.
   Adding them in the Form Builder UI after import is also perfectly fine.

4. **Repeatable measurements need a branch, not a flat triple.** q35–q37 record exactly
   one measurement per entry. Several measurements per plant means a `branch` input with
   those three nested inside it — a different structure that is far easier to build in
   the Form Builder UI (branch inputs also only accept `uniqueness` of `none` or `form`,
   and a branch cannot contain another branch).

5. **`q01` is set to `uniqueness: "form"`, as specified — reconsider it.** That makes
   Epicollect5 reject any entry whose Sample ID already exists in the form, across
   *all* contributors. For a multi-group collaboration that is a real chance of
   contributors blocking each other with a plausible ID like `plate-1`. `"none"` plus
   deduplication downstream may serve better; it is a one-word change in the schema.

6. **Export column names will not be your `qNN_` keys.** `ProjectMappingService::generateMapTo()`
   builds the EC5_AUTO mapping as `{position}_{question}`, stripped of non-alphanumerics
   and truncated to 20 characters — so `q01_sample_experiment_id` becomes
   `1_Sample__experiment`. `python3 tools/ec5_formbuilder.py check` prints the first few.
   If the downloaded CSV headers need to be stable and machine-readable, create a custom
   mapping in the Data-viewer's Mapping tab; the auto mapping also renumbers if questions
   are ever reordered.

7. **The project is `visibility: hidden`.** It will not appear in Epicollect5's project
   search, so contributors need the exact project name or a direct link to add it in the
   mobile app. Switch to `listed` in the project settings when you want it discoverable.

8. **Push before entries arrive.** The project currently holds 0 entries, which makes
   this the free moment to restructure. Once entries exist, changing an input's `type`
   or removing inputs leaves collected answers stranded.


## Pushing entries (not just the form)

Epicollect5's documented API is read-only, but the endpoint its mobile app uses to
submit entries is reachable, and for a **public** project it needs no authentication
at all — `ProjectPermissions::hasPermission()` only checks a user/role when the
project `isPrivate()`:

```
POST https://five.epicollect.net/api/upload/regolith-collaboration
  multipart/form-data
    data = json({"type":"entry", ...})                     # the answers
    data = json({"type":"file_entry", ...}) + name=<file>  # one POST per photo
```

`ec5_push_entries.py` uses it to import the OSD-476 observations this repository
already holds, with the plate photograph attached:

```bash
python3 tools/ec5_push_entries.py push --granularity plant-final --dry-run
python3 tools/ec5_push_entries.py push --granularity plant-final --limit 1
```

Granularities: `plant-final` (16 sequenced plants at the last imaging date),
`plant-date` (192 leaf-count observations), `plantcv` (133 rosette-area rows).

Two other write endpoints exist and are **not** usable here: `api/bulk-upload` is
disabled in production (`ec5_363`), and `api/import/entries` explicitly rejects public
projects (`ec5_256`) and is marked "For CGPS use only, this is not documented".

### Every answer is sourced, or blank

Answers come from the paper's Methods (read from PMC9098553), the OSD-476 ISA archive
in `data/osdr/`, this repository's own tables, and direct inspection of the plate
photographs. 30 of the 46 questions can be answered. The other 16 are left blank
because the published record does not contain them — **light source, spectrum,
intensity, photoperiod, temperature, humidity, CO₂, substrate pH and EC are all
absent**; the paper says only "growth lights in a secured plant growth room".

Two consequences worth knowing before importing:

1. **`Days after sowing at imaging` is required and cannot be answered.** No sowing
   date is published for OSD-476 — `scripts/03_build_phenotype_table.py` already says
   so, and the `day` column everywhere in `results/tables/` counts from the first plate
   scan (2021-05-02), not from sowing. The script refuses to push rather than write a
   number that means something else. Either make that question optional, or establish
   the sowing date from the investigators.

2. **One photograph shows four substrates.** Each image is a whole 48-well plate
   carrying Apollo 11, 12, 17 and JSC-1A wells together, so an entry describing one
   well attaches a photograph of all of them. The importer says so in the notes field
   of every entry. The plate scans also do not cover every plate on every date, so at
   `plant-final` only the plate scanned on the last date carries an image.

### Attaching a photo takes two linked steps

This one is easy to get wrong, because the wrong version succeeds. Uploading a
`file_entry` stores the bytes but does **not** fill in the answer, so an entry whose
photo question is blank uploads happily, returns `ec5_237 Entry successfully uploaded`
for both POSTs, and ends up with an orphaned file and no visible image.

The entry must already carry the stored filename as the answer to the photo question
(`RulePhotoInput` requires `/\.(jpg|jpeg|png)$/` there), and the `file_entry.name` must
be that same filename. Epicollect5 names them `{entry_uuid}_{unix}.jpg` — 51 characters,
which is why `entry_answer_limits['photo']` is 52.

Other limits the entry endpoint enforces, all of which this script now checks locally
before sending:

- `ec5_220` — no `<` or `>` anywhere in the payload, exactly as for the form. The
  paper's `<1 mm` had to be written out as "under 1 mm".
- `ec5_214` — `entry_answer_limits`: 255 characters for text, 1000 for textarea.
- `ec5_206` — photos must be **1024 px or less on both axes**, jpeg/jpg/png, under
  5000 KB. The plate scans are 2000x1476, so the script downscales and records the
  full-resolution source URL in the entry's notes.
- `ec5_54` — an anonymously uploaded entry **cannot be edited afterwards**, by anyone.
  Get it right the first time; a mistake means deleting the entries and re-pushing.
  Attaching a photo to an existing entry is not an edit and does still work.
