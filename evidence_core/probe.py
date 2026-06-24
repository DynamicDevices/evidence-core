"""Probe photos and videos for evidence metadata."""
from __future__ import annotations

import json
import mimetypes
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from evidence_core.location import (
    Coordinates,
    GpsStatus,
    coords_from_floats,
    gps_from_exif_rationals,
    is_zero_gps_rationals,
    parse_iso6709,
)

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]


class SourceType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    UNKNOWN = "unknown"


class DeliveryQuality(str, Enum):
    ORIGINAL = "original"
    LIKELY_REENCODED = "likely_reencoded"
    UNKNOWN = "unknown"


@dataclass
class ProbeResult:
    path: str
    source_type: SourceType
    delivery_quality: DeliveryQuality
    recorded_utc: str = ""
    recorded_bst: str = ""
    utc_stamp: str = ""
    device_make: str = ""
    device_model: str = ""
    device_software: str = ""
    latitude: str = ""
    longitude: str = ""
    lat_tag: str = "UNKNOWN"
    lon_tag: str = "UNKNOWN"
    gps_status: GpsStatus = GpsStatus.ABSENT
    width: int = 0
    height: int = 0
    duration_seconds: float | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def device(self) -> str:
        return self.device_model or self.device_make

    def to_legacy_meta(self) -> dict:
        """Shape expected by reckless-rides-uk ingest-incident.sh."""
        return {
            "utc_recorded": self.recorded_utc,
            "utc_stamp": self.utc_stamp,
            "bst_recorded": self.recorded_bst,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "lat_tag": self.lat_tag,
            "lon_tag": self.lon_tag,
            "device": self.device,
            "device_comment": "",
        }

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source_type"] = self.source_type.value
        d["delivery_quality"] = self.delivery_quality.value
        d["gps_status"] = self.gps_status.value
        d["device"] = self.device
        return d


