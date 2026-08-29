# Magister AI — backend deployment

This folder is **not** part of the GitHub Pages site (nothing under
`worker/` is linked from any HTML page). It's the source for a
separate Cloudflare Worker that acts as a secure proxy between your
website and the Groq API — the only place your Groq API key lives.

Ported from the sibling English-course project's `worker/` (same
architecture: CORS, rate limiting, Groq call, course-catalog
grounding) — this is a **separate, independently deployed Worker**
with its own name, its own KV namespace, and its own Classical Latin
system prompt/course catalog. It does not share state with the
English course's Worker, and deploying one has no effect on the other.

## Why a separate deployment?

GitHub Pages only serves static files — there's no way to keep a
secret out of the browser if the AI call happened directly from your
site's JavaScript. The Worker runs on Cloudflare's servers, holds the
key there, and your site's JS only ever talks to the Worker.

## One-time setup (about 15 minutes)

### 1. Create free accounts (no credit card required for either)
- **Groq**: [console.groq.com](https://console.groq.com) → sign up → **API Keys** → Create API Key. Copy it somewhere safe. (If you already deployed the English course's Worker, you can reuse the same Groq account/key — Groq's free-tier quota is shared per-account either way, so keep that in mind when tuning `DAILY_LIMIT_PER_ANON` below.)
- **Cloudflare**: [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) → sign up, or reuse the account you already created for the English course's Worker — a Cloudflare account can host multiple, independent Workers.

### 2. Install Wrangler (Cloudflare's deploy tool)
```bash
npm install -g wrangler
wrangler login
```
This opens a browser window to connect Wrangler to your Cloudflare account. Skip this if you already did it for the English course's Worker — it's the same account/tool.

### 3. Create the KV namespace (used for rate-limit counters)
```bash
cd worker
wrangler kv namespace create AI_TEACHER_KV
```
This prints something like:
```
id = "abcd1234..."
```
Copy that `id` value into `wrangler.toml`, replacing `REPLACE_WITH_YOUR_KV_NAMESPACE_ID`. **Do not reuse the English course's KV namespace id** — each course needs its own so their rate-limit counters (and daily quotas) stay independent.

### 4. Set your Groq API key as a secret (never committed to git)
```bash
wrangler secret put GROQ_API_KEY
```
Paste your Groq key when prompted (the same key as the English course's Worker is fine, or a separate one). This stores it encrypted on Cloudflare's side — it is never written to any file in this repo.

### 5. Confirm the allowed origin
Open `worker.js` and check the top of the file:
```js
const ALLOWED_ORIGIN = "https://renangrossi.github.io";
```
This is just the scheme+host of GitHub Pages — the same value works for every repo/project page under that account, so it's already correct for `lectioneslatinae`. Update it only if the site moves to a custom domain.

### 6. Deploy
```bash
wrangler deploy
```
This prints your live Worker URL, something like:
```
https://ai-teacher-la.your-subdomain.workers.dev
```
Note the worker is named `ai-teacher-la` (see `wrangler.toml`) specifically so it doesn't collide with the English course's `ai-teacher` Worker if both are deployed under the same Cloudflare account.

### 7. Point the website at your Worker
The `data-ai-endpoint` attribute is set in **two places** in this repo — both need the real URL from Step 6:

1. `scripts/site_chrome.py` — the `<script src="{rel}assets/js/ai-teacher.js" data-ai-endpoint="...">` line in `footer()`. After editing, regenerate every page that uses it:
   ```bash
   python3 scripts/build_lesson.py curriculum/*/*.json
   python3 scripts/build_level_page.py --all
   python3 scripts/build_hub_pages.py
   python3 scripts/build_placement_test.py
   python3 scripts/build_static_pages.py
   ```
2. The two hand-authored pages that don't go through `site_chrome.py`'s generator scripts: `index.html` and `lexicon.html` — update the same `data-ai-endpoint` attribute directly in each file.

Commit and push as usual — the chat widget will now reach your live Worker.

## Adjusting limits

At the top of `worker.js`:
- `DAILY_LIMIT_PER_ANON` — questions per browser per day (default 20).
- `BURST_LIMIT_PER_IP` / `BURST_WINDOW_SECONDS` — short-term abuse brake (default 8 requests/60s per IP).
- `MAX_MESSAGE_LENGTH` — longest question accepted (keep in sync with the `maxlength` on the textarea rendered by `scripts/site_chrome.py`'s `footer()`, and in `index.html`/`lexicon.html`, if you change it).

## Course catalog (`course-catalog.json`)

So Magister AI can recommend a *real* lesson link instead of guessing
one, `worker.js` imports `course-catalog.json` — a list of every real
course page (the 7 gradus overview pages, all lesson pages, the 7
per-gradus "Te Ipsum Proba" cumulative-review pages, and the
site-wide utility pages like Lexicon/Exercitationes/Examina) with
their real on-site URLs. At request time the Worker does a
lightweight, deterministic keyword match between the student's
message (plus recent conversation) and this catalog, and only ever
hands the model URLs that come out of that match — the model is
instructed to never output a URL that wasn't supplied to it that
turn, so it's structurally unable to invent one.

**Generated once from `assets/data/search-index.json`, then hand-enriched — it is not auto-rebuilt.** The base entries (title/url/level/type) came straight from the site's own search index (see `scripts/build_exercise_index.py`), since every lesson title there is already a real, current on-site path. The 7 "Te Ipsum Proba" test-yourself pages were added by hand (they're deliberately excluded from on-site search, but are still real, linkable pages). Most lesson entries also carry `aliases`: since lesson titles are in Latin but students may ask in English or Portuguese, a bounded synonym map (declension/declinação/dēclīnātiō, subjunctive/subjuntivo/coniūnctīvus, etc.) was merged in once to bridge the three languages — see git history for the generation approach. If you add, rename, or move a lesson/gradus page, update `course-catalog.json` by hand (re-deriving the base entries from a fresh `assets/data/search-index.json` is the fastest starting point if many pages changed at once).

Each entry:
```json
{ "level": "II", "title": "Declinatio Prima", "url": "gradus/elementa/declinatio-prima.html", "type": "lesson", "aliases": ["declension", "declinação", "first"] }
```
- `url` is site-root-relative (no leading slash, no domain) — the Worker resolves it against `SITE_BASE_URL` in `worker.js`.
- `type` is `"lesson"` (a gradus lesson page — grammar explanation AND its own exercises together), `"test"` (a gradus's "Te Ipsum Proba" cumulative review page), or `"page"` (site-wide utility pages: Exercitationes, Examina Ficta, Varia, Lexicon, Probatio Praeliminaris, Iter Meum, Recognitio Hodierna, Verba Irregularia).
- `level` is the Roman-numeral gradus code (`"I"`–`"VII"`), or `null` for a `"page"`-type entry that isn't gradus-specific.
- Optional `aliases`: extra search terms in Latin/English/Portuguese for topics where student phrasing doesn't share words with the on-site Latin title.

After editing the catalog, redeploy with `wrangler deploy` (it's bundled into the Worker at deploy time, not fetched at runtime).

## What data is sent/stored

- The student's message and the current conversation (kept in the browser tab's memory only, lost on reload) are sent to the Worker, then to Groq, to generate a reply.
- The Worker stores nothing except two small rate-limit counters in KV: an anonymous ID (a random string generated in the browser, no personal info) plus a request count, both auto-expiring after 24 hours or 60 seconds.
- Per Groq's terms (worth re-checking at console.groq.com before relying on it long-term), free-tier requests may be logged for abuse monitoring; nothing here is guaranteed private, so the frontend also tells students not to share personal information.

## Free-tier reality check

Groq's `openai/gpt-oss-120b` free tier is roughly 1,000 requests/day
**shared across every visitor to your site**, not per-student — and if
you're using the *same* Groq account/key for both the English and
Latin courses, that quota is shared across both sites too. The Worker
automatically falls back to the `openai/gpt-oss-20b` model (same
~1,000 requests/day, but a separate quota pool) if the primary model's
daily quota is exhausted, so the feature keeps working at slightly
lower quality rather than going down entirely. The per-browser daily
cap (`DAILY_LIMIT_PER_ANON`) exists specifically to stop one visitor
from using up the whole day's shared quota.
