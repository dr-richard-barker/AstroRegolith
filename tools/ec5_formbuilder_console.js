/* -----------------------------------------------------------------------------
 * Epicollect5 Form Builder - push the Regolith Collaboration question set.
 *
 * HOW TO USE
 *   1. Log in at https://five.epicollect.net and open
 *      https://five.epicollect.net/project/regolith-collaboration/formbuilder
 *      (you must be OWNER or MANAGER on the project).
 *   2. Open DevTools -> Console, paste this whole file, press Enter.
 *   3. Watch the log. On success, RELOAD the Form Builder to see the 46 questions.
 *
 * WHAT IT DOES
 *   GET  /api/internal/formbuilder/regolith-collaboration   -> current definition
 *   ...swaps in the 46 inputs, leaving every other project setting untouched...
 *   POST /api/internal/formbuilder/regolith-collaboration   -> base64(gzip(json))
 *
 * The base64+gzip body is not a quirk of this script: FormBuilderController@store
 * does json_decode(gzdecode(base64_decode(request()->getContent()))), and the
 * stock Form Builder posts btoa(pako.gzip(JSON.stringify(definition))).
 *
 * Set DRY_RUN = true to build and validate without saving anything.
 * -------------------------------------------------------------------------- */
const DRY_RUN = false;

