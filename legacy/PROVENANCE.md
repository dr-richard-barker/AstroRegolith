# Provenance of `legacy/`

Source: <https://github.com/dr-richard-barker/Lunar_regolith_AWG> (branch `main`).
Ported by `scripts/11_port_legacy_narrative.py`.

## Kept

| Source path | Ported to |
| --- | --- |
| `README (1).md` | [`legacy/01-abstract.md`](01-abstract.md) |
| `the-lunar-green-revolution-introduction.md` | [`legacy/02-introduction.md`](02-introduction.md) |
| `the-green-lunar-revolution-methods.md` | [`legacy/03-methods.md`](03-methods.md) |
| `results/README.md` | [`legacy/04-results-overview.md`](04-results-overview.md) |
| `results/regolith-image-reanalysis-stats.md` | [`legacy/05-results-image-reanalysis.md`](05-results-image-reanalysis.md) |
| `results/regolith-exploratory-data-analysis-gpt4-automated.md` | [`legacy/06-results-exploratory.md`](06-results-exploratory.md) |
| `results/regolith_simulant.md` | [`legacy/07-results-simulant.md`](07-results-simulant.md) |
| `results/broad-lunar-model-provides-evidence-for-della-potential-stabilisation.md` | [`legacy/08-results-della.md`](08-results-della.md) |
| `lunar-green-revolution-conclusion.md` | [`legacy/09-conclusion.md`](09-conclusion.md) |
| `future-work-digital-doubles/README.md` | [`legacy/10-future-work.md`](10-future-work.md) |
| `future-work-digital-doubles/regolith-stress-might-resemble-some-terrestrial-stressors.md` | [`legacy/11-future-terrestrial-analogues.md`](11-future-terrestrial-analogues.md) |
| `future-work-digital-doubles/microrna-anaylsis.md` | [`legacy/12-future-microrna.md`](12-future-microrna.md) |
| `references.md` | [`legacy/13-references.md`](13-references.md) |
| `Original_insights/readme.md` | [`legacy/14-original-insights.md`](14-original-insights.md) |
| `using-the-config-file-for-regolith-research-planning.md` | [`legacy/15-experiment-planning.md`](15-experiment-planning.md) |
| `student-lessons-the-shackleton-crater-rim-garden.md` | [`legacy/16-lesson-shackleton-garden.md`](16-lesson-shackleton-garden.md) |
| `exploration-lesson-plan.md` | [`legacy/17-lesson-exploration.md`](17-lesson-exploration.md) |
| `Student_images_and_data/readme.md` | [`legacy/18-student-data-sharing.md`](18-student-data-sharing.md) |

## Dropped

| Source path | Why |
| --- | --- |
| `README.md` | the AWG action-plan page — project management and Google-Docs links only |
| `SUMMARY.md` | GitBook table of contents, replaced by legacy/README.md |
| `.gitbook/` | ~200 GitBook assets, mostly duplicate '(1)' copies; referenced figures are ported to legacy/figures/ |
| `future-work-digital-doubles/not-sure-how-you-can-help.md` | collaborator recruitment for the AWG review |
| `results/README.md § slide links` | Google Slides and Sheets edit links inside otherwise-kept pages |

## Figures

164 of the repository's GitBook assets are referenced by a kept page and were ported to `legacy/figures/` under descriptive names. The remainder were duplicates (`image (3) (1) (1).png` and similar) or orphaned, and were not copied.

## Data

The primary data files moved to `data/awg/` (see `MANIFEST.tsv`) and are the input to the reproducible analysis in `scripts/`, not to this narrative.
