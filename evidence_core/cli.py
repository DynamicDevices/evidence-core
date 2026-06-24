"""Command-line entry points."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evidence_core.geojson import write_geojson
from evidence_core.probe import format_report, probe_file


def probe_main() -> None:
    parser = argparse.ArgumentParser(description="Probe media file for evidence metadata")
    parser.add_argument("path", help="Photo or video file")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--legacy-meta", action="store_true", help="Output ingest-compatible JSON")
    parser.add_argument("--ffprobe", default="ffprobe", help="ffprobe binary path")
    args = parser.parse_args()

    try:
        result = probe_file(args.path, ffprobe=args.ffprobe)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    if args.legacy_meta:
        print(json.dumps(result.to_legacy_meta()))
    elif args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_report(result))

    if result.delivery_quality.value == "likely_reencoded":
        sys.exit(2)
    if result.gps_status.value == "present" and result.recorded_utc:
        sys.exit(0)
    if result.recorded_utc:
        sys.exit(1)
    sys.exit(2)


def geojson_main() -> None:
    parser = argparse.ArgumentParser(description="Build GeoJSON from incident JSON files")
    parser.add_argument("input_dir", type=Path, help="Directory containing *_UPLOAD.json")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--require-youtube-url",
        action="store_true",
        help="Only include incidents with a YouTube URL (public map)",
    )
    parser.add_argument("--pattern", default="*_UPLOAD.json")
    args = parser.parse_args()

    count = write_geojson(
        args.input_dir,
        args.output,
        pattern=args.pattern,
        require_youtube_url=args.require_youtube_url,
    )
    print(f"Wrote {count} feature(s) -> {args.output}")


if __name__ == "__main__":
    probe_main()
