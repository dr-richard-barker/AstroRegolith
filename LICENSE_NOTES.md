# Licensing

This repository is dual-licensed, because it contains two different kinds of thing.

| What | Licence | Where |
| --- | --- | --- |
| Software — the web application and the analysis pipeline | **MIT** ([LICENSE](LICENSE)) | `src/`, `scripts/`, `tools/`, build config |
| Data, figures and prose — derived tables, generated figures, the manuscript, the site copy | **CC-BY-4.0** | `results/`, `manuscript/`, `legacy/`, `public/data/`, `docs/` |

Attribution for the CC-BY material: cite this repository as given in
[`CITATION.cff`](CITATION.cff), or its Zenodo DOI once deposited.

## Third-party material

Nothing here relicenses anyone else's work. Redistributed or derived material keeps
the terms of its source, and every file's provenance is recorded in
[`MANIFEST.tsv`](MANIFEST.tsv).

- **NASA OSDR and NASA PSI data** (`data/osdr/`, `public/images/osd-670/`,
  `public/data/*_catalog.json`) — NASA open data. Cite the original investigators of
  each study, not only this database; every study card links to its deposit.
- **`Lunar_regolith_AWG` material** (`data/awg/`, `legacy/`) — the author's own
  earlier work, ported here under the same CC-BY-4.0 terms as the rest of the prose.
  See [`legacy/PROVENANCE.md`](legacy/PROVENANCE.md).
- **Exolith Lab LHS-1 specification** (`results/tables/simulant_lhs1_*.csv`) —
  factual composition data transcribed from the manufacturer's published spec sheet,
  with the source URL on every row.
- **Chang'e-5 soil composition** (`results/tables/lunar_soil_ce5_composition.csv`) —
  transcribed from Li *et al.*, *National Science Review* 9(2):nwab188, with the DOI
  on every row.
- **npm dependencies** — their own licences, listed in `package-lock.json`.

## Contributed images

Images contributed through the Epicollect5 project are stored by Epicollect5 and
remain the contributor's, under whichever licence they select on the form
(CC0, CC-BY-4.0, CC-BY-NC-4.0, or "ask me first"). This repository does not
redistribute them; the site reads them from Epicollect5's API at view time.
