/*!
 * Lectiones Latinae — Progressus Ludicus (XP, series, insignia)
 * ------------------------------------------------------------------
 * Phase 1: fully offline, localStorage-only. No account, no server,
 * works the same on GitHub Pages as anywhere else. Nothing here ever
 * sends data off the student's own browser.
 *
 * Ported from the sibling English-course project's assets/js/progress.js
 * (identical mechanics/storage shape/event wiring) — LEVELS is retargeted
 * to this course's seven Latin-named Gradus, and every user-facing
 * string (badge names/descriptions, toasts, panel copy) is translated to
 * Latin. See docs/gamification.md here for the schema and tuning guide.
 *
 * Responsibilities:
 *   1. Award XP ("PE" — Puncta Experientiae) for exercise blocks (via
 *      the "exercise:submitted" event exercises.js already dispatches,
 *      plus a direct call — see the bottom of exercises.js's submit
 *      handler).
 *   2. Track a calendar-day streak ("series").
 *   3. Unlock data-driven badges ("insignia").
 *   4. Render a compact header widget + short "+PE" toasts.
 *   5. Detect "whole page" completion (Te Ipsum Proba sections, the
 *      Probatio Praeliminaris) by comparing the exercises present on
 *      the current page against what's already been recorded, and
 *      award the larger one-off bonus for finishing all of them.
 *
 * Public API (window.ProgressTracker):
 *   recordExerciseResult({ level, exerciseId, correct, total, perfect })
 *   recordTestProgress({ type, level })   // "test-yourself" | "placement"
 *   getState()                            // read-only snapshot
 *   resetProgress()                       // wipes local progress (used by iter.html)
 *   XP, BADGES                            // config, read here or from iter.html
 * ------------------------------------------------------------------ */
