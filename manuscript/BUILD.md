# Building the manuscript

```bash
make -C manuscript            # manuscript_npj.pdf
make -C manuscript check      # every \cite resolves; nothing in the .bib is uncited
make -C manuscript figures    # regenerate figures/*.pdf from results/
make -C manuscript references # regenerate references.bib from Crossref
```

## What depends on what

```
scripts/run_all.sh
  ├── results/tables/*.csv ──► every number quoted in the Results
  ├── manuscript/figures/*.pdf ◄── scripts/08_figures.py
  └── manuscript/supplementary/S*.csv ◄── scripts/12_supplementary_tables.py

scripts/check_references.py ──► manuscript/references.bib   (from Crossref, by DOI)
```

Nothing in the manuscript is hand-transcribed from a figure: each Results value is
read from a table under `results/`, and re-running the pipeline regenerates both.

## Requirements

A TeX distribution with `latexmk`, `natbib`, `siunitx`, `booktabs`, `authblk`,
`microtype` and `lineno` — TeX Live 2021 or newer, or MacTeX. On Debian/Ubuntu:

```bash
sudo apt-get install texlive-latex-recommended texlive-latex-extra texlive-science latexmk
```

No local TeX? `.github/workflows/manuscript.yml` builds the PDF on every push and
attaches it as a workflow artefact.

## Submitting to npj Microgravity

The manuscript is written against the standard `article` class so it builds anywhere.
For submission, download the publisher's class and style files and replace the
preamble's `\documentclass` and `\bibliographystyle` lines; the body, figures and
bibliography need no other change. `lineno` is loaded for review and should be dropped
for the camera-ready version.

Figures are vector PDFs at their final size. `scripts/08_figures.py` also writes PNGs
to `results/figures/` for the web database; if the publisher requires raster figures at
a specific DPI, raise `savefig.dpi` in that script rather than resampling the PDFs.
