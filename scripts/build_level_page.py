#!/usr/bin/env python3
"""
Build gradus/{slug}.html (the level overview page) and
gradus/{slug}/test-yourself.html (a full "Te Ipsum Proba" review,
aggregating every lesson's own exercise blocks under one topic section
per lesson) for one Gradus, from curriculum/index.json + curriculum/
{level-code}/*.json.

The Test-Yourself page deliberately re-embeds each lesson's exercise
blocks VERBATIM (same ids) rather than writing new ones -- this is what
lets assets/js/progress.js treat "already completed on its own lesson
page" and "completed here" as the same fact (see docs/gamification.md
"How page-completion is detected"), and what lets a topic's Test-Yourself
questions double as extra spaced-repetition material for hodie.html
without any duplicate bookkeeping.

Usage:
    python3 scripts/build_level_page.py I
    python3 scripts/build_level_page.py --all
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_chrome  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

ARROW_SVG = '<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>'
QUIZ_SVG = '<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="15" r="6"/><path d="m9 10-3-7"/><path d="m15 10 3-7"/><path d="M9.5 15.5 12 17l2.5-1.5"/></svg>'

ROMAN_VALUES = [
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def to_roman(n):
    out = []
    for value, sym in ROMAN_VALUES:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def esc(s):
    import html
    return html.escape(s, quote=False)


def load_lessons(level_key):
    idx = json.loads((REPO_ROOT / "curriculum" / "index.json").read_text(encoding="utf-8"))
    entries = idx["levels"][level_key]["units"][0]["lessons"]
    lessons = []
    for entry in entries:
        path = REPO_ROOT / "curriculum" / level_key.lower() / f"{entry['id'][len(level_key.lower())+1:]}.json"
        if not path.exists():
            continue
        lessons.append(json.loads(path.read_text(encoding="utf-8")))
    return lessons


def build_overview(level_key, level_name, slug, lessons):
    rel = "../"
    breadcrumb = (
        f'<li><a href="{rel}index.html">Domus</a></li>'
        f'<li aria-current="page">Gradus</li>'
        f'<li aria-current="page">Gradus {level_key} &mdash; {esc(level_name)}</li>'
    )
    title = f"Gradus {level_key} — {level_name} — Lectiones Latinae"
    description = site_chrome.LEVEL_DESC.get(level_key, "")[:300]

    cards = []
    for i, lesson in enumerate(lessons, start=1):
        lesson_slug = lesson["id"][len(level_key.lower()) + 1:]
        cards.append(f"""<article class="lesson-card">
                    <span class="lesson-card__index" aria-hidden="true">{to_roman(i)}</span>
                    <h3><a class="lesson-card__title-link" href="{slug}/{lesson_slug}.html">{esc(lesson['title'])}</a></h3>
                    <p>{esc(lesson['subtitle'])}</p>
                    </article>""")

    out = []
    out.append(site_chrome.head(rel, title, description))
    out.append(site_chrome.header(rel, level_key, breadcrumb))
    out.append(f"""<div class="page-header">
        {site_chrome.LAUREL_ROW}
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">{esc(site_chrome.LEVEL_EYEBROW.get(level_key, ''))}</p>
                <h1>Gradus {level_key} &mdash; {esc(level_name)}</h1>
                <p class="page-header__lede">{esc(description)}</p>
            </div>
        </div>
    </div>
    <div class="level-toc" data-scrollspy>
        <div class="level-toc__inner">
            <a href="#lectiones">Lectiones</a><a href="#te-ipsum-proba">Te Ipsum Proba</a>
        </div>
    </div>
    <section id="lectiones" class="section section--surface" aria-labelledby="lect-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Gradus {level_key}</p>
                <h2 id="lect-heading">Lectiones</h2>
                <p>{len(lessons)} lectiones, ordine &mdash; quaeque super priorem aedificat.</p>
            </div>
            <div class="grid">{''.join(cards)}</div>
        </div>
    </section>
    <section id="te-ipsum-proba" class="section section--tight" aria-labelledby="ty-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Gradus {level_key}</p>
                <h2 id="ty-heading">Te Ipsum Proba</h2>
                <p>Recognitio plena, unum argumentum ex quoque lectione &mdash; regulae, exempla, et exercitationes interactivae iterum, mixtae.</p>
            </div>
            <a class="btn btn--accent" href="{slug}/test-yourself.html">{QUIZ_SVG}Incipe probationem</a>
        </div>
    </section>""")
    out.append(site_chrome.footer(rel))

    out_path = REPO_ROOT / "gradus" / f"{slug}.html"
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Built {out_path.relative_to(REPO_ROOT)}")


def build_test_yourself(level_key, level_name, slug, lessons):
    rel = "../../"
    breadcrumb = (
        f'<li><a href="{rel}index.html">Domus</a></li>'
        f'<li aria-current="page">Gradus</li>'
        f'<li><a href="../{slug}.html">Gradus {level_key}</a></li>'
        f'<li aria-current="page">Te Ipsum Proba</li>'
    )
    title = f"Te Ipsum Proba — Gradus {level_key} — Lectiones Latinae"
    description = f"Recognitio plena Gradus {level_key} ({level_name}): omnia argumenta, omnes exercitationes, cum responso statim."

    toc_links = "".join(
        f'<a href="#{lesson["id"][len(level_key.lower())+1:]}">{esc(lesson["title"])}</a>' for lesson in lessons
    )

    sections = []
    for lesson in lessons:
        lesson_slug = lesson["id"][len(level_key.lower()) + 1:]
        blocks = "".join(
            f'<div class="exercise-block"><script type="application/json" class="exercise-data">{json.dumps(ex, ensure_ascii=False)}</script></div>'
            for ex in lesson["exercises"]
        )
        sections.append(f"""<section id="{lesson_slug}" class="section section--tight ty-topic" aria-labelledby="ty-{lesson_slug}-h">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Gradus {level_key}</p>
                <h2 id="ty-{lesson_slug}-h">{esc(lesson['title'])}</h2>
                <p>{esc(lesson['subtitle'])}</p>
            </div>
            {blocks}
        </div>
    </section>""")

    level_idx = next(i for i, (code, _n, _s) in enumerate(site_chrome.LEVELS) if code == level_key)
    next_level = site_chrome.LEVELS[level_idx + 1] if level_idx + 1 < len(site_chrome.LEVELS) else None
    next_link = (
        f'<a class="btn btn--accent" href="{rel}gradus/{next_level[2]}.html">Proximum: Gradus {next_level[0]} &mdash; {esc(next_level[1])} {ARROW_SVG}</a>'
        if next_level else ""
    )

    out = []
    out.append(site_chrome.head(rel, title, description))
    out.append(site_chrome.header(rel, level_key, breadcrumb))
    out.append(f"""<div class="page-header">
        {site_chrome.LAUREL_ROW}
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Recognitio Plena</p>
                <h1>Gradus {level_key}: Te Ipsum Proba</h1>
                <p class="page-header__lede">{esc(description)}</p>
            </div>
        </div>
    </div>
    <div class="level-toc" data-scrollspy>
        <div class="level-toc__inner">{toc_links}</div>
    </div>
    {''.join(sections)}
    <section id="bottom" class="section section--surface">
        <div class="section__inner" style="text-align:center;">
            <p class="eyebrow">Fīnis</p>
            <h2>Ad hunc locum pervēnistī!</h2>
            <div class="lesson-nav">
                <a class="btn btn--ghost" href="../{slug}.html">{ARROW_SVG} Redi ad Gradum {level_key}</a>
                {next_link}
            </div>
        </div>
    </section>""")
    out.append(site_chrome.footer(rel))

    out_dir = REPO_ROOT / "gradus" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "test-yourself.html"
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Built {out_path.relative_to(REPO_ROOT)}")


def build(level_key):
    level_name, slug = next((n, s) for c, n, s in site_chrome.LEVELS if c == level_key)
    lessons = load_lessons(level_key)
    if not lessons:
        print(f"Gradus {level_key}: no lesson JSON found yet, skipping.")
        return
    build_overview(level_key, level_name, slug, lessons)
    build_test_yourself(level_key, level_name, slug, lessons)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args == ["--all"]:
        for code, _n, _s in site_chrome.LEVELS:
            build(code)
    else:
        for a in args:
            build(a.upper())
