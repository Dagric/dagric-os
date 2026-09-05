(function () {
  "use strict";

  var input = document.getElementById("site-search");
  var status = document.getElementById("site-search-status");
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-search-card]"));
  var empty = document.getElementById("site-search-empty");
  var clear = document.getElementById("site-search-clear");
  if (!input || !status || !cards.length) return;

  function normalized(value) {
    return value.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .replace(/wi[\s-]?fi/g, "wifi")
      .replace(/\bback[ -]?ups?\b/g, "backup")
      .replace(/\bcolour\b/g, "color")
      .replace(/\b(move|moving|transfer|transferring)\b/g, "migration")
      .replace(/\b(internet|wireless)\b/g, "wifi")
      .replace(/\b(programs?|applications?)\b/g, "apps")
      .replace(/\b(downloads|installing|installed)\b/g, function (word) {
        return word === "downloads" ? "download" : "install";
      })
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  var ignored = /^(a|an|and|are|can|do|does|for|get|how|i|in|is|it|me|my|of|on|or|please|the|to|use|what|when|where|which|will|with|work|works|you|your|dagric|os)$/;
  var entries = cards.map(function (card) {
    return normalized(card.textContent + " " + (card.getAttribute("data-search") || "")).split(/\s+/);
  });

  function filter() {
    var query = normalized(input.value);
    var terms = query ? query.split(/\s+/).filter(function (term) { return !ignored.test(term); }) : [];
    var visible = 0;

    cards.forEach(function (card, index) {
      var hit = terms.every(function (term) {
        return entries[index].some(function (word) {
          return word === term || (term.length >= 3 && word.indexOf(term) === 0);
        });
      });
      card.hidden = !hit;
      if (hit) visible += 1;
    });

    status.textContent = terms.length
      ? visible + (visible === 1 ? " result" : " results") + " for “" + input.value.trim() + "”"
      : cards.length + " topics available";
    if (empty) empty.hidden = visible !== 0;
    if (clear) clear.hidden = !input.value;

    var url = new URL(window.location.href);
    if (input.value.trim()) url.searchParams.set("q", input.value.trim());
    else url.searchParams.delete("q");
    try { window.history.replaceState(null, "", url.pathname + url.search + url.hash); } catch (e) {}
  }

  var initial = new URLSearchParams(window.location.search).get("q") || "";
  input.value = initial;
  input.addEventListener("input", filter);
  if (clear) clear.addEventListener("click", function () {
    input.value = "";
    filter();
    input.focus();
  });
  filter();
})();
