"""Shared helpers for the metadata build scripts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ONE_PACE_DIR = ROOT / "One Pace"


def is_episode_nfo(name: str) -> bool:
    return name.endswith(".nfo") and "season" not in name and "tvshow" not in name
