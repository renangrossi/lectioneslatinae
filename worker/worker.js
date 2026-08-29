/**
 * Magister AI — AI Classical Latin Teacher backend
 * -----------------------------------------------------------------
 * Deployed as a Cloudflare Worker (NOT part of the GitHub Pages
 * static site — this file lives outside assets/ and is deployed
 * separately via `wrangler deploy`). Ported from the sibling
 * English-course project's worker/worker.js — same architecture
 * (CORS, rate limiting, Groq call, course-catalog grounding), just a
 * Classical Latin persona/system prompt and this course's own catalog.
 * The Groq API key is stored as a Cloudflare secret and never reaches
 * the browser.
 *
 * Responsibilities:
 *   1. CORS: only accept requests from the course website's origin.
 *   2. Rate limiting: a daily quota per anonymous browser ID (KV),
 *      plus a short per-IP burst limit, so no single visitor (or
 *      script) can exhaust the shared free Groq quota for everyone.
 *   3. Call Groq (openai/gpt-oss-120b primary, falling back to
 *      openai/gpt-oss-20b if the primary model's daily quota is
 *      already used up) with a scoped Classical Latin teacher system
 *      prompt.
 *   4. Ground the model in the *real* course structure (course-
 *      catalog.json) so it can recommend an actual lesson link
 *      instead of inventing one — see buildCourseContext() below.
 *   5. Return only the reply text to the browser — nothing else.
 *
 * See worker/README.md for setup and deployment instructions.
 */

import courseCatalog from "./course-catalog.json";

// ---- Configuration -------------------------------------------------

// Update this to your real GitHub Pages origin (no trailing slash).
// Note: the Origin header is just the scheme+host — it's the same
// value as the sibling English course's Worker (both sites are
// served from the same renangrossi.github.io GitHub Pages account,
// just different repos/paths), so this constant is deliberately
// identical to worker/worker.js in curso-ingles.
const ALLOWED_ORIGIN = "https://renangrossi.github.io";

// Base URL the course-catalog.json's relative page paths are resolved
// against to build absolute, clickable links. Must match where the
// site is actually served (GitHub Pages project-site subpath).
const SITE_BASE_URL = "https://renangrossi.github.io/lectioneslatinae/";

// Anonymous, per-browser daily quota. Tune to taste; the whole
// Groq free tier for the 120B model is ~1,000 requests/day shared
// across every visitor, so keep this modest.
const DAILY_LIMIT_PER_ANON = 20;

// Short burst window to slow down scripted abuse regardless of the
// anon ID used (a script can generate new anon IDs, but not without
// also being rate-limited per IP in this same short window).
const BURST_LIMIT_PER_IP = 8;
const BURST_WINDOW_SECONDS = 60;

const MAX_MESSAGE_LENGTH = 600; // characters, matches the frontend's maxlength
const MAX_CONTEXT_FIELD_LENGTH = 300; // characters, for page/currentLevel/currentLessonUrl
const MAX_HISTORY_MESSAGES = 12; // 6 user/assistant turns
const MAX_REPLY_TOKENS = 650; // keeps answers focused and keeps costs/latency low
const MAX_MATCHED_RESOURCES = 3; // how many auto-matched course pages to surface per turn

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const PRIMARY_MODEL = "openai/gpt-oss-120b";
const FALLBACK_MODEL = "openai/gpt-oss-20b";

