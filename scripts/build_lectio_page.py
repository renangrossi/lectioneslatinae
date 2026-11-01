#!/usr/bin/env python3
"""
Render content/lectiones/{level}/{slug}.json into lectiones/{level}/{slug}.html,
and build the lectiones.html hub.

    python3 scripts/build_lectio_page.py                      # every lectio + hub
    python3 scripts/build_lectio_page.py progressus/dies-in-foro
    python3 scripts/build_lectio_page.py --hub                # hub only

A lectio page carries either a narrated audio player or an embedded video,
decided by the source's "media.kind" -- see lectiones_common for the schema.
"""
import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lectiones_common as lc
import site_chrome

REL = "../../"

CHECK_SVG = ('<svg class="objectives-list__icon" viewBox="0 0 24 24" fill="none" '
             'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
             'stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5L20 7"/></svg>')
BOOK_SVG = ('<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
            '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>')
PLAY_SVG = ('<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4Z"/></svg>')


def esc(s):
    return html.escape(s, quote=False)


# ---------------------------------------------------------------- vocabulary

# Latin is inflected, so a glossary headword almost never appears in the
# passage in its dictionary form: "mercātor, -ōris" turns up as "mercātōrēs",
# "taberna, -ae" as "tabernās". English got away with matching surface forms
# directly; here the stem has to be recovered and the endings allowed for.
#
# The stem comes from the genitive the glossary already gives (third
# declension needs it: mercātor -> mercātōr-), and matching is anchored to
# whole words against a closed inventory of endings. Anchoring is what keeps
# a short stem honest: "forum, -ī" yields the stem "for", which would be a
# disaster as a substring match (fortis, fortūna, forma) but is safe as
# for + {um, ī, ō, a, īs, ōrum}.
#
# A term whose forms this cannot work out still appears in the glossary; it
# just is not highlighted inline. Silently highlighting the wrong word is a
# worse failure than not highlighting, so when in doubt this does nothing.
# Any term can override the guesswork with an explicit "forms": [...] list.

ENDINGS = [
    "", "a", "ae", "am", "arum", "as",                         # 1st
    "us", "i", "o", "um", "orum", "is", "os", "e",             # 2nd
    "er", "ri", "ro", "rum", "ris",
    "s", "em", "es", "ium", "ibus", "ia", "ium", "u",          # 3rd
    "us", "ui", "ua", "uum", "ubus",                           # 4th
    "ei", "erum", "ebus",                                      # 5th
    "or", "oris", "ori", "orem", "ores", "orum", "oribus",     # 3rd -or
    "io", "ionis", "ioni", "ionem", "iones", "ionum", "ionibus",
    # adjective and participle endings
    "ae", "ī", "ōs", "ās", "um", "am", "o", "a",
    # common verb endings (present/imperfect/perfect systems)
    "o", "s", "t", "mus", "tis", "nt", "re", "ri", "bam", "bat", "bant",
    "i", "isti", "it", "imus", "istis", "erunt", "tur", "ntur", "ns", "ntis",
    "turus", "tus", "ta", "tum", "sus", "sa", "sum",
]


# A LENGTH-PRESERVING macron fold. This distinction matters: the stems are
# macron-free ("mercat"), but the passage is not ("mercātōrēs"), so matching
# has to happen against a folded copy of the text. Because this maps one
# character to exactly one character, an offset in the folded copy is the
# same offset in the original -- which is what lets annotate() search the
# folded text and splice the markup into the real text. (The first version
# searched the unfolded text with folded stems and matched almost nothing.)
FOLD_1TO1 = str.maketrans({
    "ā": "a", "ē": "e", "ī": "i", "ō": "o", "ū": "u", "ȳ": "y",
    "Ā": "A", "Ē": "E", "Ī": "I", "Ō": "O", "Ū": "U", "Ȳ": "Y",
})


def fold_macrons(s):
    return s.translate(FOLD_1TO1)


