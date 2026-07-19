#!/usr/bin/env python3
"""Normalize episode .nfo files to a consistent structure.

Fixes: missing <showtitle>, <season>/<episode> shuffled to the end of the
file, datetime timestamps in <premiered>/<aired>, and the plot's episode-
count label unified to "Anime Episode(s):". Leaves plot prose, blank-line
style, and the XML declaration untouched. Idempotent.
"""
import re
import sys

from _common import ONE_PACE_DIR, ROOT, is_episode_nfo

DATETIME_RE = re.compile(
    r"(<(?:premiered|aired)>\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}(</(?:premiered|aired)>)"
)
EPISODES_LABEL_RE = re.compile(r"(?m)^Episode\(s\):\s*")
EPISODES_LABEL_RE2 = re.compile(r"(?m)^Episodes:\s*")
SHUFFLED_RE = re.compile(r"</aired>\s*<season>")


def extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return m.group(1) if m else None


def normalize(text: str) -> tuple[str, bool]:
    original = text

    text = DATETIME_RE.sub(r"\1\2", text)
    text = EPISODES_LABEL_RE.sub("Anime Episode(s): ", text)
    text = EPISODES_LABEL_RE2.sub("Anime Episode(s): ", text)

    if SHUFFLED_RE.search(text):
        title = extract_tag(text, "title")
        showtitle = extract_tag(text, "showtitle") or "One Pace"
        season = extract_tag(text, "season")
        episode = extract_tag(text, "episode")
        plot = extract_tag(text, "plot")
        premiered = extract_tag(text, "premiered")
        aired = extract_tag(text, "aired")

        text = (
            "<?xml version='1.0' encoding='UTF-8'?>\n"
            "<episodedetails>\n"
            f"  <title>{title}</title>\n"
            f"  <showtitle>{showtitle}</showtitle>\n"
            f"  <season>{season}</season>\n"
            f"  <episode>{episode}</episode>\n"
            f"  <plot>{plot}</plot>\n"
            f"  <premiered>{premiered}</premiered>\n"
            f"  <aired>{aired}</aired>\n"
            "</episodedetails>\n"
        )
    elif "<showtitle>" not in text:
        text = re.sub(
            r"(<title>.*?</title>\n)",
            r"\1  <showtitle>One Pace</showtitle>\n",
            text,
            count=1,
            flags=re.DOTALL,
        )

    return text, text != original


def main() -> int:
    changed = []
    for nfo_path in sorted(ONE_PACE_DIR.glob("*/*.nfo")):
        if not is_episode_nfo(nfo_path.name):
            continue
        text = nfo_path.read_text()
        new_text, did_change = normalize(text)
        if did_change:
            nfo_path.write_text(new_text)
            changed.append(nfo_path)

    print(f"Normalized {len(changed)} files:", file=sys.stderr)
    for p in changed:
        print(f"  {p.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