/* SCHEMA:START */
const SCHEMA = {
  "project": {
    "slug": "regolith-collaboration",
    "ref": "ebfe222d5f7f4a7a967ab0cf2949375a"
  },
  "form": {
    "ref": "ebfe222d5f7f4a7a967ab0cf2949375a_6a8cba580a614",
    "name": "Observation Form"
  },
  "inputs": [
    {
      "key": "q01_sample_experiment_id",
      "type": "text",
      "question": "Sample / experiment ID",
      "required": true,
      "uniqueness": "form",
      "verify": false,
      "is_title": true
    },
    {
      "key": "q02_contributor_name",
      "type": "text",
      "question": "Contributor name"
    },
    {
      "key": "q03_institution_group",
      "type": "text",
      "question": "Institution / group"
    },
    {
      "key": "q04_date_of_observation",
      "type": "date",
      "question": "Date of observation",
      "set_to_current_datetime": true
    },
    {
      "key": "q05_doi_citation",
      "type": "text",
      "question": "DOI or citation (optional)"
    },
    {
      "key": "q06_species_latin_binomial",
      "type": "text",
      "question": "Species (Latin binomial)",
      "required": true
    },
    {
      "key": "q07_genotype_ecotype_cultivar",
      "type": "text",
      "question": "Genotype / ecotype / cultivar"
    },
    {
      "key": "q08_substrate_class",
      "type": "dropdown",
      "question": "Substrate class",
      "required": true,
      "options": [
        "Lunar regolith (returned sample)",
        "Lunar simulant",
        "Martian simulant",
        "Asteroid simulant",
        "Blend (regolith + amendment)",
        "Non-regolith control"
      ]
    },
    {
      "key": "q09_substrate_name_source",
      "type": "text",
      "question": "Substrate name / source",
      "required": true
    },
    {
      "key": "q10_supplier_batch_lot",
      "type": "text",
      "question": "Supplier / batch or lot"
    },
    {
      "key": "q11_blend_ratio",
      "type": "integer",
      "question": "Blend ratio (% regolith by volume)",
      "min": 0,
      "max": 100
    },
    {
      "key": "q12_amendment",
      "type": "checkbox",
      "question": "Amendment",
      "options": [
        "None",
        "Perlite / vermiculite",
        "Peat / compost",
        "Nutrient solution",
        "Biochar",
        "Microbial inoculant",
        "Chelator",
        "Other"
      ]
    },
    {
      "key": "q13_amendment_details",
      "type": "textarea",
      "question": "Amendment details"
    },
    {
      "key": "q14_particle_size",
      "type": "text",
      "question": "Particle size (µm, mean or range)"
    },
    {
      "key": "q15_substrate_mass_volume",
      "type": "text",
      "question": "Substrate mass or volume per vessel"
    },
    {
      "key": "q16_substrate_ph",
      "type": "decimal",
      "question": "Substrate pH"
    },
    {
      "key": "q17_substrate_ec",
      "type": "decimal",
      "question": "Substrate EC (µS/cm)"
    },
    {
      "key": "q18_substrate_pre_treatment",
      "type": "dropdown",
      "question": "Substrate pre-treatment",
      "options": [
        "None",
        "Autoclaved",
        "Dry-heat sterilised",
        "Rinsed / leached",
        "Wetted and dried",
        "Other"
      ]
    },
    {
      "key": "q19_environment",
      "type": "dropdown",
      "question": "Environment",
      "options": [
        "Ground control (1g)",
        "Clinostat / random-positioning",
        "ISS / microgravity",
        "Parabolic flight",
        "Other"
      ]
    },
    {
      "key": "q20_location",
      "type": "location",
      "question": "Location"
    },
    {
      "key": "q21_vessel_hardware",
      "type": "text",
      "question": "Vessel / hardware"
    },
    {
      "key": "q22_watering_regime",
      "type": "textarea",
      "question": "Watering regime"
    },
    {
      "key": "q23_nutrient_solution",
      "type": "text",
      "question": "Nutrient solution"
    },
    {
      "key": "q24_light_source",
      "type": "dropdown",
      "question": "Light source",
      "options": [
        "LED",
        "Fluorescent",
        "Sunlight",
        "Mixed",
        "Other"
      ]
    },
    {
      "key": "q25_light_spectrum",
      "type": "checkbox",
      "question": "Light spectrum",
      "options": [
        "Red",
        "Green",
        "Blue",
        "White",
        "Far-red",
        "Full spectrum"
      ]
    },
    {
      "key": "q26_light_intensity",
      "type": "integer",
      "question": "Light intensity (µmol·m⁻²·s⁻¹)"
    },
    {
      "key": "q27_photoperiod",
      "type": "integer",
      "question": "Photoperiod (hours light / day)",
      "min": 0,
      "max": 24
    },
    {
      "key": "q28_temperature",
      "type": "decimal",
      "question": "Temperature (°C)"
    },
    {
      "key": "q29_relative_humidity",
      "type": "integer",
      "question": "Relative humidity (%)",
      "min": 0,
      "max": 100
    },
    {
      "key": "q30_co2",
      "type": "integer",
      "question": "CO₂ (ppm) (optional)"
    },
    {
      "key": "q31_sowing_date",
      "type": "date",
      "question": "Sowing date"
    },
    {
      "key": "q32_days_after_sowing",
      "type": "integer",
      "question": "Days after sowing at imaging",
      "required": true
    },
    {
      "key": "q33_leaf_count",
      "type": "integer",
      "question": "Leaf count"
    },
    {
      "key": "q34_germinated",
      "type": "dropdown",
      "question": "Germinated?",
      "options": [
        "Yes",
        "No",
        "Not yet"
      ]
    },
    {
      "key": "q35_measurement_type",
      "type": "dropdown",
      "question": "Measurement type",
      "options": [
        "Rosette / canopy area",
        "Plant height",
        "Root length",
        "Fresh mass",
        "Dry mass",
        "Leaf count",
        "Chlorophyll / SPAD",
        "Other"
      ]
    },
    {
      "key": "q36_measurement_value",
      "type": "decimal",
      "question": "Measurement value"
    },
    {
      "key": "q37_measurement_unit",
      "type": "dropdown",
      "question": "Measurement unit",
      "options": [
        "mm",
        "cm",
        "mm²",
        "cm²",
        "g",
        "mg",
        "count",
        "SPAD"
      ]
    },
    {
      "key": "q38_stress_symptoms",
      "type": "checkbox",
      "question": "Stress symptoms",
      "options": [
        "None",
        "Anthocyanin / reddening",
        "Chlorosis",
        "Stunting",
        "Leaf distortion",
        "Necrosis",
        "Wilting"
      ]
    },
    {
      "key": "q39_phenotype_notes",
      "type": "textarea",
      "question": "Phenotype notes"
    },
    {
      "key": "q40_photo_of_plant",
      "type": "photo",
      "question": "Photo of the plant",
      "required": false,
      "note": "The spec asked for required:true, but Epicollect5 has no required option on media types (photo/audio/video/location) - REQUIRED_ALLOWED_TYPES excludes them, and the Form Builder rejects an imported form that sets it. q42 (calibration marker) is required instead."
    },
    {
      "key": "q41_photo_of_substrate",
      "type": "photo",
      "question": "Photo of the substrate / method"
    },
    {
      "key": "q42_calibration_marker",
      "type": "dropdown",
      "question": "Calibration marker in frame?",
      "required": true,
      "options": [
        "Yes — AstroBotany ArUco card",
        "Yes — ruler / scale bar",
        "Yes — colour card",
        "No"
      ]
    },
    {
      "key": "q43_marker_type_notes",
      "type": "text",
      "question": "Marker type / notes"
    },
    {
      "key": "q44_camera_lens",
      "type": "text",
      "question": "Camera / lens (optional)"
    },
    {
      "key": "q45_licence",
      "type": "dropdown",
      "question": "Licence for this contribution",
      "options": [
        "CC0 (public domain)",
        "CC-BY 4.0",
        "CC-BY-NC 4.0",
        "Ask me first"
      ]
    },
    {
      "key": "q46_general_notes",
      "type": "textarea",
      "question": "General notes / issues"
    }
  ]
};
/* SCHEMA:END */