def strip_macrons(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.replace("ā", "a")
                   .replace("ē", "e").replace("ī", "i").replace("ō", "o")
                   .replace("ū", "u").replace("ȳ", "y"))
                   if not unicodedata.combining(c))


HEADWORD_RE = re.compile(r"^([^,(\s]+)")

# Latin dictionary convention abbreviates the later principal parts, and how
# much of the headword they replace is NOT recoverable from the abbreviation:
#
#   cūstōs, -ōdis      genitive cūstōdis     stem cūstōd-   (replaces "ōs")
#   superstes, -itis   genitive superstitis  stem superstit- (replaces "es")
#   opprimō, -pressī   perfect  oppressī     stem oppress-  (replaces "rimō")
#
# A heuristic that strips a fixed set of endings gets all three wrong -- the
# first attempt produced "custood", "supersteit" and missed "oppressit"
# entirely. So instead of guessing, generate EVERY truncation of the
# headword joined to the abbreviation's stem and let the passage decide:
# a wrong candidate like "custosod" is a nonsense string that matches
# nothing, while the right one matches. The text is the disambiguator.
GEN_ENDINGS = ("oris", "onis", "inis", "itis", "odis", "eris", "udis", "atis",
               "is", "ae", "i", "us", "ei")


def _abbrev_candidates(nom, suffix):
    """Truncation+suffix-stem candidates for an abbreviated principal part."""
    body = suffix.lstrip("-")
    for end in GEN_ENDINGS:
        if body.endswith(end) and len(body) > len(end):
            body = body[: -len(end)]
            break
    else:
        body = re.sub(r"(i|isse|re|sse)$", "", body)
    if len(body) < 2:
        return []
    out = []
    for cut in range(len(nom), 1, -1):
        cand = nom[:cut] + body
        if len(cand) >= 4:
            out.append(cand)
    return out


def term_stems(term):
    """Candidate stems for a glossary term, macron-stripped and lowercased.

    Deliberately over-generates. A stem that is not really a stem matches
    nothing, whereas a missing stem silently loses a highlight -- so the
    bias is towards offering more candidates and letting the text filter."""
    head = HEADWORD_RE.match(term.strip())
    if not head:
        return []
    nom = strip_macrons(head.group(1)).lower()
    parts = [strip_macrons(p.strip()).lower()
             for p in re.split(r"[,;]", re.sub(r"\([^)]*\)", "", term))
             if p.strip()]
    stems = {nom}
    for p in parts[1:]:
        if p.startswith("-"):
            stems.update(_abbrev_candidates(nom, p))
        elif len(p) > 2:
            # a principal part written out in full ("as, assis")
            stems.add(p)
            stems.add(re.sub(r"(oris|onis|inis|itis|eris|is|ei|us|ae|i)$", "", p))
    # bare stem of the nominative, as a fallback
    stems.add(re.sub(r"(us|um|ae|a|is|es|e|os|or|o)$", "", nom))
    return sorted({x for x in stems if len(x) >= 3}, key=len, reverse=True)


def surface_re(term, forms=None):
    if forms:
        alts = sorted((strip_macrons(f).lower() for f in forms), key=len, reverse=True)
    else:
        stems = term_stems(term)
        if not stems:
            return None
        ends = sorted(set(ENDINGS), key=len, reverse=True)
        alts = [f"{re.escape(s)}(?:{'|'.join(re.escape(e) for e in ends if e)})?"
                for s in stems]
    if not alts:
        return None
    return re.compile(r"(?<![\wĀ-ſ])(" + "|".join(alts) +
                      r")(?![\wĀ-ſ])", re.IGNORECASE)


