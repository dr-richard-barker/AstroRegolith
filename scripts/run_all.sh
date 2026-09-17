#!/usr/bin/env bash
# Rebuild every table, figure and site JSON from the primary sources.
#
#   bash scripts/run_all.sh              full run (fetches if data/ is empty)
#   SKIP_FETCH=1 bash scripts/run_all.sh  reuse what is already in data/
#
# Steps 00-02, 10, 14 and 15 hit the network (GitHub raw, NASA OSDR, NASA PSI,
# EBI QuickGO, NASA JSC curation, the PDS Apollo archive and ARES) and are
# idempotent — a file already present is not re-downloaded. Steps 03-09 and 16
# are pure functions of data/, so their outputs are byte-stable across re-runs.
# Steps 10 and 15 run with the fetch group because they download and re-encode
# imagery; their output is committed, so a SKIP_FETCH run reuses
# public/images/ as-is.
#
# 14 and 15 need the `ares-curation` client: pip install it, or clone it beside
# this repository (https://github.com/dr-richard-barker/ares-curation).
set -euo pipefail
cd "$(dirname "$0")/.."

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

if [ "${SKIP_FETCH:-0}" != "1" ]; then
  step "00  source data from Lunar_regolith_AWG";   python3 scripts/00_fetch_awg_data.py
  step "01  NASA OSDR catalogue + OSD-476 tables";  python3 scripts/01_fetch_osdr.py
  step "02  NASA PSI catalogue";                    python3 scripts/02_fetch_psi.py
  step "10  bundle gallery images";                 python3 scripts/10_bundle_images.py
  step "14  NASA ARES/JSC curation records";        python3 scripts/14_fetch_ares_curation.py
  step "15  ARES simulant table + photographs";     python3 scripts/15_fetch_simulants.py
else
  echo "SKIP_FETCH=1 — using the contents of data/ and public/images/ as-is"
fi

step "03  tidy phenotype tables";                   python3 scripts/03_build_phenotype_table.py
step "04  phenotype <-> transcriptome linkage";     python3 scripts/04_link_phenotype_transcriptome.py
step "05  growth-anchored expression analysis";     python3 scripts/05_expression_vs_growth.py
step "06  GO-slim enrichment";                      python3 scripts/06_enrichment.py
step "07  substrate characterisation";              python3 scripts/07_substrate_traits.py
step "08  figures";                                 python3 scripts/08_figures.py
step "09  site JSON";                               python3 scripts/09_export_site_data.py
step "16  curation site JSON";                      python3 scripts/16_export_curation_site_data.py
step "17  substrate registry";                      python3 scripts/17_build_substrate_registry.py
step "12  supplementary tables";                    python3 scripts/12_supplementary_tables.py

step "--  references (Crossref)";                   python3 scripts/check_references.py || \
  echo "  ! some DOIs did not resolve — see above; references.bib omits them"

printf '\n\033[1mDone.\033[0m results/, public/data/, manuscript/figures/, manuscript/supplementary/\n'
