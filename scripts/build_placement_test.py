#!/usr/bin/env python3
"""
Build probatio.html — the hard, progressively-difficult placement test.

Three parts, all on one page:
  1. 30 multiple-choice items spanning Gradus I (pronunciation/sum) through
     Gradus VII (authentic-quote recognition), difficulty strictly
     increasing -- this is the primary score used for the recommendation
     table.
  2. A 5-item reading-comprehension block on a verbatim, cited excerpt of
     Caesar, De Bello Gallico 1.1 (cross-checked against thelatinlibrary.com
     -- see the citation in the passage itself) -- diagnostic for Gradus
     VI/VII readiness specifically.
  3. A 6-item typing/production block (decline/conjugate a real form from
     scratch, not just recognize one) -- diagnostic for whether active
     morphology production, not just recognition, is solid.

Usage:
    python3 scripts/build_placement_test.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_chrome  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
REL = ""
ARROW_SVG = '<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>'

MC_ITEMS = [
    ("pt1", "Quomodo pronuntiatur littera 'C' in verbo 'centum', secundum pronuntiationem restitutam?",
     ["ut Anglicum 's'", "ut Anglicum 'k'", "ut Anglicum 'ch'"], 1,
     "C semper sonat [k] in Latinitate Classica, numquam [s]."),
    ("pt2", "Quae littera NON erat in alphabeto Latino classico?",
     ["V", "J", "X"], 1, "J est additio medii aevi; Romani antiqui eam non habebant."),
    ("pt3", "Marcus ___ discipulus.", ["est", "sunt", "es"], 0, "Tertia persona singularis verbi 'sum' est 'est'."),
    ("pt4", "'Puellam video.' — casus verbi 'puellam' est:", ["nominativus", "accusativus", "dativus"], 1,
     "'Puellam' est obiectum directum verbi 'video': accusativus."),
    ("pt5", "Pluralis nominativus verbi 'servus' est:", ["servi", "servos", "servorum"], 0,
     "Secunda declinatio masculina: -us → -i in nominativo plurali."),
    ("pt6", "'Tres' Anglice significat:", ["two", "three", "four"], 1, "tres = three."),
    ("pt7", "'Puero librum do.' — 'puero' est casus:", ["accusativus", "genetivus", "dativus"], 2,
     "Obiectum indirectum ('to the boy'): dativus."),
    ("pt8", "Nominativus verbi cuius genetivus est 'urbis' est:", ["urbs", "urbi", "urbem"], 0,
     "urbs, urbis (f.) 'city' — tertia declinatio."),
    ("pt9", "Adiectivum rectum ut 'templum pulchrum' (n.) concordet:", ["pulcher", "pulchra", "pulchrum"], 2,
     "Adiectivum prima/secunda classis concordat in genere: templum (n.) → pulchrum."),
    ("pt10", "Comparativus (masc./fem.) adiectivi 'fortis, forte' est:", ["fortior", "fortissimus", "nulla forma exsistit"], 0,
     "fortior, fortius = comparativus; fortissimus = superlativus."),
    ("pt11", "'Ambulo ___ silvam' (through the forest) — quae praepositio, cum accusativo, apta est?",
     ["per", "cum", "ab"], 0, "'per' + accusativum = 'through'."),
    ("pt12", "'Femina ___ video pulchra est.' (The woman whom I see is beautiful) — elige formam rectam:",
     ["quae", "quam", "cuius"], 1, "Accusativus femininum singulare, obiectum directum 'video': quam."),
    ("pt13", "'Puer legebat' significat:", ["the boy reads", "the boy was reading", "the boy will read"], 1,
     "Imperfectum: actio continua in praeterito."),
    ("pt14", "Futurum verbi 'amo, amare' (1a persona) est:", ["amabo", "amavi", "amem"], 0,
     "Futurum primae coniugationis: -bo, -bis, -bit..."),
    ("pt15", "'Liber legitur' significat:", ["the book reads", "the book is being read", "the book will be read"], 1,
     "Praesens passivum: 'is being read'."),
    ("pt16", "Perfectum verbi 'video, videre, vidi' (1a persona) est:", ["video", "vidi", "videbam"], 1,
     "vidi = I saw / I have seen (perfectum)."),
    ("pt17", "'Puella cantans' significat:", ["the girl who sang", "the singing girl / the girl who is singing", "the girl about to sing"], 1,
     "Participium praesens activum: actio simultanea, -ns/-ntis."),
    ("pt18", "'Liber scriptus' significat:", ["the book that writes", "the written book / the book having been written", "the book that will write"], 1,
     "Participium perfectum passivum: actio completa, ante tempus principale."),
    ("pt19", "'Hortor' est verbum deponens; ergo forma 'hortor' significatione est:",
     ["passiva forma, sed significatione activa ('I urge')", "proprie passiva ('I am urged')", "impersonalis"], 0,
     "Verba deponentia formam passivam habent, sed significationem activam."),
    ("pt20", "'Venio ut te videam' significat:", ["I come because I see you", "I come in order to see you", "I come although I see you"], 1,
     "ut + coniunctivus = clausula finalis (purpose)."),
    ("pt21", "'Tam fessus erat ut dormiret' significat:", ["He was so tired that he fell asleep", "He was tired although he slept", "He was tired in order to sleep"], 0,
     "tam...ut + coniunctivus = clausula consecutiva (result)."),
    ("pt22", "'Dicit se fessum esse' significat:", ["He says that he is tired", "He says himself tired", "He orders himself to be tired"], 0,
     "Accusativus cum infinitivo (oratio obliqua): 'dicit se...esse' = 'he says that he...is'."),
    ("pt23", "'Urbe capta, cives fugerunt' significat:", ["The city having been captured, the citizens fled", "The city will be captured and the citizens flee", "Because the city captures, the citizens flee"], 0,
     "Ablativus absolutus: participium perfectum passivum + nomen ablativo, actio antecedens."),
    ("pt24", "'Liber legendus est' significat:", ["The book is reading", "The book must be read", "The book was read"], 1,
     "Gerundivum + sum = obligatio (coniugatio periphrastica passiva): 'must be read'."),
    ("pt25", "'Nescio quid faciat' significat:", ["I don't know what he is doing (indirect question)", "I don't know — what does he do?", "I know what he does"], 0,
     "Interrogatio obliqua: verbum in coniunctivo."),
    ("pt26", "'Si hoc scirem, tibi dicerem' significat:", ["If I know this, I tell you", "If I knew this (but I don't), I would tell you", "If I had known this, I would have told you"], 1,
     "Coniunctivus imperfectus in utraque clausula = condicio contraria facto in praesenti."),
    ("pt27", "'Cum fessus esset, tamen laboravit' significat:", ["When he was tired, he worked (simple time)", "Although he was tired, he nonetheless worked", "Since he was not tired, he worked"], 1,
     "cum + coniunctivus + tamen = clausula concessiva."),
    ("pt28", "'Nemo est tam senex qui se annum non putet posse vivere' (Cicero, De Senectute, adapted) significat approximate:",
     ["No one is so old that he thinks he cannot live one more year", "No one is so old that he doesn't think he can live one more year", "Everyone is old and thinks he cannot live"], 1,
     "Clausula relativa characteristica cum negatione dupla: 'no one so old that he does NOT think...'"),
    ("pt29", "In 'Gallia est omnis divisa in partes tres', ordo verborum Latinus:",
     ["semper respondet ordini Anglico (subiectum-verbum-obiectum)", "variat libere secundum emphasim, quia casus, non positio, significationem portat", "est semper verbum-ultimum sine exceptione"], 1,
     "Ordo verborum Latinus est flexibilis; casus grammaticus, non positio, indicat officium."),
    ("pt30", "'Arma virumque cano' sunt verba initialia cuius operis?",
     ["Ciceronis, In Catilinam", "Vergilii, Aeneidos", "Caesaris, De Bello Gallico"], 1,
     "Vergilius, Aeneis 1.1: 'Arma virumque cano, Troiae qui primus ab oris...'"),
]

RC_PASSAGE = (
    "<p><em>C. Iūlius Caesar, <strong>Commentāriī dē Bellō Gallicō</strong> 1.1 (verbatim, non adaptātum):</em></p>"
    "<p>&ldquo;Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae, aliam Aquitani, "
    "tertiam qui ipsorum lingua Celtae, nostra Galli appellantur. Hi omnes lingua, institutis, legibus "
    "inter se differunt. Gallos ab Aquitanis Garumna flumen, a Belgis Matrona et Sequana dividit. "
    "Horum omnium fortissimi sunt Belgae, propterea quod a cultu atque humanitate provinciae longissime "
    "absunt.&rdquo;</p>"
)
RC_ITEMS = [
    ("rc1", "Secundum Caesarem, in quot partes divisa est Gallia?", ["duas", "tres", "quattuor"], 1,
     "'Gallia est omnis divisa in partes tres.'"),
    ("rc2", "Qui incolunt primam partem nominatam a Caesare?", ["Belgae", "Aquitani", "Celtae/Galli"], 0,
     "'quarum unam incolunt Belgae' — Belgae incolunt primam (unam) partem."),
    ("rc3", "Quid Gallos ab Aquitanis dividit?", ["mons", "flumen Garumna", "mare"], 1,
     "'Gallos ab Aquitanis Garumna flumen... dividit.'"),
    ("rc4", "Quibus rebus differunt inter se populi Galliae, secundum Caesarem?", ["lingua, institutis, legibus", "solo colore vestium", "numero tantum civium"], 0,
     "'Hi omnes lingua, institutis, legibus inter se differunt.'"),
    ("rc5", "Qui fortissimi omnium habentur, secundum hunc textum?", ["Aquitani", "Belgae", "Celtae"], 1,
     "'Horum omnium fortissimi sunt Belgae.'"),
]

PROD_ITEMS = [
    ("prod1", "Scribe accusativum singularem verbi 'puella, -ae' (f.).", "puellam", "puellam ← puella + -am (prima declinatio)."),
    ("prod2", "Scribe genetivum pluralem verbi 'rex, regis' (m.).", "regum", "regum ← tertia declinatio, genetivus pluralis -um."),
    ("prod3", "Scribe perfectum, prima persona singularis, verbi 'facio, facere'.", "feci", "feci ← perfectum irregulare (radix mutata) verbi facio."),
    ("prod4", "Scribe coniunctivum praesentis activi, prima persona singularis, verbi 'sum, esse'.", "sim", "sim ← coniunctivus praesens irregularis verbi sum."),
    ("prod5", "Scribe ablativum singularem verbi 'tempus, temporis' (n.).", "tempore", "tempore ← tertia declinatio neutra, ablativus singularis -e."),
    ("prod6", "Scribe supinum verbi 'fero, ferre, tuli'.", "latum", "latum ← supinum irregulare (radix omnino mutata) verbi fero."),
]


def build():
    title = "Probatio Praeliminaris — Lectiones Latinae"
    desc = "Probatio difficilis et progressiva, per omnes septem gradus, quae gradum aptum tibi commendat."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Probatio Praeliminaris</li>'

    mc_data = {
        "id": "probatio-praeliminaris", "type": "multiple-choice", "title": "Probatio Praeliminaris",
        "instructions": "30 quaestiones, difficultate crescente ab initio ad finem. Responde quam plurimis, deinde confirma ut summam videas.",
        "items": [
            {"id": i, "prompt": p, "options": o, "answerIndex": a, "explanation": e}
            for i, p, o, a, e in MC_ITEMS
        ],
    }
    rc_data = {
        "id": "probatio-lectio-caesar", "type": "reading-comprehension", "title": "Pars II — Lectio: Caesar",
        "instructions": "Lege excerptum authenticum, non adaptatum, deinde responde. Haec pars praecipue distinguit inter Gradus V/VI et Gradum VII.",
        "passage": RC_PASSAGE,
        "items": [
            {"id": i, "prompt": p, "options": o, "answerIndex": a, "explanation": e}
            for i, p, o, a, e in RC_ITEMS
        ],
    }
    prod_data = {
        "id": "probatio-productio", "type": "typing", "title": "Pars III — Productio Morphologica",
        "instructions": "Scribe formam ipsam, sine macronibus (e.g. 'puellam', non 'puellam' cum lineā). Haec pars proba num formas non modo agnoscere, sed etiam ipse producere possis.",
        "items": [
            {"id": i, "prompt": p, "answer": [a], "explanation": e}
            for i, p, a, e in PROD_ITEMS
        ],
    }

    main = f"""<div class="page-header">
        {site_chrome.LAUREL_ROW}
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Inveni Gradum Tuum</p>
                <h1>Probātiō Praelimināris</h1>
                <p class="page-header__lede">Probātiō brevis sed <strong>difficilis</strong>, mixtae difficultātis, quae gradum sēnsibilem incohandī tibi commendat. Nōn est probātiō certificāta &mdash; cōgitā eam ut initium honestum.</p>
            </div>
        </div>
    </div>