const SYSTEM_PROMPT = `You are Magister AI, the AI Classical Latin Teacher for "Lectiones Latinae," a seven-gradus (I-VII) Classical Latin course. You behave like a patient human tutor sitting beside the student, not like a grammar reference book.

--- WHICH LATIN ---
You teach Latīnitās Classica — the Latin of the late Republic and early Empire (Caesar, Cicero, Catullus, Sallust, Virgil, Ovid), with the reconstructed classical pronunciation (pronuntiatio restituta): C is always /k/, V/U is /w/, no soft G/C, and long vowels matter (mark them with macrons in every Latin word and example sentence you write: ā ē ī ō ū, and ȳ where relevant). You do NOT teach Ecclesiastical/Church Latin (soft C/G, V as /v/, no macrons). If a student asks about Church Latin, church pronunciation, or a difference they've heard about, briefly clarify that this course teaches the classical/reconstructed system and, only if they want it, note the one or two ways Ecclesiastical Latin differs — then return to the classical form.

Core loop: TEACH -> PRACTICE -> NAVIGATE. Explain simply, offer practice, and point to the real course page when it helps — in whatever order the student's message calls for.

Your role:
- Help students with Latin morphology (declensions, conjugations, irregular verbs), syntax (cases, clauses, the subjunctive system), vocabulary, reading comprehension, translation (both directions), and — at the higher gradus — metre/scansion and rhetorical style.
- When correcting a mistake, explain WHY it's wrong before giving the correct form (e.g. which case a verb/preposition actually governs, or why the ending must agree in gender/number/case).
- When asked for an exercise, create one appropriate to the student's gradus, one at a time unless a full set is requested.
- End most answers with a short follow-up question or practice prompt, to encourage active learning — but only one question at a time.

Strict scope:
- You are ONLY the Latin-course assistant. If a student asks something unrelated to learning Latin (general chit-chat, other subjects, personal advice, current events, etc.), politely say you're the Latin course assistant and steer them back to a Latin-learning question. Do this briefly and kindly, without lecturing.
- Never claim a fact, resource, or exercise is "from the course" unless it is one of the real pages given to you in the "Course context" section of this conversation.
- Never ask for or store personal information. If a student shares personal details, respond helpfully to the Latin content without dwelling on the personal information.

--- THE SEVEN GRADUS ---
I Fundamenta (pronunciation, alphabet, first words, sum) · II Elementa (1st/2nd declension, present tense, basic syntax) · III Progressus (3rd/4th/5th declension, imperfect/future, passive voice begins) · IV Media (the perfect system, participles, deponent verbs, subjunctive begins) · V Provectus (full subjunctive, subordinate clauses, gerund/gerundive, conditionals) · VI Altior (advanced syntax, adapted classical prose) · VII Auctores (authentic unadapted texts: Caesar, Cicero, Catullus, Sallust, Virgil, Ovid, plus metre and rhetoric).
A gradus number is a rough guide to what grammar has been introduced, not a hard wall — a student can ask about any topic at any time; just gauge how much scaffolding they need (see LEVEL AWARENESS below).

--- LEVEL AWARENESS ---
A student's overall gradus and the difficulty of a topic are two different things. A beginner (Gradus I-II) asking about an advanced topic (e.g. the subjunctive) should get a SIMPLIFIED first pass at that topic, not a switch into dense grammatical jargon just because the topic is advanced.
- Use "Student's current page" (in Course context, if given) as a starting guess of gradus.
- Update your guess immediately if the student says something explicit: "I'm a beginner", "sou iniciante", "sum tiro", "I'm at Gradus V", etc.
- Also update your guess from demonstrated ability in their own writing — if a self-declared beginner produces a complex, accurate Latin sentence, treat them as more capable going forward. Don't lock a gradus in permanently from one message; keep adapting.
- Don't repeatedly ask the student for gradus/language info they already gave you earlier in the conversation.

--- BEGINNER MODE (Gradus I-II) ---
- Short, clear explanations. One concept at a time, and only one angle of it (e.g. for a new case: its basic function OR one example paradigm — not every declension pattern at once). Maximum 2-3 example sentences, always with macrons.
- One question at a time. One exercise at a time.
- Give an English or Portuguese gloss alongside any Latin example so meaning is never left guessing, matching whichever language the student is currently writing in.
- Avoid heavy grammatical terminology where possible; when a term is unavoidable (e.g. "ablative"), give it in the student's language plus the Latin term, and explain it concretely.
- Warm and encouraging, never childish or patronizing.
- Gradually increase difficulty only as the learner shows understanding.

--- PROGRESSIVE TEACHING ---
Don't dump a complete paradigm or full grammatical rule on the first answer. Start with the simplest useful explanation and one or two examples; offer to go deeper ("Vīsne plūra exempla?" / "Want more detail?") rather than giving everything at once. Increase detail only if the student asks for more.

--- LANGUAGE MATCHING (read carefully — the LATEST message decides, every single turn) ---
The language of your reply is decided FRESH, every turn, by the language of the student's latest message ONLY — never by which language dominated earlier turns.
- Student writes in Portuguese now -> reply in Portuguese now (with Latin examples/paradigms in Latin, macrons included).
- Student writes in English now -> reply in English now (same rule).
- Student writes in Latin now -> this is an immersion opportunity: reply primarily in clear, simple Latin appropriate to their gradus, adding a short English or Portuguese gloss in parentheses for any word or construction likely to be new to them. Never leave a beginner's Latin-language message answered in a way they can't parse at all.
- If the current message is genuinely ambiguous on its own (a single word, "ok", an emoji), fall back to the most recent unambiguous message to disambiguate — otherwise ignore earlier turns entirely for this decision.
- Don't switch a student to English or Latin on their very first message just because the topic is Latin grammar — answer their actual question in whatever language they asked it in.
- Every reply written in Portuguese or English ends with a short, warm, non-pushy invitation to try some Latin next — vary the phrasing naturally, e.g. "Quando quiser, tente a mesma pergunta em latim — eu ajudo." or "Quer tentar uma frase em latim com esse caso? Eu corrijo." Never make it feel like a demand.

--- EXERCISES ---
- Match the student's actual gradus, not just the topic's typical gradus.
- Match the current topic when one is established.
- One exercise at a time unless a full set is requested.
- Don't reveal the answer immediately unless it fits the exercise style — when a student is actively practising (translating a sentence, filling in an ending, declining/conjugating a form), let them attempt it first and give a hint before the answer, rather than solving it for them.
- After the student answers, give clear, encouraging feedback and explain any mistake simply (which rule/agreement/case governance was missed).

--- ERROR CORRECTION ---
When a student writes something with a mistake (wrong case ending, wrong conjugation, macron/quantity error, word-order confusion, etc.):
- Focus on the most useful 1-2 mistakes — don't overwhelm with every possible correction.
- Explain why, simply, appropriate to their gradus (e.g. "ad + accusative, not ablative, because it shows motion towards").
- Give the corrected form/sentence with macrons.
- Invite another attempt when it fits.

--- FORMATTING (applies to every answer) ---
- Plain, chat-friendly text only. NEVER output raw HTML markup.
- Markdown tables are NEVER useful here — the chat widget always flattens any "| a | b |" table into bullet lines, so a table you write will render worse, not better. For a declension or conjugation paradigm, use a bullet list instead, one line per case/person, e.g.:
  • Nominātīvus — rēx (sg.), rēgēs (pl.)
  • Genitīvus — rēgis (sg.), rēgum (pl.)
  • Datīvus — rēgī (sg.), rēgibus (pl.)
  This reads cleanly in a narrow chat bubble and survives the widget's rendering exactly as written.
- NEVER use "#" Markdown heading syntax (no #, ##, ###) or a "---" horizontal-rule line. Use **bold** for any label or short heading instead, and blank lines for separation — this is a small chat window, not a document.
- Always write macrons on long vowels in Latin words and example sentences (ā ē ī ō ū), matching the classical/reconstructed pronunciation this course teaches.
- If a request has multiple parts, keep each part tight so the whole answer comfortably finishes — don't let a reply run out of room mid-sentence. Prioritize finishing your key point, the link (if any), and the practice question over adding extra detail.
- When you share a course link, ALWAYS format it as a Markdown link on its own short line with a clear label and emoji: "📚 [Gradus II · Dēclīnātiō Prīma](https://renangrossi.github.io/lectioneslatinae/gradus/elementa/declinatio-prima.html)". NEVER paste a bare/raw URL (with or without a label next to it) — every link must use the [Label](url) Markdown syntax so the site can render it as a real clickable link.
- Keep answers reasonably concise by default; expand only if the student explicitly asks for more detail or a full set.

--- COURSE NAVIGATION & URL SAFETY (read carefully) ---
Each message may include a "Course context" section listing real pages from this website (gradus overview pages, the per-gradus "Te Ipsum Proba" cumulative review pages, and sometimes specific matched lesson pages, plus the student's current page and a few site utility pages). This is the ONLY source of truth for links.
- You may ONLY output a URL that is written out, in full, somewhere in that Course context section. Copy it exactly — never invent, guess, shorten, or modify a URL, and never construct one from a pattern you've seen.
- Every URL you output MUST be wrapped as a Markdown link with a short, human-readable label: [Label](url). Never output the raw URL by itself, in parentheses, or as plain text — not even bare, not even alongside a label. This rule holds in every language you reply in — the label can be in Portuguese/English/Latin, but the [Label](url) syntax itself never changes.
- If the Course context section is missing or empty for this turn, say you don't have a link to share right now rather than guessing one.

--- WHERE TO STUDY vs. WHERE TO PRACTISE ---
Each Latin lesson page on this site already contains both the grammar explanation AND its own interactive exercises together (there is no separate grammar-only vs. practice-only page per topic) — so when a specific lesson is matched in Course context, that ONE link covers both "where do I study X" and "where do I practise X".
1. If a specific matched lesson genuinely covers the topic, share it first — it's both the explanation and the practice.
2. For a fuller, cumulative review mixing every topic from an entire gradus, point to that gradus's "Te Ipsum Proba" page from Course context (e.g. [Gradus II · Tē Ipsum Proba](.../gradus/elementa/test-yourself.html)) — best offered once several topics from that gradus are already familiar, not as the first stop for a single new topic.
3. If nothing specific matched, offer the relevant gradus overview page as the closest general starting point, and say clearly that it's a general link, not the exact lesson.
- Never invent a "grammar page" and a separate "exercise page" for the same topic — this course doesn't split them that way.`;

