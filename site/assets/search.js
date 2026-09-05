(function () {
  "use strict";

  var input = document.getElementById("site-search");
  var status = document.getElementById("site-search-status");
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-search-card]"));
  if (!input || !status || !cards.length) return;

  function normalized(value) {
    return value.toLowerCase()
      .replace(/wi[\s-]?fi/g, "wifi")
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function filter() {
    var query = normalized(input.value);
    var terms = query ? query.split(/\s+/) : [];
    var visible = 0;

    cards.forEach(function (card) {
      var haystack = " " + normalized(card.textContent + " " + (card.getAttribute("data-search") || "")) + " ";
      var hit = terms.every(function (term) {
        return haystack.indexOf(" " + term + " ") !== -1;
      });
      card.hidden = !hit;
      if (hit) visible += 1;
    });

    status.textContent = query
      ? visible + (visible === 1 ? " result" : " results") + " for “" + input.value.trim() + "”"
      : cards.length + " topics available";

    var url = new URL(window.location.href);
    if (input.value.trim()) url.searchParams.set("q", input.value.trim());
    else url.searchParams.delete("q");
    window.history.replaceState(null, "", url.pathname + url.search);
  }

  var initial = new URLSearchParams(window.location.search).get("q") || "";
  input.value = initial;
  input.addEventListener("input", filter);
  filter();
})();
