#!/usr/bin/env python3
"""Bootstrap chapters.json from the episode NFOs.

Usage: python3 scripts/extract_chapters.py [--out chapters.json] [--force]

Safe to re-run for new episodes - won't overwrite existing entries unless
--force is passed.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from _common import ROOT, ONE_PACE_DIR, is_episode_nfo

CHAPTER_LINE_RE = re.compile(r"Manga\s*Chapter\(s\)?:\s*([^\n]+)", re.IGNORECASE)
LEADING_NUMBER_RE = re.compile(r"^\s*(\d+)(?:\s*-\s*(\d+))?")


def parse_component(text: str) -> str | None:
    """Leading 'N' or 'N-M' from a chapter-list component, ignoring trailing
    text (e.g. 'cover stories'). None if it doesn't start with a digit."""
    m = LEADING_NUMBER_RE.match(text)
    if not m:
        return None
    start = m.group(1)
    end = m.group(2) or start
    return f"{start}-{end}"


def extract_chapter_data(plot: str) -> dict:
    match = CHAPTER_LINE_RE.search(plot or "")
    if not match:
        return {"range": None, "note": "no Manga Chapter(s) line found in NFO"}

    value = match.group(1).strip()

    if value.lower() == "unavailable":
        return {"range": None, "note": "Unavailable"}

    components = [c.strip() for c in value.split(",")]
    primary = parse_component(components[0])

    if primary is None:
        return {"range": None, "note": f"non-numeric: {value}"}

    result = {"range": primary}

    extras = [parse_component(c) for c in components[1:]]
    extras = [e for e in extras if e is not None]
    if extras:
        result["extraRanges"] = extras

    # note when there's trailing text after the number, for human review
    stripped_primary_num = LEADING_NUMBER_RE.match(components[0])
    if stripped_primary_num and stripped_primary_num.end() < len(components[0]):
        result["note"] = f"trailing text in source: {components[0]!r}"

    return result


def load_episode(path: Path) -> tuple[str, str, dict]:
    tree = ET.parse(path)
    root = tree.getroot()
    season = (root.findtext("season") or "").strip()
    episode = (root.findtext("episode") or "").strip()
    plot = root.findtext("plot") or ""
    return season, episode, extract_chapter_data(plot)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "chapters.json"))
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing season/episode entries in the output file",
    )
    args = parser.parse_args()

    out_path = Path(args.out)
    chapters: dict[str, dict[str, dict]] = {}
    if out_path.exists() and not args.force:
        chapters = json.loads(out_path.read_text())

    flagged: list[tuple[str, dict]] = []
    count = 0

    for nfo_path in sorted(ONE_PACE_DIR.glob("*/*.nfo")):
        if not is_episode_nfo(nfo_path.name):
            continue

        season, episode, data = load_episode(nfo_path)
        if not season or not episode:
            print(f"SKIP (missing season/episode tag): {nfo_path}", file=sys.stderr)
            continue

        season_entries = chapters.setdefault(season, {})
        if episode in season_entries and not args.force:
            continue

        season_entries[episode] = data
        count += 1

        if data.get("range") is None or "note" in data:
            flagged.append((str(nfo_path.relative_to(ROOT)), data))

    # keep season/episode keys sorted numerically for a readable diff
    ordered = {
        s: dict(sorted(chapters[s].items(), key=lambda kv: int(kv[0])))
        for s in sorted(chapters, key=int)
    }

    out_path.write_text(json.dumps(ordered, indent=2, sort_keys=False) + "\n")

    print(f"Wrote {count} new entries to {out_path}", file=sys.stderr)
    print(f"\n{len(flagged)} entries flagged for manual review:", file=sys.stderr)
    for path, data in flagged:
        print(f"  {path}: {data}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