def _bst_from_utc(dt_utc: datetime) -> str:
    if ZoneInfo is None:
        return ""
    return dt_utc.astimezone(ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M:%S %Z")


def _parse_utc_tag(raw: str) -> datetime | None:
    if not raw:
        return None
    raw = raw.rstrip("Z")
    if raw.endswith(".000000"):
        raw = raw[:-7]
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y:%m:%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _apply_coords(result: ProbeResult, coords: Coordinates | None) -> None:
    if coords is None:
        result.gps_status = GpsStatus.ABSENT
        result.lat_tag = "UNKNOWN"
        result.lon_tag = "UNKNOWN"
        return
    result.gps_status = coords.status
    if coords.status == GpsStatus.PRESENT:
        result.latitude = coords.latitude
        result.longitude = coords.longitude
        result.lat_tag = coords.lat_tag
        result.lon_tag = coords.lon_tag
    elif coords.status == GpsStatus.ZERO:
        result.notes.append("GPS IFD present but coordinates are zero (no fix, often indoor)")


def _guess_delivery_quality(
    path: Path,
    width: int,
    height: int,
    has_device: bool,
    has_time: bool,
) -> DeliveryQuality:
    name = path.name.lower()
    if "whatsapp" in name:
        return DeliveryQuality.LIKELY_REENCODED
    if width and height and max(width, height) < 720 and not has_device:
        return DeliveryQuality.LIKELY_REENCODED
    if has_device and has_time:
        return DeliveryQuality.ORIGINAL
    if not has_device and not has_time:
        return DeliveryQuality.LIKELY_REENCODED
    return DeliveryQuality.UNKNOWN


def probe_video(path: Path, ffprobe: str = "ffprobe") -> ProbeResult:
    result = ProbeResult(
        path=str(path),
        source_type=SourceType.VIDEO,
        delivery_quality=DeliveryQuality.UNKNOWN,
    )
    out = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "quiet",
            "-show_entries",
            "format_tags:stream=width,height",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    data = json.loads(out)
    tags = data.get("format", {}).get("tags", {})
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            result.width = int(stream.get("width") or 0)
            result.height = int(stream.get("height") or 0)
            break

    fmt = data.get("format", {})
    try:
        result.duration_seconds = float(fmt.get("duration") or 0) or None
    except (TypeError, ValueError):
        result.duration_seconds = None

    result.device_make = tags.get("com.apple.quicktime.make", "")
    result.device_model = tags.get("com.apple.quicktime.model", "")
    result.device_software = tags.get("com.apple.quicktime.software", "")

    utc_raw = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time") or ""
    dt_utc = _parse_utc_tag(utc_raw)
    if dt_utc:
        result.recorded_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        result.utc_stamp = dt_utc.strftime("%Y%m%dT%H%M%SZ")
        result.recorded_bst = _bst_from_utc(dt_utc)

    coords = parse_iso6709(tags.get("com.apple.quicktime.location.ISO6709", ""))
    _apply_coords(result, coords)

    result.delivery_quality = _guess_delivery_quality(
        path,
        result.width,
        result.height,
        bool(result.device),
        bool(result.recorded_utc),
    )
    if result.delivery_quality == DeliveryQuality.LIKELY_REENCODED:
        result.notes.append("Likely chat-app or re-encoded copy — metadata stripped")
    return result


def probe_image_exifread(path: Path) -> ProbeResult | None:
    try:
        import exifread
    except ImportError:
        return None

    result = ProbeResult(
        path=str(path),
        source_type=SourceType.IMAGE,
        delivery_quality=DeliveryQuality.UNKNOWN,
    )
    with path.open("rb") as fh:
        tags = exifread.process_file(fh, details=False)

    if not tags:
        result.delivery_quality = DeliveryQuality.LIKELY_REENCODED
        result.notes.append("No EXIF — likely screenshot or chat re-encode")
        return result

    result.device_make = str(tags.get("Image Make", ""))
    result.device_model = str(tags.get("Image Model", ""))
    result.device_software = str(tags.get("Image Software", ""))

    dt_raw = str(tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime") or "")
    dt_utc = _parse_utc_tag(dt_raw)
    if dt_utc is None and dt_raw:
        dt_utc = _parse_utc_tag(dt_raw.replace(" ", "T"))
    if dt_utc:
        result.recorded_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        result.utc_stamp = dt_utc.strftime("%Y%m%dT%H%M%SZ")
        result.recorded_bst = _bst_from_utc(dt_utc)

    lat_parts = tags.get("GPS GPSLatitude")
    lon_parts = tags.get("GPS GPSLongitude")
    lat_ref = tags.get("GPS GPSLatitudeRef")
    lon_ref = tags.get("GPS GPSLongitudeRef")

    if lat_parts and lon_parts:
        if is_zero_gps_rationals(lat_parts.values, lon_parts.values):
            _apply_coords(
                result,
                Coordinates("", "", "UNKNOWN", "UNKNOWN", GpsStatus.ZERO),
            )
        else:
            _apply_coords(
                result,
                gps_from_exif_rationals(
                    lat_parts.values,
                    str(lat_ref or ""),
                    lon_parts.values,
                    str(lon_ref or ""),
                ),
            )
    else:
        _apply_coords(result, None)

    for tag in ("EXIF ExifImageWidth", "EXIF PixelXDimension"):
        if tag in tags:
            try:
                result.width = int(str(tags[tag]))
                break
            except ValueError:
                pass
    for tag in ("EXIF ExifImageLength", "EXIF PixelYDimension"):
        if tag in tags:
            try:
                result.height = int(str(tags[tag]))
                break
            except ValueError:
                pass

    result.delivery_quality = _guess_delivery_quality(
        path,
        result.width,
        result.height,
        bool(result.device),
        bool(result.recorded_utc),
    )
    return result


def probe_image(path: Path) -> ProbeResult:
    from_exif = probe_image_exifread(path)
    if from_exif is not None:
        return from_exif

    result = ProbeResult(
        path=str(path),
        source_type=SourceType.IMAGE,
        delivery_quality=DeliveryQuality.UNKNOWN,
        notes=["exifread not installed — pip install evidence-core[exif]"],
    )
    return result


def probe_file(path: str | Path, ffprobe: str = "ffprobe") -> ProbeResult:
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(p)

    mime, _ = mimetypes.guess_type(p.name)
    suffix = p.suffix.lower()

    if (mime and mime.startswith("video/")) or suffix in {
        ".mov",
        ".mp4",
        ".m4v",
        ".avi",
        ".mkv",
        ".webm",
    }:
        return probe_video(p, ffprobe=ffprobe)
    if (mime and mime.startswith("image/")) or suffix in {
        ".jpg",
        ".jpeg",
        ".png",
        ".heic",
        ".heif",
        ".webp",
    }:
        return probe_image(p)

    return ProbeResult(
        path=str(p),
        source_type=SourceType.UNKNOWN,
        delivery_quality=DeliveryQuality.UNKNOWN,
        notes=[f"Unrecognised type: {mime or suffix}"],
    )


def format_report(result: ProbeResult) -> str:
    lines = [
        f"File: {result.path}",
        f"Type: {result.source_type.value}",
        f"Delivery: {result.delivery_quality.value}",
    ]
    if result.width and result.height:
        lines.append(f"Dimensions: {result.width}x{result.height}")
    if result.duration_seconds is not None:
        lines.append(f"Duration: {result.duration_seconds:.1f}s")
    if result.device:
        lines.append(f"Device: {result.device_make} {result.device_model}".strip())
    if result.device_software:
        lines.append(f"Software: {result.device_software}")
    if result.recorded_utc:
        lines.append(f"Recorded (UTC): {result.recorded_utc}")
    if result.recorded_bst:
        lines.append(f"Recorded (local): {result.recorded_bst}")
    lines.append(f"GPS: {result.gps_status.value}")
    if result.gps_status == GpsStatus.PRESENT:
        lines.append(f"  {result.latitude}, {result.longitude} ({result.lat_tag} {result.lon_tag})")
    for note in result.notes:
        lines.append(f"Note: {note}")

    if result.delivery_quality == DeliveryQuality.LIKELY_REENCODED:
        lines.append("Verdict: FAIL for evidence metadata (use original via Drive/email/USB)")
    elif result.gps_status == GpsStatus.PRESENT and result.recorded_utc:
        lines.append("Verdict: PASS — device, time, and GPS present")
    elif result.recorded_utc and result.gps_status == GpsStatus.ZERO:
        lines.append("Verdict: PARTIAL — device/time OK; GPS zero (try outdoors)")
    elif result.recorded_utc:
        lines.append("Verdict: PARTIAL — device/time OK; no GPS")
    else:
        lines.append("Verdict: FAIL — insufficient metadata")
    return "\n".join(lines)