def annotate(paragraphs, vocabulary):
    """Wrap the first occurrence of each glossary term in a vocab-term span.

    First occurrence only: a passage peppered with the same highlight is
    noise, and the point is to teach the word once, where the reader first
    meets it. Returns (html_paragraphs, matched_term_count)."""
    pending = []
    for n, v in enumerate(vocabulary):
        rx = surface_re(v["term"], v.get("forms"))
        if rx:
            pending.append((n, rx, v))

    out, matched = [], 0
    for para in paragraphs:
        # escape first, then splice spans in, so a definition cannot inject markup
        text = esc(para)
        haystack = fold_macrons(text)   # same length as `text`; see FOLD_1TO1
        spans = []
        for n, rx, v in list(pending):
            # never match inside markup we have already inserted
            for m in rx.finditer(haystack):
                if any(a <= m.start() < b for a, b, _ in spans):
                    continue
                spans.append((m.start(), m.end(), (n, v, m.group(0))))
                pending.remove((n, rx, v))
                matched += 1
                break
        for start, end, (n, v, word) in sorted(spans, reverse=True):
            tag = (f'<span class="vocab-term" tabindex="0" role="note" '
                   f'aria-describedby="vocab-{n}" '
                   f'data-definition="{html.escape(v["definition"], quote=True)}">'
                   f'{word}</span>')
            text = text[:start] + tag + text[end:]
        out.append(text)
    return out, matched


def glossary(vocabulary):
    items = "".join(
        f'<li id="vocab-{n}"><strong>{esc(v["term"])}</strong> '
        f'<span class="reading-glossary__def">{esc(v["definition"])}</span></li>'
        for n, v in enumerate(vocabulary))
    return (f'<div class="reading-glossary"><h2 class="reading-glossary__heading">'
            f'Vocabula Praecipua</h2><ul class="reading-glossary__list">{items}</ul></div>')


# ---------------------------------------------------------------------- media

def media_block(d, level, slug):
    m = d.get("media") or {}
    kind = m.get("kind", "audio")
    if kind == "video":
        vid = m["youtube"]
        title = esc(m.get("title", "Vīdeō"))
        note = m.get("note")
        note_html = f'<div class="notice lectio-media__note"><strong>Nota</strong><p>{note}</p></div>' if note else ""
        label = ("Haec pagina <strong>transcrīptiōnem</strong> vīdeī continet."
                 if m.get("transcript") else
                 "Lectio īnfrā nōn est transcrīptiō vīdeī, sed textus comes.")
        return f"""<div class="lectio-media lectio-media--video">
                <div class="lectio-video">
                    <iframe src="https://www.youtube-nocookie.com/embed/{esc(vid)}"
                        title="{title}" loading="lazy" allowfullscreen
                        referrerpolicy="strict-origin-when-cross-origin"
                        allow="accelerometer; clipboard-write; encrypted-media; picture-in-picture"></iframe>
                </div>
                <p class="lectio-media__caption">{title} &mdash; <a href="https://www.youtube.com/watch?v={esc(vid)}" rel="noopener">in YouTube spectā</a>. {label}</p>
                {note_html}
            </div>"""
    href = lc.audio_href(level, slug, REL)
    return f"""<div class="lectio-media lectio-media--audio">
                <audio controls preload="metadata" src="{href}">
                    <p>Hoc programma audītum reddere nōn potest. <a href="{href}">MP3 dēpōne</a>.</p>
                </audio>
            </div>"""


# ---------------------------------------------------------------------- page

def page_header(d, level):
    return f"""<div class="page-header">
        {site_chrome.LAUREL_ROW}
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Lectiōnēs &middot; Gradus {lc.LEVEL_CODE[level]} &middot; {esc(lc.LEVEL_NAME[level])}</p>
                <h1>{esc(d['title'])}</h1>
                <p class="page-header__lede">{esc(d['subtitle'])}</p>
            </div>
        </div>
    </div>"""


def toc(ids):
    labels = {"lege": "Lege et Audī", "practice": "Exercitium", "colloquium": "Colloquium"}
    links = "".join(f'<a href="#{a}">{labels[a]}</a>' for a in labels if a in ids)
    return f'<div class="level-toc"><div class="level-toc__inner">{links}</div></div>'


