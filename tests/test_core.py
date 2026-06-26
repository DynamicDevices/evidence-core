import pytest

from evidence_core.location import (
    GpsStatus,
    coords_from_floats,
    lon_for_map,
    map_url,
    parse_iso6709,
)
from evidence_core.manifest import build_manifest
from evidence_core.geojson import build_geojson, incident_to_feature


def test_parse_iso6709_liverpool_area():
    coords = parse_iso6709("+53.4792-003.0207+013.765/")
    assert coords is not None
    assert coords.latitude == "53.4792"
    assert coords.longitude == "-3.0207"
    assert coords.lat_tag == "53.4792N"
    assert coords.lon_tag == "3.0207W"
    assert coords.status == GpsStatus.PRESENT


def test_lon_for_map_west():
    assert lon_for_map("53.4792", "3.0207", "3.0207W") == "-3.0207"


def test_map_url():
    url = map_url("53.4792", "3.0207", "3.0207W")
    assert "53.4792" in url and "-3.0207" in url


def test_build_manifest_evidence_v1():
    m = build_manifest(
        product="personal-safety-app",
        incident_id="VAWG-20260624T064356Z_53.4792N_3.0207W_001",
        base_name="VAWG-20260624T064356Z_53.4792N_3.0207W_001",
        recorded_utc="2026-06-24T06:43:56Z",
        recorded_bst="2026-06-24 07:43:56 BST",
        latitude="53.4792",
        longitude="-3.0207",
        lat_tag="53.4792N",
        lon_tag="3.0207W",
        files={"original": {"path": "x", "sha256": "abc", "role": "INTAKE"}},
        ingested_utc="2026-06-24T08:00:00Z",
        map_visible=False,
    )
    assert m["schema"] == "evidence/v1"
    assert m["location"]["map_visible"] is False


def test_geojson_skips_map_invisible(tmp_path):
    upload = {
        "schema": "dangerous-ebikers-youtube-upload/v1",
        "incident_id": "DEB-001",
        "base_name": "DEB-001",
        "youtube_url": "https://www.youtube.com/watch?v=abc123",
        "incident": {
            "latitude": "53.4",
            "longitude": "-2.9",
            "map_visible": False,
            "recorded_utc": "2026-06-23T08:00:00Z",
        },
        "youtube": {"title": "Test"},
    }
    path = tmp_path / "DEB-001_UPLOAD.json"
    path.write_text(__import__("json").dumps(upload))
    collection = build_geojson(tmp_path, require_youtube_url=True)
    assert collection["features"] == []


def test_geojson_skips_private_youtube():
    meta = {
        "incident_id": "DEB-002",
        "base_name": "DEB-002",
        "youtube_url": "https://www.youtube.com/watch?v=abc123",
        "incident": {
            "latitude": "53.4092",
            "longitude": "-2.9778",
            "recorded_utc": "2026-06-23T08:03:03Z",
        },
        "youtube": {"title": "Test", "privacy": "private"},
    }
    assert incident_to_feature(meta, require_public_youtube=True) is None
    assert incident_to_feature(meta, require_public_youtube=False) is not None


def test_geojson_includes_youtube_incident():
    meta = {
        "incident_id": "DEB-001",
        "base_name": "DEB-001",
        "youtube_url": "https://www.youtube.com/watch?v=abc123",
        "incident": {
            "latitude": "53.4092",
            "longitude": "-2.9778",
            "recorded_utc": "2026-06-23T08:03:03Z",
            "recorded_bst": "2026-06-23 09:03:03 BST",
            "map_url": "https://www.google.com/maps?q=53.4092,-2.9778",
        },
        "youtube": {"title": "Reckless Rides UK — test", "privacy": "public"},
    }
    feature = incident_to_feature(meta)
    assert feature is not None
    assert feature["geometry"]["coordinates"] == [-2.9778, 53.4092]
    assert feature["properties"]["youtube_url"].endswith("abc123")
