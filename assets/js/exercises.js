/*!
 * Lectiones Latinae — Interactive Exercise Engine
 * ------------------------------------------------------------------
 * A small, dependency-free, data-driven engine for classroom-style
 * exercises. New exercises are added by editing a JSON block, not by
 * writing JavaScript — see any lesson page's
 * <script type="application/json" class="exercise-data"> block for
 * a live example of the format.
 *
 * Adapted verbatim (logic, data contract, DOM structure, CSS classes,
 * localStorage/event wiring) from the sibling English-course project's
 * assets/js/exercises.js — only the user-facing strings below are
 * translated to Latin. See that project's header comment for the full
 * design rationale; it applies unchanged here.
 *
 * Supported "type" values:
 *   multiple-choice, true-false, fill-blank, matching, ordering,
 *   correction, typing, reading-comprehension, vocabulary, writing
 *   ("writing" is self-check only, handled separately -- see the
 *   dedicated `data.type === "writing"` branches below rather than
 *   the `renderers` table used by every other type.)
 *
 * Contract
 * --------
 * Each `.exercise-block` element carries a child
 * <script type="application/json" class="exercise-data"> with a
 * single exercise definition (see SCHEMA below). On DOMContentLoaded
 * the engine finds every such pair, renders the questions, and wires
 * up Submit / Retry-incorrect behaviour. Nothing here talks to a
 * server — everything is graded in the browser, which is what keeps
 * this deployable as a static GitHub Pages site.
 *
 * SCHEMA (informal):
 * {
 *   "id": "unique-id",
 *   "type": "multiple-choice" | "true-false" | "fill-blank" | "matching"
 *         | "ordering" | "correction" | "typing" | "reading-comprehension"
 *         | "vocabulary",
 *   "title": "Exercise title",
 *   "instructions": "One line of instructions shown under the title.",
 *   "passage": "Optional HTML passage, used by reading-comprehension.",
 *   "items": [ ...type-specific items, see renderers below... ]
 * }
 *
 * Every item's "explanation" is shown after grading regardless of whether
 * the answer was correct — write it as a short rule/reason a student can
 * learn from, not just "Correct answer."
 *
 * Correct-answer keys ("answer"/"answers"/pair "right" values, etc.) are
 * written WITHOUT macrons throughout this course's curriculum JSON, even
 * though prompts/explanations use them for pedagogy — macron diacritics
 * are hard to type, so norm() below (plain trim/lowercase/whitespace,
 * unchanged from the English version) is deliberately never asked to
 * strip them from a typed answer; there's simply nothing to strip.
 *
 * fill-blank items render a <select> dropdown per blank when "options" is
 * given (see renderFillBlank below for the exact shape), and fall back to
 * a free-text <input> for any blank without options.
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------- *
   * Utilities
   * ------------------------------------------------------------- */
  function norm(s) {
    return String(s || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ")
      .replace(/[.!?]+$/g, "");
  }

  function matchesAny(value, accepted) {
    var list = Array.isArray(accepted) ? accepted : [accepted];
    var v = norm(value);
    return list.some(function (a) {
      return norm(a) === v;
    });
  }

  // Author-supplied item ids (e.g. "n5") are only meant to be unique
  // within one exercise block's JSON, but repeat across topics on the
  // same page (test-yourself.html concatenates many blocks) -- verified
  // on gradus/provectus/test-yourself.html, where several topics reuse
  // the same item ids. Building radio "name"/element "id" attributes
  // straight from item.id therefore produces duplicate DOM ids: a
  // <label for> resolves to the *first* element in the document with
  // that id, so clicking an option can silently check/focus a same-id
  // control in a completely different, earlier exercise instead of the
  // one clicked. A monotonically increasing counter guarantees every
  // generated id is unique for the life of the page, regardless of what
  // item ids the JSON reuses.
  var uidCounter = 0;
  function uniqueId(base) {
    return "q_" + base + "_" + (uidCounter++);
  }

  function shuffled(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "html") node.innerHTML = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      if (c) node.appendChild(c);
    });
    return node;
  }

  function iconSpan(kind) {
    var d = kind === "check" ? '<path d="m5 12 5 5L20 7"/>' : '<path d="M18 6 6 18M6 6l12 12"/>';
    var wrap = el("span");
    wrap.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + "</svg>";
    return wrap.firstChild;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /* ------------------------------------------------------------- *
   * syncLiveFormState — the actual fix for the "Serva responsa mea"
   * PDF/print bug.
   *
   * `container.cloneNode(true)` is used to build the printable
   * overlay (see performSaveAnswers below). Per the HTML Living
   * Standard, <input> and <textarea> have defined "cloning steps"
   * that copy their *current* value onto the clone, but <select>/
   * <option> have no such cloning steps at all — cloneNode() only
   * reproduces a <select>'s parsed/initial state, never whichever
   * <option> the user (or script) currently has selected. Since the
   * "matching" exercise type — and every "fill-blank" item that
   * supplies dropdown options — renders its answer controls as
   * <select> elements, the cloned printable overlay silently lost
   * every one of those answers while the rest of the page looked
   * fine.
   *
   * Fix: after cloning, walk the live source container and the
   * clone's form controls in lockstep (querySelectorAll order is
   * identical for two structurally-identical trees) and copy the
   * live value/checkedness across explicitly.
   * ------------------------------------------------------------- */
  function syncLiveFormState(source, clone) {
    var sourceControls = source.querySelectorAll("input, select, textarea");
    var cloneControls = clone.querySelectorAll("input, select, textarea");
    sourceControls.forEach(function (src, i) {
      var dst = cloneControls[i];
      if (!dst) return;
      if (src.type === "checkbox" || src.type === "radio") {
        dst.checked = src.checked;
      } else {
        dst.value = src.value;
      }
    });
  }

  /* ------------------------------------------------------------- *
   * Shared save/print system — used by every "Serva responsa mea" /
   * print button on the site (both graded exercise blocks and
   * free-text writing blocks), so a fix here applies everywhere at
   * once rather than per exercise type.
   * ------------------------------------------------------------- */
  var SECTION_LABELS = {
    exercises: "Exercitationes",
    vocabulary: "Vocabularium",
    reading: "Lectio",
    listening: "Auditio",
    writing: "Scriptio",
    speaking: "Locutio",
    revision: "Recognitio",
    "mock-tests": "Examina Ficta",
  };
  var TYPE_LABELS = {
    "fill-blank": "spatia complenda",
    "multiple-choice": "electio multiplex",
    vocabulary: "vocabularium",
    "true-false": "verum an falsum",
    matching: "paria iungenda",
    ordering: "ordinatio verborum",
    correction: "correctio",
    typing: "dictatio",
    "reading-comprehension": "comprehensio lectionis",
  };
  // Same labels as TYPE_LABELS, title-cased, for the printed/PDF
  // document header (buildExercisePrintHeaderText below).
  var TYPE_LABELS_TITLE = {
    "fill-blank": "Spatia Complenda",
    "multiple-choice": "Electio Multiplex",
    vocabulary: "Vocabularium",
    "true-false": "Verum an Falsum",
    matching: "Paria Iungenda",
    ordering: "Ordinatio Verborum",
    correction: "Correctio",
    typing: "Dictatio",
    "reading-comprehension": "Comprehensio Lectionis",
    writing: "Scriptio",
  };

  function sanitizeFilename(name) {
    return name
      .replace(/[\\/:*?"<>|]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function buildSavePathParts(container) {
    var levelCode = (document.body.getAttribute("data-level-code") || "").trim();
    var parts = [];
    if (levelCode) parts.push(levelCode);

    var sectionEl = container.closest("section[id]");
    if (sectionEl) {
      var id = sectionEl.id;
      if (SECTION_LABELS[id]) {
        parts.push(SECTION_LABELS[id]);
      } else {
        var heading = sectionEl.querySelector("h2, h3");
        var topicTitle = heading ? heading.textContent.trim() : "";
        parts.push("Te Ipsum Proba");
        if (topicTitle) parts.push(topicTitle);
      }
    }
    return parts;
  }

  function buildSaveFilename(container, data) {
    var parts = buildSavePathParts(container);
    var last = "";
    if (data.type && data.type !== "writing" && TYPE_LABELS[data.type]) {
      last += TYPE_LABELS[data.type] + " ";
    }
    last += data.title || "Exercitatio";
    parts.push(last.trim());

    return sanitizeFilename(parts.join(" - "));
  }

  function buildExercisePrintHeaderText(container, data) {
    var parts = buildSavePathParts(container);
    var typeLabel = TYPE_LABELS_TITLE[data.type];
    if (typeLabel) parts.push(typeLabel);
    parts.push(data.title || "Exercitatio");
    return parts.join(" - ");
  }

  function buildTopicPrintHeaderText(topicSection) {
    var levelCode = (document.body.getAttribute("data-level-code") || "").trim();
    var heading = topicSection.querySelector("h2, h3");
    var topicTitle = heading ? heading.textContent.trim() : (topicSection.id || "Argumentum");
    var parts = [];
    if (levelCode) parts.push(levelCode);
    parts.push("Te Ipsum Proba");
    parts.push(topicTitle + " (Argumentum)");
    return parts.join(" - ");
  }

  function buildTestPrintHeaderText() {
    var levelCode = (document.body.getAttribute("data-level-code") || "").trim();
    var parts = [];
    if (levelCode) parts.push(levelCode);
    parts.push("Te Ipsum Proba (Totum)");
    return parts.join(" - ");
  }

  function buildPrintHeaderNode(text) {
    return el("div", { class: "print-doc-header" }, [
      el("p", { class: "print-doc-header__path", text: text }),
    ]);
  }

  function wrapWithPrintHeader(headerText, contentNode) {
    var wrap = el("div", { class: "print-doc" });
    wrap.appendChild(buildPrintHeaderNode(headerText));
    wrap.appendChild(contentNode);
    return wrap;
  }

  function performSaveAnswers(container, data, buildOverlayContent) {
    var scrollX = window.scrollX;
    var scrollY = window.scrollY;
    var originalTitle = document.title;
    var restored = false;

    var overlay = document.getElementById("print-overlay");
    if (!overlay) {
      overlay = el("div", { id: "print-overlay" });
      document.body.appendChild(overlay);
    }
    overlay.innerHTML = "";
    overlay.appendChild(buildOverlayContent());

    document.title = buildSaveFilename(container, data) || originalTitle;
    document.body.classList.add("is-printing-block");

    function restore() {
      if (restored) return;
      restored = true;
      document.body.classList.remove("is-printing-block");
      overlay.innerHTML = "";
      document.title = originalTitle;
      var root = document.documentElement;
      var prevBehavior = root.style.scrollBehavior;
      function jump() {
        root.style.scrollBehavior = "auto";
        window.scrollTo(scrollX, scrollY);
      }
      [0, 30, 80, 150, 300, 500].forEach(function (delay) {
        setTimeout(jump, delay);
      });
      setTimeout(function () {
        root.style.scrollBehavior = prevBehavior;
      }, 520);
      window.removeEventListener("afterprint", restore);
    }

    window.addEventListener("afterprint", restore);
    window.print();
    setTimeout(restore, 1000);
  }

  /* ------------------------------------------------------------- *
   * Item renderers — one per exercise type.
   * Each renderer returns { node, reset(), grade() }. grade() locks
   * the item, reveals correct/incorrect state + explanation, and
   * returns { correct, attempted }.
   * ------------------------------------------------------------- */
  var renderers = {};

  function itemShell(index, promptHtml) {
    var wrap = el("div", { class: "exercise-item", "data-item-index": index });
    var num = el("span", { class: "exercise-item__number", "aria-hidden": "true", text: String(index + 1) });
    if (promptHtml !== null) {
      var p = el("p", { class: "exercise-item__prompt" });
      p.appendChild(num);
      var span = el("span");
      span.innerHTML = promptHtml;
      p.appendChild(span);
      wrap.appendChild(p);
    }
    return wrap;
  }

  function feedbackNode(explanation) {
    var fb = el("div", { class: "item-feedback", role: "status" });
    var body = el("div", { class: "item-feedback__body" });
    var strong = el("strong");
    body.appendChild(strong);
    var explanationEl = null;
    if (explanation) {
      explanationEl = el("span", { text: explanation });
      body.appendChild(explanationEl);
    }
    fb.appendChild(body);
    return { node: fb, strongEl: strong, body: body, explanationEl: explanationEl };
  }

  function setFeedback(fbRef, correct, correctAnswerText, iconWrap) {
    fbRef.node.classList.add("is-visible");
    fbRef.node.classList.toggle("is-correct", correct);
    fbRef.node.classList.toggle("is-incorrect", !correct);
    iconWrap.innerHTML = "";
    iconWrap.appendChild(iconSpan(correct ? "check" : "cross"));
    fbRef.strongEl.textContent = correct ? "Recte." : "Non recte.";
    if (!correct && correctAnswerText) {
      var existing = fbRef.body.querySelector(".correct-answer");
      if (!existing) {
        var correctAnswerEl = el("div", { class: "correct-answer", html: "<em>Responsum rectum:</em> " + correctAnswerText });
        if (fbRef.explanationEl) fbRef.body.insertBefore(correctAnswerEl, fbRef.explanationEl);
        else fbRef.body.appendChild(correctAnswerEl);
      }
    }
  }

  // ---- multiple-choice / vocabulary / reading-comprehension question ----
  //
  // Options are displayed in a shuffled order (Fisher-Yates, via the
  // shared shuffled() helper) so the correct answer doesn't keep landing
  // in the same position across every question -- the curriculum JSON
  // authors wrote `answerIndex` without thinking about position bias, and
  // an audit of the data showed correct answers heavily concentrated in
  // the first two slots. Each rendered <input> keeps `value` set to the
  // option's *original* index into item.options (origIndex below), not
  // its on-screen position, so item.answerIndex, extractChoice() (used by
  // the "save answers" print feature) and any other code that reasons
  // about option identity by original index keeps working unchanged --
  // only the DOM order changes, once, at render time. Shuffling happens
  // exactly once per page load (here, when the item is first built), not
  // on every re-render/reset, so retrying a question never reshuffles
  // the options out from under the student mid-attempt.
  function renderChoice(item, index) {
    var wrap = itemShell(index, item.prompt);
    var fieldset = el("fieldset");
    fieldset.appendChild(el("legend", { class: "visually-hidden", text: "Unum responsum elige" }));
    var list = el("div", { class: "option-list" });
    var name = uniqueId(item.id);
    var optionEls = [];

    var options = item.options || [];
    var order = shuffled(options.map(function (opt, i) { return i; }));

    order.forEach(function (origIndex) {
      var inputId = name + "_" + origIndex;
      var input = el("input", { type: "radio", name: name, id: inputId, value: String(origIndex) });
      var label = el("label", { class: "option", for: inputId }, [
        input,
        el("span", { class: "option__label", text: options[origIndex] }),
      ]);
      optionEls.push({ input: input, label: label, origIndex: origIndex });
      list.appendChild(label);
    });

    fieldset.appendChild(list);
    wrap.appendChild(fieldset);

    var iconWrap = el("span");
    var fb = feedbackNode(item.explanation || "");
    fb.node.insertBefore(iconWrap, fb.node.firstChild);
    wrap.appendChild(fb.node);

    return {
      node: wrap,
      reset: function () {
        optionEls.forEach(function (o) {
          o.input.checked = false;
          o.input.disabled = false;
          o.label.classList.remove("is-correct", "is-incorrect");
          var tag = o.label.querySelector(".option__tag");
          if (tag) tag.remove();
        });
        fb.node.classList.remove("is-visible", "is-correct", "is-incorrect");
        var ca = fb.body.querySelector(".correct-answer");
        if (ca) ca.remove();
        wrap.classList.remove("is-locked");
      },
      grade: function () {
        var checkedEntry = optionEls.find(function (o) { return o.input.checked; });
        var chosen = checkedEntry ? checkedEntry.origIndex : -1;
        var correct = chosen === item.answerIndex;
        optionEls.forEach(function (o) {
          o.input.disabled = true;
          if (o.origIndex === item.answerIndex) {
            o.label.classList.add("is-correct");
            o.label.appendChild(el("span", { class: "option__tag", "aria-hidden": "true", text: "✓ rectum" }));
          } else if (o.origIndex === chosen) {
            o.label.classList.add("is-incorrect");
            o.label.appendChild(el("span", { class: "option__tag", "aria-hidden": "true", text: "✗ responsum tuum" }));
          }
        });
        wrap.classList.add("is-locked");
        setFeedback(fb, correct, null, iconWrap);
        return { correct: correct, attempted: chosen !== -1 };
      },
    };
  }
  renderers["multiple-choice"] = renderChoice;
  renderers["vocabulary"] = renderChoice;
  renderers["reading-comprehension"] = renderChoice;

  // ---- true-false ----
  function renderTrueFalse(item, index) {
    var wrap = itemShell(index, item.statement);
    var fieldset = el("fieldset");
    fieldset.appendChild(el("legend", { class: "visually-hidden", text: "Verum an falsum" }));
    var list = el("div", { class: "option-list tf-options" });
    var name = uniqueId(item.id);
    var trueId = name + "_t", falseId = name + "_f";
    var trueInput = el("input", { type: "radio", name: name, id: trueId, value: "true" });
    var falseInput = el("input", { type: "radio", name: name, id: falseId, value: "false" });
    var trueLabel = el("label", { class: "option", for: trueId }, [trueInput, el("span", { class: "option__label", text: "Verum" })]);
    var falseLabel = el("label", { class: "option", for: falseId }, [falseInput, el("span", { class: "option__label", text: "Falsum" })]);
    list.appendChild(trueLabel);
    list.appendChild(falseLabel);
    fieldset.appendChild(list);
    wrap.appendChild(fieldset);

    var iconWrap = el("span");
    var fb = feedbackNode(item.explanation || "");
    fb.node.insertBefore(iconWrap, fb.node.firstChild);
    wrap.appendChild(fb.node);

    return {
      node: wrap,
      reset: function () {
        trueInput.checked = false; falseInput.checked = false;
        trueInput.disabled = false; falseInput.disabled = false;
        trueLabel.classList.remove("is-correct", "is-incorrect");
        falseLabel.classList.remove("is-correct", "is-incorrect");
        var t1 = trueLabel.querySelector(".option__tag"); if (t1) t1.remove();
        var t2 = falseLabel.querySelector(".option__tag"); if (t2) t2.remove();
        fb.node.classList.remove("is-visible", "is-correct", "is-incorrect");
        wrap.classList.remove("is-locked");
      },
      grade: function () {
        var chosen = trueInput.checked ? true : falseInput.checked ? false : null;
        var correct = chosen === item.answer;
        trueInput.disabled = true; falseInput.disabled = true;
        var correctLabel = item.answer ? trueLabel : falseLabel;
        correctLabel.classList.add("is-correct");
        correctLabel.appendChild(el("span", { class: "option__tag", "aria-hidden": "true", text: "✓ rectum" }));
        if (chosen !== null && chosen !== item.answer) {
          var wrongLabel = chosen ? trueLabel : falseLabel;
          wrongLabel.classList.add("is-incorrect");
          wrongLabel.appendChild(el("span", { class: "option__tag", "aria-hidden": "true", text: "✗ responsum tuum" }));
        }
        wrap.classList.add("is-locked");
        setFeedback(fb, correct, null, iconWrap);
        return { correct: correct, attempted: chosen !== null };
      },
    };
  }
  renderers["true-false"] = renderTrueFalse;

  // ---- fill-blank ----
  function renderFillBlank(item, index) {
    var wrap = itemShell(index, null);
    var sentence = el("p", { class: "blank-sentence exercise-item__prompt" });
    var num = el("span", { class: "exercise-item__number", "aria-hidden": "true", text: String(index + 1) });
    sentence.appendChild(num);

    var parts = String(item.prompt).split("___");
    var numBlanks = parts.length - 1;

    function optionsForBlank(i) {
      if (!item.options || !item.options.length) return null;
      if (Array.isArray(item.options[0])) return item.options[i] || null;
      return numBlanks === 1 ? item.options : null;
    }

    var inputs = [];
    parts.forEach(function (part, i) {
      sentence.appendChild(document.createTextNode(part));
      if (i < numBlanks) {
        var blankOptions = optionsForBlank(i);
        var control;
        if (blankOptions && blankOptions.length) {
          control = el("select", {
            class: "blank-input",
            "aria-label": "Spatium " + (i + 1) + " ex " + numBlanks,
          });
          control.appendChild(el("option", { value: "", text: "Elige…" }));
          shuffled(blankOptions).forEach(function (opt) {
            control.appendChild(el("option", { value: opt, text: opt }));
          });
        } else {
          control = el("input", {
            type: "text",
            class: "blank-input",
            "aria-label": "Spatium " + (i + 1) + " ex " + numBlanks,
            autocomplete: "off",
            autocapitalize: "off",
            spellcheck: "false",
          });
        }
        inputs.push(control);
        sentence.appendChild(control);
      }
    });
    wrap.appendChild(sentence);

    var fb = feedbackNode(item.explanation || "");
    var iconWrap = el("span");
    fb.node.insertBefore(iconWrap, fb.node.firstChild);
    wrap.appendChild(fb.node);

    return {
      node: wrap,
      reset: function () {
        inputs.forEach(function (inp) {
          inp.value = "";
          inp.disabled = false;
          inp.classList.remove("is-correct", "is-incorrect");
        });
        fb.node.classList.remove("is-visible", "is-correct", "is-incorrect");
        var ca = fb.body.querySelector(".correct-answer");
        if (ca) ca.remove();
        wrap.classList.remove("is-locked");
      },
      grade: function () {
        var allCorrect = true;
        var attempted = false;
        var answers = item.answers || [];
        inputs.forEach(function (inp, i) {
          if (inp.value.trim()) attempted = true;
          var ok = matchesAny(inp.value, answers[i]);
          inp.classList.add(ok ? "is-correct" : "is-incorrect");
          inp.disabled = true;
          if (!ok) allCorrect = false;
        });
        wrap.classList.add("is-locked");
        var correctText = (item.answers || []).map(function (a) { return Array.isArray(a) ? a[0] : a; }).join(" &middot; ");
        setFeedback(fb, allCorrect, allCorrect ? null : correctText, iconWrap);
        return { correct: allCorrect, attempted: attempted };
      },
    };
  }
  renderers["fill-blank"] = renderFillBlank;

  // ---- correction (grammar correction) ----
  function renderCorrection(item, index) {
    var wrap = itemShell(index, null);
    wrap.appendChild(el("p", { class: "exercise-item__source", html: "&ldquo;" + item.incorrect + "&rdquo;" }));
    var qid = uniqueId(item.id);
    var label = el("label", { class: "exercise-item__prompt", for: qid });
    label.appendChild(el("span", { class: "exercise-item__number", "aria-hidden": "true", text: String(index + 1) }));
    label.appendChild(document.createTextNode("Sententiam rectam scribe:"));
    wrap.appendChild(label);
    var input = el("input", { type: "text", id: qid, class: "answer-input", autocomplete: "off", spellcheck: "false" });
    wrap.appendChild(input);

    var fb = feedbackNode(item.explanation || "");
    var iconWrap = el("span");
    fb.node.insertBefore(iconWrap, fb.node.firstChild);
    wrap.appendChild(fb.node);

    return {
      node: wrap,
      reset: function () {
        input.value = ""; input.disabled = false;
        input.classList.remove("is-correct", "is-incorrect");
        fb.node.classList.remove("is-visible", "is-correct", "is-incorrect");
        var ca = fb.body.querySelector(".correct-answer");
        if (ca) ca.remove();
        wrap.classList.remove("is-locked");
      },
      grade: function () {
        var ok = matchesAny(input.value, item.answer);
        input.classList.add(ok ? "is-correct" : "is-incorrect");
        input.disabled = true;
        wrap.classList.add("is-locked");
        var correctText = Array.isArray(item.answer) ? item.answer[0] : item.answer;
        setFeedback(fb, ok, ok ? null : correctText, iconWrap);
        return { correct: ok, attempted: input.value.trim().length > 0 };
      },
    };
  }
  renderers["correction"] = renderCorrection;

  // ---- typing (short-answer; graded if item.answer given, else self-check) ----
  function renderTyping(item, index) {
    var wrap = itemShell(index, item.prompt);
    var input = el("input", { type: "text", class: "answer-input", autocomplete: "off", spellcheck: "false", "aria-label": item.prompt || "Responsum tuum" });
    wrap.appendChild(input);

    var selfCheck = !item.answer;
    var fb = feedbackNode(selfCheck ? "" : item.explanation || "");
    var iconWrap = el("span");
    if (!selfCheck) fb.node.insertBefore(iconWrap, fb.node.firstChild);
    wrap.appendChild(fb.node);

    return {
      node: wrap,
      reset: function () {
        input.value = ""; input.disabled = false;
        input.classList.remove("is-correct", "is-incorrect");
        fb.node.classList.remove("is-visible", "is-correct", "is-incorrect");
        var ma = fb.body.querySelector(".model-answer");
        if (ma) ma.remove();
        var ca = fb.body.querySelector(".correct-answer");
        if (ca) ca.remove();
        wrap.classList.remove("is-locked");
      },
      grade: function () {
        input.disabled = true;
        wrap.classList.add("is-locked");
        if (selfCheck) {
          fb.node.classList.add("is-visible");
          fb.strongEl.textContent = item.modelAnswer ? "Exemplar responsi:" : "Servatum ad tuam recognitionem.";
          if (item.modelAnswer && !fb.body.querySelector(".model-answer")) {
            fb.body.appendChild(el("div", { class: "model-answer", text: item.modelAnswer }));
          }
          return { correct: true, attempted: input.value.trim().length > 0, selfCheck: true };
        }
        var ok = matchesAny(input.value, item.answer);
        input.classList.add(ok ? "is-correct" : "is-incorrect");
        var correctText = Array.isArray(item.answer) ? item.answer[0] : item.answer;
        setFeedback(fb, ok, ok ? null : correctText, iconWrap);
        return { correct: ok, attempted: input.value.trim().length > 0 };
      },
    };
  }
  renderers["typing"] = renderTyping;

  // ---- matching (dropdown-based: accessible & mobile-friendly) ----
  function renderMatching(item, index) {
    var wrap = itemShell(index, null);
    var table = el("div", { class: "match-table" });
    var rightOptions = shuffled(item.pairs.map(function (p) { return p.right; }));
    var selects = [];
    var rowWraps = [];

    item.pairs.forEach(function (pair, i) {
      var rowWrap = el("div", { class: "match-row-wrap" });
      var row = el("div", { class: "match-row" });
      row.appendChild(el("span", { class: "match-row__left" }, [
        el("span", { class: "exercise-item__number", "aria-hidden": "true", text: String(i + 1) }),
        el("span", { text: pair.left }),
      ]));
      row.appendChild(el("span", { class: "match-row__arrow", "aria-hidden": "true", text: "→" }));
      var select = el("select", { class: "answer-input", "aria-label": "Par ad " + pair.left });
      select.appendChild(el("option", { value: "", text: "Elige…" }));
      rightOptions.forEach(function (opt) {
        select.appendChild(el("option", { value: opt, text: opt }));
      });
      selects.push(select);
      row.appendChild(select);
      rowWrap.appendChild(row);
      table.appendChild(rowWrap);
      rowWraps.push(rowWrap);
    });
    wrap.appendChild(table);

    var fb = feedbackNode(item.explanation || "");
    var iconWrap = el("span");
    fb.node.insertBefore(iconWrap, fb.node.firstChild);
    wrap.appendChild(fb.node);

    return {
      node: wrap,
      reset: function () {
        selects.forEach(function (s) { s.value = ""; s.disabled = false; s.classList.remove("is-correct", "is-incorrect"); });
        rowWraps.forEach(function (rw) {
          var hint = rw.querySelector(".match-row__correct");
          if (hint) hint.remove();
        });
        fb.node.classList.remove("is-visible", "is-correct", "is-incorrect");
        wrap.classList.remove("is-locked");
      },
      grade: function () {
        var allCorrect = true, attempted = false;
        selects.forEach(function (s, i) {
          if (s.value) attempted = true;
          var ok = norm(s.value) === norm(item.pairs[i].right);
          s.classList.add(ok ? "is-correct" : "is-incorrect");
          s.disabled = true;
          if (!ok) {
            allCorrect = false;
            rowWraps[i].appendChild(el("p", {
              class: "match-row__correct",
              html: "<em>Rectum:</em> " + escapeHtml(item.pairs[i].right),
            }));
          }
        });
        wrap.classList.add("is-locked");
        setFeedback(fb, allCorrect, null, iconWrap);
        return { correct: allCorrect, attempted: attempted };
      },
    };
  }
  renderers["matching"] = renderMatching;

  // ---- ordering (sentence ordering via word chips) ----
  function renderOrdering(item, index) {
    var wrap = itemShell(index, item.prompt || "Verba ordine recto compone.");
    var buildArea = el("div", { class: "order-build", role: "list", "aria-label": "Sententia tua" });
    var pool = el("div", { class: "order-pool", role: "list", "aria-label": "Verba praesto" });
    var words = item.words;
    var chips = shuffled(words.map(function (w, i) { return { word: w, key: i, placed: false }; }));
    var built = [];

    function renderPool() {
      pool.innerHTML = "";
      chips.forEach(function (c) {
        var chip = el("button", { type: "button", class: "word-chip" + (c.placed ? " is-placed" : ""), text: c.word });
        chip.disabled = !!c.placed;
        chip.addEventListener("click", function () {
          c.placed = true;
          built.push(c);
          renderPool();
          renderBuild();
        });
        pool.appendChild(chip);
      });
    }
    function renderBuild() {
      buildArea.innerHTML = "";
      built.forEach(function (c) {
        var chip = el("button", { type: "button", class: "word-chip", text: c.word, "aria-label": "Tolle " + c.word });
        chip.addEventListener("click", function () {
          c.placed = false;
          built = built.filter(function (b) { return b !== c; });
          renderPool();
          renderBuild();
        });
        buildArea.appendChild(chip);
      });
    }
    renderPool();
    renderBuild();

    var resetBtn = el("button", { type: "button", class: "btn btn--ghost btn--small order-reset", text: "Purga" });
    resetBtn.addEventListener("click", function () {
      built.forEach(function (c) { c.placed = false; });
      built = [];
      renderPool();
      renderBuild();
    });

    wrap.appendChild(buildArea);
    wrap.appendChild(pool);
    wrap.appendChild(resetBtn);

    var fb = feedbackNode(item.explanation || "");
    var iconWrap = el("span");
    fb.node.insertBefore(iconWrap, fb.node.firstChild);
    wrap.appendChild(fb.node);

    return {
      node: wrap,
      reset: function () {
        chips.forEach(function (c) { c.placed = false; });
        built = [];
        renderPool();
        renderBuild();
        fb.node.classList.remove("is-visible", "is-correct", "is-incorrect");
        var ca = fb.body.querySelector(".correct-answer");
        if (ca) ca.remove();
        wrap.classList.remove("is-locked");
        resetBtn.disabled = false;
      },
      grade: function () {
        var userOrder = built.map(function (c) { return c.word; });
        var correct = userOrder.length === words.length && userOrder.every(function (w, i) { return w === words[i]; });
        buildArea.querySelectorAll(".word-chip").forEach(function (b) { b.disabled = true; });
        pool.querySelectorAll(".word-chip").forEach(function (b) { b.disabled = true; });
        resetBtn.disabled = true;
        wrap.classList.add("is-locked");
        var correctText = words.join(" ");
        setFeedback(fb, correct, correct ? null : correctText, iconWrap);
        return { correct: correct, attempted: userOrder.length > 0 };
      },
    };
  }
  renderers["ordering"] = renderOrdering;

  /* ------------------------------------------------------------- *
   * Block controller — wires items + submit/retry/score for one
   * .exercise-block
   * ------------------------------------------------------------- */
  function scorePanelNode() {
    var panel = el("div", { class: "score-panel", role: "status", "aria-live": "polite" });
    var ring = el("div", { class: "score-panel__ring", text: "" });
    var textWrap = el("div", { class: "score-panel__text" });
    panel.appendChild(ring);
    panel.appendChild(textWrap);
    return { node: panel, ring: ring, textWrap: textWrap };
  }

  function buildBlock(container, data) {
    var head = el("div", { class: "exercise-block__head" });
    head.appendChild(el("span", { class: "exercise-block__type", text: TYPE_LABELS[data.type] || data.type.replace(/-/g, " ") }));
    head.appendChild(el("h3", { class: "exercise-block__title", text: data.title || "Exercitatio" }));
    if (data.instructions) head.appendChild(el("p", { class: "exercise-block__instructions", text: data.instructions }));
    container.appendChild(head);

    if (data.passage) {
      container.appendChild(el("div", { class: "reading-passage", html: data.passage }));
    }

    var scoreTop = scorePanelNode();
    container.appendChild(scoreTop.node);

    var itemsWrap = el("div", { class: "exercise-block__items" });
    container.appendChild(itemsWrap);

    var renderFn = renderers[data.type];
    if (!renderFn) {
      itemsWrap.appendChild(el("p", { text: "Genus exercitationis non subventum: " + data.type }));
      return;
    }

    var built = (data.items || []).map(function (item, i) {
      var r = renderFn(item, i);
      itemsWrap.appendChild(r.node);
      return r;
    });

    var scoreBottom = scorePanelNode();
    container.appendChild(scoreBottom.node);
    var scorePanels = [scoreTop, scoreBottom];

    var actions = el("div", { class: "exercise-actions" });
    var submitBtn = el("button", { type: "button", class: "btn btn--accent", text: "Proba" });
    var retryBtn = el("button", { type: "button", class: "btn btn--ghost", text: "Itera falsa tantum" });
    var retryAllBtn = el("button", { type: "button", class: "btn btn--ghost", text: "Itera omnia" });
    var printBtn = el("button", { type: "button", class: "btn btn--ghost print-hidden", text: "Serva responsa mea" });
    retryBtn.style.display = "none";
    retryAllBtn.style.display = "none";
    printBtn.style.display = "none";
    actions.appendChild(submitBtn);
    actions.appendChild(retryBtn);
    actions.appendChild(retryAllBtn);
    actions.appendChild(printBtn);
    container.appendChild(actions);

    var lastResults = null;

    function showScore(results) {
      var correctCount = results.filter(function (r) { return r.correct; }).length;
      var total = results.length;
      var pct = total ? Math.round((correctCount / total) * 100) : 0;
      var ringClass = pct < 50 ? "is-low" : pct < 80 ? "is-mid" : "";
      var headingText = pct === 100 ? "Optime — summa scientia!" : pct >= 80 ? "Bene factum." : pct >= 50 ? "Bonus progressus." : "Plus exercendum est.";
      var subText = correctCount + " ex " + total + " recta (" + pct + "%).";
      scorePanels.forEach(function (sp) {
        sp.ring.textContent = correctCount + "/" + total;
        sp.ring.classList.remove("is-low", "is-mid");
        if (ringClass) sp.ring.classList.add(ringClass);
        sp.textWrap.innerHTML = "";
        sp.textWrap.appendChild(el("h4", { text: headingText }));
        sp.textWrap.appendChild(el("p", { text: subText }));
        sp.node.classList.add("is-visible");
      });
    }

    submitBtn.addEventListener("click", function () {
      lastResults = built.map(function (r) { return r.grade(); });
      showScore(lastResults);
      submitBtn.style.display = "none";
      var anyIncorrect = lastResults.some(function (r) { return !r.correct; });
      retryBtn.style.display = anyIncorrect ? "" : "none";
      retryAllBtn.style.display = "";
      printBtn.style.display = "";
      var resultsWithItemIds = lastResults.map(function (r, i) {
        var withId = {};
        for (var k in r) { if (Object.prototype.hasOwnProperty.call(r, k)) withId[k] = r[k]; }
        withId.itemId = (data.items[i] || {}).id;
        return withId;
      });
      container.dispatchEvent(new CustomEvent("exercise:submitted", {
        bubbles: true,
        detail: { id: data.id, results: resultsWithItemIds },
      }));

      if (window.ProgressTracker && typeof window.ProgressTracker.recordExerciseResult === "function") {
        var correctCount = lastResults.filter(function (r) { return r.correct; }).length;
        var total = lastResults.length;
        window.ProgressTracker.recordExerciseResult({
          exerciseId: data.id,
          level: document.body.getAttribute("data-level-code") || "",
          correct: correctCount,
          total: total,
          perfect: total > 0 && correctCount === total,
        });
      }
    });

    printBtn.addEventListener("click", function () {
      performSaveAnswers(container, data, function () {
        var clone = container.cloneNode(true);
        syncLiveFormState(container, clone);
        return wrapWithPrintHeader(buildExercisePrintHeaderText(container, data), clone);
      });
    });

    retryBtn.addEventListener("click", function () {
      built.forEach(function (r, i) {
        if (!lastResults[i].correct) r.reset();
      });
      scorePanels.forEach(function (sp) { sp.node.classList.remove("is-visible"); });
      submitBtn.style.display = "";
      retryBtn.style.display = "none";
      retryAllBtn.style.display = "none";
      printBtn.style.display = "none";
      var firstOpen = itemsWrap.querySelector(".exercise-item:not(.is-locked)");
      if (firstOpen) firstOpen.scrollIntoView({ behavior: "smooth", block: "center" });
    });

    retryAllBtn.addEventListener("click", function () {
      built.forEach(function (r) { r.reset(); });
      scorePanels.forEach(function (sp) { sp.node.classList.remove("is-visible"); });
      submitBtn.style.display = "";
      retryBtn.style.display = "none";
      retryAllBtn.style.display = "none";
      printBtn.style.display = "none";
    });
  }

  /* ---------------------------------------------------------------
     Writing prompts — free-text, ungraded. No submit/check button;
     the only action is saving/printing the prompt(s) together with
     whatever the student has written, exactly as-is.
     --------------------------------------------------------------- */
  function buildWritingBlock(container, data) {
    var head = el("div", { class: "exercise-block__head" });
    head.appendChild(el("span", { class: "exercise-block__type", text: "scriptio" }));
    head.appendChild(el("h3", { class: "exercise-block__title", text: data.title || "Scriptio" }));
    if (data.instructions) head.appendChild(el("p", { class: "exercise-block__instructions", text: data.instructions }));
    container.appendChild(head);

    var itemsWrap = el("div", { class: "exercise-block__items" });
    container.appendChild(itemsWrap);

    var textareas = [];
    (data.items || []).forEach(function (item, i) {
      var wrap = el("div", { class: "exercise-item writing-item" });
      wrap.appendChild(el("span", { class: "exercise-item__number", "aria-hidden": "true", text: String(i + 1) }));
      var promptEl = el("p", { class: "exercise-item__prompt writing-item__prompt", text: item.prompt || "" });
      wrap.appendChild(promptEl);
      var textarea = el("textarea", {
        class: "writing-item__textarea",
        rows: "6",
        placeholder: "Hic responsum tuum scribe…",
        "aria-label": item.prompt || "Responsum tuum",
      });
      textarea.dataset.prompt = item.prompt || "";
      textareas.push(textarea);
      wrap.appendChild(textarea);
      itemsWrap.appendChild(wrap);
    });

    var actions = el("div", { class: "exercise-actions" });
    var saveBtn = el("button", { type: "button", class: "btn btn--ghost print-hidden", text: "Serva responsa mea" });
    actions.appendChild(saveBtn);
    container.appendChild(actions);

    saveBtn.addEventListener("click", function () {
      performSaveAnswers(container, data, function () {
        var printWrap = el("div", { class: "exercise-block" });
        printWrap.appendChild(el("h3", { class: "exercise-block__title", text: data.title || "Scriptio" }));
        textareas.forEach(function (ta, i) {
          var block = el("div", { class: "writing-item" });
          block.appendChild(el("p", { class: "writing-item__prompt", text: "" + (i + 1) + ". " + (ta.dataset.prompt || "") }));
          var answerP = el("p", { class: "writing-item__saved-answer" });
          answerP.textContent = ta.value.trim() || "(Nullum responsum adhuc scriptum.)";
          block.appendChild(answerP);
          printWrap.appendChild(block);
        });
        return wrapWithPrintHeader(buildExercisePrintHeaderText(container, data), printWrap);
      });
    });
  }

  /* ---------------------------------------------------------------
     Topic-level and full-test answer aggregation
     --------------------------------------------------------------- */

  function extractChoice(itemEl, item) {
    var checked = itemEl.querySelector('input[type="radio"]:checked');
    var options = item.options || [];
    var userIndex = checked ? Number(checked.value) : -1;
    var attempted = userIndex >= 0;
    return {
      question: item.prompt || "",
      userAnswer: attempted ? options[userIndex] : null,
      correctAnswer: options[item.answerIndex],
      result: !attempted ? "unanswered" : (userIndex === item.answerIndex ? "correct" : "incorrect"),
      explanation: item.explanation || "",
    };
  }

  function extractTrueFalse(itemEl, item) {
    var checked = itemEl.querySelector('input[type="radio"]:checked');
    var userAnswer = checked ? checked.value === "true" : null;
    return {
      question: item.statement || "",
      userAnswer: checked ? (userAnswer ? "Verum" : "Falsum") : null,
      correctAnswer: item.answer ? "Verum" : "Falsum",
      result: !checked ? "unanswered" : (userAnswer === item.answer ? "correct" : "incorrect"),
      explanation: item.explanation || "",
    };
  }

  function extractFillBlank(itemEl, item) {
    var blanks = itemEl.querySelectorAll(".blank-input");
    var values = Array.prototype.map.call(blanks, function (b) { return b.value; });
    var attempted = values.some(function (v) { return v && v.trim(); });
    var answers = item.answers || [];
    var allCorrect = values.length > 0 && values.every(function (v, i) { return matchesAny(v, answers[i]); });
    var correctText = answers.map(function (a) { return Array.isArray(a) ? a[0] : a; }).join(" · ");
    var userText = values.map(function (v) { return v && v.trim() ? v : "(spatium)"; }).join(" / ");
    return {
      question: String(item.prompt || "").replace(/___/g, "____"),
      userAnswer: attempted ? userText : null,
      correctAnswer: correctText,
      result: !attempted ? "unanswered" : (allCorrect ? "correct" : "incorrect"),
      explanation: item.explanation || "",
    };
  }

  function extractCorrection(itemEl, item) {
    var input = itemEl.querySelector(".answer-input");
    var val = input ? input.value : "";
    var attempted = val.trim().length > 0;
    var ok = attempted && matchesAny(val, item.answer);
    var correctText = Array.isArray(item.answer) ? item.answer[0] : item.answer;
    return {
      question: "“" + item.incorrect + "”",
      userAnswer: attempted ? val : null,
      correctAnswer: correctText,
      result: !attempted ? "unanswered" : (ok ? "correct" : "incorrect"),
      explanation: item.explanation || "",
    };
  }

  function extractTyping(itemEl, item) {
    var input = itemEl.querySelector(".answer-input");
    var val = input ? input.value : "";
    var attempted = val.trim().length > 0;
    if (!item.answer) {
      return {
        question: item.prompt || "",
        userAnswer: attempted ? val : null,
        correctAnswer: item.modelAnswer || null,
        result: attempted ? "self-check" : "unanswered",
        explanation: item.explanation || "",
      };
    }
    var ok = attempted && matchesAny(val, item.answer);
    var correctText = Array.isArray(item.answer) ? item.answer[0] : item.answer;
    return {
      question: item.prompt || "",
      userAnswer: attempted ? val : null,
      correctAnswer: correctText,
      result: !attempted ? "unanswered" : (ok ? "correct" : "incorrect"),
      explanation: item.explanation || "",
    };
  }

  function extractMatching(itemEl, item) {
    var selects = itemEl.querySelectorAll(".match-table select");
    var rows = item.pairs.map(function (pair, i) {
      var sel = selects[i];
      var chosen = sel ? sel.value : "";
      var attempted = !!chosen;
      var ok = attempted && norm(chosen) === norm(pair.right);
      return { left: pair.left, userRight: attempted ? chosen : null, correctRight: pair.right, ok: ok, attempted: attempted };
    });
    var anyAttempted = rows.some(function (r) { return r.attempted; });
    var allCorrect = rows.length > 0 && rows.every(function (r) { return r.ok; });
    return {
      question: rows.map(function (r) { return r.left; }).join(", "),
      userAnswer: anyAttempted ? rows.map(function (r) { return r.left + " → " + (r.userRight || "(nullum responsum)"); }).join("; ") : null,
      correctAnswer: rows.map(function (r) { return r.left + " → " + r.correctRight; }).join("; "),
      result: !anyAttempted ? "unanswered" : (allCorrect ? "correct" : "incorrect"),
      explanation: item.explanation || "",
    };
  }

  function extractOrdering(itemEl, item) {
    var chips = itemEl.querySelectorAll(".order-build .word-chip");
    var userWords = Array.prototype.map.call(chips, function (c) { return c.textContent; });
    var attempted = userWords.length > 0;
    var correct = attempted && userWords.length === item.words.length && userWords.every(function (w, i) { return w === item.words[i]; });
    return {
      question: item.prompt || "",
      userAnswer: attempted ? userWords.join(" ") : null,
      correctAnswer: item.words.join(" "),
      result: !attempted ? "unanswered" : (correct ? "correct" : "incorrect"),
      explanation: item.explanation || "",
    };
  }

  var EXTRACTORS = {
    "multiple-choice": extractChoice,
    vocabulary: extractChoice,
    "reading-comprehension": extractChoice,
    "true-false": extractTrueFalse,
    "fill-blank": extractFillBlank,
    correction: extractCorrection,
    typing: extractTyping,
    matching: extractMatching,
    ordering: extractOrdering,
  };

  function collectExerciseAnswers(container, data) {
    if (data.type === "writing") {
      var textareas = container.querySelectorAll(".writing-item__textarea");
      var writingItems = (data.items || []).map(function (item, i) {
        var ta = textareas[i];
        var val = ta ? ta.value : "";
        var attempted = val.trim().length > 0;
        return {
          question: item.prompt || "",
          userAnswer: attempted ? val : null,
          correctAnswer: null,
          result: attempted ? "self-check" : "unanswered",
          explanation: "",
        };
      });
      return { id: data.id, type: "writing", title: data.title || "Scriptio", instructions: data.instructions || "", items: writingItems };
    }

    var extractor = EXTRACTORS[data.type];
    var itemsWrap = container.querySelector(".exercise-block__items");
    var itemEls = itemsWrap ? itemsWrap.querySelectorAll(":scope > .exercise-item") : [];
    var items = (data.items || []).map(function (item, i) {
      var itemEl = itemEls[i];
      if (!extractor || !itemEl) {
        return { question: item.prompt || item.statement || "", userAnswer: null, correctAnswer: null, result: "unsupported", explanation: item.explanation || "" };
      }
      return extractor(itemEl, item);
    });
    return { id: data.id, type: data.type, title: data.title || "Exercitatio", instructions: data.instructions || "", items: items };
  }

  function collectTopicAnswers(topicSection) {
    var heading = topicSection.querySelector(".section__head h2, h2, h3");
    var topicTitle = heading ? heading.textContent.trim() : (topicSection.id || "Argumentum");
    var exercises = [];
    topicSection.querySelectorAll(".exercise-block").forEach(function (block) {
      var script = block.querySelector("script.exercise-data");
      if (!script) return;
      try {
        var data = JSON.parse(script.textContent);
        exercises.push(collectExerciseAnswers(block, data));
      } catch (e) {
        if (window.console) console.error("Could not collect answers for an exercise block", e);
      }
    });
    return { level: document.body.getAttribute("data-level-code") || "", topic: topicTitle, id: topicSection.id || "", exercises: exercises };
  }

  function collectTestYourselfAnswers() {
    var topics = [];
    document.querySelectorAll(".ty-topic[id]").forEach(function (section) {
      topics.push(collectTopicAnswers(section));
    });
    return { level: document.body.getAttribute("data-level-code") || "", topics: topics };
  }

  var RESULT_LABELS = {
    correct: "Rectum",
    incorrect: "Non recte",
    unanswered: "Non responsum",
    "self-check": "Scriptum",
    unsupported: "Non praesto",
  };

  function buildResultItemNode(entry) {
    var resultClass = entry.result === "correct" || entry.result === "incorrect" || entry.result === "unanswered" ? entry.result : "unanswered";
    var wrap = el("div", { class: "saved-summary-item is-" + resultClass });
    wrap.appendChild(el("p", { class: "saved-summary-item__status", text: RESULT_LABELS[entry.result] || entry.result }));
    if (entry.question) wrap.appendChild(el("p", { class: "saved-summary-item__q", text: entry.question }));
    wrap.appendChild(el("p", {
      class: "saved-summary-item__a",
      html: "<strong>Responsum tuum:</strong> " + (entry.userAnswer ? escapeHtml(entry.userAnswer) : "<em>(Nullum responsum)</em>"),
    }));
    if (entry.correctAnswer) {
      wrap.appendChild(el("p", {
        class: "saved-summary-item__correct",
        html: "<strong>" + (entry.result === "self-check" ? "Exemplar responsi:" : "Responsum rectum:") + "</strong> " + escapeHtml(entry.correctAnswer),
      }));
    }
    if (entry.explanation) {
      wrap.appendChild(el("p", { class: "saved-summary-item__explanation", text: entry.explanation }));
    }
    return wrap;
  }

  function buildExerciseSummaryNode(ex) {
    var block = el("div", { class: "exercise-block saved-summary-block" });
    var typeLabel = TYPE_LABELS[ex.type] ? TYPE_LABELS[ex.type] + " — " : "";
    block.appendChild(el("h3", { class: "exercise-block__title", text: typeLabel + (ex.title || "Exercitatio") }));
    if (ex.instructions) block.appendChild(el("p", { class: "exercise-block__instructions", text: ex.instructions }));
    var list = el("div", { class: "saved-summary-list" });
    ex.items.forEach(function (entry) { list.appendChild(buildResultItemNode(entry)); });
    block.appendChild(list);
    return block;
  }

  function buildTopicSummaryNode(topic) {
    var wrap = el("div", { class: "saved-summary-topic" });
    wrap.appendChild(el("h2", { class: "saved-summary-topic__title", text: topic.topic }));
    topic.exercises.forEach(function (ex) { wrap.appendChild(buildExerciseSummaryNode(ex)); });
    return wrap;
  }

  function performTopicSave(topicSection) {
    var topic = collectTopicAnswers(topicSection);
    var fakeData = { type: null, title: "Omnes Exercitationes Argumenti — Responsa Servata" };
    performSaveAnswers(topicSection, fakeData, function () {
      return wrapWithPrintHeader(buildTopicPrintHeaderText(topicSection), buildTopicSummaryNode(topic));
    });
  }

  function performTestSave() {
    var testData = collectTestYourselfAnswers();
    var fakeData = { type: null, title: "Te Ipsum Proba — Omnia Argumenta — Responsa Servata" };
    performSaveAnswers(document.body, fakeData, function () {
      var wrap = el("div", { class: "exercise-block saved-summary-root" });
      testData.topics.forEach(function (topic) { wrap.appendChild(buildTopicSummaryNode(topic)); });
      return wrapWithPrintHeader(buildTestPrintHeaderText(), wrap);
    });
  }

  // Shared button factory for every "save this whole scope's answers"
  // button (a Practice section, or one Test Yourself topic) -- one
  // place to change the visible text or the post-click feedback.
  // Grading + saving already has its own visible feedback (each
  // block's score panel, then the native print/save dialog); this
  // adds a brief "Servatum ✓" flash on the button itself as a
  // lightweight extra confirmation.
  function buildSaveAllAnswersButton(ariaLabel, onClick) {
    var label = "Serva Omnia Responsa";
    var btn = el("button", {
      type: "button",
      class: "btn btn--accent print-hidden save-all-answers-btn",
      text: label,
      "aria-label": ariaLabel,
    });
    var revertTimer = null;
    btn.addEventListener("click", function () {
      onClick();
      if (revertTimer) clearTimeout(revertTimer);
      btn.textContent = "Servatum ✓";
      revertTimer = setTimeout(function () {
        btn.textContent = label;
        revertTimer = null;
      }, 1500);
    });
    return btn;
  }

  // Finds the .exercise-actions row of the last exercise-block within
  // `root` that actually has a Submit ("Proba") button -- i.e. the
  // last *graded* block, searching backwards through document order.
  // A "writing" block's actions row only ever has a "Serva responsa
  // mea" button (no grading, so no Submit), so this skips over one
  // should a Practice section or Test Yourself topic ever end with
  // one, rather than assuming the very last DOM block is graded.
  function findLastSubmitActionsRow(root) {
    var blocks = root.querySelectorAll(".exercise-block");
    for (var i = blocks.length - 1; i >= 0; i--) {
      var actions = blocks[i].querySelector(".exercise-actions");
      var firstBtn = actions ? actions.querySelector("button") : null;
      if (firstBtn && firstBtn.textContent === "Proba") return actions;
    }
    return null;
  }

  // Inserts `btn` as the row's second control, immediately after
  // Submit -- [Proba] [Serva Omnia Responsa] -- rather than at the
  // end of the row (after Retry/Retry all/Save my answers, which only
  // reveal themselves once that one exercise has been graded). The
  // new button stays visible before, during and after that exercise's
  // own Submit/Retry cycle, since what it saves is the whole
  // section/topic, not just this one exercise.
  function insertBesideSubmit(actionsRow, btn) {
    var submitBtn = actionsRow.querySelector("button");
    if (submitBtn && submitBtn.nextSibling) {
      actionsRow.insertBefore(btn, submitBtn.nextSibling);
    } else {
      actionsRow.appendChild(btn);
    }
  }

  // Individual lesson pages have exactly one exercise-bearing section,
  // id="practice" (same id every lesson page uses, verified across the
  // whole site). The button is inserted beside that section's own
  // last Submit button and saves every exercise block inside it.
  function addPracticeSaveAllButton() {
    var practice = document.getElementById("practice");
    if (!practice) return;
    if (practice.querySelector(".save-all-answers-btn")) return;
    var actionsRow = findLastSubmitActionsRow(practice);
    if (!actionsRow) return;

    var heading = practice.querySelector(".section__head h2, h2, h3");
    var label = heading ? heading.textContent.trim() : "Exercitium";

    var btn = buildSaveAllAnswersButton(
      "Serva omnia responsa: " + label,
      function () { submitUnsubmittedBlocksIn([practice]); performGenericSave([practice], label); }
    );
    insertBesideSubmit(actionsRow, btn);
  }

  // Test Yourself: every .ty-topic (including the last) gets its own
  // "Serva Omnia Responsa" button beside its own last Submit button,
  // scoped to only that topic's own exercises (never another topic's).
  function addTestYourselfTopicSaveButtons() {
    document.querySelectorAll(".ty-topic[id]").forEach(function (topicSection) {
      var actionsRow = findLastSubmitActionsRow(topicSection);
      if (!actionsRow) return;
      var heading = topicSection.querySelector(".section__head h2, h2, h3");
      var topicTitle = heading ? heading.textContent.trim() : "hoc argumentum";
      var btn = buildSaveAllAnswersButton(
        "Serva omnia responsa argumenti: " + topicTitle,
        function () { performTopicSave(topicSection); }
      );
      insertBesideSubmit(actionsRow, btn);
    });
  }

  // `roots` is an array of sections whose .exercise-block children
  // should all be graded (if not already) and then saved together --
  // used by addPracticeSaveAllButton above so grading an un-submitted
  // block, the score UI, and mastery/progress recording all happen
  // exactly as they would if the student clicked that block's own
  // Submit by hand.
  function submitUnsubmittedBlocksIn(roots) {
    roots.forEach(function (root) {
      root.querySelectorAll(".exercise-block").forEach(function (block) {
        var submitBtn = block.querySelector(".exercise-actions > button.btn--accent");
        if (submitBtn && submitBtn.textContent === "Proba" && submitBtn.style.display !== "none") submitBtn.click();
      });
    });
  }

  function collectAnswersInRoots(roots) {
    var exercises = [];
    roots.forEach(function (root) {
      root.querySelectorAll(".exercise-block").forEach(function (block) {
        var script = block.querySelector("script.exercise-data");
        if (!script) return;
        try {
          var data = JSON.parse(script.textContent);
          exercises.push(collectExerciseAnswers(block, data));
        } catch (e) {
          if (window.console) console.error("Could not collect answers for an exercise block", e);
        }
      });
    });
    return exercises;
  }

  function buildGenericPrintHeaderText(label) {
    var levelCode = (document.body.getAttribute("data-level-code") || "").trim();
    var parts = [];
    if (levelCode) parts.push(levelCode);
    parts.push(label);
    return parts.join(" - ");
  }

  function performGenericSave(roots, label) {
    var exercises = collectAnswersInRoots(roots);
    var fakeData = { type: null, title: label + " — Responsa Servata" };
    performSaveAnswers(document.body, fakeData, function () {
      var wrap = el("div", { class: "exercise-block saved-summary-root" });
      exercises.forEach(function (ex) { wrap.appendChild(buildExerciseSummaryNode(ex)); });
      return wrapWithPrintHeader(buildGenericPrintHeaderText(label), wrap);
    });
  }

  function init() {
    document.querySelectorAll(".exercise-block").forEach(function (container) {
      var dataScript = container.querySelector("script.exercise-data");
      if (!dataScript) return;
      try {
        var data = JSON.parse(dataScript.textContent);
        if (data.type === "writing") {
          buildWritingBlock(container, data);
        } else {
          buildBlock(container, data);
        }
      } catch (e) {
        container.innerHTML = "<p>Haec exercitatio onerari non potuit.</p>";
        if (window.console) console.error("Exercise parse error", e);
      }
    });
    addTestYourselfTopicSaveButtons();
    addPracticeSaveAllButton();
    maybeAddTestSaveButton();
  }

  function maybeAddTestSaveButton() {
    if (!document.querySelector(".ty-topic[id]")) return;
    var bottomNav = document.querySelector("#bottom .lesson-nav");
    if (!bottomNav || document.getElementById("ty-save-all-btn")) return;
    var levelCode = document.body.getAttribute("data-level-code") || "";
    var wrap = el("div", { class: "lesson-nav", style: "justify-content:center;border-top:none;padding-top:0;" });
    var btn = el("button", {
      type: "button",
      id: "ty-save-all-btn",
      class: "btn btn--accent print-hidden",
      text: "Serva Omnia Responsa",
      "aria-label": "Serva omnia responsa ex omnibus argumentis" + (levelCode ? " (" + levelCode + ")" : "") + " (Te Ipsum Proba)",
    });
    btn.addEventListener("click", function () {
      performTestSave();
    });
    wrap.appendChild(btn);
    bottomNav.parentNode.insertBefore(wrap, bottomNav);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Minimal public API -- lets a page (hodie.html) build fresh
  // .exercise-block markup at runtime (e.g. for spaced-repetition due
  // items assembled from assets/data/exercise-items-index.json) and
  // have it graded by the exact same engine as every hand-authored
  // lesson page, instead of a second rendering implementation.
  window.ExerciseEngine = { init: init };
})();
