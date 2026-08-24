#!/usr/bin/env python3
"""
Build the small set of hand-curated, non-curriculum top-level pages that
share the standard site chrome but have their own bespoke <main> content:
iter.html (progress), hodie.html (spaced-repetition review), and
verba-irregularia.html (irregular-verb reference table).

Run once per edit to these pages' content (defined inline below, in this
file) -- there's no external data source to regenerate from, unlike
build_lesson.py/build_level_page.py.

Usage:
    python3 scripts/build_static_pages.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_chrome  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
REL = ""

CHECK_SVG = '<svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/></svg>'


def write(name, html):
    path = REPO_ROOT / name
    path.write_text(html, encoding="utf-8")
    print(f"Built {path.relative_to(REPO_ROOT)}")


def build_iter():
    title = "Iter Meum — Lectiones Latinae"
    desc = "Progressus tuus: Puncta Experientiae (PE), series dierum, et insignia — omnia in hoc navigatro servata, sine ratione (account)."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Iter Meum</li>'
    main = f"""<div class="page-header">
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Progressus Tuus</p>
                <h1>Iter Meum</h1>
                <p class="page-header__lede">{desc}</p>
            </div>
        </div>
    </div>
<section class="section section--tight" aria-labelledby="summary-heading">
        <div class="section__inner">
            <h2 id="summary-heading" class="visually-hidden">Summarium</h2>
            <div class="progress-stats" id="progress-summary">
                <div class="progress-stat"><strong>0</strong><span>PE Tota</span></div>
                <div class="progress-stat"><strong>0</strong><span>Series Dierum</span></div>
                <div class="progress-stat"><strong>0 / 0</strong><span>Insignia Obtenta</span></div>
                <div class="progress-stat"><strong>0</strong><span>Exercitationes Confectae</span></div>
            </div>
        </div>
    </section>
<section class="section section--tight" aria-labelledby="review-heading">
        <div class="section__inner section__inner--narrow">
            <div class="section__head">
                <p class="eyebrow">Repetitio Distributa</p>
                <h2 id="review-heading">Recognitio Hodierna</h2>
            </div>
            <div class="notice" id="progress-review-callout"><p>Ordo recognitionis oneratur&hellip;</p></div>
            <div class="hero__actions" style="margin-top:var(--space-sm);">
                <a class="btn btn--accent" href="hodie.html">Ad Recognitionem Hodiernam</a>
            </div>
        </div>
    </section>
<section class="section section--surface" aria-labelledby="levels-heading">
        <div class="section__inner section__inner--narrow">
            <div class="section__head">
                <p class="eyebrow">Per Gradum</p>
                <h2 id="levels-heading">Progressus per gradum</h2>
                <p>Fīnis insignis "Explorator" cuiusque gradūs pōnitur ad ~30% exercitātiōnum eius gradūs, ut labor aequus ubīque sit.</p>
            </div>
            <div class="progress-levels-list" id="progress-levels"></div>
        </div>
    </section>
<section class="section" aria-labelledby="badges-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Iactūrae</p>
                <h2 id="badges-heading">Insignia</h2>
                <p>Insignia occlūsa (locked) monstrant quid faciendum sit deinde — tange ut vīderis.</p>
            </div>
            <ul class="badge-grid badge-grid--page" id="progress-badges"></ul>
        </div>
    </section>
<section class="section section--surface" aria-labelledby="topics-heading">
        <div class="section__inner section__inner--narrow">
            <div class="section__head">
                <p class="eyebrow">Lectiō post Lectiōnem</p>
                <h2 id="topics-heading">Argumenta Confecta</h2>
                <p>Confice omnem exercitātiōnem ūnīus lēctiōnis (e.g. lēctiō Gradūs II) ut hīc appāreat.</p>
            </div>
            <div id="progress-topics"></div>
        </div>
    </section>
