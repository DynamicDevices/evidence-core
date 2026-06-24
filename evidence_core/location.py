"""Location parsing and map URL helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class GpsStatus(str, Enum):
    ABSENT = "absent"
    ZERO = "zero"
    PRESENT = "present"


@dataclass
class Coordinates:
    latitude: str
    longitude: str
    lat_tag: str
    lon_tag: str
    status: GpsStatus


def parse_iso6709(iso6709: str) -> Coordinates | None:
    """Parse Apple QuickTime ISO6709 location string (+lat-lon+alt/)."""
    if not iso6709:
        return None
    m = re.match(
        r"\+([0-9.]+)-([0-9.]+)(?:\+[0-9.]+)?/?",
        iso6709.strip(),
    )
    if not m:
        return None
    lat_val = float(m.group(1))
    lon_val = -float(m.group(2))
    return coords_from_floats(lat_val, lon_val)


def coords_from_floats(lat_val: float, lon_val: float) -> Coordinates:
    lat = f"{lat_val:.4f}"
    lon = f"{lon_val:.4f}"
    lat_tag = f"{abs(lat_val):.4f}N" if lat_val >= 0 else f"{abs(lat_val):.4f}S"
    lon_tag = f"{abs(lon_val):.4f}W" if lon_val < 0 else f"{abs(lon_val):.4f}E"
    return Coordinates(lat, lon, lat_tag, lon_tag, GpsStatus.PRESENT)


def exif_rational_to_float(parts: list) -> float | None:
    """Convert exifread rational tuples to float degrees."""
    if not parts or len(parts) != 3:
        return None
    try:
        deg = float(parts[0].num) / float(parts[0].den)
        minutes = float(parts[1].num) / float(parts[1].den)
        seconds = float(parts[2].num) / float(parts[2].den)
        return deg + minutes / 60.0 + seconds / 3600.0
    except (AttributeError, TypeError, ZeroDivisionError):
        return None


def gps_from_exif_rationals(
    lat_parts: list,
    lat_ref: str,
    lon_parts: list,
    lon_ref: str,
) -> Coordinates | None:
    lat_val = exif_rational_to_float(lat_parts)
    lon_val = exif_rational_to_float(lon_parts)
    if lat_val is None or lon_val is None:
        return None
    if str(lat_ref).strip().upper() == "S":
        lat_val = -abs(lat_val)
    if str(lon_ref).strip().upper() == "W":
        lon_val = -abs(lon_val)
    if lat_val == 0.0 and lon_val == 0.0:
        return Coordinates("", "", "UNKNOWN", "UNKNOWN", GpsStatus.ZERO)
    return coords_from_floats(lat_val, lon_val)


def is_zero_gps_rationals(lat_parts: list, lon_parts: list) -> bool:
    """Samsung indoor shots may write GPS IFD with 0/0,0/0,0/0."""
    for parts in (lat_parts, lon_parts):
        if not parts or len(parts) != 3:
            continue
        try:
            if all(float(p.num) == 0 for p in parts):
                continue
            return False
        except AttributeError:
            return False
    return bool(lat_parts and lon_parts)


def lon_for_map(lat: str, lon: str, lon_tag: str) -> str:
    if lat and lon and lon_tag.endswith("W") and not str(lon).startswith("-"):
        return f"-{str(lon).lstrip('-')}"
    return lon


def map_url(lat: str, lon: str, lon_tag: str = "") -> str:
    lon_m = lon_for_map(lat, lon, lon_tag) if lon_tag else lon
    if lat and lon_m:
        return f"https://www.google.com/maps?q={lat},{lon_m}"
    return ""
