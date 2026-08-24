/*!
 * Lectiones Latinae — Verba Irregularia (verba-irregularia.html)
 * Progressive enhancement only: the full table is already in the
 * page's static HTML (works with no JS, indexable, printable). This
 * just adds live client-side filtering across every column (present,
 * perfect, supine, meaning...) as the student types. Ported from the
 * sibling English-course project's irregular-verbs.js.
 */
(function () {
  "use strict";

  var input = document.querySelector("[data-verb-filter]");
  var tbody = document.querySelector("[data-verb-tbody]");
  if (!input || !tbody) return;

  var countNotice = document.querySelector("[data-verb-count]");
  var emptyNotice = document.querySelector("[data-verb-empty]");
  var emptyTerm = document.querySelector("[data-verb-empty-term]");
  var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
  var total = rows.length;

  function filter() {
    var q = input.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var match = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
      row.hidden = !match;
      if (match) shown++;
    });

    if (emptyNotice) emptyNotice.hidden = shown !== 0;
    if (emptyTerm) emptyTerm.textContent = input.value.trim();
    if (countNotice) {
      countNotice.hidden = shown === 0;
      var text = q
        ? shown + " ex " + total + " formis monstrantur quae cum “" + input.value.trim() + "” congruunt."
        : "Omnes " + total + " formae monstrantur.";
      var textNode = Array.prototype.find.call(countNotice.childNodes, function (n) { return n.nodeType === 3; });
      if (textNode) textNode.textContent = text;
    }
  }

  var debounceTimer;
  input.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(filter, 80);
  });
})();