def lege_section(d, level, slug):
    paras, _ = annotate(d["passage"], d.get("vocabulary") or [])
    body = "".join(f"<p>{p}</p>" for p in paras)
    pron = d.get("pronuntiatio")
    pron_html = (f'<div class="notice"><strong>Dē Pronūntiātiōne</strong><p>{esc(pron)}</p></div>'
                 if pron else "")
    intro = ("Audī et simul lege; deinde ipse alta vōce lege. Verbum "
             '<span class="vocab-term" tabindex="0" role="note" '
             'data-definition="Sīcut hoc — verba īnsignīta dēfīnītiōnem ferunt.">īnsignītum</span> '
             "tange ut significātiōnem videās.")
    if lc.media_kind(d) == "video":
        intro = ("Specta vīdeō, deinde lege lectiōnem alta vōce. Verbum "
                 '<span class="vocab-term" tabindex="0" role="note" '
                 'data-definition="Sīcut hoc — verba īnsignīta dēfīnītiōnem ferunt.">īnsignītum</span> '
                 "tange ut significātiōnem videās.")
    return f"""<section id="lege" class="section" aria-labelledby="lege-heading">
        <div class="section__inner">
            <h2 id="lege-heading" class="reading-title">{esc(d['title'])}</h2>
            <p class="reading-subtitle">{esc(d['subtitle'])}</p>
            <p class="reading-intro print-hidden">{intro}</p>
            {media_block(d, level, slug)}
            {pron_html}
            <div class="reading-passage">{body}</div>
            {glossary(d.get('vocabulary') or [])}
        </div>
    </section>"""


def practice_section(d):
    if not d.get("exercises"):
        return ""
    blocks = "".join(
        f'<div class="exercise-block"><script type="application/json" class="exercise-data">'
        f'{json.dumps(ex, ensure_ascii=False)}</script></div>' for ex in d["exercises"])
    return f"""<section id="practice" class="section section--surface" aria-labelledby="practice-heading">
        <div class="section__inner">
            <p class="eyebrow">Exercitationes Interactivae</p>
            <h2 id="practice-heading">Exercitium</h2>
            <p style="color:var(--color-text-muted);margin-bottom:var(--space-md);max-width:60ch;">Confice quamque exercitationem, deinde <strong>Proba</strong> preme ut summam et explicationem cuiusque responsi videas.</p>
            {blocks}
        </div>
    </section>"""


def colloquium_section(d):
    if not d.get("discussion"):
        return ""
    items = "".join(f"<li>{CHECK_SVG}<span>{esc(q)}</span></li>" for q in d["discussion"])
    return f"""<section id="colloquium" class="section section--tight" aria-labelledby="coll-heading">
        <div class="section__inner section__inner--narrow">
            <p class="eyebrow">Colloquium</p>
            <h2 id="coll-heading">Dē Hīs Cōgitā</h2>
            <ul class="objectives-list">{items}</ul>
        </div>
    </section>"""