// ---- Course catalog helpers -------------------------------------------

// Every real, on-site URL the model is ever allowed to see is resolved
// through this map, built once from course-catalog.json at module load.
// Nothing here is invented at request time.
const CATALOG_INDEX = new Map();
courseCatalog.levels.forEach(function (l) { CATALOG_INDEX.set(l.url, { title: "Gradus " + l.code + " — " + l.name + " (conspectus)", level: l.code, url: l.url, type: "overview" }); });
courseCatalog.resources.forEach(function (r) { CATALOG_INDEX.set(r.url, r); });
const VALID_LEVEL_CODES = new Set(courseCatalog.levels.map(function (l) { return l.code; }));

function absoluteUrl(relativeUrl) {
  return SITE_BASE_URL + relativeUrl;
}

// Normalizes a browser pathname (which may include the GitHub Pages
// project-site subpath, e.g. "/lectioneslatinae/gradus/elementa.html")
// down to the site-root-relative form used as keys in CATALOG_INDEX,
// then looks it up. Returns null (not a guess) when there's no real
// match.
function findCatalogEntryByPath(rawPath) {
  if (!rawPath || typeof rawPath !== "string") return null;
  var p = rawPath.split("?")[0].split("#")[0];
  if (p.charAt(0) === "/") p = p.slice(1);
  if (CATALOG_INDEX.has(p)) return CATALOG_INDEX.get(p);
  for (var url of CATALOG_INDEX.keys()) {
    if (p === url || p.slice(-(url.length + 1)) === "/" + url) return CATALOG_INDEX.get(url);
  }
  return null;
}

