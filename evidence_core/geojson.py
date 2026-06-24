"""Build GeoJSON from incident upload JSON files."""
from __future__ import annotations

import json
from pathlib import Path


def incident_to_feature(meta: dict) -> dict | None:
    youtube_url = meta.get("youtube_url") or meta.get("youtube", {}).get("url", "")
    incident = meta.get("incident") or meta.get("location") or {}
    lat = incident.get("latitude")
    lon = incident.get("longitude")

    if incident.get("map_visible") is False:
        return None
    if not lat or not lon:
        return None

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return None

    yt = meta.get("youtube") or {}
    title = yt.get("title", "")
    if not title:
        title = meta.get("title", "")

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
        "properties": {
            "incident_id": meta.get("incident_id", ""),
            "base_name": meta.get("base_name", ""),
            "title": title,
            "recorded_utc": incident.get("recorded_utc", meta.get("recorded_utc", "")),
            "recorded_bst": incident.get("recorded_bst", meta.get("recorded_bst", "")),
            "youtube_url": youtube_url,
            "map_url": incident.get(
                "map_url",
                f"https://www.google.com/maps?q={lat},{lon}",
            ),
        },
    }


def load_features_from_dir(
    directory: Path,
    *,
    pattern: str = "*_UPLOAD.json",
    require_youtube_url: bool = False,
) -> list[dict]:
    features: list[dict] = []
    for path in sorted(directory.glob(pattern)):
        try:
            meta = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        youtube_url = meta.get("youtube_url") or meta.get("youtube", {}).get("url", "")
        if require_youtube_url and not youtube_url:
            continue

        feature = incident_to_feature(meta)
        if feature:
            if require_youtube_url and not feature["properties"].get("youtube_url"):
                continue
            features.append(feature)
    return features


def build_geojson(
    directory: Path,
    *,
    pattern: str = "*_UPLOAD.json",
    require_youtube_url: bool = False,
) -> dict:
    features = load_features_from_dir(
        directory,
        pattern=pattern,
        require_youtube_url=require_youtube_url,
    )
    return {"type": "FeatureCollection", "features": features}


def write_geojson(
    directory: Path,
    output: Path,
    *,
    pattern: str = "*_UPLOAD.json",
    require_youtube_url: bool = False,
) -> int:
    collection = build_geojson(
        directory,
        pattern=pattern,
        require_youtube_url=require_youtube_url,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(collection, indent=2) + "\n")
    return len(collection["features"])
