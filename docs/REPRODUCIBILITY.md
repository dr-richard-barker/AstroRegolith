# Reproducibility

Everything under `results/`, `public/data/`, `manuscript/figures/` and
`manuscript/supplementary/` is generated. Nothing in them is hand-edited, and
`bash scripts/run_all.sh` rebuilds all of it from the primary sources.

## Environment the committed results were produced in

| | |
| --- | --- |
| Date of the committed run | 2026-08-21 |
| Platform | macOS (Darwin 25.5.0), arm64 |
| Python | 3.9.6 |
| pandas / numpy / scipy | 2.3.3 / 2.0.2 / 1.13.1 |
| matplotlib | 3.9.4 |
| Pillow / pillow-heif | 11.3.0 / 1.1.1 |
| Node / npm (site build only) | 22.19.0 / 10.9.3 |

`requirements.txt` pins the Python packages. Nothing in the analysis depends on macOS;
the only platform-specific note is that a case-insensitive filesystem forced unique
temporary filenames in `scripts/11_port_legacy_narrative.py`, since three source pages
are all called `README.md`.

## What is deterministic, and what is not

**Deterministic.** Steps 03–09 and 12–13 are pure functions of `data/`. There is no
sampling, no random seed, no wall-clock input to a computation. Re-running them on the
same `data/` produces byte-identical tables and figures, except for two documented
timestamps: `public/data/manifest.json` carries a build date, and `MANIFEST.tsv` carries
a retrieval date.

**Not deterministic across time.** Steps 00–02 and 10 read live APIs:

- `01_fetch_osdr.py` seeds from a curated accession list, then runs a live search and
  flags anything new as needing curation. A study deposited after the committed run will
  appear and change the catalogue counts. This is intentional — the alternative is a
  catalogue that silently goes stale.
- `02_fetch_psi.py` behaves the same way for PSI.
- `06_enrichment.py` resolves GO term *names* from EBI QuickGO, cached in
  `data/go_terms.json`. The cache makes re-runs offline and stable; deleting it and
  re-running could pick up renamed terms. Term *membership* comes from the annotation
  OSDR ships with GLDS-476, not from QuickGO, so enrichment statistics do not move.
- `check_references.py` reads Crossref, so a publisher metadata correction would change
  `references.bib`. That is the point: the alternative is a bibliography written from
  memory, which is how three references in an early draft came to be misattributed.

To reproduce the committed numbers exactly, run with `SKIP_FETCH=1` against the
committed `data/` directory.

## Verifying an untouched checkout

```bash
shasum -a 256 -c CHECKSUMS.sha256      # Linux: sha256sum -c
```

`CHECKSUMS.sha256` covers every committed file under `data/`, `results/`, `public/data/`,
`public/images/`, `manuscript/figures/`, `manuscript/supplementary/` and `legacy/`.
Files listed in `MANIFEST.tsv` with `redistributed_here = no` are deliberately absent —
they are large NASA tables the pipeline re-fetches, and their source URL and size are
recorded there.

## Checks built into the pipeline

These fail the run rather than producing quietly wrong output:

- **Unit safety.** `03_build_phenotype_table.py` asserts `area_scale == linear_scale²`
  before converting pixels to mm², and cross-checks the imaging date parsed from each
  filename against the source table's day-of-month column.
- **Join integrity.** `04_link_phenotype_transcriptome.py` asserts exactly 20 samples,
  16 with morphometrics, 12 one-to-one Apollo joins each matching a single plant, 4
  JSC-1A plate-mean joins over four plants each, and 4 unlinked.
- **Independent-measurement QC.** The same script reports the Spearman correlation
  between the two phenotype layers (ρ = 0.843, p = 4.2 × 10⁻⁵) — a check on the join,
  since the layers were measured separately.
- **Out-of-range flagging.** Solidity above 1 is impossible; two upstream PlantCV rows
  exceed it, and are flagged in the output rather than silently corrected.
- **Statistical implementation.** The vectorised Spearman in `05_expression_vs_growth.py`
  was validated against `scipy.stats.spearmanr` (agreement to ~1e-16); genes whose ranks
  are fully tied within a subset are excluded rather than divided by zero.
- **Bibliography.** `check_references.py` exits non-zero on an unresolved DOI;
  `check_citations.py` exits non-zero if the manuscript cites a key the bibliography
  does not define.

## Known limitations of the committed results

- The analysis rests on one study (OSD-476) because no second study with returned lunar
  material, paired transcriptomes and per-plant phenotypes exists.
- n = 16 phenotyped plants; the per-substrate standard deviations behind the power
  estimates come from n = 4 each and are themselves poorly determined.
- Growth and substrate are confounded in the primary analysis. The within-lunar analysis
  breaks the confounding at the cost of power, which is why rosette area yields no robust
  hits.
- GO-slim over ~1,900 terms is conservative under Benjamini–Hochberg at this sample size;
  the reported enrichment is a floor.
- No sowing date is published for OSD-476 because the deposited ages and leaf counts
  admit none consistent with all samples. Growth is reported on days from the first plate
  scan. See `results/tables/sowing_date_check.csv`.
