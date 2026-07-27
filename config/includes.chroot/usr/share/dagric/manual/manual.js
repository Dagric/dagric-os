/* Dagric OS Manual — everything the manual needs, offline, no libraries.
 *
 * WHY THE HASH. This manual is opened as file:// URLs by `dagric-manual`,
 * which knows the edition (it reads /etc/dagric-edition) while the HTML
 * cannot: a page loaded from file:// may not read /etc, and there is no
 * server to ask. So the launcher states the edition in the URL fragment
 * (#e=pro / #e=free) and every internal link carries it onward.
 *
 * When there is no marker at all — somebody double-clicked index.html in
 * Dolphin — the edition is "unknown" and the manual says nothing either way.
 * Guessing wrong is worse than staying quiet: telling a Pro owner that their
 * installed software "is not on this edition" is a support ticket.
 */
(function () {
  /* Read the marker and stamp it on <html> so CSS can act on it. Called before
     the body paints (so the free-edition notice never flashes in and out on a
     Pro machine) and again on every hashchange — a URL that differs only in its
     fragment does NOT reload the page, so without this a manual left open would
     keep showing the edition it was first opened with. */
  function readEdition() {
    var m = /(?:^|[#&])e=(pro|free)\b/.exec(window.location.hash || '');
    var edition = m ? m[1] : 'unknown';
    document.documentElement.setAttribute('data-edition', edition);
    return edition === 'unknown' ? '' : '#e=' + edition;
  }

  /* Rewrite internal links so the marker travels. Idempotent: any marker
     already on the href is stripped first, so calling this twice cannot
     produce "app-kate.html#e=free#e=pro". */
  function tagLinks(tag) {
    var links = document.querySelectorAll('a[href*=".html"]');
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href').replace(/#e=(?:pro|free)$/, '');
      links[i].setAttribute('href', href + tag);
    }
  }

  var tag = readEdition();

  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else { fn(); }
  }

  onReady(function () {
    /* 1. Carry the edition across every page of the manual. */
    tagLinks(tag);
    window.addEventListener('hashchange', function () { tagLinks(readEdition()); });

    /* 2. Landing page only: search, the Pro filter, and section jumps. */
    var q = document.getElementById('q');
    if (!q) return;

    var cards    = Array.prototype.slice.call(document.querySelectorAll('a.card'));
    var sections = Array.prototype.slice.call(document.querySelectorAll('section.group'));
    var counter  = document.getElementById('count');
    var none     = document.getElementById('noresults');
    var hidepro  = document.getElementById('hidepro');
    var total    = cards.length;

    function apply() {
      var needle = q.value.toLowerCase().trim();
      var words  = needle ? needle.split(/\s+/) : [];
      var shown  = 0;
      for (var i = 0; i < cards.length; i++) {
        var hay = cards[i].getAttribute('data-s');
        var ok = true;
        for (var w = 0; w < words.length; w++) {
          if (hay.indexOf(words[w]) === -1) { ok = false; break; }
        }
        if (ok && hidepro && hidepro.checked &&
            cards[i].getAttribute('data-avail') === 'pro') { ok = false; }
        cards[i].classList.toggle('hide', !ok);
        if (ok) shown++;
      }
      for (var s = 0; s < sections.length; s++) {
        sections[s].classList.toggle(
          'empty', !sections[s].querySelector('a.card:not(.hide)'));
      }
      counter.textContent = shown === total
        ? total + ' pages'
        : shown + ' of ' + total + ' pages';
      none.style.display = shown ? 'none' : 'block';
    }

    q.addEventListener('input', apply);
    if (hidepro) hidepro.addEventListener('change', function () {
      document.documentElement.setAttribute('data-hidepro', hidepro.checked ? '1' : '0');
      apply();
    });

    /* Escape clears the box; "/" jumps into it from anywhere on the page. */
    q.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { q.value = ''; apply(); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === '/' && document.activeElement !== q) {
        e.preventDefault(); q.focus(); q.select();
      }
    });

    /* Sidebar jumps scroll instead of navigating: an href="#writing" would
       overwrite the #e= marker and the manual would forget the edition. */
    var jumps = document.querySelectorAll('a[data-goto]');
    for (var j = 0; j < jumps.length; j++) {
      jumps[j].addEventListener('click', function (e) {
        e.preventDefault();
        var el = document.getElementById(this.getAttribute('data-goto'));
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }

    apply();
  });
})();
