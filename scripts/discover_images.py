#!/usr/bin/env python3
"""Populate technique images in syllabus.json from Wikimedia Commons.

Collects illustrations (Michael Hultström's Gokyo series, vector SVG diagrams)
and Wikimedia Commons photos/diagrams for each technique, storing up to 4
thumbnails per technique with attribution metadata.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYLLABUS_PATH = ROOT / "syllabus.json"
API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "judo-syllabus/1.0 (https://github.com/nxnarbais/judo-syllabus)"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".svg", ".webp")
MAX_IMAGES = 4

# Alternate search terms for techniques whose Commons files use shorter/variant names.
ALIASES: dict[str, list[str]] = {
    "hon-gesa-gatame": ["Kesa-gatame", "Hon kesa gatame"],
    "kuzure-gesa-gatame": ["Kuzure-kesa-gatame", "Kuzure kesa gatame"],
    "ude-hishigi-juji-gatame": ["Juji-gatame", "Ude-hishigi-juji-gatame"],
    "ude-hishigi-waki-gatame": ["Waki-gatame", "Ude-hishigi-waki-gatame"],
    "ude-hishigi-ude-gatame": ["Ude-gatame", "Ude-hishigi-ude-gatame"],
    "ude-hishigi-hiza-gatame": ["Hiza-gatame", "Ude-hishigi-hiza-gatame"],
    "ude-hishigi-ashi-gatame": ["Ashi-gatame", "Ude-hishigi-ashi-gatame"],
    "ude-hishigi-hara-gatame": ["Hara-gatame", "Ude-hishigi-hara-gatame"],
    "ude-hishigi-sankaku-gatame": ["Sankaku-gatame", "Ude-hishigi-sankaku-gatame"],
    "ude-hishigi-te-gatame": ["Te-gatame", "Ude-hishigi-te-gatame"],
    "kuchiki-daoshi": ["Kuchiki-taoshi", "Kuchiki daoshi"],
    "te-guruma": ["Sukui-nage", "Te guruma"],
    "katate-jime": ["Kata-te-jime", "Katate jime"],
}


def api_get(params: dict[str, str | int]) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def clean_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw or "").strip()


def fetch_category_files(category: str) -> list[str]:
    res = api_get({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": 250,
        "cmtype": "file",
    })
    return [
        m["title"]
        for m in res.get("query", {}).get("categorymembers", [])
        if m["title"].lower().endswith(IMAGE_EXTS)
    ]


def search_commons(query: str, limit: int = 6) -> list[str]:
    res = api_get({
        "action": "query",
        "list": "search",
        "srnamespace": 6,
        "srsearch": f"judo {query}",
        "srlimit": limit,
    })
    return [
        m["title"]
        for m in res.get("query", {}).get("search", [])
        if m["title"].lower().endswith(IMAGE_EXTS)
    ]


def fetch_image_info(titles: list[str]) -> dict[str, dict]:
    info_by_title: dict[str, dict] = {}
    for i in range(0, len(titles), 40):
        batch = titles[i : i + 40]
        res = api_get({
            "action": "query",
            "titles": "|".join(batch),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 640,
        })
        for page in res.get("query", {}).get("pages", {}).values():
            title = page.get("title")
            ii = (page.get("imageinfo") or [None])[0]
            if not title or not ii:
                continue
            thumb = ii.get("thumburl") or ii.get("url")
            if not thumb:
                continue
            meta = ii.get("extmetadata") or {}
            artist = clean_html((meta.get("Artist") or {}).get("value", ""))
            lic = clean_html((meta.get("LicenseShortName") or {}).get("value", ""))
            credit = " · ".join(part for part in (artist[:60], lic) if part)
            clean_title = title.removeprefix("File:").rsplit(".", 1)[0].replace("_", " ")
            info_by_title[title] = {
                "url": thumb,
                "source_url": ii.get("descriptionurl") or ii.get("url"),
                "title": clean_title,
                "credit": credit or "Wikimedia Commons",
            }
    return info_by_title


def main() -> int:
    data = json.loads(SYLLABUS_PATH.read_text(encoding="utf-8"))
    techniques = data.get("techniques") or {}

    print("Fetching Wikimedia Commons judo illustration categories...")
    hult_files = fetch_category_files("Category:Illustrations of Judo techniques by Michael Hultström")
    vec_files = fetch_category_files("Category:Vector illustrations of Judo techniques")

    curated_by_norm: dict[str, list[str]] = {}
    for title in hult_files + vec_files:
        base = title.removeprefix("File:").rsplit(".", 1)[0]
        # Skip cropped variants when main file exists, or keep both under norm
        if "(crop)" in base.lower():
            continue
        curated_by_norm.setdefault(norm(base), []).append(title)

    candidates_by_tid: dict[str, list[str]] = {}
    all_titles: list[str] = []
    seen_titles: set[str] = set()

    for tid, tech in techniques.items():
        picks: list[str] = []
        terms = [tech["name"], tid, *ALIASES.get(tid, [])]
        for term in terms:
            for t in curated_by_norm.get(norm(term), []):
                if t not in picks:
                    picks.append(t)

        # Also search Commons for additional diagrams/photos to populate carousel
        for term in terms[:2]:
            if len(picks) >= MAX_IMAGES:
                break
            for t in search_commons(term, limit=6):
                if t not in picks and "gokyo-no-waza" not in t.lower():
                    picks.append(t)
                if len(picks) >= MAX_IMAGES:
                    break

        picks = picks[:MAX_IMAGES]
        candidates_by_tid[tid] = picks
        for t in picks:
            if t not in seen_titles:
                seen_titles.add(t)
                all_titles.append(t)

    print(f"Fetching image metadata for {len(all_titles)} Wikimedia Commons files...")
    info_map = fetch_image_info(all_titles)

    with_images = 0
    with_multi = 0
    for tid, tech in techniques.items():
        imgs = [info_map[t] for t in candidates_by_tid.get(tid, []) if t in info_map]
        tech["images"] = imgs
        if imgs:
            with_images += 1
        if len(imgs) > 1:
            with_multi += 1

    SYLLABUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Done: {with_images}/{len(techniques)} techniques have images ({with_multi} with multiple images).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