<section class="section section--surface" aria-labelledby="account-heading">
        <div class="section__inner section__inner--narrow">
            <div class="section__head">
                <p class="eyebrow">Phasis I &mdash; Sine Servō</p>
                <h2 id="account-heading">Quōmodo Hoc Fungitur</h2>
                <p>Omnia haec tantum in hōc navigātrō, in hōc īnstrūmentō, servantur. Sī memoriam navigātrī pūrgās (vel aliud navigātrum/īnstrūmentum adhibēs), omnia dēnuō incipiunt. Nūlla ratiō (account) nunc exsistit, et nihil umquam ad servum mittitur.</p>
            </div>
            <button type="button" class="btn btn--ghost" id="progress-reset-btn">Dēlē progressum meum in hōc īnstrūmentō</button>
        </div>
    </section>"""
    out = [site_chrome.head(REL, title, desc), site_chrome.header(REL, "", breadcrumb), main, site_chrome.footer(REL)]
    write("iter.html", "\n".join(out))


def build_hodie():
    title = "Recognitio Hodierna — Lectiones Latinae"
    desc = "Elementa quae adhuc discis, reducta cum opus est — non omnia quae umquam studuisti."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Recognitio Hodierna</li>'
    main = f"""<div class="page-header">
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Repetitio Distributa</p>
                <h1>Recognitiō Hodierna</h1>
                <p class="page-header__lede">{desc}</p>
            </div>
        </div>
    </div>
<section class="section section--tight" aria-labelledby="review-status-heading">
        <div class="section__inner">
            <h2 id="review-status-heading" class="visually-hidden">Status</h2>
            <div id="review-status-box" class="notice"><p>Ordo recognitionis oneratur&hellip;</p></div>
        </div>
    </section>
<section class="section section--surface" aria-labelledby="review-blocks-heading">
        <div class="section__inner">
            <h2 id="review-blocks-heading" class="visually-hidden">Exercitationes</h2>
            <div id="review-blocks"></div>
        </div>
    </section>"""
    out = [site_chrome.head(REL, title, desc), site_chrome.header(REL, "", breadcrumb), main, site_chrome.footer(REL)]
    out[-1] = out[-1].replace(
        '<script src="assets/js/mastery.js"></script>',
        '<script src="assets/js/mastery.js"></script><script src="assets/js/hodie.js"></script>',
    )
    write("hodie.html", "\n".join(out))


# (verbum, infinitivus, perfectum [+ supinum ubi exstat], significatio)
IRREGULAR_VERBS = [
    ("sum", "esse", "fuī", "esse, exsistere"),
    ("absum", "abesse", "āfuī", "abesse, procul esse"),
    ("adsum", "adesse", "adfuī (affuī)", "adesse, praestō esse"),
    ("dēsum", "dēesse", "dēfuī", "dēficere, abesse cum dētrīmentō"),
    ("īnsum", "inesse", "(perfectum rārō āttestātum)", "inesse, intus esse"),
    ("intersum", "interesse", "interfuī", "interesse, particeps esse"),
    ("obsum", "obesse", "obfuī (offuī)", "obesse, nocēre"),
    ("praesum", "praeesse", "praefuī", "praeesse, dūcere"),
    ("prōsum", "prōdesse", "prōfuī", "prōdesse, ūtilem esse"),
    ("subsum", "subesse", "(perfectum nōn ūsitātum)", "subesse, subiacēre"),
    ("supersum", "superesse", "superfuī", "superesse, superstitem esse"),
    ("possum", "posse", "potuī", "posse, valēre"),
    ("volō", "velle", "voluī", "velle, cupere"),
    ("nōlō", "nōlle", "nōluī", "nōlle (nōn velle)"),
    ("mālō", "mālle", "māluī", "mālle, praeferre"),
    ("ferō", "ferre", "tulī, lātum", "ferre, portāre"),
    ("afferō", "afferre", "attulī, allātum", "afferre, ad sē ferre"),
    ("auferō", "auferre", "abstulī, ablātum", "auferre, sēcum ferre"),
    ("cōnferō", "cōnferre", "contulī, collātum", "cōnferre, comparāre"),
    ("differō", "differre", "distulī, dīlātum", "differre, prōrogāre"),
    ("efferō", "efferre", "extulī, ēlātum", "efferre, ecferre, laudāre"),
    ("īnferō", "īnferre", "intulī, illātum", "īnferre, importāre"),
    ("offerō", "offerre", "obtulī, oblātum", "offerre, praebēre"),
    ("referō", "referre", "rettulī, relātum", "referre, nūntiāre"),
    ("eō", "īre", "iī (īvī), itum", "īre, sē movēre"),
    ("abeō", "abīre", "abiī, abitum", "abīre, discēdere"),
    ("adeō", "adīre", "adiī, aditum", "adīre, accēdere"),
    ("exeō", "exīre", "exiī, exitum", "exīre, ēgredī"),
    ("ineō", "inīre", "iniī, initum", "inīre, ingredī"),
    ("pereō", "perīre", "periī, peritum", "perīre, morī"),
    ("redeō", "redīre", "rediī, reditum", "redīre, revertī"),
    ("trānseō", "trānsīre", "trānsiī, trānsitum", "trānsīre, trānsgredī"),
    ("vēneō", "vēnīre", "vēniī", "vēnīre, vēnum īre (vēndī)"),
    ("fīō", "fierī", "factus sum", "fierī, ēvenīre (passīvum verbī faciō)"),
    ("edō", "ēsse (edere)", "ēdī, ēsum", "edere, cibum sūmere"),
]

VERB_ROWS = "".join(
    f"<tr><td><strong>{v}</strong></td><td>{inf}</td><td>{perf}</td><td>{sig}</td></tr>"
    for v, inf, perf, sig in IRREGULAR_VERBS
)


def build_verba_irregularia():
    title = "Verba Irregularia — Lectiones Latinae"
    desc = f"Sum, possum, volo/nolo/malo, fero, eo, fio, edo — conspectus plenus omnium verborum vere irregularium Latinorum ({len(IRREGULAR_VERBS)} formae), cum coniugatis suis."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Verba Irregularia</li>'
    main = f"""<div class="page-header">
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Conspectus</p>
                <h1>Verba Irregulāria</h1>
                <p class="page-header__lede">{desc}</p>
            </div>
        </div>
    </div>