window.ec5Sync = async function ec5Sync() {
  const BASE = 'https://five.epicollect.net';
  const slug = SCHEMA.project.slug;
  const url = `${BASE}/api/internal/formbuilder/${slug}`;
  const log = (...a) => console.log('%c[ec5]', 'color:#2e7d32;font-weight:bold', ...a);
  const fail = (m) => { console.error('%c[ec5]', 'color:#c62828;font-weight:bold', m); throw new Error(m); };

  // --- rules mirrored from the Epicollect5 server -----------------------------
  const EMPTY_STRING_DEFAULT = new Set(['integer', 'decimal', 'dropdown', 'checkbox', 'radio', 'searchsingle', 'searchmultiple']);
  const CHOICE_TYPES = new Set(['dropdown', 'checkbox', 'radio', 'searchsingle', 'searchmultiple']);
  const NUMERIC_TYPES = new Set(['integer', 'decimal']);
  // The Form Builder client is stricter than the server (consts.js in the formbuilder
  // repo). Honour it here too, or the saved form cannot be re-imported or edited.
  const MEDIA_TYPES = new Set(['audio', 'photo', 'video', 'location']);
  const REQUIRED_ALLOWED = new Set(['text', 'textarea', 'date', 'time', 'integer', 'decimal',
    'barcode', 'phone', 'radio', 'checkbox', 'dropdown', 'searchmultiple', 'searchsingle']);
  const UNIQUENESS_ALLOWED = new Set(['text', 'textarea', 'date', 'time', 'integer', 'decimal', 'barcode', 'phone']);
  const VERIFY_ALLOWED = new Set(['text', 'textarea', 'integer', 'decimal', 'barcode', 'phone']);
  const EMOJI_RANGES = [[0x1F600, 0x1F64F], [0x1F300, 0x1F5FF], [0x1F680, 0x1F6FF],
                        [0x2600, 0x26FF], [0x2700, 0x27BF], [0x1F1E6, 0x1F1FF], [0x1F910, 0x1F95E]];
  const KEY_ORDER = ['max', 'min', 'ref', 'type', 'group', 'jumps', 'regex', 'branch', 'verify',
                     'default', 'is_title', 'question', 'uniqueness', 'is_required',
                     'datetime_format', 'possible_answers', 'set_to_current_datetime'];

  // --- deterministic 13-char refs (identical algorithm to ec5_formbuilder.py) --
  const ref13 = async (...parts) => {
    const buf = new TextEncoder().encode(parts.join('\x1f'));
    const hash = await crypto.subtle.digest('SHA-1', buf);
    return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 13);
  };

  // --- auth -------------------------------------------------------------------
  const cookie = (name) => {
    const hit = document.cookie.split(';').map((c) => c.trim().split('='))
      .find(([k]) => k === name);
    return hit ? decodeURIComponent(hit.slice(1).join('=')) : '';
  };
  const headers = { 'X-Requested-With': 'XMLHttpRequest' };
  const xsrf = cookie('XSRF-TOKEN');
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (xsrf) headers['X-XSRF-TOKEN'] = xsrf;            // what /js/site.js sends
  if (meta && meta.content) headers['X-CSRF-TOKEN'] = meta.content;
  if (!xsrf && !(meta && meta.content)) {
    fail('No CSRF token found. Are you logged in, and is this five.epicollect.net?');
  }

  // --- 1. current definition ---------------------------------------------------
  const got = await fetch(url, { credentials: 'include', headers: { ...headers, Accept: 'application/json' } });
  if (!got.ok) fail(`GET ${url} -> ${got.status}. Need a MANAGER/OWNER session on this project.`);
  const definition = (await got.json()).data;
  if (!definition || !definition.project) fail('GET returned no project definition.');

  const forms = definition.project.forms || [];
  const idx = forms.findIndex((f) => f.ref === SCHEMA.form.ref);
  if (idx < 0) fail(`form ref ${SCHEMA.form.ref} not in project (have ${forms.map((f) => f.ref)})`);

  // --- 2. build the inputs -----------------------------------------------------
  const formRef = SCHEMA.form.ref;
  const inputs = [];
  for (const spec of SCHEMA.inputs) {
    const inputRef = `${formRef}_${await ref13(formRef, spec.key)}`;
    const answers = [];
    for (const opt of spec.options || []) {
      const label = typeof opt === 'string' ? opt : opt.label;
      const seed = typeof opt === 'string' ? opt : (opt.id || label);
      answers.push({ answer: label, answer_ref: await ref13(inputRef, String(seed)) });
    }
    const numeric = NUMERIC_TYPES.has(spec.type);
    const item = {
      max: numeric ? (spec.max ?? '') + '' : null,
      min: numeric ? (spec.min ?? '') + '' : null,
      ref: inputRef,
      type: spec.type,
      group: [],
      jumps: spec.jumps || [],
      regex: numeric ? '' : null,
      branch: [],
      verify: !!spec.verify,
      // null here trips ec5_339 on these types - RuleInput tests `default !== ''`
      default: EMPTY_STRING_DEFAULT.has(spec.type) ? '' : null,
      is_title: !!spec.is_title,
      question: spec.question,
      uniqueness: spec.uniqueness || 'none',
      is_required: !!spec.required,
      datetime_format: spec.datetime_format
        ?? (spec.type === 'date' ? 'dd/MM/YYYY' : (spec.type === 'time' ? 'HH:mm' : null)),
      possible_answers: answers,
      set_to_current_datetime: !!spec.set_to_current_datetime,
    };
    inputs.push(Object.fromEntries(KEY_ORDER.map((k) => [k, item[k]])));
  }

  forms[idx].name = SCHEMA.form.name;
  forms[idx].slug = SCHEMA.form.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  forms[idx].type = 'hierarchy';
  forms[idx].inputs = inputs;

  // --- 3. preflight ------------------------------------------------------------
  const errs = [];
  const blob = JSON.stringify(definition);
  if (/[<>]/.test(blob)) errs.push("ec5_220: definition contains '<' or '>'");
  for (const ch of blob) {
    const cp = ch.codePointAt(0);
    if (EMOJI_RANGES.some(([lo, hi]) => cp >= lo && cp <= hi)) {
      errs.push(`ec5_323: emoji-range char U+${cp.toString(16).toUpperCase()}`); break;
    }
  }
  if (definition.project.ref !== SCHEMA.project.ref) errs.push('ec5_321: project ref mismatch');
  if (inputs.length > 300) errs.push('ec5_262: more than 300 inputs');
  if (inputs.filter((i) => i.is_title).length > 3) errs.push('ec5_211: more than 3 title inputs');
  if (!/^[a-zA-Z0-9_\- ]{1,50}$/.test(forms[idx].name)) errs.push('ec5_29: bad form name');
  const seen = new Set();
  inputs.forEach((i, n) => {
    const at = `#${n + 1} "${i.question.slice(0, 30)}"`;
    if (!new RegExp(`^${formRef}_[a-zA-Z0-9]{13}$`).test(i.ref)) errs.push(`ec5_243: ${at} bad ref`);
    if (seen.has(i.ref)) errs.push(`ec5_224: ${at} duplicate ref`);
    seen.add(i.ref);
    if (i.question.length > 255) errs.push(`ec5_244: ${at} question over 255 chars`);
    if (i.ref.length !== 60 || i.ref.split('_').length !== 3) errs.push(`${at} ref must be 60 chars in 3 parts`);
    if (i.is_required && !REQUIRED_ALLOWED.has(i.type)) {
      errs.push(`${at} type ${i.type} cannot be required - Epicollect5 has no required option on ${MEDIA_TYPES.has(i.type) ? 'media' : 'this'} type`);
    }
    if (i.uniqueness !== 'none' && !UNIQUENESS_ALLOWED.has(i.type)) errs.push(`${at} type ${i.type} must have uniqueness 'none'`);
    if (i.verify && !VERIFY_ALLOWED.has(i.type)) errs.push(`${at} type ${i.type} does not support verify`);
    if (i.set_to_current_datetime && !['date', 'time'].includes(i.type)) errs.push(`${at} set_to_current_datetime is date/time only`);
    if (MEDIA_TYPES.has(i.type) && i.possible_answers.length) errs.push(`ec5_398: ${at} media types cannot have options`);
    if (CHOICE_TYPES.has(i.type) && i.possible_answers.length === 0) errs.push(`ec5_336/337/338: ${at} needs options`);
    i.possible_answers.forEach((a) => {
      if (a.answer_ref.length !== 13) errs.push(`ec5_355: ${at} answer_ref must be exactly 13 chars`);
      if (a.answer.length > 250) errs.push(`ec5_341: ${at} answer over 250 chars`);
    });
    if (i.datetime_format && !['dd/MM/YYYY', 'MM/dd/YYYY', 'YYYY/MM/dd', 'MM/YYYY', 'dd/MM',
      'HH:mm:ss', 'hh:mm:ss', 'HH:mm', 'hh:mm', 'mm:ss'].includes(i.datetime_format)) {
      errs.push(`ec5_29: ${at} datetime_format "${i.datetime_format}" is not allowed`);
    }
    if (i.min !== null && i.min !== '' && i.max !== null && i.max !== '' && Number(i.max) <= Number(i.min)) {
      errs.push(`ec5_28: ${at} max must exceed min`);
    }
  });
  if (errs.length) { errs.forEach((e) => console.error('[ec5]', e)); fail(`${errs.length} preflight error(s) - nothing was sent`); }
  log(`built ${inputs.length} inputs, ${inputs.reduce((n, i) => n + i.possible_answers.length, 0)} options, 0 preflight errors`);

  // --- 4. encode: json -> gzip -> base64 --------------------------------------
  const json = new TextEncoder().encode(JSON.stringify({ data: definition }));
  const gz = new Uint8Array(await new Response(
    new Blob([json]).stream().pipeThrough(new CompressionStream('gzip'))
  ).arrayBuffer());
  let bin = '';
  for (let i = 0; i < gz.length; i += 0x8000) bin += String.fromCharCode(...gz.subarray(i, i + 0x8000));
  const body = btoa(bin);
  log(`payload ${json.length} B json -> ${body.length} B base64(gzip)`);

  if (DRY_RUN) { log('DRY_RUN - not posting'); return { dry_run: true, inputs: inputs.length, definition }; }

  // --- 5. save -----------------------------------------------------------------
  const res = await fetch(url, {
    method: 'POST', credentials: 'include',
    headers: { ...headers, 'Content-Type': 'text/plain;charset=UTF-8' },
    body,
  });
  const text = await res.text();
  if (!res.ok) {
    console.error('[ec5] POST failed', res.status, text.slice(0, 2000));
    fail(`POST -> ${res.status}. See the errors above (ec5_* codes map to the rules in the header comment).`);
  }
  const saved = JSON.parse(text).data.project.forms[idx];
  log(`saved: "${saved.name}" now has ${saved.inputs.length} inputs. Reload the Form Builder to see them.`);
  return { ok: true, inputs: saved.inputs.length };
};

window.__ec5Sync = window.ec5Sync();
