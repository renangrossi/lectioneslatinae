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


EXAM_I_MC = [
    ("e1-1", "Genetivus singularis verbi 'civitas, civitatis' est:", ["civitas", "civitatis", "civitati"], 1, "Tertia declinatio: genetivus semper -is."),
    ("e1-2", "'Puellae rosam dant' — 'puellae' hic est:", ["nominativus pluralis", "genetivus/dativus singularis", "vocativus"], 0, "Contextu (subiectum plurale + 'dant'): nominativus pluralis."),
    ("e1-3", "Comparativus verbi 'facilis, facile' est:", ["facilior", "facillimus", "faciliter"], 0, "-ior: signum comparativi."),
    ("e1-4", "'In urbe manemus' — 'in' hic postulat casum:", ["accusativum (motus)", "ablativum (quies)"], 1, "Verbum 'maneo' = quies, non motus."),
    ("e1-5", "Imperfectum, 1a persona singularis, verbi 'audio' est:", ["audiebam", "audivi", "audiam"], 0, "-iebam: imperfectum quartae coniugationis."),
    ("e1-6", "'Bellum forte' — 'forte' concordat cum 'bellum' quia ambo sunt:", ["masculina", "neutra"], 1, "bellum est neutrum: forte (non fortis)."),
    ("e1-7", "Futurum, 3a persona pluralis, verbi 'mitto' (tertia coniugatio) est:", ["mittent", "mittunt", "mittebant"], 0, "III/IV: -ent futurum."),
    ("e1-8", "'Rex quem videmus bonus est' — 'quem' habet casum ex:", ["antecedente 'rex'", "officio proprio in clausula relativa (obiectum 'videmus')"], 1, "Regula Aurea: casus ex clausula propria."),
    ("e1-9", "Vocativus verbi 'filius' est:", ["fili", "filius", "filie"], 0, "Nomina in -ius: vocativus -i."),
    ("e1-10", "'Multo maior' — 'multo' est ablativus:", ["instrumenti", "mensurae (cum comparativo)"], 1, "Gradus differentiae cum comparativo."),
]
EXAM_I_FILL = [
    ("e1-11", "___ puellam video. (This — hanc)", ["Haec", "Hanc", "Huius"], ["Hanc"], "Accusativus femininum singulare."),
    ("e1-12", "Milites urbem ___. (defended — defenderunt)", ["defendunt", "defenderunt", "defendent"], ["defenderunt"], "Perfectum: defendērunt."),
    ("e1-13", "___ librum legis? (Whose — cuius)", ["cui", "cuius", "quem"], ["cuius"], "Genetivus interrogativus."),
    ("e1-14", "Nos ___ semper amamus. (our country — patriam nostram)", ["patria nostra", "patriam nostram", "patriae nostrae"], ["patriam nostram"], "Accusativus, obiectum directum."),
    ("e1-15", "Puer ___ canem amat. (his own — suum)", ["eius", "suum", "suus"], ["suum"], "Reflexivum, accusativum masculinum."),
]
EXAM_I_RC_PASSAGE = "<p><strong>In Villa Rustica.</strong><br>Marcus, agricola Romanus, in villa rustica cum familia sua habitat. Mane surgit et cum servis in agros it. Ibi frumentum serit et vites colit. Uxor eius, Iulia, domi manet et liberos docet. Vespere omnes ad cenam conveniunt et de die narrant. Marcus semper dicit: 'Vita rustica dura est, sed bona.'</p>"
EXAM_I_RC = [
    ("e1-16", "Ubi habitat Marcus?", ["in urbe", "in villa rustica", "in monte"], 1, "'in villā rūsticā cum familiā suā habitat'."),
    ("e1-17", "Quid Marcus mane facit?", ["dormit", "cum servis in agros it", "ad forum it"], 1, "'cum servīs in agrōs it'."),
    ("e1-18", "Quid Iulia domi facit?", ["liberos docet", "vites colit", "frumentum serit"], 0, "'Uxor eius, Iūlia, domī manet et līberōs docet'."),
    ("e1-19", "Quid Marcus de vita rustica dicit?", ["est facilis et mala", "est dura, sed bona", "est semper laeta"], 1, "'Vīta rūstica dūra est, sed bona.'"),
]

