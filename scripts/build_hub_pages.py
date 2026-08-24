#!/usr/bin/env python3
"""
Build exercitationes.html, examina.html, and varia.html -- hand-curated
hub/extras pages with their own bespoke content that doesn't come from
curriculum/*.json. See build_static_pages.py for the sibling
iter.html/hodie.html/verba-irregularia.html.

Usage:
    python3 scripts/build_hub_pages.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_chrome  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
REL = ""
ARROW_SVG = '<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>'


def write(name, html):
    path = REPO_ROOT / name
    path.write_text(html, encoding="utf-8")
    print(f"Built {path.relative_to(REPO_ROOT)}")


def build_exercitationes():
    title = "Exercitationes — Lectiones Latinae"
    desc = "Omnes recognitiones Te Ipsum Proba, gradu post gradum, plus lectiones liberae extra ordinem."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Exercitationes</li>'

    cards = "".join(
        f"""<article class="lesson-card">
                    <span class="lesson-card__index" aria-hidden="true">{code}</span>
                    <h3><a class="lesson-card__title-link" href="gradus/{slug}/test-yourself.html">Gradus {code} &mdash; {name}</a></h3>
                    <p>{site_chrome.LEVEL_DESC[code]}</p>
                </article>"""
        for code, name, slug in site_chrome.LEVELS
    )

    passage_ii = "<p><strong>Marcus et Iulia in foro.</strong><br>Marcus in foro ambulat. Iulia quoque in foro est. “Salve, Marce!” inquit Iulia. “Salve, Iulia! Quo is?” respondet Marcus. “Ad macellum eo,” inquit Iulia, “quia panem et vinum emere volo. Tu quo is?” “Ego ad templum eo,” respondet Marcus, “quia deos orare volo.” Iulia et Marcus simul ambulant, et de familia sua loquuntur.</p>"

    passage_v = "<p><strong>Ex epistula ficta ad amicum.</strong><br>Cum Romam pervenissem, statim ad forum contendi, ut ea omnia viderem quae de urbe tanta audiveram. Erat ibi multitudo hominum ingens, quorum plerique negotia sua agebant; alii mercaturam faciebant, alii de re publica disputabant. Cui rei cum diu adstitissem, intellexi Romanos non solum viribus, sed etiam eloquentia et consilio orbem terrarum rexisse. Si quis rogaverit cur haec urbs tot annos steterit, respondebo: quia cives eius, quamvis inter se saepe dissentirent, patriam semper amaverunt.</p>"

    main = f"""<div class="page-header">
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Exercitium</p>
                <h1>Exercitationes</h1>
                <p class="page-header__lede">{desc}</p>
            </div>
        </div>
    </div>
<section id="te-ipsum-proba" class="section section--surface" aria-labelledby="ty-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Recognitiones Plenae</p>
                <h2 id="ty-heading">Te Ipsum Proba, per Gradum</h2>
                <p>Quaeque pagina colligit omnes exercitationes eius gradus, argumentum post argumentum, mixtas et prontas ad recognitionem.</p>
            </div>
            <div class="grid">{cards}</div>
        </div>
    </section>
