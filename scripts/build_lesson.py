#!/usr/bin/env python3
"""
Render one curriculum/{level}/{lesson-id}.json into gradus/{level}/{lesson-id}.html,
following the section structure (Proposita -> Explicatio -> Regulae ->
Exempla -> Errores Communes -> Exercitium -> Summarium -> Perge), using
the shared chrome from site_chrome.py.

Adapted from the sibling English-course project's scripts/build_lesson.py
(identical structure/pipeline) -- section labels and all generated copy
are Latin; there is no sourceMaterial/PDF concept in this course (every
lesson is authored directly against curriculum/SCHEMA.md, not converted
from a scanned document), so that section of the original is dropped.

Usage:
    python3 scripts/build_lesson.py curriculum/iv/perfectum-activum.json
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_chrome  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
REL = "../../"  # gradus/{level}/{lesson}.html -> repo root
NAV_MAP_PATH = Path(__file__).resolve().parent / "lesson_nav_map.json"

CHECK_SVG = '<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5L20 7"/></svg>'
ARROW_SVG = '<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>'

LEVEL_NAMES = {code: name for code, name, _slug in site_chrome.LEVELS}
LEVEL_SLUGS = {code: slug for code, name, slug in site_chrome.LEVELS}


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def page_header(lesson):
    return f"""<div class="page-header">
        {site_chrome.LAUREL_ROW}
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Gradus {lesson['level']} &middot; {esc(LEVEL_NAMES.get(lesson['level'], ''))}</p>
                <h1>{esc(lesson['title'])}</h1>
                <p class="page-header__lede">{esc(lesson['subtitle'])}</p>
            </div>
        </div>
    </div>"""


def toc(present_ids):
    labels = {
        "objectives": "Proposita", "explanation": "Explicatio", "rules": "Regulae",
        "examples": "Exempla", "mistakes": "Errores Communes", "practice": "Exercitium",
        "summary": "Summarium", "lesson-test-yourself": "Te Ipsum Proba",
    }
    links = "".join(f'<a href="#{a}">{labels[a]}</a>' for a in labels if a in present_ids)
    return f'<div class="level-toc"><div class="level-toc__inner">{links}</div></div>'


def objectives_section(lesson):
    items = "".join(f"<li>{CHECK_SVG}<span>{esc(o)}</span></li>" for o in lesson["objectives"])
    return f"""<section id="objectives" class="section section--tight" aria-labelledby="obj-heading">
        <div class="section__inner split">
            <div>
                <p class="eyebrow">Prooemium</p>
                <p style="font-size:var(--step-0);color:var(--color-text-muted);max-width:56ch;">{esc(lesson['content']['intro'])}</p>
            </div>
            <div class="card card--feature">
                <h2 id="obj-heading" style="font-size:var(--step-0);">Post hanc lectionem poteris&hellip;</h2>
                <ul class="objectives-list">{items}</ul>
            </div>
        </div>
    </section>"""


def explanation_section(lesson):
    c = lesson["content"]
    explanation = c.get("explanation")
    register = f'<div class="notice mt-lg"><strong>Nota</strong><p>{esc(c["registerNote"])}</p></div>' if c.get("registerNote") else ""
    if not explanation and not register:
        return ""
    if explanation:
        inner = explanation if "<" in explanation else f"<p>{esc(explanation)}</p>"
        body = f'<div class="prose">{inner}</div>'
    else:
        body = ""
    return f"""<section id="explanation" class="section section--surface" aria-labelledby="exp-heading">
        <div class="section__inner section__inner--narrow">
            <p class="eyebrow">Explicatio</p>
            <h2 id="exp-heading" class="visually-hidden">Explicatio</h2>
            {body}
            {register}
        </div>
    </section>"""


def rules_section(lesson):
    rules = lesson["content"].get("rules") or []
    if not rules:
        return ""
    blocks = "".join(f'<div class="card" style="margin-bottom:var(--space-md);"><h3>{esc(r["heading"])}</h3>{r["body"]}</div>' for r in rules)
    return f"""<section id="rules" class="section section--tight" aria-labelledby="rules-heading">
        <div class="section__inner">
            <p class="eyebrow">Regulae Grammaticae</p>
            <h2 id="rules-heading">Regulae</h2>
            {blocks}
        </div>
    </section>"""


def examples_section(lesson):
    items = "".join(
        f'<li><svg class="examples-list__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5L20 7"/></svg><span>{esc(e)}</span></li>'
        for e in lesson["content"]["examples"]
    )
    return f"""<section id="examples" class="section section--surface" aria-labelledby="ex-heading">
        <div class="section__inner">
            <p class="eyebrow">Exempla</p>
            <h2 id="ex-heading">Exempla in Usu</h2>
            <ul class="examples-list">{items}</ul>
        </div>
    </section>"""


def mistakes_section(lesson):
    if not lesson["content"].get("commonMistakes"):
        return ""
    cards = "".join(
        f"""<div class="mistake-card">
            <p class="mistake-card__wrong"><span class="badge badge--pdf" style="margin-right:.5em;">Vita</span>{esc(m['wrong'])}</p>
            <p class="mistake-card__right"><span class="badge badge--doc" style="margin-right:.5em;">Rectius</span>{esc(m['right'])}</p>
            <p class="mistake-card__why">{esc(m['why'])}</p>
        </div>"""
        for m in lesson["content"]["commonMistakes"]
    )
    return f"""<section id="mistakes" class="section section--tight" aria-labelledby="mist-heading">
        <div class="section__inner">
            <p class="eyebrow">Errores Communes</p>
            <h2 id="mist-heading">Cave</h2>
            <div class="mistakes-grid">{cards}</div>
        </div>
    </section>"""


def practice_section(lesson):
    blocks = "".join(
        f'<div class="exercise-block"><script type="application/json" class="exercise-data">{json.dumps(ex, ensure_ascii=False)}</script></div>'
        for ex in lesson["exercises"]
    )
    return f"""<section id="practice" class="section section--surface" aria-labelledby="practice-heading">
        <div class="section__inner">
            <p class="eyebrow">Exercitationes Interactivae</p>
            <h2 id="practice-heading">Exercitium</h2>
            <p style="color:var(--color-text-muted);margin-bottom:var(--space-md);max-width:60ch;">Confice quamque exercitationem, deinde <strong>Proba</strong> preme ut summam et explicationem cuiusque responsi videas.</p>
            {blocks}
        </div>
    </section>"""


def summary_section(lesson):
    items = "".join(f"<li>{esc(s)}</li>" for s in lesson["summary"])
    return f"""<section id="summary" class="section section--tight" aria-labelledby="sum-heading">
        <div class="section__inner section__inner--narrow">
            <p class="eyebrow">Summarium</p>
            <h2 id="sum-heading">Recognitio</h2>
            <ul class="summary-list">{items}</ul>
        </div>
    </section>"""


def test_yourself_section(lesson, level_slug, ty_anchor):
    if not ty_anchor:
        return ""
    return f"""<section id="lesson-test-yourself" class="section section--tight" aria-labelledby="lesson-ty-heading">
        <div class="section__inner section__inner--narrow" style="text-align:center;">
            <p class="eyebrow">Te Ipsum Proba</p>
            <h2 id="lesson-ty-heading">Visne scientiam tuam probare?</h2>
            <p style="color:var(--color-text-muted);max-width:56ch;margin:0 auto var(--space-md);">Confice totam recognitionem &ldquo;Te Ipsum Proba&rdquo; Gradus {lesson['level']} de hoc argumento &mdash; plures quaestiones, mixtae, cum responso statim.</p>
            <a class="btn btn--accent" href="test-yourself.html#{ty_anchor}">Te Ipsum Proba: {esc(lesson['title'])} {ARROW_SVG}</a>
        </div>
    </section>"""


def related_section(lesson, level_slug, prev_lesson, next_lesson):
    prev_link = (
        f'<a class="btn btn--ghost" href="{prev_lesson["slug"]}.html">{ARROW_SVG} Prior: {esc(prev_lesson["title"])}</a>'
        if prev_lesson else ""
    )
    next_link = (
        f'<a class="btn btn--accent" href="{next_lesson["slug"]}.html">Proximum: {esc(next_lesson["title"])} {ARROW_SVG}</a>'
        if next_lesson else ""
    )
    return f"""<section id="related" class="section section--surface" aria-labelledby="rel-heading">
        <div class="section__inner">
            <p class="eyebrow">Proximum</p>
            <h2 id="rel-heading">Perge</h2>
            <div class="lesson-nav">
                {prev_link}
                <a class="btn btn--ghost" href="../{level_slug}.html">Redi ad Gradum {lesson['level']}</a>
                {next_link}
            </div>
        </div>
    </section>"""


def build(lesson_path: Path):
    lesson = json.loads(lesson_path.read_text(encoding="utf-8"))
    level_slug = LEVEL_SLUGS[lesson["level"]]
    id_prefix = lesson["level"].lower() + "-"  # lesson ids use the level CODE prefix (i-, ii-...), not the slug
    lesson_slug = lesson["id"][len(id_prefix):] if lesson["id"].startswith(id_prefix) else lesson["id"]

    title = f"{lesson['title']} — Gradus {lesson['level']} — Lectiones Latinae"
    description = f"{lesson['title']}: {lesson['subtitle']}"[:300]
    breadcrumb = (
        f'<li><a href="{REL}index.html">Domus</a></li>'
        f'<li aria-current="page">Gradus</li>'
        f'<li><a href="../{level_slug}.html">Gradus {lesson["level"]}</a></li>'
        f'<li aria-current="page">{esc(lesson["title"])}</li>'
    )

    sections = {
        "objectives": objectives_section(lesson),
        "explanation": explanation_section(lesson),
        "rules": rules_section(lesson),
        "examples": examples_section(lesson),
        "mistakes": mistakes_section(lesson),
        "practice": practice_section(lesson),
        "summary": summary_section(lesson),
    }
    present_ids = [k for k, v in sections.items() if v]

    nav_map = json.loads(NAV_MAP_PATH.read_text(encoding="utf-8")) if NAV_MAP_PATH.exists() else {}
    nav_list = nav_map.get(level_slug, [])
    pos = next((i for i, l in enumerate(nav_list) if l["slug"] == lesson_slug), None)
    prev_lesson = nav_list[pos - 1] if pos is not None and pos > 0 else None
    next_lesson = nav_list[pos + 1] if pos is not None and pos < len(nav_list) - 1 else None
    ty_anchor = nav_list[pos]["ty"] if pos is not None else None
    toc_ids = present_ids + (["lesson-test-yourself"] if ty_anchor else [])

    out = []
    out.append(site_chrome.head(REL, title, description))
    out.append(site_chrome.header(REL, lesson["level"], breadcrumb))
    out.append(page_header(lesson))
    out.append(toc(toc_ids))
    for k in present_ids:
        out.append(sections[k])
    out.append(test_yourself_section(lesson, level_slug, ty_anchor))
    out.append(related_section(lesson, level_slug, prev_lesson, next_lesson))
    out.append(site_chrome.footer(REL))

    out_dir = REPO_ROOT / "gradus" / level_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{lesson_slug}.html"
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Built {out_path.relative_to(REPO_ROOT)}")
    return out_path


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        build(Path(arg))
