#!/usr/bin/env python3
"""Discover candidate YouTube instructional videos for techniques in syllabus.json.

Requires `yt-dlp` installed locally (`brew install yt-dlp` or `pip install yt-dlp`).
Outputs results to `scripts/candidates.json` for manual watching and validation.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYLLABUS_PATH = ROOT / "syllabus.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "candidates.json"

TRUSTED_CHANNELS = [
    "KODOKAN",
    "Shintaro Higashi",
    "Travis Stevens",
    "Neil Adams",
    "HanpanTV",
]


def is_trusted(channel: str | None) -> bool:
    return bool(channel) and any(t.lower() in channel.lower() for t in TRUSTED_CHANNELS)


def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """Run yt-dlp ytsearch and return compact candidate metadata."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        f"ytsearch{max_results}:{query}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []

    results = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        video_id = item.get("id")
        if not video_id:
            continue
        results.append(
            {
                "youtube_id": video_id,
                "title": item.get("title"),
                "channel": item.get("channel") or item.get("uploader"),
                "duration": item.get("duration"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "trusted": is_trusted(item.get("channel") or item.get("uploader")),
            }
        )
    # Trusted channels first, keeping YouTube's relevance order otherwise.
    results.sort(key=lambda r: not r["trusted"])
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch candidate Judo YouTube videos.")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only query techniques where videos.baseline is null.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of techniques to query (0 = all).",
    )
    parser.add_argument(
        "--per-tech",
        type=int,
        default=5,
        help="Number of YouTube search results per technique.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON file path.",
    )
    args = parser.parse_args()

    if not shutil.which("yt-dlp"):
        print("Error: yt-dlp is not installed. Install via `brew install yt-dlp`.", file=sys.stderr)
        return 1

    syllabus = json.loads(SYLLABUS_PATH.read_text(encoding="utf-8"))
    techniques = syllabus.get("techniques", {})

    targets = []
    for tech_id, tech in techniques.items():
        has_baseline = bool((tech.get("videos") or {}).get("baseline"))
        if args.only_missing and has_baseline:
            continue
        targets.append((tech_id, tech["name"]))

    if args.limit > 0:
        targets = targets[: args.limit]

    candidates: dict[str, list[dict]] = {}
    for idx, (tech_id, name) in enumerate(targets, start=1):
        query = f"judo {name} Kodokan OR \"Shintaro Higashi\" OR \"Travis Stevens\""
        print(f"[{idx}/{len(targets)}] Searching: {name}...", flush=True)
        candidates[tech_id] = search_youtube(query, max_results=args.per_tech)

    args.output.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(candidates)} technique candidate lists to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
