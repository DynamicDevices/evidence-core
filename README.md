# evidence-core

Shared library for evidence intake products under [Dynamic Devices Ltd](https://dynamicdevices.co.uk).

Used as a **git submodule** by product repos (e.g. [reckless-rides-uk](https://github.com/DynamicDevices/reckless-rides-uk), private VAWG lab). This repo is **public** and contains **no credentials**, **no real incident media**, and **no victim data**.

## Modules

| Module | Purpose |
|--------|---------|
| `probe` | Read date/time, device, and GPS from photos and videos (ffprobe, EXIF) |
| `location` | ISO6709 parsing, map URLs, GPS zero/absent detection |
| `manifest` | Build `evidence/v1` chain-of-custody manifests |
| `geojson` | Build GeoJSON from incident JSON (optional YouTube URL filter) |
| `media` | ffmpeg helpers: metadata strip, 16:9 letterbox |

## Install (development)

```bash
pip install -e ".[dev]"
```

## CLI

```bash
# Human-readable metadata report (pass/fail for evidence use)
probe-media /path/to/file.MOV
probe-media /path/to/photo.jpg --json

# GeoJSON from a directory of *_UPLOAD.json incident files
build-geojson evidence/processed -o docs/data/incidents.geojson --require-youtube-url
```

## Product integration

Product repos pin this submodule at `core/` and wrap with product-specific scripts:

- **Prefix** — e.g. `DEB-` (rides), `VAWG-` (lab)
- **Extensions** — YouTube upload JSON, channel templates, compliance docs stay in the product repo
- **Secrets** — OAuth tokens, client secrets, real evidence files never go here

## Schema

Base manifest schema: `schema/evidence-v1.manifest.json`

Products set `product` and `incident_id` with their prefix; optional `extensions` object for YouTube etc.

## Tests

```bash
pytest
```

Fixtures are synthetic only.

## Licence

MIT — Dynamic Devices Ltd.
