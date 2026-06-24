"""ffmpeg media processing helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path


def letterbox_strip_metadata(
    source: Path,
    dest: Path,
    *,
    ffmpeg: str = "ffmpeg",
    width: int = 1920,
    height: int = 1080,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale=-2:{height},pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "copy",
            "-map_metadata",
            "-1",
            str(dest),
        ],
        check=True,
    )


def run_deface(
    source: Path,
    dest: Path,
    *,
    deface: str,
    mask_scale: float = 1.3,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            deface,
            str(source),
            "--replacewith",
            "blur",
            "--mask-scale",
            str(mask_scale),
            "--keep-audio",
            "-o",
            str(dest),
        ],
        check=True,
    )
