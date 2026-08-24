#!/usr/bin/env python3
"""
Build scripts/lesson_nav_map.json: for every Gradus, the ordered list of
its own lessons (slug, title, and -- if a matching topic exists in that
level's *unmodified* test-yourself.html -- the anchor id to deep-link to),
used by build_lesson.py to render Prior/Proximum navigation and a "Te
Ipsum Proba" button on every generated lesson page.

Adapted from the sibling English-course project's scripts/build_nav_map.py
-- simpler here since every one of this course's seven levels goes
through the curriculum/*.json pipeline uniformly (the English original
special-cases its hand-authored A1 level; this course has no such
exception). This script only reads existing files (curriculum/*.json,
curriculum/index.json, gradus/{level}/test-yourself.html) -- it never
invents lesson names or test-yourself topics. A lesson with no matching
test-yourself topic gets "ty": null.

Usage:
    python3 scripts/build_nav_map.py
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LEVEL_KEYS = ["I", "II", "III", "IV", "V", "VI", "VII"]
LEVEL_SLUGS = {
    "I": "fundamenta", "II": "elementa", "III": "progressus", "IV": "media",
    "V": "provectus", "VI": "altior", "VII": "auctores",
}

# Slug overrides where a lesson's own slug doesn't literally match its
# test-yourself.html anchor id.
TY_ANCHOR_OVERRIDE = {}


def ty_anchors(level_slug: str) -> dict:
    """id -> heading text, for every ty-topic section in that level's
    existing, untouched test-yourself.html (empty dict if none exists)."""
    path = REPO_ROOT / "gradus" / level_slug / "test-yourself.html"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<section id="([^"]+)"[^>]*ty-topic[^>]*aria-labelledby="([^"]+)"[^>]*>.*?<h2 id="\2">([^<]+)</h2>',
        re.S,
    )
    return {sid: heading for sid, _hid, heading in pattern.findall(text)}


def build_level(level_key: str) -> list:
    level_slug = LEVEL_SLUGS[level_key]
    idx_path = REPO_ROOT / "curriculum" / "index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"levels": {}}
    level_entry = idx.get("levels", {}).get(level_key)
    lessons = level_entry["units"][0]["lessons"] if level_entry and level_entry["units"] else []
    anchors = ty_anchors(level_slug)
    id_prefix = level_key.lower() + "-"  # lesson ids use the level CODE prefix (i-, ii-...), not the slug
    out = []
    for entry in lessons:
        lesson_id = entry["id"]
        slug = lesson_id[len(id_prefix):] if lesson_id.startswith(id_prefix) else lesson_id
        lesson_json_path = REPO_ROOT / "curriculum" / level_key.lower() / f"{slug}.json"
        if not lesson_json_path.exists():
            continue
        title = json.loads(lesson_json_path.read_text(encoding="utf-8"))["title"]
        ty = TY_ANCHOR_OVERRIDE.get((level_key, slug))
        if ty is None:
            ty = slug if slug in anchors else None
        out.append({"slug": slug, "title": title, "ty": ty})
    return out


def main():
    nav_map = {}
    for key in LEVEL_KEYS:
        nav_map[LEVEL_SLUGS[key]] = build_level(key)
    out_path = REPO_ROOT / "scripts" / "lesson_nav_map.json"
    out_path.write_text(json.dumps(nav_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for lvl, lessons in nav_map.items():
        with_ty = sum(1 for l in lessons if l["ty"])
        print(f"{lvl}: {len(lessons)} lessons, {with_ty} with a Te Ipsum Proba match")


if __name__ == "__main__":
    main()