(function () {
  "use strict";

  var STORAGE_KEY = "ll_progress";
  var SCHEMA_VERSION = 1;

  /* ------------------------------------------------------------- *
   * Toast timing
   * ------------------------------------------------------------- */
  var TOAST_VISIBLE_MS = 2400 * 3; // ~7.2s
  var TOAST_EXIT_MS = 350;

  /* ------------------------------------------------------------- *
   * XP table — the single place to tune point values.
   * ------------------------------------------------------------- */
  var XP = {
    exercise: 10,       // submitting an exercise block, first time (any score)
    perfectBonus: 5,    // extra, only if that first submission was 100%
    testYourself: 25,   // completing every exercise block on a Te Ipsum Proba page
    placement: 40,      // completing the Probatio Praeliminaris
    dailyBonus: 5,       // first activity of a new calendar day (on top of streak +1)
  };

  // Seven Latin-named Gradus, short-code first (used as data-level-code
  // and in badge ids), matching scripts/site_chrome.py's LEVELS tuple.
  var LEVELS = ["I", "II", "III", "IV", "V", "VI", "VII"];
  var LEVEL_NAMES = {
    I: "Fundamenta", II: "Elementa", III: "Progressus",
    IV: "Media", V: "Provectus", VI: "Altior", VII: "Auctores",
  };
  var LEVEL_GENITIVE = {
    I: "Fundamentorum", II: "Elementorum", III: "Progressūs",
    IV: "Mediorum", V: "Provectūs", VI: "Altioris", VII: "Auctorum",
  };

  // How many exercise blocks actually exist per level (level overview
  // page + every individual lesson page combined). "Explorator"
  // thresholds below are ~30% of that total, so the badge means about
  // the same amount of real effort at every level instead of
  // penalizing students on the levels with less standalone content.
  // Kept in sync with the real curriculum by scripts/build_exercise_index.py
  // (see its printed counts) whenever a level's lesson set changes.
  var LEVEL_EXERCISE_COUNTS = { I: 27, II: 49, III: 27, IV: 35, V: 24, VI: 20, VII: 20 };
  function explorerThreshold(level) {
    var total = LEVEL_EXERCISE_COUNTS[level] || 36;
    return Math.max(6, Math.round(total * 0.3));
  }

  /* ------------------------------------------------------------- *
   * Badge XP
   * ------------------------------------------------------------- */
  var BADGE_XP_DEFAULT = 10;
  var BADGE_XP = {
    first_steps: 10,
    perfectionist: 10,
    streak_3: 10,
    streak_7: 15,
    streak_14: 20,
    streak_30: 30,
    placement_done: 15,
    comeback: 15,
    first_test_yourself: 15,
    xp_100: 10,
    xp_250: 15,
    xp_500: 20,
    xp_1000: 25,
    no_hints_needed: 15,
    sherlock: 15,
    dictionary_power_user: 15,
    polyglot: 25,
    night_owl: 10,
    early_bird: 10,
    topic_complete: 20,
  };
  LEVELS.forEach(function (l) { BADGE_XP[l.toLowerCase() + "_explorer"] = 20; });

  function badgeXp(id) {
    return typeof BADGE_XP[id] === "number" ? BADGE_XP[id] : BADGE_XP_DEFAULT;
  }

  /* ------------------------------------------------------------- *
   * Badge definitions — data-driven. `check(state)` returns true
   * once the badge should be (or stay) unlocked.
   * ------------------------------------------------------------- */
  var BADGES = [
    {
      id: "first_steps", icon: "🌱", name: "Prima Vestigia",
      desc: "Confice primam exercitationem tuam.",
      check: function (s) { return countExercisesDone(s) >= 1; },
    },
    {
      id: "perfectionist", icon: "🎯", name: "Immaculatus",
      desc: "In una exercitatione centesimum centesimo obtine (100%).",
      check: function (s) { return countPerfect(s) >= 1; },
    },
    {
      id: "streak_3", icon: "🔥", name: "Series Trium Dierum",
      desc: "Tribus diebus continuis exercere.",
      check: function (s) { return s.streak.count >= 3; },
    },
    {
      id: "streak_7", icon: "🔥", name: "Series Septem Dierum",
      desc: "Septem diebus continuis exercere.",
      check: function (s) { return s.streak.count >= 7; },
    },
    {
      id: "placement_done", icon: "🧭", name: "Gradum Tuum Cognosce",
      desc: "Probationem Praeliminarem confice.",
      check: function (s) { return !!s.pagesCompleted.placement; },
    },
    {
      id: "streak_14", icon: "🔥", name: "Series Quattuordecim Dierum",
      desc: "Quattuordecim diebus continuis exercere.",
      check: function (s) { return s.streak.count >= 14; },
    },
    {
      id: "streak_30", icon: "🔥", name: "Series Triginta Dierum",
      desc: "Triginta diebus continuis exercere.",
      check: function (s) { return s.streak.count >= 30; },
    },
    {
      id: "comeback", icon: "🔄", name: "Reditus",
      desc: "Post intermissam seriem redi et aliam exercitationem confice.",
      check: function (s) { return !!(s.streak && s.streak.brokenOnce); },
    },
    {
      id: "first_test_yourself", icon: "📝", name: "Te Ipsum Probavisti",
      desc: "Primum omnino paginam “Te Ipsum Proba” totam confice.",
      check: function (s) {
        return Object.keys(s.pagesCompleted).some(function (k) { return k.indexOf("test-yourself:") === 0; });
      },
    },
    {
      id: "xp_100", icon: "⭐", name: "C PE",
      desc: "Centum Puncta Experientiae (PE) tota collige.",
      check: function (s) { return s.xp >= 100; },
    },
    {
      id: "xp_250", icon: "🌟", name: "CCL PE",
      desc: "Ducenta quinquaginta PE tota collige.",
      check: function (s) { return s.xp >= 250; },
    },
    {
      id: "xp_500", icon: "💫", name: "D PE",
      desc: "Quingenta PE tota collige.",
      check: function (s) { return s.xp >= 500; },
    },
    {
      id: "xp_1000", icon: "👑", name: "M PE",
      desc: "Mille PE tota collige.",
      check: function (s) { return s.xp >= 1000; },
    },
    {
      id: "no_hints_needed", icon: "💎", name: "Sine Ope",
      desc: "In quinque diversis exercitationibus centesimum centesimo obtine.",
      check: function (s) { return countPerfect(s) >= 5; },
    },
    {
      id: "sherlock", icon: "🕵️", name: "Investigator",
      desc: "Primum verbum in lexico quaere.",
      check: function (s) { return (s.dictionaryUses || 0) >= 1; },
    },
    {
      id: "dictionary_power_user", icon: "📚", name: "Lexicophilus",
      desc: "Decem verba in lexico quaere.",
      check: function (s) { return (s.dictionaryUses || 0) >= 10; },
    },
    {
      id: "polyglot", icon: "🌍", name: "Per Omnes Gradus",
      desc: "Confice saltem unam exercitationem in tribus gradibus diversis.",
      check: function (s) { return countLevelsWithActivity(s) >= 3; },
    },
    {
      id: "night_owl", icon: "🦉", name: "Noctua",
      desc: "Exercitationem inter mediam noctem et horam quintam confice (secundum horologium tuum).",
      check: function (s) { return !!(s.timeFlags && s.timeFlags.nightOwl); },
    },
    {
      id: "early_bird", icon: "🐦", name: "Alauda Matutina",
      desc: "Exercitationem inter horam quintam et septimam matutinam confice.",
      check: function (s) { return !!(s.timeFlags && s.timeFlags.earlyBird); },
    },
  ].concat(LEVELS.map(function (level) {
    var threshold = explorerThreshold(level);
    return {
      id: level.toLowerCase() + "_explorer",
      icon: "🏅",
      name: "Explorator " + LEVEL_GENITIVE[level],
      desc: "Confice " + threshold + " exercitationes in Gradu " + level + " (" + LEVEL_NAMES[level] + ").",
      level: level,
      threshold: threshold,
      check: function (s) {
        return ((s.levelStats[level] && s.levelStats[level].exercisesDone) || 0) >= threshold;
      },
    };
  }));

  function countExercisesDone(state) {
    var n = 0;
    for (var id in state.exercises) if (state.exercises.hasOwnProperty(id)) n++;
    return n;
  }
  function countPerfect(state) {
    var n = 0;
    for (var id in state.exercises) {
      if (state.exercises.hasOwnProperty(id) && state.exercises[id].perfect) n++;
    }
    return n;
  }

  function countLevelsWithActivity(state) {
    var n = 0;
    LEVELS.forEach(function (l) {
      if (state.levelStats[l] && state.levelStats[l].exercisesDone > 0) n++;
    });
    return n;
  }

  function hasProgress(state) {
    return state.xp > 0 || countExercisesDone(state) > 0 || state.badges.length > 0;
  }

  /* ------------------------------------------------------------- *
   * Storage
   * ------------------------------------------------------------- */
  function defaultState() {
    var levelStats = {};
    LEVELS.forEach(function (l) { levelStats[l] = { xp: 0, exercisesDone: 0 }; });
    return {
      version: SCHEMA_VERSION,
      xp: 0,
      streak: { count: 0, lastActiveDate: "", brokenOnce: false },
      badges: [],
      exercises: {},
      levelStats: levelStats,
      pagesCompleted: {},
      dictionaryUses: 0,
      topicsCompleted: {},
      timeFlags: {},
    };
  }

  function loadState() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultState();
      var parsed = JSON.parse(raw);
      if (!parsed || parsed.version !== SCHEMA_VERSION) return defaultState();
      var base = defaultState();
      base.xp = typeof parsed.xp === "number" ? parsed.xp : 0;
      base.streak = parsed.streak || base.streak;
      base.badges = Array.isArray(parsed.badges) ? parsed.badges : [];
      base.exercises = parsed.exercises || {};
      base.pagesCompleted = parsed.pagesCompleted || {};
      base.dictionaryUses = typeof parsed.dictionaryUses === "number" ? parsed.dictionaryUses : 0;
      base.topicsCompleted = parsed.topicsCompleted || {};
      base.timeFlags = parsed.timeFlags || {};
      Object.keys(parsed.levelStats || {}).forEach(function (l) {
        if (base.levelStats[l]) base.levelStats[l] = parsed.levelStats[l];
      });
      return base;
    } catch (e) {
      return defaultState();
    }
  }

  function saveState(state) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      // Storage full/blocked — progress just won't persist this run.
    }
  }

  /* ------------------------------------------------------------- *
   * Streak (calendar day, based on the student's own device clock)
   * ------------------------------------------------------------- */
  function todayStr() {
    var d = new Date();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return d.getFullYear() + "-" + m + "-" + day;
  }
  function daysBetween(a, b) {
    var msPerDay = 24 * 60 * 60 * 1000;
    var da = new Date(a + "T00:00:00");
    var db = new Date(b + "T00:00:00");
    return Math.round((db - da) / msPerDay);
  }

  function touchStreak(state) {
    var today = todayStr();
    if (state.streak.lastActiveDate === today) return { isNewDay: false };
    var hadPreviousActivity = !!state.streak.lastActiveDate;
    var gap = hadPreviousActivity ? daysBetween(state.streak.lastActiveDate, today) : null;
    if (gap === 1) {
      state.streak.count += 1;
    } else {
      if (hadPreviousActivity && gap > 1) state.streak.brokenOnce = true;
      state.streak.count = 1;
    }
    state.streak.lastActiveDate = today;
    return { isNewDay: true };
  }

  /* ------------------------------------------------------------- *
   * XP + badge helpers
   * ------------------------------------------------------------- */
  var pendingToasts = [];

  function awardXp(state, amount, level, label) {
    if (amount <= 0) return;
    state.xp += amount;
    if (level && state.levelStats[level]) state.levelStats[level].xp += amount;
    pendingToasts.push({ kind: "xp", text: "+" + amount + " PE" + (label ? " · " + label : "") });
  }

  function grantBadgeXp(state, badge) {
    var amount = badgeXp(badge.id);
    if (amount <= 0) return 0;
    state.xp += amount;
    if (badge.level && state.levelStats[badge.level]) state.levelStats[badge.level].xp += amount;
    return amount;
  }

  function evaluateBadges(state) {
    BADGES.forEach(function (b) {
      if (state.badges.indexOf(b.id) !== -1) return;
      if (!b.check(state)) return;
      state.badges.push(b.id);
      var xpAwarded = grantBadgeXp(state, b);
      pendingToasts.push({
        kind: "badge",
        text: b.name + " obtentum" + (xpAwarded > 0 ? " · +" + xpAwarded + " PE" : ""),
        icon: b.icon,
      });
    });
  }

  /* ------------------------------------------------------------- *
   * Page inventory
   * ------------------------------------------------------------- */
  function detectPageKind() {
    var path = window.location.pathname;
    if (/test-yourself\.html$/.test(path)) return "test-yourself";
    if (/probatio\.html$/.test(path)) return "placement";
    // A single nested lesson page (e.g. gradus/ii/sum.html) teaches
    // exactly one topic. Level overview pages (gradus/ii.html — no
    // nested segment) are deliberately excluded, same rationale as the
    // English original.
    if (/\/gradus\/[^/]+\/[^/]+\.html$/.test(path)) return "topic";
    return "lesson";
  }

  function topicSlug() {
    var m = window.location.pathname.match(/\/([^/]+)\.html$/);
    return m ? m[1] : "";
  }

  function slugToTitle(slug) {
    return slug.replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function pageInventory() {
    var ids = [];
    document.querySelectorAll(".exercise-block script.exercise-data").forEach(function (scriptEl) {
      try {
        var data = JSON.parse(scriptEl.textContent);
        if (data && data.id && data.type !== "writing") ids.push(data.id);
      } catch (e) { /* ignore malformed block, doesn't block the rest */ }
    });
    return ids;
  }

  function maybeCompletePage(state, pageKind, level, inventory) {
    if (!inventory.length) return;
    if (pageKind === "topic") {
      maybeCompleteTopic(state, level, inventory);
      return;
    }
    if (pageKind === "lesson") return;
    var key = pageKind === "placement" ? "placement" : "test-yourself:" + (level || "");
    if (state.pagesCompleted[key]) return;
    var allDone = inventory.every(function (id) { return !!state.exercises[id]; });
    if (!allDone) return;
    recordTestProgressInternal(state, { type: pageKind, level: level });
  }

  function maybeCompleteTopic(state, level, inventory) {
    var slug = topicSlug();
    if (!slug) return;
    var topicId = (level || "?") + ":" + slug;
    if (state.topicsCompleted[topicId]) return;
    var allDone = inventory.every(function (id) { return !!state.exercises[id]; });
    if (!allDone) return;
    var name = (level ? level + " · " : "") + slugToTitle(slug);
    state.topicsCompleted[topicId] = { name: name, level: level || "", awardedAt: todayStr() };
    var xpAwarded = badgeXp("topic_complete");
    if (xpAwarded > 0) {
      state.xp += xpAwarded;
      if (level && state.levelStats[level]) state.levelStats[level].xp += xpAwarded;
    }
    pendingToasts.push({
      kind: "badge",
      text: "Argumentum confectum: " + name + (xpAwarded > 0 ? " · +" + xpAwarded + " PE" : ""),
      icon: "📘",
    });
  }

  function recordTestProgressInternal(state, opts) {
    var type = opts.type;
    var level = opts.level;
    var key = type === "placement" ? "placement" : "test-yourself:" + (level || "");
    if (state.pagesCompleted[key]) return;
    state.pagesCompleted[key] = true;
    if (type === "placement") {
      awardXp(state, XP.placement, null, "Probatio Praeliminaris confecta");
    } else {
      awardXp(state, XP.testYourself, level, "Te Ipsum Proba (" + (level || "") + ") confectum");
    }
    evaluateBadges(state);
  }

  /* ------------------------------------------------------------- *
   * Public API
   * ------------------------------------------------------------- */
  function recordExerciseResult(opts) {
    opts = opts || {};
    var exerciseId = opts.exerciseId;
    if (!exerciseId) return getState();
    var level = (opts.level || "").toUpperCase();
    var total = typeof opts.total === "number" ? opts.total : 0;
    var correct = typeof opts.correct === "number" ? opts.correct : 0;
    var perfect = typeof opts.perfect === "boolean" ? opts.perfect : (total > 0 && correct === total);

    var state = loadState();
    touchStreakAndDailyBonus(state);

    var existing = state.exercises[exerciseId];
    if (!existing) {
      awardXp(state, XP.exercise, level, "Exercitatio confecta");
      if (perfect) awardXp(state, XP.perfectBonus, level, "Summa scientia");
      state.exercises[exerciseId] = { bestCorrect: correct, total: total, xpAwarded: true, perfect: perfect };
      if (level && state.levelStats[level]) state.levelStats[level].exercisesDone += 1;
    } else {
      existing.bestCorrect = Math.max(existing.bestCorrect, correct);
      existing.total = total || existing.total;
      existing.perfect = existing.perfect || perfect;
    }

    touchTimeOfDayFlags(state);
    evaluateBadges(state);

    var pageKind = detectPageKind();
    if (pageKind !== "lesson") maybeCompletePage(state, pageKind, level, pageInventory());

    saveState(state);
    flushUI(state);
    return getStateFrom(state);
  }

  function recordTestProgress(opts) {
    opts = opts || {};
    var state = loadState();
    touchStreakAndDailyBonus(state);
    recordTestProgressInternal(state, opts);
    saveState(state);
    flushUI(state);
    return getStateFrom(state);
  }

  function touchTimeOfDayFlags(state) {
    var hour = new Date().getHours();
    if (hour >= 0 && hour < 5) state.timeFlags.nightOwl = true;
    if (hour >= 5 && hour < 7) state.timeFlags.earlyBird = true;
  }

  function touchStreakAndDailyBonus(state) {
    var wasCount = state.streak.count;
    var res = touchStreak(state);
    if (res.isNewDay) {
      pendingToasts.push({ kind: "streak", text: "Series: dies " + state.streak.count + "!" });
      if (XP.dailyBonus > 0 && wasCount > 0) awardXp(state, XP.dailyBonus, null, "Praemium Cotidianum");
    }
  }

  function recordDictionaryUse() {
    var state = loadState();
    state.dictionaryUses = (state.dictionaryUses || 0) + 1;
    evaluateBadges(state);
    saveState(state);
    flushUI(state);
    return getStateFrom(state);
  }

  function getStateFrom(state) {
    return JSON.parse(JSON.stringify(state));
  }
  function getState() {
    return getStateFrom(loadState());
  }

  function resetProgress() {
    try { window.localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
    if (window.MasteryTracker && typeof window.MasteryTracker.resetMastery === "function") {
      window.MasteryTracker.resetMastery();
    }
    flushUI(loadState());
  }

  /* ------------------------------------------------------------- *
   * UI — header widget (button + dropdown panel) and toasts.
   * ------------------------------------------------------------- */
  var els = null;

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "html") node.innerHTML = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) node.appendChild(c); });
    return node;
  }

  function flameIcon(flameClass) {
    var s = el("span", { "aria-hidden": "true", class: flameClass });
    s.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2s6 5.5 6 11a6 6 0 1 1-12 0c0-1.6.7-2.8 1.5-4 .3 1.2 1 1.8 1.7 1.8C10.2 10.8 9.5 8 12 2Z"/></svg>';
    return s;
  }

  function closeMobileNav() {
    var nav = document.getElementById("primary-nav");
    var navToggle = document.querySelector("[data-nav-toggle]");
    if (nav) nav.classList.remove("is-open");
    if (navToggle) navToggle.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  function buildWidget() {
    var navUtility = document.querySelector(".nav-utility");
    var navList = document.querySelector("#primary-nav .primary-nav__list");
    var dictLink = navList && navList.querySelector('a[href$="lexicon.html"]');
    var dictItem = dictLink ? dictLink.closest("li") : null;

    var toggle = el("button", {
      type: "button",
      class: "progress-toggle progress-toggle--pill",
      "aria-haspopup": "dialog",
      "aria-expanded": "false",
      "aria-label": "Progressus tuus: PE, series, et insignia",
    });
    var xpEl = el("span", { class: "progress-toggle__xp", text: "0 PE" });
    toggle.appendChild(flameIcon("progress-toggle__flame"));
    var streakEl = el("span", { class: "progress-toggle__streak", text: "0" });
    toggle.appendChild(streakEl);
    toggle.appendChild(el("span", { class: "progress-toggle__dot", "aria-hidden": "true", text: "·" }));
    toggle.appendChild(xpEl);

    var menuItem = null, menuToggle = null, menuStreakEl = null, menuXpEl = null;
    if (dictItem) {
      menuToggle = el("button", {
        type: "button",
        class: "progress-menu-toggle",
        "aria-haspopup": "dialog",
        "aria-expanded": "false",
      });
      menuToggle.appendChild(el("span", { class: "progress-menu-toggle__label", text: "Progressus" }));
      var stat = el("span", { class: "progress-menu-toggle__stat" });
      stat.appendChild(flameIcon("progress-menu-toggle__flame"));
      menuStreakEl = el("span", { class: "progress-menu-toggle__streak", text: "0" });
      stat.appendChild(menuStreakEl);
      stat.appendChild(el("span", { class: "progress-menu-toggle__dot", "aria-hidden": "true", text: "·" }));
      menuXpEl = el("span", { class: "progress-menu-toggle__xp", text: "0 PE" });
      stat.appendChild(menuXpEl);
      menuToggle.appendChild(stat);

      menuItem = el("li", { class: "primary-nav__item primary-nav__item--progress" }, [menuToggle]);
      dictItem.insertAdjacentElement("afterend", menuItem);
    }

    var panel = el("div", { class: "progress-panel", role: "dialog", "aria-label": "Progressus tuus" });
    panel.hidden = true;

    if (navUtility) {
      navUtility.insertBefore(toggle, navUtility.firstChild);
      navUtility.parentNode.style.position = navUtility.parentNode.style.position || "relative";
      document.body.appendChild(panel);
    } else {
      toggle.classList.add("progress-toggle--floating");
      toggle.classList.remove("progress-toggle--pill");
      document.body.appendChild(toggle);
      document.body.appendChild(panel);
    }

    function positionPanel() {
      panel.classList.remove("progress-panel--sheet");
      var r = toggle.getBoundingClientRect();
      panel.style.position = "fixed";
      panel.style.top = Math.round(r.bottom + 8) + "px";
      var right = Math.max(8, window.innerWidth - r.right);
      panel.style.right = Math.round(right) + "px";
      panel.style.left = "auto";
    }

    function positionPanelAsSheet() {
      panel.style.position = "";
      panel.style.top = "";
      panel.style.right = "";
      panel.style.left = "";
      panel.classList.add("progress-panel--sheet");
    }

    function open(fromMenu) {
      renderPanel(loadState());
      panel.hidden = false;
      if (fromMenu) {
        closeMobileNav();
        positionPanelAsSheet();
      } else {
        positionPanel();
        window.addEventListener("resize", positionPanel);
      }
      toggle.setAttribute("aria-expanded", "true");
      if (menuToggle) menuToggle.setAttribute("aria-expanded", "true");
      document.addEventListener("click", onDocClick, true);
    }
    function close() {
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      if (menuToggle) menuToggle.setAttribute("aria-expanded", "false");
      document.removeEventListener("click", onDocClick, true);
      window.removeEventListener("resize", positionPanel);
    }
    function onDocClick(e) {
      if (panel.contains(e.target) || toggle.contains(e.target)) return;
      if (menuToggle && menuToggle.contains(e.target)) return;
      close();
    }
    toggle.addEventListener("click", function () {
      if (panel.hidden) open(false); else close();
    });
    if (menuToggle) {
      menuToggle.addEventListener("click", function () {
        if (panel.hidden) open(true); else close();
      });
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !panel.hidden) close();
    });

    var toastHost = el("div", { class: "xp-toast-host", "aria-live": "polite" });
    document.body.appendChild(toastHost);

    els = {
      toggle: toggle, xpEl: xpEl, streakEl: streakEl,
      menuItem: menuItem, menuToggle: menuToggle, menuStreakEl: menuStreakEl, menuXpEl: menuXpEl,
      panel: panel, toastHost: toastHost, close: close,
    };
  }

  function badgeGridHtml(state) {
    return BADGES.map(function (b) {
      var earned = state.badges.indexOf(b.id) !== -1;
      return (
        '<li class="badge-chip' + (earned ? " is-earned" : "") + '" title="' + escapeHtml(b.desc) + '">' +
        '<span class="badge-chip__icon" aria-hidden="true">' + (earned ? b.icon : "🔒") + "</span>" +
        '<span class="badge-chip__name">' + escapeHtml(b.name) + "</span>" +
        "</li>"
      );
    }).join("");
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = String(s || "");
    return d.innerHTML;
  }

  function topicNames(state) {
    return Object.keys(state.topicsCompleted).map(function (id) { return state.topicsCompleted[id].name; }).sort();
  }

  function topicSummaryHtml(state) {
    var n = topicNames(state).length;
    if (!n) return "";
    return '<p class="progress-panel__hint">📘 ' + n + " argument" + (n === 1 ? "um confectum." : "a confecta.") + "</p>";
  }

  function topicListHtml(state) {
    var names = topicNames(state);
    if (!names.length) return '<p class="progress-panel__hint">Nullum argumentum adhuc confectum — omnes exercitationes unius paginae confice ut insigne obtineas.</p>';
    return '<ul class="topic-list">' + names.map(function (n) { return "<li>" + escapeHtml(n) + "</li>"; }).join("") + "</ul>";
  }

  function renderPanel(state) {
    if (!els) return;
    var earnedCount = state.badges.length;
    var levelRows = LEVELS.map(function (l) {
      var ls = state.levelStats[l] || { xp: 0, exercisesDone: 0 };
      var threshold = explorerThreshold(l);
      var pct = Math.min(100, Math.round((ls.exercisesDone / threshold) * 100));
      return (
        '<div class="progress-panel__level-row">' +
        '<div class="progress-label"><span>' + l + "</span><span>" + ls.exercisesDone + " factae · " + ls.xp + " PE</span></div>" +
        '<div class="progress-track"><div class="progress-track__fill" style="width:' + pct + '%"></div></div>' +
        "</div>"
      );
    }).join("");

    els.panel.innerHTML =
      '<div class="progress-panel__head">' +
      '<div><strong>' + state.xp + ' PE</strong><span class="progress-panel__streak-label">🔥 series ' + state.streak.count + ' dierum</span></div>' +
      '<button type="button" class="progress-panel__close" aria-label="Occlude">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>' +
      "</div>" +
      '<p class="progress-panel__hint">Progressus tantum in hoc navigatro (browser) servatur — nulla ratio (account) opus est.</p>' +
      '<div class="progress-panel__levels">' + levelRows + "</div>" +
      topicSummaryHtml(state) +
      '<p class="progress-panel__badges-label">Insignia — ' + earnedCount + " ex " + BADGES.length + " obtenta</p>" +
      '<ul class="badge-grid">' + badgeGridHtml(state) + "</ul>" +
      '<a class="btn btn--ghost btn--small progress-panel__link" href="' + progressPageHref() + '">Totum progressum vide</a>';

    var closeBtn = els.panel.querySelector(".progress-panel__close");
    if (closeBtn) closeBtn.addEventListener("click", function () {
      els.panel.hidden = true;
      els.toggle.setAttribute("aria-expanded", "false");
    });
  }

  function progressPageHref() {
    // Works whether this page is at the site root, one level deep
    // (gradus/ii.html) or two levels deep (gradus/ii/sum.html).
    var depth = (window.location.pathname.match(/\/gradus\/[^/]+\/[^/]+$/)) ? 2
      : (window.location.pathname.match(/\/gradus\/[^/]+$/)) ? 1 : 0;
    return (depth === 2 ? "../../" : depth === 1 ? "../" : "") + "iter.html";
  }

  function renderToggle(state) {
    if (!els) return;
    els.xpEl.textContent = state.xp + " PE";
    els.streakEl.textContent = String(state.streak.count);
    els.toggle.classList.toggle("has-streak", state.streak.count > 0);
    var active = hasProgress(state);
    els.toggle.hidden = !active;
    if (els.menuItem) els.menuItem.hidden = !active;
    if (els.menuStreakEl) els.menuStreakEl.textContent = String(state.streak.count);
    if (els.menuXpEl) els.menuXpEl.textContent = state.xp + " PE";
    if (els.menuToggle) {
      els.menuToggle.classList.toggle("has-streak", state.streak.count > 0);
      els.menuToggle.setAttribute(
        "aria-label",
        "Progressus tuus: " + state.xp + " PE, series " + state.streak.count + " dierum"
      );
    }
    if (!active && !els.panel.hidden) els.close();
  }

  var prefersReducedMotion = function () {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  };

  function buildBurst(kind) {
    var burst = el("div", { class: "xp-burst xp-burst--" + kind, "aria-hidden": "true" });
    var count = kind === "badge" ? 12 : kind === "streak" ? 8 : 6;
    for (var i = 0; i < count; i++) {
      var spark = document.createElement("span");
      spark.className = "xp-burst__spark";
      spark.style.setProperty("--angle", Math.round((360 / count) * i + (Math.random() * 20 - 10)) + "deg");
      spark.style.setProperty("--delay", Math.round(Math.random() * 90) + "ms");
      burst.appendChild(spark);
    }
    return burst;
  }

  function showToast(item) {
    if (!els) return;
    var node = el("div", { class: "xp-toast xp-toast--" + item.kind });
    if (!prefersReducedMotion()) node.appendChild(buildBurst(item.kind));
    if (item.icon) node.appendChild(el("span", { class: "xp-toast__icon", "aria-hidden": "true", text: item.icon }));
    node.appendChild(el("span", { text: item.text }));

    var hideTimer;
    var dismissed = false;
    function dismiss() {
      if (dismissed) return;
      dismissed = true;
      clearTimeout(hideTimer);
      node.classList.remove("is-visible");
      setTimeout(function () { node.remove(); }, TOAST_EXIT_MS);
    }
    node.addEventListener("click", dismiss);

    els.toastHost.appendChild(node);
    requestAnimationFrame(function () { node.classList.add("is-visible"); });
    hideTimer = setTimeout(dismiss, TOAST_VISIBLE_MS);
  }

  var visibilityQueue = [];
  var VISIBILITY_QUEUE_GAP_MS = 700;
  var isDrainingVisibilityQueue = false;

  function isPageVisible() {
    return typeof document.visibilityState !== "string" || document.visibilityState === "visible";
  }

  function drainVisibilityQueue() {
    if (isDrainingVisibilityQueue || !visibilityQueue.length) return;
    isDrainingVisibilityQueue = true;
    var queue = visibilityQueue;
    visibilityQueue = [];
    queue.forEach(function (item, i) {
      setTimeout(function () { showToast(item); }, i * VISIBILITY_QUEUE_GAP_MS);
    });
    setTimeout(function () { isDrainingVisibilityQueue = false; }, queue.length * VISIBILITY_QUEUE_GAP_MS);
  }

  document.addEventListener("visibilitychange", function () {
    if (isPageVisible()) drainVisibilityQueue();
  });

  function flushUI(state) {
    if (!els) return;
    renderToggle(state);
    if (!els.panel.hidden) renderPanel(state);
    var queue = pendingToasts;
    pendingToasts = [];
    if (!queue.length) return;
    if (isPageVisible()) {
      queue.forEach(function (item, i) {
        setTimeout(function () { showToast(item); }, i * 260);
      });
    } else {
      visibilityQueue.push.apply(visibilityQueue, queue);
    }
  }

  /* ------------------------------------------------------------- *
   * Full progress page (iter.html)
   * ------------------------------------------------------------- */
  function renderProgressPage() {
    var summaryEl = document.getElementById("progress-summary");
    var levelsEl = document.getElementById("progress-levels");
    var badgesEl = document.getElementById("progress-badges");
    var topicsEl = document.getElementById("progress-topics");
    if (!summaryEl && !levelsEl && !badgesEl && !topicsEl) return;

    function render() {
      var state = loadState();
      if (summaryEl) {
        summaryEl.innerHTML =
          '<div class="progress-stat"><strong>' + state.xp + '</strong><span>PE Tota</span></div>' +
          '<div class="progress-stat"><strong>' + state.streak.count + '</strong><span>Series Dierum</span></div>' +
          '<div class="progress-stat"><strong>' + state.badges.length + " / " + BADGES.length + '</strong><span>Insignia Obtenta</span></div>' +
          '<div class="progress-stat"><strong>' + countExercisesDone(state) + '</strong><span>Exercitationes Confectae</span></div>';
      }
      if (levelsEl) {
        levelsEl.innerHTML = LEVELS.map(function (l) {
          var ls = state.levelStats[l] || { xp: 0, exercisesDone: 0 };
          var threshold = explorerThreshold(l);
          var pct = Math.min(100, Math.round((ls.exercisesDone / threshold) * 100));
          return (
            '<div class="progress-panel__level-row">' +
            '<div class="progress-label"><span>Gradus ' + l + " — " + LEVEL_NAMES[l] + "</span><span>" + ls.exercisesDone + " factae · " + ls.xp + " PE</span></div>" +
            '<div class="progress-track"><div class="progress-track__fill" style="width:' + pct + '%"></div></div>' +
            "</div>"
          );
        }).join("");
      }
      if (badgesEl) {
        badgesEl.innerHTML = badgeGridHtml(state);
      }
      if (topicsEl) {
        topicsEl.innerHTML = topicListHtml(state);
      }
    }

    render();

    var resetBtn = document.getElementById("progress-reset-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        if (window.confirm("Omnia PE, series, et insignia in hoc instrumento delere? Hoc reverti non potest.")) {
          resetProgress();
          render();
        }
      });
    }
  }

  /* ------------------------------------------------------------- *
   * Boot
   * ------------------------------------------------------------- */
  function init() {
    buildWidget();
    renderToggle(loadState());
    renderProgressPage();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.ProgressTracker = {
    recordExerciseResult: recordExerciseResult,
    recordTestProgress: recordTestProgress,
    recordDictionaryUse: recordDictionaryUse,
    getState: getState,
    resetProgress: resetProgress,
    XP: XP,
    BADGES: BADGES,
    LEVELS: LEVELS,
    explorerThreshold: explorerThreshold,
  };
})();