def build(level, slug, d):
    ids = ["lege"] + (["practice"] if d.get("exercises") else []) \
                   + (["colloquium"] if d.get("discussion") else [])
    crumbs = (f'<li><a href="{REL}index.html">Domus</a></li>'
              f'<li><a href="{REL}lectiones.html">Lectiōnēs</a></li>'
              f'<li aria-current="page">{esc(d["title"])}</li>')
    html_out = (
        site_chrome.head(REL, f"{d['title']} — Lectiōnēs Latīnae", d["description"])
        + site_chrome.header(REL, lc.LEVEL_CODE[level], crumbs)
        + page_header(d, level) + toc(ids)
        + lege_section(d, level, slug) + practice_section(d) + colloquium_section(d)
        + site_chrome.footer(REL)
    )
    out = lc.page_path(level, slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    return out


# ----------------------------------------------------------------------- hub

def hub_card(level, slug, d):
    kind = lc.media_kind(d)
    chip = lc.ARGUMENTA.get(d.get("argumentum", ""), "")
    badge = ("Vīdeō" if kind == "video" else "Audītiō")
    icon = PLAY_SVG if kind == "video" else BOOK_SVG
    tags = f'argumentum:{d.get("argumentum","")} medium:{kind} gradus:{level}'
    return f"""<article class="lesson-card" id="lectio-{esc(slug)}" data-tags="{esc(tags)}">
            <span class="lesson-card__index" aria-hidden="true">{lc.LEVEL_CODE[level]}</span>
            <h3>{esc(d['title'])}</h3>
            <p>{esc(d['subtitle'])}</p>
            <p class="lesson-card__meta"><span class="badge">{badge}</span>{f'<span class="badge badge--doc">{esc(chip)}</span>' if chip else ''}</p>
            <div class="lesson-card__actions">
                <a class="btn btn--accent btn--small" href="lectiones/{esc(level)}/{esc(slug)}.html">{icon}{'Specta et Lege' if kind == 'video' else 'Lege et Audī'}</a>
            </div>
        </article>"""


def build_hub(sources):
    by_level = {}
    for lv, slug, d in sources:
        by_level.setdefault(lv, []).append((lv, slug, d))
    groups = ""
    for lv, code, name in lc.LEVELS:
        if lv not in by_level:
            continue
        cards = "".join(hub_card(*x) for x in by_level[lv])
        groups += (f'<h3 class="topic-group">Gradus {code} &middot; {esc(name)}</h3>'
                   f'<div class="grid">{cards}</div>')
    n = len(sources)
    desc = ("Bibliothēca lectiōnum Latīnārum: textūs classicī et adaptātī, "
            "cum audītiōne, vocābulīs et exercitātiōnibus, per gradūs dispositī.")
    crumbs = ('<li><a href="index.html">Domus</a></li>'
              '<li aria-current="page">Lectiōnēs</li>')
    page = (
        site_chrome.head("", "Lectiōnēs — Lectiōnēs Latīnae", desc)
        + site_chrome.header("", "", crumbs)
        + f"""<div class="page-header">
        {site_chrome.LAUREL_ROW}
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Bibliothēca Lectiōnum</p>
                <h1>Lectiōnēs</h1>
                <p class="page-header__lede">{esc(desc)}</p>
            </div>
        </div>
    </div>
    <section class="section" aria-labelledby="lectiones-heading">
        <div class="section__inner">
            <p class="eyebrow">{n} lectio{'nēs' if n != 1 else ''}</p>
            <h2 id="lectiones-heading">Textūs per Gradūs</h2>
            <p style="color:var(--color-text-muted);max-width:62ch;margin-bottom:var(--space-lg);">Quaeque lectio textum Latīnum cum audītiōne aut vīdeō, vocābulīs et exercitātiōnibus praebet. Omnēs textūs macrōnibus īnsignītī sunt, ut quantitās et accentus pateant.</p>
            {groups}
        </div>
    </section>"""
        + site_chrome.footer("")
    )
    lc.HUB_PAGE.write_text(page, encoding="utf-8")
    return lc.HUB_PAGE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="level/slug")
    ap.add_argument("--hub", action="store_true", help="build only lectiones.html")
    args = ap.parse_args()

    sources = list(lc.all_sources())
    if not sources:
        print("no content/lectiones/*/*.json found")
        return 1
    if not args.hub:
        for lv, slug, d in sources:
            if args.targets and f"{lv}/{slug}" not in args.targets:
                continue
            paras, matched = annotate(d["passage"], d.get("vocabulary") or [])
            out = build(lv, slug, d)
            total = len(d.get("vocabulary") or [])
            print(f"  wrote {out.relative_to(lc.REPO_ROOT)}  "
                  f"({matched}/{total} vocabula in textu reperta)")
    out = build_hub(sources)
    print(f"  wrote {out.relative_to(lc.REPO_ROOT)}  ({len(sources)} lectiones)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