<section id="lectiones-liberae" class="section" aria-labelledby="free-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Praeter Ordinem</p>
                <h2 id="free-heading">Lectiones Liberae</h2>
                <p>Duo textus extra, unus simplicior (Gradus II) et unus provectior (Gradus V), ad legendum quocumque tempore.</p>
            </div>
            <div class="card" style="margin-bottom:var(--space-lg);">
                <h3>Marcus et Iulia in Foro (Gradus II)</h3>
                <div class="reading-passage">{passage_ii}</div>
                <div style="margin-top:var(--space-md);">
                    <div class="exercise-block"><script type="application/json" class="exercise-data">{json.dumps({
                        "id": "extra-ii-forum-rc", "type": "reading-comprehension", "title": "Comprehensio: In Foro",
                        "instructions": "Lege textum supra, deinde responde.",
                        "items": [
                            {"id": "extra-ii-1", "prompt": "Quo it Iulia?", "options": ["ad templum", "ad macellum", "ad domum"], "answerIndex": 1, "explanation": "‘Ad macellum eo’ dicit Iulia."},
                            {"id": "extra-ii-2", "prompt": "Cur Iulia ad macellum it?", "options": ["ut amicos videat", "ut panem et vinum emat", "ut libros legat"], "answerIndex": 1, "explanation": "‘Panem et vinum emere volo’."},
                            {"id": "extra-ii-3", "prompt": "Quo it Marcus?", "options": ["ad forum", "ad macellum", "ad templum"], "answerIndex": 2, "explanation": "Marcus ‘ad templum eo’ dicit, ‘quia deos orare volo’."}
                        ]
                    }, ensure_ascii=False)}</script></div>
                </div>
            </div>
            <div class="card">
                <h3>Ex Epistula Ficta (Gradus V)</h3>
                <div class="reading-passage">{passage_v}</div>
                <div style="margin-top:var(--space-md);">
                    <div class="exercise-block"><script type="application/json" class="exercise-data">{json.dumps({
                        "id": "extra-v-epistula-rc", "type": "reading-comprehension", "title": "Comprehensio: Epistula",
                        "instructions": "Lege textum supra, deinde responde.",
                        "items": [
                            {"id": "extra-v-1", "prompt": "Quo primum contendit scriptor epistulae, postquam Romam pervenit?", "options": ["ad templum", "ad forum", "ad theatrum"], "answerIndex": 1, "explanation": "‘Statim ad forum contendi’."},
                            {"id": "extra-v-2", "prompt": "Secundum scriptorem, quibus rebus Romani orbem terrarum rexerunt?", "options": ["solis viribus", "viribus, eloquentia, et consilio", "sola fortuna"], "answerIndex": 1, "explanation": "‘Non solum viribus, sed etiam eloquentia et consilio’."},
                            {"id": "extra-v-3", "prompt": "Quae est ratio, secundum scriptorem, cur urbs tot annos steterit?", "options": ["cives semper inter se consenserunt", "cives, quamvis dissentirent, patriam amaverunt", "urbs numquam hostes habuit"], "answerIndex": 1, "explanation": "‘Cives eius, quamvis inter se saepe dissentirent, patriam semper amaverunt.’"}
                        ]
                    }, ensure_ascii=False)}</script></div>
                </div>
            </div>
        </div>
    </section>"""
    out = [site_chrome.head(REL, title, desc), site_chrome.header(REL, "", breadcrumb), main, site_chrome.footer(REL)]
    write("exercitationes.html", "\n".join(out))


def build_examina():
    title = "Examina Ficta — Lectiones Latinae"
    desc = "Examina ficta plena, imitantia probationem praeliminarem, cum clavibus responsorum."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Examina Ficta</li>'
    main = f"""<div class="page-header">
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Praxis Examinis</p>
                <h1>Examina Ficta</h1>
                <p class="page-header__lede">{desc}</p>
            </div>
        </div>
    </div>
<section class="section section--surface" aria-labelledby="exam-heading">
        <div class="section__inner section__inner--narrow">
            <div class="section__head">
                <p class="eyebrow">Nunc Praesto</p>
                <h2 id="exam-heading">Probatio Praeliminaris</h2>
                <p>Antequam examina ficta separata ad quemque gradum addantur, incipe cum nostra <strong>Probatione Praeliminari</strong> &mdash; ipsa iam structuram examinis plene simulat: triginta quaestiones, difficultate crescente, per omnes septem gradus.</p>
            </div>
            <a class="btn btn--accent" href="probatio.html">Incipe Probationem Praeliminarem {ARROW_SVG}</a>
        </div>
    </section>
<section class="section" aria-labelledby="soon-heading">
        <div class="section__inner section__inner--narrow">
            <p class="eyebrow">Mox</p>
            <h2 id="soon-heading" class="visually-hidden">Ventura</h2>
            <div class="notice"><svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>Examina ficta propria ad singulos gradus (I&ndash;VII) adduntur incrementaliter &mdash; interim, quaeque pagina <a href="exercitationes.html">Te Ipsum Proba</a> iam functionat ut recognitio plena illius gradus.</div>
        </div>
    </section>"""
    out = [site_chrome.head(REL, title, desc), site_chrome.header(REL, "", breadcrumb), main, site_chrome.footer(REL)]
    write("examina.html", "\n".join(out))


def build_varia():
    title = "Varia — Lectiones Latinae"
    desc = "Res additiciae de cultu Romano: calendarium, proverbia, et prima mythologia."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Varia</li>'

    proverbs = [
        ("Errāre hūmānum est.", "To err is human.", "Sēneca (attribūtum), lātē citātum."),
        ("Carpe diem.", "Seize the day.", "Horātius, Odēs 1.11."),
        ("Cōgitō, ergō sum.", "I think, therefore I am.", "Dēscartes (Latīnē, saeculō XVII — nōn antīquum, sed omnipraesēns)."),
        ("Alea iacta est.", "The die is cast.", "Attribūtum Caesarī, Rubicōnem trānseuntī."),
        ("Vēnī, vīdī, vīcī.", "I came, I saw, I conquered.", "Caesar, dē victōriā apud Zēlam."),
        ("Sī vīs pācem, parā bellum.", "If you want peace, prepare for war.", "Vegetius (adaptātum)."),
        ("Tempus fugit.", "Time flies.", "Vergilius, Geōrgica 3.284 (fugit inreparābile tempus)."),
        ("Ā fonte pūrō pūra dēfluit aqua.", "From a pure source flows pure water.", "Prōverbium medīaevāle."),
        ("Nōn scholae, sed vītae discimus.", "We learn not for school, but for life.", "Sēneca (adaptātum; orīginem inversam habet)."),
        ("Amor vincit omnia.", "Love conquers all.", "Vergilius, Eclogae 10.69 (omnia vincit amor)."),
    ]
    proverb_rows = "".join(
        f"<tr><td><strong>{la}</strong></td><td>{en}</td><td class=\"text-muted\">{src}</td></tr>"
        for la, en, src in proverbs
    )

    calendar = [
        ("Kalendae", "1st of the month"),
        ("Nōnae", "5th or 7th of the month (depending on month)"),
        ("Īdūs", "13th or 15th of the month"),
        ("a.C.n. (ante Christum nātum)", "BC / BCE"),
        ("p.C.n. (post Christum nātum)", "AD / CE"),
        ("A.U.C. (ab urbe conditā)", "from the founding of the city [of Rome], 753 BC"),
    ]
    cal_rows = "".join(f"<tr><td><strong>{a}</strong></td><td>{b}</td></tr>" for a, b in calendar)

    main = f"""<div class="page-header">
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Praeter Curriculum</p>
                <h1>Varia</h1>
                <p class="page-header__lede">{desc}</p>
            </div>
        </div>
    </div>
