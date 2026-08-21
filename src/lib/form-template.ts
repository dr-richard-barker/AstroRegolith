// Generate a downloadable Epicollect5 form template for a regolith growth study.
// The JSON matches Epicollect5's own project-structure schema (project → forms →
// inputs), so it doubles as a precise build checklist for the form builder and is
// ready for any import path Epicollect5 offers.

export interface TemplateField {
  question: string;
  type: 'text' | 'textarea' | 'integer' | 'decimal' | 'date' | 'location' | 'photo' | 'dropdown' | 'checkbox';
  required?: boolean;
  title?: boolean;
  options?: string[];      // for dropdown / checkbox
  help?: string;           // shown in the CSV / builder notes
}

// The recommended regolith form. It keeps the identity/imaging/climate spine any
// astrobotany contribution needs, and adds the substrate description a regolith
// experiment lives or dies by. Two fields are deliberately shaped to match
// OSD-476's own metadata — `Days after sowing at imaging` and `Leaf count` — so a
// contributed series can be plotted on the same axes as the Apollo study rather
// than in a parallel universe of its own.
export const TEMPLATE_FIELDS: TemplateField[] = [
  // Identity & provenance
  { question: 'Sample / experiment ID', type: 'text', required: true, title: true, help: 'Unique key, e.g. LAB-REG-2026-001. Ties images, metadata and results together.' },
  { question: 'Contributor name', type: 'text', help: 'Who recorded this entry.' },
  { question: 'Institution / group', type: 'text' },
  { question: 'Date of observation', type: 'date', help: 'ISO 8601. The app can auto-fill the current date.' },
  { question: 'DOI or citation (optional)', type: 'text', help: 'Reference for the protocol or dataset.' },
  // Organism
  { question: 'Species (Latin binomial)', type: 'text', required: true, help: 'e.g. Arabidopsis thaliana, Lactuca sativa, Raphanus sativus.' },
  { question: 'Genotype / ecotype / cultivar', type: 'text', help: 'e.g. Col-0, Outredgeous, Micro-Tom.' },
  // Substrate — the fields a regolith study turns on
  { question: 'Substrate class', type: 'dropdown', required: true, options: ['Lunar regolith (returned sample)', 'Lunar simulant', 'Martian simulant', 'Asteroid simulant', 'Blend (regolith + amendment)', 'Non-regolith control'], help: 'What the plant is rooted in. Blends go here; give the ratio below.' },
  { question: 'Substrate name / source', type: 'text', required: true, help: 'e.g. Apollo 11, JSC-1A, LHS-1, LMS-1, MGS-1, MMS-2, Exolith CI. Name the batch if you have it.' },
  { question: 'Supplier / batch or lot', type: 'text', help: 'Simulant composition varies between batches; record it so others can match yours.' },
  { question: 'Blend ratio (% regolith by volume)', type: 'integer', help: '100 for neat regolith, 0 for the control. Used to place the entry on a dose-response axis.' },
  { question: 'Amendment', type: 'checkbox', options: ['None', 'Perlite / vermiculite', 'Peat / compost', 'Nutrient solution', 'Biochar', 'Microbial inoculant', 'Chelator', 'Other'], help: 'Anything mixed in or applied beyond water.' },
  { question: 'Amendment details', type: 'textarea', help: 'Rates, timing, product names.' },
  { question: 'Particle size (µm, mean or range)', type: 'text', help: 'Grain size drives water holding and root penetration more than chemistry does.' },
  { question: 'Substrate mass or volume per vessel', type: 'text', help: 'e.g. 900 mg per well; 15 mL per pot. State the unit.' },
  { question: 'Substrate pH', type: 'decimal', help: 'Measured, not the supplier value, if you can.' },
  { question: 'Substrate EC (µS/cm)', type: 'decimal' },
  { question: 'Substrate pre-treatment', type: 'dropdown', options: ['None', 'Autoclaved', 'Dry-heat sterilised', 'Rinsed / leached', 'Wetted and dried', 'Other'], help: 'Leaching in particular changes the ionic stress a plant sees.' },
  // Growth environment
  { question: 'Environment', type: 'dropdown', options: ['Ground control (1g)', 'Clinostat / random-positioning', 'ISS / microgravity', 'Parabolic flight', 'Other'] },
  { question: 'Location', type: 'location', help: 'GPS, auto-captured by the app, for ground samples.' },
  { question: 'Vessel / hardware', type: 'text', help: 'e.g. vented terrarium chamber, Petri plate, 2-inch pot.' },
  { question: 'Watering regime', type: 'textarea', help: 'Volume, interval, and whether it was to field capacity.' },
  { question: 'Nutrient solution', type: 'text', help: 'e.g. 0.125× Murashige & Skoog, pH 5.7.' },
  // Light & climate
  { question: 'Light source', type: 'dropdown', options: ['LED', 'Fluorescent', 'Sunlight', 'Mixed', 'Other'] },
  { question: 'Light spectrum', type: 'checkbox', options: ['Red', 'Green', 'Blue', 'White', 'Far-red', 'Full spectrum'] },
  { question: 'Light intensity (µmol·m⁻²·s⁻¹)', type: 'integer', help: 'PPFD.' },
  { question: 'Photoperiod (hours light / day)', type: 'integer', help: '0–24.' },
  { question: 'Temperature (°C)', type: 'decimal' },
  { question: 'Relative humidity (%)', type: 'integer' },
  { question: 'CO₂ (ppm) (optional)', type: 'integer' },
  // Timing & phenotype — aligned to OSD-476 so contributions are comparable
  { question: 'Sowing date', type: 'date', help: 'Record it. OSD-476 did not, and its growth curves cannot be placed on an absolute age axis as a result.' },
  { question: 'Days after sowing at imaging', type: 'integer', required: true, help: 'The shared time axis. Matches OSD-476 “age at sample harvest”.' },
  { question: 'Leaf count', type: 'integer', help: 'Visible true leaves. Matches OSD-476 “Number of Leaves”, so your series can be plotted against the Apollo plants.' },
  { question: 'Germinated?', type: 'dropdown', options: ['Yes', 'No', 'Not yet'], help: 'Germination failure is data — record the zeroes.' },
  { question: 'Measurement type', type: 'dropdown', options: ['Rosette / canopy area', 'Plant height', 'Root length', 'Fresh mass', 'Dry mass', 'Leaf count', 'Chlorophyll / SPAD', 'Other'] },
  { question: 'Measurement value', type: 'decimal', help: 'Record with the unit below.' },
  { question: 'Measurement unit', type: 'dropdown', options: ['mm', 'cm', 'mm²', 'cm²', 'g', 'mg', 'count', 'SPAD'] },
  { question: 'Stress symptoms', type: 'checkbox', options: ['None', 'Anthocyanin / reddening', 'Chlorosis', 'Stunting', 'Leaf distortion', 'Necrosis', 'Wilting'], help: 'The morphologies Apollo-grown plants showed. Free-text detail below.' },
  { question: 'Phenotype notes', type: 'textarea' },
  // Imaging — the point of the database
  { question: 'Photo of the plant', type: 'photo', required: true, help: 'Photograph the plant NEXT TO the calibration marker so scale and colour are recoverable in the browser.' },
  { question: 'Photo of the substrate / method', type: 'photo', help: 'The dry substrate, the vessel, or the setup. Regolith work is hard to reproduce from text alone.' },
  { question: 'Calibration marker in frame?', type: 'dropdown', required: true, options: ['Yes — AstroBotany ArUco card', 'Yes — ruler / scale bar', 'Yes — colour card', 'No'], help: 'Without a marker the image cannot be measured, only looked at.' },
  { question: 'Marker type / notes', type: 'text' },
  { question: 'Camera / lens (optional)', type: 'text' },
  // Sharing
  { question: 'Licence for this contribution', type: 'dropdown', options: ['CC0 (public domain)', 'CC-BY 4.0', 'CC-BY-NC 4.0', 'Ask me first'], help: 'Tells re-users what they may do.' },
  { question: 'General notes / issues', type: 'textarea' },
];

