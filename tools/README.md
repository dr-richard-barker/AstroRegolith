# `tools/`

Helpers for preparing a **contributed** image folder before adding it to the database.
They are for contributors, not part of the analysis pipeline — that lives in
[`../scripts/`](../scripts/) and is driven by `run_all.sh`.

| Tool | Does |
| --- | --- |
| `generate_sidecar.py` | Build `metadata.csv` and a Frictionless `datapackage.json` from a folder of images (local or a GitHub folder). |
| `make_metadata_csv.py` | Simpler: just the `metadata.csv`, from filenames and EXIF. |
| `validate_sidecar.py` | Check a sidecar against [`../sidecar-schema.json`](../sidecar-schema.json) before you push. |
| `metadata_template.csv` | A blank sidecar with the expected column names. |
| `plantcv_pipeline_gui.py` | Interactive PlantCV pipeline builder for scoring shoot traits from plate photographs — the same measurements as `results/tables/plantcv_traits_long.csv`. |
| `validate-sidecar.yml` | Drop-in GitHub Action so your own image repository validates its sidecar on every push. |

## The sidecar contract

Images in a GitHub folder are joined to metadata by a `filename` column — that is the
only required field. Everything else is optional, but the regolith fields
(`substrate_name`, `substrate_batch`, `substrate_blend_pct`,
`substrate_particle_size_um`, `substrate_pretreatment`) are what decide whether anyone
can reuse your data, and `days_after_sowing` / `n_leaves` are named to match the NASA
OSD-476 deposit so a contributed series can be plotted against the Apollo plants.

```bash
python3 tools/generate_sidecar.py /path/to/images
python3 tools/validate_sidecar.py /path/to/images/metadata.csv
```

The Epicollect5 route asks the same questions; see the "Share your data" page in the app.