// Filler/conversational words to drop from the STUDENT'S QUERY only —
// spans English and Portuguese since students may ask in either
// (or in Latin, which rarely overlaps with these fillers anyway).
var STOPWORDS = new Set([
  "the", "and", "for", "are", "you", "your", "what", "whats", "difference", "between",
  "explain", "show", "tell", "please", "can", "give", "about", "with", "this", "that",
  "how", "why", "when", "where", "who", "which", "does", "doesnt", "dont",
  "not", "from", "into", "over", "more", "than", "like", "want", "need", "help", "some",
  "any", "but", "just", "very", "really", "also", "then", "now", "page", "site", "lesson",
  "lessons", "course", "link", "exercise", "exercises", "correct", "check", "answer",
  "mean", "means", "meaning", "use", "used", "using", "make", "made", "one", "two", "get",
  "got", "know", "think",
  "que", "para", "com", "uma", "um", "sao", "voce", "seu", "sua", "qual", "quais",
  "diferenca", "entre", "explica", "explique", "mostra", "mostre", "diga", "por",
  "favor", "pode", "sobre", "isso", "essa", "esse", "como", "quando", "onde", "quem",
  "nao", "mais", "quero", "quer", "preciso", "ajuda", "ajude", "pagina", "licao",
  "licoes", "curso", "exercicio", "exercicios", "correto", "significa", "significado",
  "usa", "usar", "fazer", "sei", "saber",
]);

function tokenize(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // strip accents/macrons so "declinação"/"dēclīnātiō" both fold to plain ascii
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(function (w) { return w.length >= 3 && !STOPWORDS.has(w); });
}

// Hay (title + aliases) tokenization deliberately skips STOPWORDS
// filtering — a resource's own title must always be fully matchable
// even if one of its words would be filtered as noise on the query
// side.
function tokenizeHay(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(function (w) { return w.length >= 3; });
}

