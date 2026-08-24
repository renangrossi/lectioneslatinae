/*!
 * Lectiones Latinae — Lexicon word lookup
 * Rewrites every lexicon/pronunciation-reference link on the page to
 * point at whatever word the user has typed, entirely client-side.
 * Ported from the sibling English-course project's dictionary.js.
 */
(function () {
  "use strict";

  var input = document.querySelector("[data-dict-word]");
  if (!input) return;
  var cards = document.querySelectorAll(".dict-card[data-url-template]");

  function update() {
    var raw = input.value.trim();
    var word = raw || "rosa";
    var encoded = encodeURIComponent(word.toLowerCase());
    cards.forEach(function (card) {
      var tmpl = card.getAttribute("data-url-template");
      var link = card.querySelector("[data-dict-link]");
      if (!link) return;
      link.href = tmpl.replace("{word}", encoded);
      link.textContent = "";
      var icon = link.querySelector("svg");
      if (icon) link.appendChild(icon);
      link.appendChild(document.createTextNode(raw ? "Quaere “" + raw + "”" : "Quaere"));
    });
  }

  input.addEventListener("input", update);
  update();

  // Enter key opens a random one of the core lexica
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      var primaryLinks = document.querySelectorAll(".card--feature.dict-card [data-dict-link]");
      if (!primaryLinks.length) return;
      var pick = primaryLinks[Math.floor(Math.random() * primaryLinks.length)];
      recordDictionaryUse();
      window.open(pick.href, "_blank", "noopener");
    }
  });

  // Any outbound "Quaere" click is a real dictionary use.
  function recordDictionaryUse() {
    if (window.ProgressTracker && typeof window.ProgressTracker.recordDictionaryUse === "function") {
      window.ProgressTracker.recordDictionaryUse();
    }
  }
  document.querySelectorAll(".dict-card[data-url-template] [data-dict-link]").forEach(function (link) {
    link.addEventListener("click", recordDictionaryUse);
  });
})();