// Deterministic 13-hex ref parts so downloads are stable.
const PROJECT_REF = 'a57 b0da 71c 4e5 8f60 astroregolith'.replace(/[^a-f0-9]/g, '').padEnd(32, '0').slice(0, 32);
const hex = (n: number) => (n + 0x1000000000000).toString(16).slice(-13);

// Build the Epicollect5 project structure object.
export function buildEc5Template(projectName = 'AstroRegolith Plant & Substrate Metadata') {
  const formRef = `${PROJECT_REF}_${hex(1)}`;
  const inputs = TEMPLATE_FIELDS.map((f, i) => {
    const ref = `${formRef}_${hex(100 + i)}`;
    const possible_answers = (f.options || []).map((answer, j) => ({ answer, answer_ref: hex(500 + i * 20 + j).slice(-5) }));
    return {
      max: null, min: null, ref, type: f.type, group: [], jumps: [], regex: null, branch: [],
      verify: false, default: null, is_title: !!f.title, question: f.question,
      uniqueness: 'none', is_required: !!f.required,
      datetime_format: f.type === 'date' ? 'dd/MM/yyyy' : null,
      possible_answers, set_to_current_datetime: false,
    };
  });
  return {
    data: {
      id: PROJECT_REF, type: 'project',
      project: {
        ref: PROJECT_REF, name: projectName, slug: projectName.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        access: 'public', status: 'active', visibility: 'listed',
        description: 'Metadata form for regolith plant-growth experiments: substrate provenance, blend ratio, amendment and particle size alongside the usual organism/light/climate fields, with days-after-sowing and leaf count shaped to match NASA OSD-476 so contributions are directly comparable to the Apollo study.',
        small_description: 'AstroRegolith plant + substrate metadata form.',
        forms: [{ ref: formRef, name: projectName, slug: 'form-1', type: 'hierarchy', inputs }],
      },
    },
    _note: 'Epicollect5 project-structure format. Build these questions in the Epicollect5 form builder (or import if your instance supports it). Field types + options are ready to copy.',
  };
}

function csvEscape(s: string): string {
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// A readable CSV for building the form by hand.
export function templateCsv(): string {
  const rows = [['#', 'Question', 'Type', 'Required', 'Title', 'Options', 'Notes']];
  TEMPLATE_FIELDS.forEach((f, i) => rows.push([
    String(i + 1), f.question, f.type, f.required ? 'yes' : '', f.title ? 'yes' : '',
    (f.options || []).join(' | '), f.help || '',
  ]));
  return rows.map(r => r.map(csvEscape).join(',')).join('\r\n');
}

export function download(filename: string, text: string, mime: string) {
  const blob = new Blob([text], { type: mime });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