<section class="section section--tight" style="padding-bottom:0;">
        <div class="section__inner">
            <div class="exercise-block">
                <script type="application/json" class="exercise-data">{json.dumps(mc_data, ensure_ascii=False)}</script>
            </div>
        </div>
    </section>
<section class="section section--surface">
        <div class="section__inner">
            <div class="exercise-block">
                <script type="application/json" class="exercise-data">{json.dumps(rc_data, ensure_ascii=False)}</script>
            </div>
        </div>
    </section>
<section class="section section--tight">
        <div class="section__inner">
            <div class="exercise-block">
                <script type="application/json" class="exercise-data">{json.dumps(prod_data, ensure_ascii=False)}</script>
            </div>
        </div>
    </section>
<section class="section section--surface" aria-labelledby="guide-heading">
        <div class="section__inner section__inner--narrow">
            <div class="section__head">
                <p class="eyebrow">Quōmodo Summam Legere</p>
                <h2 id="guide-heading">Ubi incipere</h2>
                <p>Secundum numerum rēctum in <strong>Parte I</strong> (ex 30):</p>
            </div>
            <div class="table-scroll">
                <table class="ref-table">
                    <thead><tr><th>Summa</th><th>Gradus commendātus</th><th></th></tr></thead>
                    <tbody>
                        <tr><td>0&ndash;4 rēcta</td><td>Incipe Gradū I &mdash; Fundamenta</td><td><a class="btn btn--ghost btn--small" href="gradus/fundamenta.html">Perge {ARROW_SVG}</a></td></tr>
                        <tr><td>5&ndash;9 rēcta</td><td>Incipe Gradū II &mdash; Elementa</td><td><a class="btn btn--ghost btn--small" href="gradus/elementa.html">Perge {ARROW_SVG}</a></td></tr>
                        <tr><td>10&ndash;14 rēcta</td><td>Incipe Gradū III &mdash; Progressus</td><td><a class="btn btn--ghost btn--small" href="gradus/progressus.html">Perge {ARROW_SVG}</a></td></tr>
                        <tr><td>15&ndash;19 rēcta</td><td>Incipe Gradū IV &mdash; Media</td><td><a class="btn btn--ghost btn--small" href="gradus/media.html">Perge {ARROW_SVG}</a></td></tr>
                        <tr><td>20&ndash;23 rēcta</td><td>Incipe Gradū V &mdash; Provectus</td><td><a class="btn btn--ghost btn--small" href="gradus/provectus.html">Perge {ARROW_SVG}</a></td></tr>
                        <tr><td>24&ndash;27 rēcta</td><td>Incipe Gradū VI &mdash; Altior</td><td><a class="btn btn--ghost btn--small" href="gradus/altior.html">Perge {ARROW_SVG}</a></td></tr>
                        <tr><td>28&ndash;30 rēcta</td><td>Es fortasse ultrā Gradum VI &mdash; tenta Gradum VII</td><td><a class="btn btn--ghost btn--small" href="gradus/auctores.html">Perge {ARROW_SVG}</a></td></tr>
                    </tbody>
                </table>
            </div>
            <p class="notice mt-lg"><svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/></svg><strong>Partes II et III sunt cōnfirmātiōnēs</strong>, nōn pars prīncipālis summae. Sī bene in Parte Iēgistī (24+) sed male in Parte II (lēctiō Caesaris), incipe Gradū V vel VI, nōn VII &mdash; lēctiō textūs authenticī nōn adaptātī postulat exercitātiōnem suam propriam.</p>
        </div>
    </section>"""
    out = [site_chrome.head(REL, title, desc), site_chrome.header(REL, "", breadcrumb), main, site_chrome.footer(REL)]
    path = REPO_ROOT / "probatio.html"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"Built {path.relative_to(REPO_ROOT)} ({len(MC_ITEMS)} + {len(RC_ITEMS)} + {len(PROD_ITEMS)} = {len(MC_ITEMS)+len(RC_ITEMS)+len(PROD_ITEMS)} items)")


if __name__ == "__main__":
    build()
