#!/usr/bin/env python3
"""Check syllabus.json for structural mistakes before publishing.

Catches the errors that otherwise only show up as broken cards in the browser:
unknown technique ids, bad groups, duplicate belt ids, malformed video entries.
Exits with status 1 if any error is found.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYLLABUS_PATH = ROOT / "syllabus.json"

GROUPS = {"Nage-waza", "Katame-waza"}
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def check_video(where: str, video: dict, errors: list[str]) -> None:
    for field in ("title", "url", "youtube_id"):
        if not video.get(field):
            errors.append(f"{where}: missing '{field}'")
    vid = video.get("youtube_id")
    if vid and not YOUTUBE_ID.match(vid):
        errors.append(f"{where}: youtube_id '{vid}' is not an 11-character YouTube id")
    if vid and video.get("url") and vid not in video["url"]:
        errors.append(f"{where}: url does not contain youtube_id '{vid}'")


def validate(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    techniques = data.get("techniques") or {}
    tracks = data.get("tracks") or {}

    if not tracks:
        errors.append("no tracks defined")

    used: set[str] = set()
    belt_ids: set[str] = set()
    for track_key, track in tracks.items():
        if track.get("id") not in (None, track_key):
            errors.append(f"track '{track_key}': id '{track.get('id')}' does not match its key")
        for belt in track.get("belts") or []:
            bid = belt.get("id")
            where = f"{track_key}/{bid}"
            if not bid:
                errors.append(f"{track_key}: belt without id")
                continue
            if bid in belt_ids or bid in tracks:
                errors.append(f"{where}: belt id is not unique (used in URLs as #{bid})")
            belt_ids.add(bid)
            for field in ("name", "short_name"):
                if not belt.get(field):
                    errors.append(f"{where}: missing '{field}'")
            if not HEX_COLOR.match(belt.get("color") or ""):
                errors.append(f"{where}: color '{belt.get('color')}' is not #rrggbb")
            seen: set[str] = set()
            for item in belt.get("items") or []:
                tid = item.get("id")
                used.add(tid)
                if tid not in techniques:
                    errors.append(f"{where}: unknown technique '{tid}'")
                if item.get("group") not in GROUPS:
                    errors.append(f"{where}/{tid}: group '{item.get('group')}' not in {sorted(GROUPS)}")
                if tid in seen:
                    warnings.append(f"{where}: technique '{tid}' listed twice")
                seen.add(tid)

    for tid, tech in techniques.items():
        for field in ("name", "french_name", "category"):
            if not tech.get(field):
                errors.append(f"technique '{tid}': missing '{field}'")
        if len(tech.get("mechanics") or []) != 3:
            warnings.append(f"technique '{tid}': expected 3 mechanics, found {len(tech.get('mechanics') or [])}")
        videos = tech.get("videos") or {}
        if videos.get("baseline"):
            check_video(f"technique '{tid}' baseline", videos["baseline"], errors)
        for i, video in enumerate(videos.get("mistakes_and_counters") or []):
            check_video(f"technique '{tid}' mistakes_and_counters[{i}]", video, errors)
        for i, img in enumerate(tech.get("images") or []):
            if not (img.get("url") or "").startswith("https://"):
                errors.append(f"technique '{tid}' images[{i}]: invalid url")
            if not img.get("title"):
                errors.append(f"technique '{tid}' images[{i}]: missing 'title'")

    for tid in sorted(set(techniques) - used):
        warnings.append(f"technique '{tid}' is not referenced by any belt")

    return errors, warnings


def main() -> int:
    try:
        data = json.loads(SYLLABUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: syllabus.json is not valid JSON: {exc}", file=sys.stderr)
        return 1

    errors, warnings = validate(data)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}", file=sys.stderr)

    techniques = data.get("techniques") or {}
    with_video = sum(1 for t in techniques.values() if (t.get("videos") or {}).get("baseline"))
    print(f"{len(techniques)} techniques, {with_video} with a validated exam video.")
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
