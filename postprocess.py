#!/usr/bin/env python3
import re
import tempfile
import subprocess
from pathlib import Path

ALBUM_PATTERNS = {
    "Unser Freitag": r"unser\s*freitag",
    "Throwback Night": r"throwback\s*night",
    "Saturday Vibes": r"saturday\s*vibes",
    "Saturday Night Vibes": r"saturday\s*night\s*vibes",
    "Saturday Night Beats": r"saturday\s*night\s*beats",
    "Samstags Short Session": r"samstags\s*short\s*session",
    "We Will Rock You": r"we\s*will\s*rock\s*you",
    "Monday Motivation": r"monday\s*motivation",
    "Genre Wheel": r"genre\s*wheel",
}


FILENAME_RE = re.compile(
    r"""
    ^
    (?P<artist>.+?)\s*-\s*
    (?P<date>\d{4}-\d{2}-\d{2})\s+
    (?P<hour>\d{2})h
    (?P<minute>\d{2})m
    (?P<second>\d{2})s
    \s*-\s*
    (?P<title>.+?)
    \.m4a$
    """,
    re.VERBOSE | re.IGNORECASE,
)


def normalize_whitespace(s: str) -> str:
    return " ".join(s.split())


def safe_printable(s: str) -> str:
    return s.encode("utf-8", "replace").decode("utf-8")


def detect_album(title: str) -> str:
    """
    Case-insensitive, matches even if words are glued together.
    Falls back to 'specials'.
    """
    t = title.lower().replace(" ", "")
    for album, pat in ALBUM_PATTERNS.items():
        if re.search(pat.replace(r"\s*", ""), t):
            return album
    return "Specials"


def tag_file(path: Path, dry_run: bool) -> str:
    m = FILENAME_RE.match(path.name)
    if not m:
        raise ValueError(f"Filename does not match pattern: {path.name}")

    original_name = path.name

    title = normalize_whitespace(m.group("title"))
    album = detect_album(title)

    iso_utc = (
        f"{m.group('date')}T"
        f"{m.group('hour')}:{m.group('minute')}:{m.group('second')}Z"
    )

    final_name = f"{title}-{iso_utc}.m4a"

    cmd = [
        "AtomicParsley",
        str(path),
        "--title", title,
        "--artist", "Jani",
        "--composer", "Jani",
        "--album", album,
        "--comment", f"Original filename: {original_name}",
        "--overWrite",
    ]

    if dry_run:
        print(f"DRY  tag {path.name} → {final_name} [{album}]")
        return final_name

    subprocess.run(cmd, check=True)
    return final_name

def ffmpeg_extract_aac_to_m4a_with_progress(
    input_path: Path,
    output_path: Path,
    overwrite: bool = True,
) -> None:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y" if overwrite else "-n",
        "-i", str(input_path),
        "-vn",
        "-map", "a:0",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        "-nostats",
        str(output_path),
    ]

    subprocess.run(cmd, check=True)

def run(input_path: Path, output_path: Path, dry_run: bool = False) -> None:
    output_path.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        suffix=".m4a",
        dir=output_path,
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # 1. Extract AAC → temp m4a
        ffmpeg_extract_aac_to_m4a_with_progress(
            input_path=input_path,
            output_path=tmp_path,
        )

        # 2. Tag temp file, get final filename
        final_name = tag_file(tmp_path, dry_run=dry_run)
        final_path = output_path / final_name

        if dry_run:
            print(f"DRY  move {tmp_path.name} → {final_path.name}")
            return

        # 3. Move temp → final destination
        tmp_path.replace(final_path)

    finally:
        if not dry_run and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    