<section class="section section--surface" aria-labelledby="filter-heading">
        <div class="section__inner">
            <h2 id="filter-heading" class="visually-hidden">Filtrum</h2>
            <div class="section__inner--narrow" style="margin-bottom:var(--space-md);">
                <label for="verb-filter" class="eyebrow" style="margin-bottom:0.6em;display:block;">Quaere formam</label>
                <div class="dict-input-row">
                    <svg class="" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
                    <input type="text" id="verb-filter" class="dict-input" placeholder="Scribe formam, e.g. &ldquo;tulī&rdquo; vel &ldquo;ferō&rdquo;" autocomplete="off" data-verb-filter>
                </div>
                <p class="notice mt-lg" data-verb-count>{CHECK_SVG}Omnes {len(IRREGULAR_VERBS)} formae monstrantur. Multa composita ferō/eō assimilationem cōnsonantium ostendunt (ad+ferō &rarr; afferō).</p>
            </div>
            <div class="table-scroll">
                <table class="ref-table" data-verb-table>
                    <thead><tr><th scope="col">Verbum</th><th scope="col">Īnfīnītīvus</th><th scope="col">Perfectum (+ Supīnum)</th><th scope="col">Significātiō</th></tr></thead>
                    <tbody data-verb-tbody>{VERB_ROWS}</tbody>
                </table>
            </div>
            <p class="notice mt-lg" data-verb-empty hidden>{CHECK_SVG}Nulla forma congruit cum &ldquo;<span data-verb-empty-term></span>.&rdquo; Aliam scripturam tenta.</p>
        </div>
    </section>
<section class="section" aria-labelledby="edo-heading">
        <div class="section__inner section__inner--narrow">
            <p class="eyebrow">Nota Speciālis</p>
            <h2 id="edo-heading">Edō: Fōrmae Geminae</h2>
            <p><strong>Edō</strong> ('edere', 'to eat') fōrmās alternātīvās habet, similēs verbō 'sum', praeter fōrmās regulārēs tertiae coniugātiōnis: <strong>ēs</strong> ('tū edis' — nōtā vōcālem longam, distinguēns ab 'es' = 'tū es') , <strong>ēst</strong> ('is ēdit'), <strong>ēsse</strong> (īnfīnītīvus, prō 'edere'), <strong>ēssem</strong> (coniūnctīvus imperfectī, prō 'ederem'). Contextus semper significātiōnem clārificat.</p>
        </div>
    </section>"""
    out = [site_chrome.head(REL, title, desc), site_chrome.header(REL, "", breadcrumb), main, site_chrome.footer(REL)]
    out[-1] = out[-1].replace(
        '<script src="assets/js/mastery.js"></script>',
        '<script src="assets/js/mastery.js"></script><script src="assets/js/verba-irregularia.js"></script>',
    )
    write("verba-irregularia.html", "\n".join(out))


if __name__ == "__main__":
    build_iter()
    build_hodie()
    build_verba_irregularia()
