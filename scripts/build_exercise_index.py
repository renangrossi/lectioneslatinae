#!/usr/bin/env python3
"""
Build assets/data/exercise-items-index.json (spaced-repetition lookup)
and assets/data/search-index.json (site search) from the curriculum.

Adapted from the sibling English-course project's
scripts/build_exercise_index.py, which only built the exercise-items
index (that project's search-index.json was hand-maintained separately,
with no generator script committed). This version does both from the
same curriculum walk, so the search index can never drift from what's
actually published the way a hand-maintained list can.

exercise-items-index.json: a flat lookup of every exercise item across
every curriculum/{level}/*.json lesson, keyed by item id -- this is what
makes hodie.html's spaced-repetition review possible without a backend:
mastery.js tracks *which* item ids are due for review (in localStorage,
using only the id + correctness history), but has no way to know what an
item actually says. This index is the other half.

search-index.json: one entry per Gradus overview page, per lesson, and
per fixed top-level hub page (STATIC_PAGES below) -- read by
assets/js/search.js.

Usage:
    python3 scripts/build_exercise_index.py
"""
import json
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_chrome  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ITEMS_OUT_PATH = REPO_ROOT / "assets" / "data" / "exercise-items-index.json"
SEARCH_OUT_PATH = REPO_ROOT / "assets" / "data" / "search-index.json"

LEVEL_SLUGS = {code: slug for code, name, slug in site_chrome.LEVELS}
LEVEL_NAMES = {code: name for code, name, slug in site_chrome.LEVELS}
LEVEL_DESC = site_chrome.LEVEL_DESC

# Fixed top-level hub pages -- title/desc/type curated by hand since
# there's no per-lesson JSON backing them.
STATIC_PAGES = [
    {"title": "Exercitationes", "url": "exercitationes.html", "type": "exercise",
     "desc": "Exercitationes et lectiones ordine per omnes gradus, ad legendum et scribendum.",
     "keywords": ["practice", "lectio", "scriptio"]},
    {"title": "Examina Ficta", "url": "examina.html", "type": "mock",
     "desc": "Examina ficta imitantia probationes veras, per gradus.",
     "keywords": ["mock exam", "probatio"]},
    {"title": "Varia", "url": "varia.html", "type": "extra",
     "desc": "Res additiciae: proverbia, mythologia, historia Romana, et plura.",
     "keywords": ["extras", "proverbia", "mythologia"]},
    {"title": "Lexicon", "url": "lexicon.html", "type": "extra",
     "desc": "Verba in lexicis praecipuis Latinis quaere: Logeion, Perseus, Victionarium.",
     "keywords": ["dictionary", "vocabularium"]},
    {"title": "Probatio Praeliminaris", "url": "probatio.html", "type": "extra",
     "desc": "Probatio difficilis quae gradum aptum tibi commendat.",
     "keywords": ["placement test", "gradus initialis"]},
    {"title": "Iter Meum", "url": "iter.html", "type": "extra",
     "desc": "Progressus tuus: PE, series dierum, et insignia.",
     "keywords": ["progress", "xp", "insignia"]},
    {"title": "Recognitio Hodierna", "url": "hodie.html", "type": "extra",
     "desc": "Exercitationes ad memoriam confirmandam, secundum repetitionem distributam.",
     "keywords": ["review", "spaced repetition"]},
    {"title": "Verba Irregularia", "url": "verba-irregularia.html", "type": "grammar",
     "desc": "Sum, possum, eo, fero, volo/nolo/malo, fio: conspectus plenus.",
     "keywords": ["irregular verbs", "sum", "possum", "fero", "eo"]},
]


def lesson_url(level: str, lesson_id: str) -> str:
    slug = LEVEL_SLUGS[level]
    id_prefix = level.lower() + "-"  # lesson ids use the level CODE prefix (i-, ii-...), not the slug
    file_slug = lesson_id[len(id_prefix):] if lesson_id.startswith(id_prefix) else lesson_id
    return f"gradus/{slug}/{file_slug}.html"


def main():
    items_index = {}
    search_index = []
    skipped_no_answer = 0
    files = sorted(glob.glob(str(REPO_ROOT / "curriculum" / "*" / "*.json")))

    for level, slug in LEVEL_SLUGS.items():
        search_index.append({
            "title": f"Gradus {level} — {LEVEL_NAMES[level]}",
            "url": f"gradus/{slug}.html",
            "level": level,
            "type": "level",
            "desc": LEVEL_DESC[level],
            "keywords": [LEVEL_NAMES[level].lower()],
        })

    for fpath in files:
        lesson = json.loads(Path(fpath).read_text(encoding="utf-8"))
        level = lesson.get("level", "")
        lesson_id = lesson.get("id", "")
        title = lesson.get("title", "")
        subtitle = lesson.get("subtitle", "")
        url = lesson_url(level, lesson_id)

        search_index.append({
            "title": title,
            "url": url,
            "level": level,
            "type": "lesson",
            "desc": subtitle,
            "keywords": [lesson.get("strand", "")],
        })

        for ex in lesson.get("exercises", []):
            ex_type = ex.get("type")
            for item in ex.get("items", []):
                item_id = item.get("id")
                if not item_id:
                    continue
                has_checkable_answer = (
                    "answers" in item or "answer" in item
                    or (ex_type == "matching" and "pairs" in item)
                    or (ex_type == "ordering" and "words" in item)
                    or (ex_type == "multiple-choice" and "answerIndex" in item)
                )
                if not has_checkable_answer:
                    skipped_no_answer += 1
                    continue
                entry = dict(item)
                entry["exerciseType"] = ex_type
                entry["exerciseId"] = ex.get("id")
                entry["exerciseTitle"] = ex.get("title")
                entry["exerciseInstructions"] = ex.get("instructions")
                entry["lessonId"] = lesson_id
                entry["lessonTitle"] = title
                entry["level"] = level
                entry["lessonUrl"] = url
                items_index[item_id] = entry

    search_index.extend(STATIC_PAGES)

    ITEMS_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ITEMS_OUT_PATH.write_text(json.dumps(items_index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    SEARCH_OUT_PATH.write_text(json.dumps(search_index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"Indexed {len(items_index)} reviewable items from {len(files)} lessons "
          f"({skipped_no_answer} self-check-only items excluded) -> {ITEMS_OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"Search index: {len(search_index)} entries -> {SEARCH_OUT_PATH.relative_to(REPO_ROOT)}")

    # Per-level exercise-block counts, to keep assets/js/progress.js's
    # LEVEL_EXERCISE_COUNTS honest -- print only; that object is edited
    # by hand since it's JS, not generated.
    counts = {level: 0 for level in LEVEL_SLUGS}
    for fpath in files:
        lesson = json.loads(Path(fpath).read_text(encoding="utf-8"))
        counts[lesson.get("level", "")] = counts.get(lesson.get("level", ""), 0) + len(lesson.get("exercises", []))
    print("Exercise-block counts per level (lesson pages only, excludes level/test-yourself/placement pages):")
    for level in LEVEL_SLUGS:
        print(f"  {level}: {counts.get(level, 0)}")


if __name__ == "__main__":
    main()
