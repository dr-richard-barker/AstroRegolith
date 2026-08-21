# Contributing

Three kinds of contribution are useful here, in roughly this order of value.

## 1. Contribute regolith data

This is the one that matters most: the field's problem is that there is too little
comparable data, not too little code.

**Through the app.** Install [Epicollect5](https://five.epicollect.net) (free), add the
AstroRegolith project, and submit an entry per plant per imaging day. Photograph the
plant **beside a calibration marker** — the AstroBotany ArUco card, a colour chart, or at
minimum a ruler — and take a second photo of the dry substrate and the vessel. The
"Share your data" page in the app walks through it and offers the form as a downloadable
JSON/CSV.

**Through git.** Commit images to a public GitHub folder with a `metadata.csv` beside
them, one row per image joined by a `filename` column, then add that folder as a source
in the app's "Add a source" tab. `tools/generate_sidecar.py` builds the sidecar from a
folder and `tools/validate_sidecar.py` checks it against `sidecar-schema.json`.

**What to record, and why.** Fields that decide whether anyone can reuse your data:

| Field | Why it matters |
| --- | --- |
| Substrate name **and supplier batch** | Simulant composition varies between production runs; the LHS-1 spec sheet is itself versioned. Two labs reporting "LHS-1" may not be comparable. |
| Blend ratio (% regolith by volume) | Places the entry on a dose-response axis instead of a binary one. |
| Particle size | Drives water retention and root penetration resistance more than chemistry does. |
| Pre-treatment (rinsed, autoclaved, dry-heat) | Leaching changes the ionic stress the root actually sees. |
| Sowing date **and** days after sowing | OSD-476 omitted the sowing date; its growth curves cannot be placed on an absolute age axis as a result. |
| Leaf count | Matches OSD-476's own metadata, so your series can be plotted against the Apollo plants. |
| Germination failures and deaths | Zeroes are results. One Apollo 11 plant never produced a true leaf, and that is among the most informative points in the dataset. |

Contributed images stay yours, under the licence you pick on the form. This repository
does not redistribute them; the site reads them from Epicollect5 at view time.

## 2. Extend the catalogue or the analysis

The catalogue is curated in code, not in a spreadsheet:

- **A new regolith study at OSDR** — add its accession and a one-line reason to `SEED` in
  `scripts/01_fetch_osdr.py`. The live search also picks up new deposits whose title
  matches a regolith term and flags them as needing curation.
- **A new PSI investigation** — add it to `CURATED` in `scripts/02_fetch_psi.py` with a
  note on what a regolith grower would take from it. Be honest about the limits: PSI
  holds no plant-in-regolith data, and the site says so.
- **A new analysis** — add a numbered script and wire it into `scripts/run_all.sh`.

House rules for analysis code, because this repository is meant to survive peer review:

1. **Assert the joins.** `04_link_phenotype_transcriptome.py` fails if the sample→plant
   join is not exactly twelve one-to-one, four plate-mean and four unlinked. If a
   restructured upstream deposit breaks that, the pipeline should stop, not quietly
   produce different numbers.
2. **Never invent a value.** Where the deposited metadata is inconsistent — as with
   OSD-476's sowing date — report the inconsistency and use an axis that needs no
   inference. `results/tables/sowing_date_check.csv` exists for exactly this reason.
3. **State units, or state that there are none.** The soil probe reports N/P/K as
   unitless indices; the tables say so rather than implying mg/kg.
4. **Round p-values by significant figures, never decimals.** Fixed-decimal rounding
   turns 1e-8 into 0, which downstream reads as infinite significance.
5. **Figures come from committed tables.** `08_figures.py` reads `results/tables/`, so a
   figure cannot drift from the number it claims to show.
6. **Citations come from Crossref.** Add a DOI to `scripts/check_references.py`; never
   hand-write BibTeX. The script has already caught three misattributed references.

## 3. Improve the site

```bash
npm install
npm run dev
npm run lint     # tsc --noEmit — keep this clean
npm run build
```

The site has no backend and must keep working with none. Dashboards read pre-baked JSON
from `public/data/` written by `scripts/09_export_site_data.py`; do not add a runtime
call to `osdr.nasa.gov` or `psi.nasa.gov`, because both refuse cross-origin requests and
the call will fail in production while appearing to work behind a local proxy.

Styling uses the CoSE design tokens in `src/index.css` (`--accent`, `--card`, `--line`,
…). Use them rather than literal colours so light and dark themes both work, and check
both before opening a pull request.

## Reporting a problem with the data

Open an issue with the accession, the table and the row. Data problems are more valuable
than code problems: if a number here disagrees with the source deposit, we want to know
which, and the pipeline is designed so the disagreement can be traced to a single script.