EXAM_II_MC = [
    ("e2-1", "Perfectum, 1a persona singularis, verbi 'facio' est:", ["facio", "feci", "faciebam"], 1, "Perfectum irregulare: fēcī."),
    ("e2-2", "'Urbe capta' est constructio:", ["genetivi qualitatis", "ablativi absoluti"], 1, "Nomen + participium perfectum, ambo ablativo."),
    ("e2-3", "Participium praesens verbi 'venio' est:", ["veniens", "venturus", "ventus"], 0, "-iens: participium praesens quartae coniugationis."),
    ("e2-4", "'Dico te bonum esse' — 'te' est:", ["subiectum sententiae principalis", "subiectum accusativum intra AcI"], 1, "Accusativus cum infinitivo."),
    ("e2-5", "Coniunctivus praesens, 1a persona singularis, verbi 'sum' est:", ["sum", "sim", "eram"], 1, "sim: coniunctivus irregularis."),
    ("e2-6", "'Venit ut videat' — 'videat' est coniunctivus:", ["praesens (sequentia primaria)", "imperfectum (sequentia historica)"], 0, "'Venit' praesens: sequentia primaria."),
    ("e2-7", "Negatio clausulae consecutivae ('so...that not') est:", ["ne", "ut non"], 1, "Distinctio ab clausula finali."),
    ("e2-8", "'Nemo est qui hoc credat' est clausula:", ["factualis", "characteristica"], 1, "Antecedens indefinitus + coniunctivus."),
    ("e2-9", "Gerundium caret casu:", ["genetivo", "nominativo"], 1, "Infinitivus supplet locum nominativi."),
    ("e2-10", "'Liber legendus est' significat:", ["The book is reading", "The book must be read"], 1, "Gerundivum + sum: obligatio."),
]
EXAM_II_FILL = [
    ("e2-11", "Si hoc ___, tibi dicerem. (I knew — scirem)", ["scio", "scirem", "sciverim"], ["scirem"], "Condicio irrealis praesens: coniunctivus imperfectus."),
    ("e2-12", "Milites, hostibus ___, domum redierunt. (having been defeated — victis)", ["victi", "victis", "vincentes"], ["victis"], "Ablativus absolutus."),
    ("e2-13", "Timeo ___ hostes veniant. (that — ne)", ["ut", "ne", "quod"], ["ne"], "Timor positivus: ne."),
    ("e2-14", "Ad urbem ___ milites misit. (defending — defendendam)", ["defendendum", "defendendam", "defendens"], ["defendendam"], "Attractio gerundiva, concordans cum 'urbem'."),
    ("e2-15", "Nescio quid ___. (he did — fecerit)", ["facit", "fecit", "fecerit"], ["fecerit"], "Interrogatio obliqua, coniunctivus perfectus."),
]
EXAM_II_RC_PASSAGE = "<p><strong>De Bello Narratio Brevis.</strong><br>Cum hostes ad urbem appropinquavissent, cives, magno timore commoti, arma ceperunt. Dux, qui iam multa bella gesserat, milites hortatus est ut fortiter pugnarent. 'Si urbem defenderitis,' inquit, 'patriam servabitis; si autem fugeritis, omnia perdetis.' His verbis auditis, milites, tam fortiter pugnaverunt ut hostes tandem fugerent. Urbs, ita servata, dux liber remansit.</p>"
EXAM_II_RC = [
    ("e2-16", "Quid cives fecerunt cum hostes appropinquavissent?", ["fugerunt", "arma ceperunt", "portas clauserunt"], 1, "'cīvēs...arma cēpērunt'."),
    ("e2-17", "Quid dux milites facere hortatus est?", ["ut domum irent", "ut fortiter pugnarent", "ut cum hostibus loquerentur"], 1, "'mīlitēs hortātus est ut fortiter pugnārent'."),
    ("e2-18", "Secundum ducem, quid eveniet si milites fugerint?", ["omnia perdent", "praemium accipient", "nihil mutabitur"], 0, "'sī...fūgeritis, omnia perdētis'."),
    ("e2-19", "Quomodo pugnaverunt milites, secundum clausulam consecutivam?", ["tam fortiter ut hostes fugerent", "tam male ut urbs caperetur", "sine ullo studio"], 0, "'tam fortiter pugnāvērunt ut hostēs...fugerent'."),
]


def _mc_data(id_, title, items):
    return {"id": id_, "type": "multiple-choice", "title": title,
            "items": [{"id": i, "prompt": p, "options": o, "answerIndex": a, "explanation": e} for i, p, o, a, e in items]}


