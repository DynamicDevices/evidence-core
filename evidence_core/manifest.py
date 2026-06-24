"""Build evidence/v1 manifests."""
from __future__ import annotations

from typing import Any

from evidence_core.location import lon_for_map, map_url

SCHEMA = "evidence/v1"


def build_manifest(
    *,
    product: str,
    incident_id: str,
    base_name: str,
    recorded_utc: str,
    recorded_bst: str,
    latitude: str,
    longitude: str,
    lat_tag: str,
    lon_tag: str,
    device_model: str = "",
    device_comment: str = "",
    files: dict[str, dict[str, str]],
    ingested_utc: str,
    processing: dict[str, Any] | None = None,
    police_ref: str = "",
    youtube_url: str = "",
    notes: str = "",
    map_visible: bool = True,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lon_m = lon_for_map(latitude, longitude, lon_tag) if latitude and longitude else longitude
    loc_lon = lon_m if latitude and lon_m else longitude
    label = f"{lat_tag}_{lon_tag}" if lat_tag and lon_tag else ""

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "product": product,
        "incident_id": incident_id,
        "base_name": base_name,
        "recorded_utc": recorded_utc,
        "recorded_bst": recorded_bst,
        "location": {
            "latitude": latitude,
            "longitude": loc_lon,
            "label": label,
            "map_url": map_url(latitude, longitude, lon_tag),
            "map_visible": map_visible,
        },
        "source_device": {
            "model": device_model,
            "comment": device_comment,
        },
        "files": files,
        "processing": processing or {},
        "police_ref": police_ref,
        "youtube_url": youtube_url,
        "notes": notes,
    }
    if extensions:
        manifest["extensions"] = extensions
    return manifest


def rides_legacy_manifest(
    *,
    incident_id: str,
    base_name: str,
    recorded_utc: str,
    recorded_bst: str,
    latitude: str,
    longitude: str,
    lat_tag: str,
    lon_tag: str,
    device_model: str,
    device_comment: str,
    orig_path: str,
    proc_path: str,
    pub_path: str,
    upload_meta_path: str,
    sha_orig: str,
    sha_proc: str,
    sha_pub: str,
    ingested_utc: str,
    notes: str = "",
) -> dict[str, Any]:
    """Manifest matching reckless-rides-uk pre-core shape + evidence/v1 fields."""
    m = build_manifest(
        product="reckless-rides-uk",
        incident_id=incident_id,
        base_name=base_name,
        recorded_utc=recorded_utc,
        recorded_bst=recorded_bst,
        latitude=latitude,
        longitude=longitude,
        lat_tag=lat_tag,
        lon_tag=lon_tag,
        device_model=device_model,
        device_comment=device_comment,
        files={
            "original": {"path": orig_path, "sha256": sha_orig, "role": "POLICE_EVIDENCE"},
            "processed": {"path": proc_path, "sha256": sha_proc, "role": "INTERNAL_REVIEW"},
            "publish": {"path": pub_path, "sha256": sha_pub, "role": "YOUTUBE_UPLOAD"},
            "upload_metadata": {
                "path": upload_meta_path,
                "role": "YOUTUBE_METADATA",
            },
        },
        ingested_utc=ingested_utc,
        processing={
            "ingested_utc": ingested_utc,
            "face_blur": "deface --replacewith blur --mask-scale 1.3",
            "letterbox_16x9": "ffmpeg scale/pad 1920x1080",
            "metadata_stripped_on_publish": True,
        },
        notes=notes,
    )
    # Back-compat for tools expecting dangerous-ebikers-evidence/v1
    m["schema"] = "dangerous-ebikers-evidence/v1"
    return m