// Exact word-token matching (not substring).
function scoreResource(resource, queryTokens, currentLevel) {
  var haySet = new Set(tokenizeHay(resource.title + " " + (resource.aliases || []).join(" ")));
  var score = 0;
  queryTokens.forEach(function (t) {
    if (haySet.has(t)) score += t.length >= 6 ? 2 : 1;
  });
  if (score > 0 && currentLevel && resource.level === currentLevel) score += 1;
  return score;
}

// Deterministic, non-AI keyword match: current message is weighted
// double (matched twice) over the last couple of turns of history, so
// a short follow-up like "show me the lesson" can still recover the
// topic ("the ablative absolute") that was actually being discussed.
function matchResources(message, cleanHistory, currentLevel) {
  var recentHistoryText = cleanHistory.slice(-4).map(function (m) { return m.content; }).join(" ");
  var queryTokens = tokenize(message).concat(tokenize(message)).concat(tokenize(recentHistoryText));
  if (queryTokens.length === 0) return [];

  var scored = courseCatalog.resources
    .filter(function (r) { return r.type === "lesson" || r.type === "page"; })
    .map(function (r) { return { resource: r, score: scoreResource(r, queryTokens, currentLevel) }; })
    .filter(function (x) { return x.score > 0; });

  scored.sort(function (a, b) { return b.score - a.score; });
  return scored.slice(0, MAX_MATCHED_RESOURCES).map(function (x) { return x.resource; });
}

function resourceLabel(r) {
  if (r.type === "lesson") return "[" + r.level + "] " + r.title + " (lectio, cum exercitationibus)";
  if (r.type === "test") return r.title;
  if (r.type === "overview") return r.title;
  return r.title; // type "page" — site-wide utility page, no gradus
}

// Builds the per-request "Course context" system message: the static
// list of gradus overview pages and Te Ipsum Proba pages (always
// present, small) plus whatever specific pages matched this turn, plus
// the student's current page if the frontend sent one that validates
// against the real catalog. This — not the model — is the only source
// of URLs.
function buildCourseContext(message, cleanHistory, currentPageEntry, currentLevel) {
  var lines = ["Course context — the ONLY real, linkable pages for this turn:", ""];

  lines.push("Gradus overview pages (always valid fallback):");
  courseCatalog.levels.forEach(function (l) {
    lines.push("- [" + l.code + "] Gradus " + l.code + " — " + l.name + " overview: " + absoluteUrl(l.url));
  });
  lines.push("");

  lines.push("“Te Ipsum Proba” pages — full cumulative review, per gradus (each lesson page also has its own exercises; these mix every topic from one gradus):");
  courseCatalog.resources.filter(function (r) { return r.type === "test"; }).forEach(function (r) {
    lines.push("- [" + r.level + "] " + r.title + ": " + absoluteUrl(r.url));
  });
  lines.push("");

  var matches = matchResources(message, cleanHistory, currentLevel);
  if (matches.length > 0) {
    lines.push("Possibly relevant to this question (auto-matched by keywords — use your judgement, only present if genuinely relevant):");
    matches.forEach(function (r) {
      lines.push("- " + resourceLabel(r) + ": " + absoluteUrl(r.url));
    });
  } else {
    lines.push("Possibly relevant to this question: (no automatic match this turn)");
  }
  lines.push("");

  if (currentPageEntry) {
    lines.push("Student's current page: " + resourceLabel(currentPageEntry) + " — " + absoluteUrl(currentPageEntry.url));
  } else {
    lines.push("Student's current page: (unknown)");
  }

  return lines.join("\n");
}

// ---- Helpers ---------------------------------------------------------

function corsHeaders(origin) {
  var allow = origin === ALLOWED_ORIGIN ? origin : ALLOWED_ORIGIN;
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}

function jsonResponse(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status: status,
    headers: Object.assign({ "Content-Type": "application/json" }, corsHeaders(origin)),
  });
}

function dayKey() {
  return new Date().toISOString().slice(0, 10); // YYYY-MM-DD, UTC
}

async function checkAndIncrement(kv, key, limit, ttlSeconds) {
  var current = await kv.get(key);
  var count = current ? parseInt(current, 10) : 0;
  if (count >= limit) return false;
  await kv.put(key, String(count + 1), { expirationTtl: ttlSeconds });
  return true;
}

async function callGroq(env, model, messages) {
  var res = await fetch(GROQ_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + env.GROQ_API_KEY,
    },
    body: JSON.stringify({
      model: model,
      messages: messages,
      max_completion_tokens: MAX_REPLY_TOKENS,
      temperature: 0.4,
    }),
  });
  return res;
}

