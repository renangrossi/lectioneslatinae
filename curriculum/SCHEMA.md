# Curriculum data schema (v1)

Single source of truth for lesson content. Each lesson is one JSON file
at `curriculum/{level-code-lowercase}/{lesson-id}.json` (e.g.
`curriculum/iv/perfectum-activum.json` for a Gradus IV lesson — the
directory uses the level's short code lowercased, `i`..`vii`, matching
the `{code}-` prefix every lesson id already carries; it is NOT the
Gradus slug used for URLs, e.g. `media`, which only appears under
`gradus/`). `curriculum/index.json` lists
every Gradus's units and the lesson ids that belong to each, in order,
with prerequisites — this is what lets a level page, the search index,
and the exercise-items index all be generated instead of hand-maintained.

Adapted from the sibling English-course project's `curriculum/SCHEMA.md`
(same shape, same build pipeline) — `level` values are this course's
seven Latin-named Gradus short codes (`I`..`VII`, see
`scripts/site_chrome.py`'s `LEVELS`), and `exercises` items use the
exact schema `assets/js/exercises.js` reads (identical engine, ported
and Latinized — see that file's own header comment).

## Lesson JSON shape

```jsonc
{
  "id": "iv-perfectum-activum",         // matches the generated filename
  "level": "IV",                        // I | II | III | IV | V | VI | VII
  "unit": "2",              // curriculum/index.json unit number this belongs to
  "order": 3,                // position within the unit
  "skill": "grammatica",     // grammatica | vocabularium | pronuntiatio | lectio
                              // | auditio | scriptio | locutio | functionale
  "strand": "perfectum",     // free-text grouping used for prerequisite/related lookups
  "title": "Perfectum Activum",
  "subtitle": "Formare et uti perfecto activo omnium coniugationum.",
  "prerequisites": ["iii-imperfectum"],   // lesson ids; [] if none
  "objectives": [
    "Perfectum activum omnium coniugationum recte formare",
    "..."
  ],
  "content": {
    "intro": "One short paragraph, Latin (English gloss only at Gradus I).",
    "explanation": "<p>...</p>",     // may contain inline HTML (strong/em), no block tags
    "rules": [ { "heading": "a) Radix Perfecti", "body": "<p>...</p>" }, ... ],
    "examples": ["Puella rosam vīdit.", "..."],
    "commonMistakes": [
      { "wrong": "...", "right": "...", "why": "..." }
    ]
  },
  "exercises": [ /* verbatim assets/js/exercises.js exercise-data objects */ ],
  "summary": ["One-line takeaway", "..."],
  "related": [ { "lessonId": "iv-participium-perfectum", "label": "Participium Perfectum" } ]
}
```

Correct-answer keys inside `exercises` (`answer`/`answers`/pair
`right` values, `words` for ordering, `answerIndex`'s corresponding
`options` entry) are written **without macrons** even when the prompt
or explanation uses them — macrons are a typing burden the grading
should never impose. Macrons appear in prompts/explanations/examples
wherever they matter pedagogically.

## `curriculum/index.json` shape

```jsonc
{
  "levels": {
    "IV": {
      "units": [
        {
          "id": "1",
          "title": "Systema Perfectum Activum",
          "lessons": [
            { "id": "iv-perfectum-activum", "status": "published" },
            { "id": "iv-plusquamperfectum-futurum-perfectum", "status": "published" }
          ]
        }
      ]
    }
  }
}
```

`status` on a lesson entry is `"published"` (generated HTML exists and
is linked from its Gradus page) or `"drafted"` (JSON exists, not yet
built).

## Build

`python3 scripts/build_lesson.py curriculum/{level}/{lesson-id}.json`
renders one lesson to `gradus/{level}/{lesson-id}.html`, reusing the
shared header/footer markup (via `scripts/site_chrome.py`).

`python3 scripts/build_nav_map.py` regenerates
`scripts/lesson_nav_map.json` (Previous/Next + Test-Yourself-anchor
data) from `curriculum/index.json` — run it after adding/reordering
lessons, before rebuilding pages.

`python3 scripts/build_exercise_index.py` regenerates
`assets/data/exercise-items-index.json` (used by `hodie.html`'s spaced
repetition) and `assets/data/search-index.json` (used by the site
search) from every built page — run it last, after all pages for a
batch are built.