<section id="proverbia" class="section section--surface" aria-labelledby="prov-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Sapientia Antiqua</p>
                <h2 id="prov-heading">Decem Proverbia Latina</h2>
                <p>Locūtiōnēs quae hodiē quoque, in linguīs modernīs, adhibentur.</p>
            </div>
            <div class="table-scroll">
                <table class="ref-table">
                    <thead><tr><th>Latīnē</th><th>Anglicē</th><th>Fōns</th></tr></thead>
                    <tbody>{proverb_rows}</tbody>
                </table>
            </div>
            <div style="margin-top:var(--space-md);"><div class="exercise-block"><script type="application/json" class="exercise-data">{json.dumps({
                "id": "varia-proverbia-match", "type": "matching", "title": "Iunge Proverbium cum Versione",
                "items": [{"id": "varia-p1", "pairs": [
                    {"left": "Errāre hūmānum est.", "right": "To err is human."},
                    {"left": "Carpe diem.", "right": "Seize the day."},
                    {"left": "Alea iacta est.", "right": "The die is cast."},
                    {"left": "Vēnī, vīdī, vīcī.", "right": "I came, I saw, I conquered."},
                    {"left": "Tempus fugit.", "right": "Time flies."}
                ], "explanation": "Haec proverbia adhuc hodie in multis linguis citantur."}]
            }, ensure_ascii=False)}</script></div></div>
        </div>
    </section>
<section id="calendarium" class="section" aria-labelledby="cal-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Tempus Rōmānum</p>
                <h2 id="cal-heading">Calendārium Rōmānum</h2>
                <p>Rōmānī diēs mēnsis nōn per numerōs currentēs (1, 2, 3...) computābant, sed retrō ā tribus punctīs fīxīs.</p>
            </div>
            <div class="table-scroll">
                <table class="ref-table">
                    <thead><tr><th>Terminus</th><th>Significātiō</th></tr></thead>
                    <tbody>{cal_rows}</tbody>
                </table>
            </div>
        </div>
    </section>
<section id="mythologia" class="section section--surface" aria-labelledby="myth-heading">
        <div class="section__inner section__inner--narrow">
            <p class="eyebrow">Prīma Fābula</p>
            <h2 id="myth-heading">Deī Praecipuī</h2>
            <p><strong>Iuppiter</strong> (rēx deōrum), <strong>Iūnō</strong> (rēgīna, coniūnx Iovis), <strong>Neptūnus</strong> (deus maris), <strong>Plūtō</strong> (deus Īnferōrum), <strong>Minerva</strong> (dea sapientiae), <strong>Mārs</strong> (deus bellī), <strong>Venus</strong> (dea amōris), <strong>Apollō</strong> (deus sōlis et artium), <strong>Diāna</strong> (dea lūnae et vēnātiōnis), <strong>Mercurius</strong> (nūntius deōrum), <strong>Vulcānus</strong> (deus ignis), <strong>Vesta</strong> (dea focī). Hī duodecim "Diī Cōnsentēs" in Gradū VII, cum carminibus Ovidiī et Vergiliī, plēnius occurrent.</p>
        </div>
    </section>"""
    out = [site_chrome.head(REL, title, desc), site_chrome.header(REL, "", breadcrumb), main, site_chrome.footer(REL)]
    write("varia.html", "\n".join(out))


if __name__ == "__main__":
    build_exercitationes()
    build_examina()
    build_varia()