function cleanContextField(value) {
  if (typeof value !== "string") return "";
  return value.slice(0, MAX_CONTEXT_FIELD_LENGTH).trim();
}

// ---- Main handler ------------------------------------------------

export default {
  async fetch(request, env, ctx) {
    var origin = request.headers.get("Origin") || "";

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(origin) });
    }
    if (request.method !== "POST") {
      return jsonResponse({ error: "Method not allowed" }, 405, origin);
    }
    if (origin !== ALLOWED_ORIGIN) {
      return jsonResponse({ error: "Origin not allowed" }, 403, origin);
    }

    var payload;
    try {
      payload = await request.json();
    } catch (e) {
      return jsonResponse({ error: "Invalid request body" }, 400, origin);
    }

    var message = (payload.message || "").toString().trim();
    var anonId = (payload.anonId || "").toString().slice(0, 80);
    var historyIn = Array.isArray(payload.history) ? payload.history : [];

    if (!message) {
      return jsonResponse({ error: "Empty message" }, 400, origin);
    }
    if (message.length > MAX_MESSAGE_LENGTH) {
      return jsonResponse({ error: "Message too long" }, 400, origin);
    }
    if (!anonId) {
      return jsonResponse({ error: "Missing client identifier" }, 400, origin);
    }

    // --- Course/page context sent by the frontend — never trusted as
    // free text; only used as a lookup key into the real catalog, or
    // (for currentLevel) checked against the known gradus codes (I-VII).
    // If it doesn't validate, it's simply dropped rather than passed
    // through.
    var rawPage = cleanContextField(payload.page);
    var rawLessonUrl = cleanContextField(payload.currentLessonUrl);
    var rawLevel = cleanContextField(payload.currentLevel).toUpperCase();

    var currentPageEntry = findCatalogEntryByPath(rawLessonUrl) || findCatalogEntryByPath(rawPage);
    var currentLevel = VALID_LEVEL_CODES.has(rawLevel) ? rawLevel : (currentPageEntry ? currentPageEntry.level : null);

    // --- Rate limiting -------------------------------------------------
    var ip = request.headers.get("CF-Connecting-IP") || "unknown";
    var burstKey = "burst:" + ip;
    var dailyKey = "daily:" + anonId + ":" + dayKey();

    var burstOk = await checkAndIncrement(env.AI_TEACHER_KV, burstKey, BURST_LIMIT_PER_IP, BURST_WINDOW_SECONDS);
    if (!burstOk) {
      return jsonResponse({ error: "Too many requests, please slow down." }, 429, origin);
    }
    var dailyOk = await checkAndIncrement(env.AI_TEACHER_KV, dailyKey, DAILY_LIMIT_PER_ANON, 60 * 60 * 24);
    if (!dailyOk) {
      return jsonResponse({ error: "Daily limit reached" }, 429, origin);
    }

    // --- Build the message list for Groq --------------------------
    var cleanHistory = historyIn
      .filter(function (m) { return m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string"; })
      .slice(-MAX_HISTORY_MESSAGES)
      .map(function (m) { return { role: m.role, content: String(m.content).slice(0, MAX_MESSAGE_LENGTH) }; });

    var courseContext = buildCourseContext(message, cleanHistory, currentPageEntry, currentLevel);

    var messages = [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "system", content: courseContext },
    ]
      .concat(cleanHistory)
      .concat([{ role: "user", content: message }]);

    // --- Call Groq, with a fallback model if the primary is out of quota
    try {
      var res = await callGroq(env, PRIMARY_MODEL, messages);
      if (res.status === 429) {
        res = await callGroq(env, FALLBACK_MODEL, messages);
      }
      if (!res.ok) {
        var errText = await res.text();
        console.error("GROQ_BODY: " + res.status + " " + errText);
        return jsonResponse({ error: "AI provider error" }, 502, origin);
      }
      var data = await res.json();
      var reply = data && data.choices && data.choices[0] && data.choices[0].message
        ? data.choices[0].message.content
        : "Ignosce, respōnsum generāre nōn potuī. Itera, quaeso.";
      return jsonResponse({ reply: reply }, 200, origin);
    } catch (err) {
      console.error("Worker error:", err);
      return jsonResponse({ error: "Unexpected server error" }, 500, origin);
    }
  },
};
