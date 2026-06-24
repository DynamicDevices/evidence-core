# evidence-core

Shared library for evidence intake products under [Dynamic Devices Ltd](https://dynamicdevices.co.uk).

Used as a **git submodule** at `core/` by product repos:

| Product | Repo | Visibility |
|---------|------|------------|
| Reckless Rides UK | [reckless-rides-uk](https://github.com/DynamicDevices/reckless-rides-uk) | Public |
| VAWG evidence lab | [vawg-evidence-lab](https://github.com/DynamicDevices/vawg-evidence-lab) | Private (org) |

This repo is **public**. It contains **no credentials**, **no real incident media**, and **no victim data**.

## What it does

| Module | Purpose |
|--------|---------|
| `probe` | Read date/time, device, and GPS from photos and videos |
| `location` | ISO6709 parsing, map URLs, GPS zero/absent detection |
| `manifest` | Build `evidence/v1` chain-of-custody manifests |
| `geojson` | Build GeoJSON from incident JSON (optional YouTube URL filter) |
| `media` | ffmpeg helpers: metadata strip, 16:9 letterbox, deface wrapper |

### Supported sources (probe)

| Source | Time | Device | GPS |
|--------|------|--------|-----|
| iPhone `.MOV` (original) | QuickTime tags | Yes | ISO6709 |
| Samsung JPEG (original) | EXIF | Yes | EXIF (zero if indoor/no fix) |
| WhatsApp video | Stripped | No | No |
| Chat/screenshot re-encode | Usually stripped | No | No |

Install **exifread** for JPEG probing: `pip install -e ".[exif]"`.

## Install

**As a submodule** (typical for product repos):

```bash
git submodule update --init --recursive
pip install -e "./core[dev]"
```

**Standalone clone:**

```bash
git clone https://github.com/DynamicDevices/evidence-core.git
cd evidence-core
pip install -e ".[dev]"
```

## CLI

```bash
# Human-readable report (exit code: 0=pass, 1=partial, 2=fail)
probe-media /path/to/file.MOV
probe-media /path/to/photo.jpg --json
probe-media /path/to/file.MOV --legacy-meta   # ingest-compatible JSON

# GeoJSON from incident metadata files
build-geojson evidence/processed -o docs/data/incidents.geojson --require-youtube-url
```

### Probe verdicts

| Verdict | Meaning | Typical cause |
|---------|---------|---------------|
| **PASS** | Device, time, and real GPS | Outdoor original (e.g. iPhone MOV) |
| **PARTIAL** | Device and time; GPS missing or zero | Indoor shot, or location tags off |
| **FAIL** | Stripped or insufficient metadata | WhatsApp, screenshot, chat preview |

## Python API

```python
from evidence_core.probe import probe_file, format_report
from evidence_core.manifest import build_manifest, rides_legacy_manifest
from evidence_core.geojson import write_geojson

result = probe_file("/path/to/clip.MOV")
print(format_report(result))

write_geojson(
    Path("evidence/processed"),
    Path("docs/data/incidents.geojson"),
    require_youtube_url=True,
)
```

## Product integration

Product repos pin this submodule at `core/` and add wrappers only:

| In product repo | In evidence-core |
|-----------------|------------------|
| Incident prefix (`DEB-`, `VAWG-`) | Generic `evidence/v1` schema |
| YouTube templates, OAuth, channel copy | Probe, manifest, geojson, media |
| Compliance / LIA per purpose | No secrets, synthetic test fixtures only |
| Real evidence files (gitignored) | — |

**Bump core in a product repo:**

```bash
cd core && git fetch && git checkout v0.1.0 && cd ..
git add core && git commit -m "Bump evidence-core to v0.1.0"
```

## Schema

Base manifest: [`schema/evidence-v1.manifest.json`](schema/evidence-v1.manifest.json)

- `schema`: `evidence/v1`
- `product`: e.g. `reckless-rides-uk`
- `incident_id`: product prefix + timestamp + location + sequence
- `location.map_visible`: optional; geojson builder skips when `false`
- `extensions`: product-specific (e.g. YouTube block in rides)

Rides manifests still emit `dangerous-ebikers-evidence/v1` via `rides_legacy_manifest()` for back-compat.

## Tests & CI

```bash
pytest
```

GitHub Actions runs on every push to `main` (pytest + CLI smoke).

## Releases

Tagged with semver (`v0.1.0`, …). Product repos should pin the submodule to a release tag, not floating `main`, for reproducible ingest.

## Licence

MIT — Dynamic Devices Ltd.
