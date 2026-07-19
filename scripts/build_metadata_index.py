#!/usr/bin/env python3
"""Build One Pace/metadata-index.json from chapters.json + the NFOs.

This is the single source of generation logic, run both as a one-shot local
step and by the CI workflow (.github/workflows/build-metadata-index.yml) on
every push. Output shape matches opforjellyfin's shared.MetadataIndex exactly
(internal/shared/types.go / internal/metadata/indexbuilder.go there - not
modified by this repo):

    {"seasons": {"Season 1": {"range": "1-45", "name": "Romance Dawn",
                               "episodes": {"1-1": {"title": "<nfo filename
                               stem>"}, ...}}, "Specials": {...}}}

EpisodeData.title is the NFO's filename stem (not the <title> tag), matching
opforjellyfin's existing indexbuilder.go behavior exactly, so upgrading an
existing install doesn't change any already-placed filenames.

Exit codes:
    0  success (validation warnings, if any, are non-fatal - printed to stderr)
    1  a hard failure: an episode NFO exists on disk with no corresponding
       chapters.json entry at all (a real oversight - every current episode
       has one; this only trips for future episodes added without updating
       chapters.json first)
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ONE_PACE_DIR = ROOT / "One Pace"
CHAPTERS_PATH = ROOT / "chapters.json"
OUT_PATH = ONE_PACE_DIR / "metadata-index.json"

NAMEDSEASON_RE = re.compile(r'<namedseason\s+number="(\d+)">([^<]+)</namedseason>')


def is_episode_nfo(name: str) -> bool:
    return name.endswith(".nfo") and "season" not in name and "tvshow" not in name


def season_key(season: str) -> str:
    return "Specials" if season in ("0", "00") else f"Season {int(season)}"


def load_season_names() -> dict[str, str]:
    data = (ONE_PACE_DIR / "tvshow.nfo").read_text()
    names = {}
    for num, name in NAMEDSEASON_RE.findall(data):
        clean = name.strip()
        if ". " in clean:
            clean = clean.split(". ", 1)[1]
        names[f"Season {int(num)}"] = clean
    return names


def parse_range(r: str) -> tuple[int, int]:
    start, end = r.split("-")
    return int(start), int(end)


def main() -> int:
    chapters = json.loads(CHAPTERS_PATH.read_text())
    season_names = load_season_names()

    seasons: dict[str, dict] = {}
    missing_entries: list[str] = []
    seen_keys: set[tuple[str, str]] = set()

    for nfo_path in sorted(ONE_PACE_DIR.glob("*/*.nfo")):
        if not is_episode_nfo(nfo_path.name):
            continue

        root = ET.parse(nfo_path).getroot()
        season = (root.findtext("season") or "").strip()
        episode = (root.findtext("episode") or "").strip()
        if not season or not episode:
            continue

        seen_keys.add((season, episode))
        entry = chapters.get(season, {}).get(episode)
        if entry is None:
            missing_entries.append(str(nfo_path.relative_to(ROOT)))
            continue

        chapter_range = entry.get("range")
        if chapter_range is None:
            continue

        skey = season_key(season)
        season_bucket = seasons.setdefault(
            skey, {"range": "00-00", "name": season_names.get(skey, ""), "episodes": {}}
        )
        title = nfo_path.stem

        for r in [chapter_range, *entry.get("extraRanges", [])]:
            season_bucket["episodes"][r] = {"title": title}

    # Orphaned chapters.json entries (on disk previously, file since removed/renamed).
    orphans = []
    for season, eps in chapters.items():
        for episode in eps:
            if (season, episode) not in seen_keys:
                orphans.append(f"season {season} episode {episode}")

    # Season chapter-range summary (min/max across all indexed keys), except Specials.
    for skey, bucket in seasons.items():
        if skey == "Specials":
            continue
        starts_ends = [parse_range(r) for r in bucket["episodes"]]
        lo = min(s for s, _ in starts_ends)
        hi = max(e for _, e in starts_ends)
        bucket["range"] = f"{lo}-{hi}"

    OUT_PATH.write_text(
        json.dumps({"seasons": seasons}, indent=2, sort_keys=True) + "\n"
    )

    if orphans:
        print(
            f"NOTE: {len(orphans)} chapters.json entries have no matching NFO on disk (informational):",
            file=sys.stderr,
        )
        for o in orphans:
            print(f"  {o}", file=sys.stderr)

    print(
        f"Wrote {OUT_PATH.relative_to(ROOT)} ({len(seasons)} seasons)", file=sys.stderr
    )

    if missing_entries:
        print(
            f"\nFAIL: {len(missing_entries)} episode NFOs have no chapters.json entry at all:",
            file=sys.stderr,
        )
        for m in missing_entries:
            print(f"  {m}", file=sys.stderr)
        print(
            "\nAdd entries for these to chapters.json (see scripts/extract_chapters.py --force to bootstrap new ones), then re-run.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
