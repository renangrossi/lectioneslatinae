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
**Avus** ("grandfather") was introduced for Gradus III: a retired
soldier/sailor who tells Mārcus, Iūlia, and Claudia stories, giving that
level's declension/conjugation lessons a consistent narrator without
forcing the younger cast into a war/sea backstory of their own. Gradus VI
and VII (advanced syntax and authentic authors) instead use **magister**
in dialogue with an adult Mārcus (and sometimes Lūcius) walking through
real classical passages — a classroom framing rather than a family scene,
which fits material that is explicitly *about* Cicero/Caesar/etc. rather
than a story that happens to use a grammatical point.

Reuse these names — and settings already established (Iūlia's rose
garden, the forum, avus's sea/army stories, magister's classroom) —
rather than inventing new characters per lesson; that repetition is what
makes later encounters cheaper for the learner (they already know who
Mārcus is, so a new lesson only has to teach the new construction, not a
new cast too). `scripts/audit_curriculum.py`'s `CAST_RE`/`AVUS_RE` are
the authoritative list if you add a new recurring name — update them
there too, so the audit keeps tracking cast usage accurately. Note that
`CAST_RE` matches on macron-stripped name *stems* (e.g. `Marc\w*`), not
just the bare nominative, because Latin is inflected: a story that
addresses "Mārce" (vocative) or narrates about "avī" (genitive) is still
using the character, and the classifier needs to credit that.

## What's transformed vs. what's audited-but-untouched

Run the audit script for current numbers. As of this pass: **91/91
lessons score A, 0 B, 0 C** — every lesson in the curriculum now opens
with a comprehensible scene before any formal grammar label appears.
This finished a multi-batch effort; the last B-lessons closed were the
3 Gradus III lessons missed by an earlier "top-up" pass
(`iii-declinatio-tertia-consonantes`, `iii-comparatio-adverbiorum`,
`iii-numeri-tempus-et-calendarium`) and 6 lessons in Gradus VI/VII that
needed a `magister`-led classroom scene plus an extra meaning-based
exercise block (`vi-ablativus-usus-provectiores`,
`vi-numeri-usus-litterarii`, `vi-lectio-adaptata-caesar`,
`vi-recognitio-syntaxis-integra`, `vii-rhetorica-ciceroniana`,
`vii-cicero-de-amicitia`).

If the classifier ever finds new B/C lessons again (e.g. after adding
new curriculum content), re-run
`python3 scripts/audit_curriculum.py --csv docs/natural-method-audit.csv`
and follow the pattern above. Two things worth remembering from this
pass: (1) a lesson can look done — a story, a reading-comprehension
block — and still score B because the classifier only credits
*recurring-cast* narrative, not any narrative; a passage about `Gāius
Iūlius Caesar` alone doesn't reliably read as "the course's characters"
the way an explicit `Mārcō` or `avus` does, so name-check the cast
explicitly when in doubt. (2) `identify_ratio` (the fraction of exercise
items that read as bare grammar-identification, e.g. "'X' est:") is
easy to accidentally push over the 0.35/0.6 penalty thresholds on a
short lesson — adding one more *meaning*-based block (a `true-false` or
`reading-comprehension` with content questions, not label questions)
dilutes that ratio at least as effectively as rewriting the
identification-style items themselves.
