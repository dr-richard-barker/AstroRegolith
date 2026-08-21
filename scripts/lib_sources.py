"""Shared helpers for the AstroRegolith acquisition scripts.

Everything here is stdlib-only so `scripts/01_*`/`02_*` can run in a bare CI
container. The analysis scripts (03 onward) use pandas/numpy/scipy.

Why the scripts fetch instead of the app: both NASA APIs restrict CORS —
`osdr.nasa.gov/osdr/data/*` answers `Access-Control-Allow-Origin: osdr.nasa.gov`,
`visualization.osdr.nasa.gov/biodata/api/v2/` sends no CORS header at all, and
PSI's `psi.nasa.gov/geode-py/ws/*` is the same GeoDE backend. A browser on
github.io therefore cannot call them. These scripts run offline (or in the
monthly refresh workflow) and bake JSON into `public/data/`, which the static
site reads.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
SITE_DATA = ROOT / "public" / "data"

OSDR_API = "https://osdr.nasa.gov/osdr/data"
OSDR_BIODATA = "https://visualization.osdr.nasa.gov/biodata/api/v2"
OSDR_DL = "https://osdr.nasa.gov/geode-py/ws/studies/{acc}/download?source=datamanager&file={fn}"
OSDR_STUDY_URL = "https://osdr.nasa.gov/bio/repo/data/studies/{acc}"
PSI_API = "https://psi.nasa.gov/geode-py/ws/repo"
PSI_STUDY_URL = "https://psi.nasa.gov/physci/repo/data/investigations/{acc}"

UA = "AstroRegolith/1.0 (https://github.com/dr-richard-barker/AstroRegolith)"


def _open(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"Accept": "*/*", "User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url: str, retries: int = 3, timeout: int = 120):
    """GET a URL and parse JSON, with a short linear backoff."""
    last = None
    for attempt in range(retries):
        try:
            with _open(url, timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} tries: {last}")


def download(url: str, dest: Path, retries: int = 3, timeout: int = 600) -> Path:
    """Download to `dest` unless it already exists (idempotent re-runs)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    last = None
    for attempt in range(retries):
        try:
            with _open(url, timeout) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(tmp, dest)
            return dest
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"download {url} failed after {retries} tries: {last}")


def osdr_files(accession: str) -> dict:
    """The OSDR file listing for e.g. 'OSD-476'."""
    return get_json(f"{OSDR_API}/osd/files/{accession.split('-')[-1]}")


def osdr_meta(accession: str) -> dict:
    """Rich study metadata (title, organism, factors, description).

    The files API carries no title, and `/osdr/data/osd/meta/` returns raw
    ISA-JSON; the biodata v2 endpoint is the one that answers with a flat,
    stable metadata block.
    """
    d = get_json(f"{OSDR_BIODATA}/dataset/{accession}/metadata/")
    return (d.get(accession) or {}).get("metadata", {})


def osdr_search(term: str, size: int = 50) -> list[dict]:
    url = f"{OSDR_API}/search?term={urllib.parse.quote(term)}&size={size}"
    return [h.get("_source", {}) for h in get_json(url).get("hits", {}).get("hits", [])]


def osdr_download_url(accession: str, file_name: str) -> str:
    return OSDR_DL.format(acc=accession, fn=urllib.parse.quote(file_name))


def write_json(path: Path, obj) -> Path:
    """Write pretty, key-sorted JSON so re-runs produce byte-identical files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    return path


def log(*a):
    print(*a, file=sys.stderr, flush=True)
