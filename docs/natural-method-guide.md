# Natural Method transformation guide

Working notes for continuing the Natural-Method redesign started in this
pass. Read `docs/natural-method-audit.csv` (regenerate with
`python3 scripts/audit_curriculum.py --csv docs/natural-method-audit.csv`)
before picking the next lesson — it is ordered by curriculum sequence and
carries every lesson's A/B/C classification and score.

## The pattern used on every transformed lesson so far

No new JSON fields, exercise types, or components were introduced — this
reuses the existing `curriculum/{level}/*.json` → `build_lesson.py` →
`assets/js/exercises.js` pipeline exactly as documented in
`curriculum/SCHEMA.md`. What changed is *content and sequencing* within
that schema:

1. **`content.intro`** — replace an abstract opening ("The ablative is
   used for...") with a two-or-three-sentence comprehensible scene
   using the course's recurring cast (see below). Plain text only — the
   build script always HTML-escapes `intro`, so no `<em>`/`<strong>` tags
   here (a real bug found and fixed in the original pilot lesson).
2. **`content.explanation`** — this is the one field allowed to hold
   real HTML (`build_lesson.py` uses it raw whenever it contains `<`).
   Write it as: a short narrative paragraph or two using the target
   construction in context, then a "Notāvistīne...?" (did you notice...?)
   paragraph that names the pattern the learner just saw, ending with the
   grammatical term. The existing `content.rules` section (which follows
   immediately on the page) is where the formal paradigm/reference table
   belongs — keep it, don't duplicate it in the narrative.
3. **`content.examples`** — recycle the story's own vocabulary/characters
   into the example sentences rather than introducing fresh nouns just to
   fill the list.
4. **`exercises`** — add a `reading-comprehension` block (the story, or
   an extended version of it, as `passage`, with 3-4 Latin comprehension
   questions as `items`) and one meaning-based block (`true-false` or
   `matching`) *before* the lesson's existing `multiple-choice`/
   `fill-blank`/`ordering` exercises. Keep the existing exercises if they
   were already reasonably meaning-anchored (most were, via English
   glosses in parentheses) — just resequence them after the new
   comprehension-first material, and consider retitling the closing
   `multiple-choice` block "Nunc Nomina: ..." ("now name it") to signal
   it's consolidation, not the starting point.

Every exercise type used here (`reading-comprehension`, `matching`,
`true-false`, plus the pre-existing `multiple-choice`/`fill-blank`/
`ordering`/`typing`) is already implemented in `assets/js/exercises.js` —
see that file's header comment for the full schema. Nothing new needs to
be built in JS or CSS to keep doing this.

## The recurring cast

Established in Gradus I's dialogue lessons and reused throughout this
pass: **Mārcus**, **Iūlia**, **Claudia** (Iūlia's sister), and **Lūcius**
(introduced in `v-clausulae-characteristicae`, reused in the
`v-clausulae-consecutivae` / `v-interrogationes-obliquae` forum scene).
Reuse these names — and settings already established (Iūlia's rose
garden, the forum) — rather than inventing new characters per lesson;
that repetition is what makes later encounters cheaper for the learner
(they already know who Mārcus is, so a new lesson only has to teach the
new construction, not a new cast too). `scripts/audit_curriculum.py`'s
`CAST_RE` is the authoritative list if you add a new recurring name —
update it there too, so the audit keeps tracking cast usage accurately.

## What's transformed vs. what's audited-but-untouched

Run the audit script for current numbers. As of this pass: 15/91 lessons
score A, 27 B, 49 C. Gradus IV and V (the subjunctive-system core) remain
the most C-heavy and are the natural next targets — in particular
`iv-clausulae-finales` (purpose clauses, the worst-scoring lesson in the
whole curriculum) pairs naturally with `iv-coniunctivus-praesens`
(already transformed) since purpose clauses are presumably taught right
after the subjunctive's form. `v-consecutio-temporum` was deliberately
left alone: it's a cross-cutting sequence-of-tenses reference lesson, not
tied to one construction, and doesn't fit the narrative-first template as
naturally as a lesson built around a single construction does — it may
need a different treatment (e.g. a timeline/table-first design) rather
than forcing a story onto it.