def _fill_data(id_, title, items):
    return {"id": id_, "type": "fill-blank", "title": title,
            "items": [{"id": i, "prompt": p, "options": o, "answers": ans, "explanation": e} for i, p, o, ans, e in items]}


def _rc_data(id_, title, passage, items):
    return {"id": id_, "type": "reading-comprehension", "title": title, "passage": passage,
            "items": [{"id": i, "prompt": p, "options": o, "answerIndex": a, "explanation": e} for i, p, o, a, e in items]}


def build_examina():
    title = "Examina Ficta — Lectiones Latinae"
    desc = "Duo examina ficta plena (Gradus II-III et Gradus IV-V), plus Probatio Praeliminaris, cum clavibus responsorum."
    breadcrumb = '<li><a href="index.html">Domus</a></li><li aria-current="page">Examina Ficta</li>'

    exam1_mc = json.dumps(_mc_data("examen-i-mc", "Pars I: Grammatica (Gradus II-III)", EXAM_I_MC), ensure_ascii=False)
    exam1_fill = json.dumps(_fill_data("examen-i-fill", "Pars II: Formae", EXAM_I_FILL), ensure_ascii=False)
    exam1_rc = json.dumps(_rc_data("examen-i-rc", "Pars III: Lectio", EXAM_I_RC_PASSAGE, EXAM_I_RC), ensure_ascii=False)

    exam2_mc = json.dumps(_mc_data("examen-ii-mc", "Pars I: Grammatica (Gradus IV-V)", EXAM_II_MC), ensure_ascii=False)
    exam2_fill = json.dumps(_fill_data("examen-ii-fill", "Pars II: Formae", EXAM_II_FILL), ensure_ascii=False)
    exam2_rc = json.dumps(_rc_data("examen-ii-rc", "Pars III: Lectio", EXAM_II_RC_PASSAGE, EXAM_II_RC), ensure_ascii=False)

    main = f"""<div class="page-header">
        {site_chrome.LAUREL_ROW}
        <div class="page-header__inner">
            <div class="page-header__text">
                <p class="eyebrow hero__eyebrow">Praxis Examinis</p>
                <h1>Examina Ficta</h1>
                <p class="page-header__lede">{desc}</p>
            </div>
        </div>
    </div>
<section class="section section--tight" aria-labelledby="exam1-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Examen I</p>
                <h2 id="exam1-heading">Gradus II&ndash;III: Nomina, Casus, Tempora</h2>
                <p>Decem quaestiones grammaticae, quinque formae, et lectio brevis cum quattuor quaestionibus &mdash; 19 elementa tota.</p>
            </div>
            <div class="exercise-block"><script type="application/json" class="exercise-data">{exam1_mc}</script></div>
            <div class="exercise-block"><script type="application/json" class="exercise-data">{exam1_fill}</script></div>
            <div class="exercise-block"><script type="application/json" class="exercise-data">{exam1_rc}</script></div>
        </div>
    </section>
<section class="section section--surface" aria-labelledby="exam2-heading">
        <div class="section__inner">
            <div class="section__head">
                <p class="eyebrow">Examen II</p>
                <h2 id="exam2-heading">Gradus IV&ndash;V: Perfectum, Participia, Coniunctivus</h2>
                <p>Decem quaestiones grammaticae, quinque formae, et lectio brevis cum quattuor quaestionibus &mdash; 19 elementa tota.</p>
            </div>
            <div class="exercise-block"><script type="application/json" class="exercise-data">{exam2_mc}</script></div>
            <div class="exercise-block"><script type="application/json" class="exercise-data">{exam2_fill}</script></div>
            <div class="exercise-block"><script type="application/json" class="exercise-data">{exam2_rc}</script></div>
        </div>
    </section>
<section class="section section--tight" aria-labelledby="exam0-heading">
        <div class="section__inner section__inner--narrow">
            <div class="section__head">
                <p class="eyebrow">Antequam Incipis</p>
                <h2 id="exam0-heading">Probatio Praeliminaris</h2>
                <p>Sī nescīs ubi incipere dēbeās, tenta prīmum nostram <strong>Probātiōnem Praelimināre</strong> &mdash; XLI (41) quaestiōnēs per omnēs septem gradūs, cum commendātiōne explicitā.</p>
            </div>
            <a class="btn btn--accent" href="probatio.html">Incipe Probationem Praeliminarem {ARROW_SVG}</a>
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
