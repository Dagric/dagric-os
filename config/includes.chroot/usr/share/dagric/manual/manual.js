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
 *
 * THE SECOND MARKER, l=, IS THE TRANSLATION STRATEGY, and it is worth stating
 * plainly because it is a decision rather than an oversight.
 *
 * Dagric's German documentation is the welcome page and the user guide — the
 * two things a new owner reads in their first hour, both single pages, both
 * translated in full. This manual is 95 pages and 46,000 words of reference
 * material, and translating it has two costs that do not shrink: the words
 * themselves, and the fact that every English edit re-opens every language.
 * More to the point, this manual's whole promise is that its search knows the
 * Windows names — "type Notepad and you get Kate". Half-translating it breaks
 * exactly that: a German owner typing "Editor" or "Datei-Explorer" into an
 * English index finds nothing, and a page that looks translated but answers in
 * English is worse than one that never claimed to be.
 *
 * So the manual stays English, and says so — in the reader's own language, at
 * the top of the page, with a link back to the German guide. An honest English
 * manual is a normal state of affairs for an OS. A manual that pretends is not.
 * When a language earns the translation (see docs for the po4a route), drop the
 * pages in a per-language directory and add the code to LANGS below.
 */
(function () {
  /* Languages with real, complete Dagric documentation. A language belongs
     here only when its guide and welcome page are actually translated —
     never offer a language you have not shipped. */
  var LANGS = {
    de: {
      /* Shown on manual pages to somebody who arrived from the German guide,
         or whose browser is German. Keep it short and keep it true. */
      note:    'Das Handbuch gibt es bisher nur auf Englisch.',
      body:    'Auf Deutsch sind die Willkommensseite und die Kurzanleitung für die erste Woche verfügbar. Diese 95 Seiten mit ihrer Suche nach Windows-Namen sind noch nicht übersetzt — ehrlich englisch ist uns lieber als halb übersetzt.',
      guide:   'Zur deutschen Kurzanleitung',
      dismiss: 'Verstanden'
    }
  };

  /* Read both markers out of the fragment and stamp them on <html> so CSS can
     act on them. Called before the body paints (so the free-edition notice
     never flashes in and out on a Pro machine) and again on every hashchange —
     a URL that differs only in its fragment does NOT reload the page, so
     without this a manual left open would keep showing the edition, or the
     language, it was first opened with. */
  function readMarkers() {
    var hash = window.location.hash || '';
    var e = /(?:^|[#&])e=(pro|free)\b/.exec(hash);
    var l = /(?:^|[#&])l=([a-z]{2}(?:-[A-Za-z]{2,4})?)\b/.exec(hash);
    var edition = e ? e[1] : 'unknown';
    var lang = l && LANGS[l[1].slice(0, 2)] ? l[1].slice(0, 2) : '';
    document.documentElement.setAttribute('data-edition', edition);
    document.documentElement.setAttribute('data-lang', lang || 'en');
    var parts = [];
    if (edition !== 'unknown') { parts.push('e=' + edition); }
    if (lang) { parts.push('l=' + lang); }
    return { tag: parts.length ? '#' + parts.join('&') : '', lang: lang };
  }

  /* Rewrite internal links so the markers travel. Idempotent: any marker
     already on the href is stripped first, so calling this twice cannot
     produce "app-kate.html#e=free#e=free&l=de". */
  function tagLinks(tag) {
    var links = document.querySelectorAll('a[href*=".html"]');
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href').replace(/#(?:e|l)=[^#]*$/, '');
      links[i].setAttribute('href', href + tag);
    }
  }

  var state = readMarkers();

  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else { fn(); }
  }

  /* Say, in the reader's language, that this manual is not in it. Shown when
     the fragment carries l=xx, and otherwise when the browser's own language
     has Dagric documentation — that second case is the one that matters, since
     `dagric-manual` opens these pages with no language marker at all. */
  function languageNotice(lang) {
    if (!lang) {
      var nav = (navigator.language || '').slice(0, 2).toLowerCase();
      if (LANGS[nav]) { lang = nav; }
    }
    if (!lang) { return; }
    try {
      if (window.sessionStorage &&
          sessionStorage.getItem('dagric-langnote-' + lang) === 'off') { return; }
    } catch (err) { /* file:// storage can be walled off; the note just returns */ }

    var t = LANGS[lang];
    var main = document.querySelector('main.content');
    if (!main) { return; }

    var box = document.createElement('div');
    box.className = 'langnote';
    box.setAttribute('lang', lang);
    /* role=note, not alert: it is context, and an alert would interrupt a
       screen reader mid-sentence on every single page. */
    box.setAttribute('role', 'note');

    var head = document.createElement('strong');
    head.textContent = t.note;
    box.appendChild(head);
    box.appendChild(document.createTextNode(' ' + t.body + ' '));

    var link = document.createElement('a');
    /* The guide sits beside the manual in /usr/share/dagric, and its
       translations sit one directory deeper: guide/de/index.html. The extra
       ../ covers a future manual/<lang>/ without needing a second edit. */
    var rest = location.pathname.split('/manual/')[1] || '';
    var up = rest.indexOf('/') === -1 ? '../' : '../../';
    link.href = up + 'guide/' + lang + '/index.html';
    link.setAttribute('hreflang', lang);
    link.textContent = t.guide;
    box.appendChild(link);

    var off = document.createElement('button');
    off.type = 'button';
    off.className = 'dismiss';
    off.textContent = t.dismiss;
    off.addEventListener('click', function () {
      try { sessionStorage.setItem('dagric-langnote-' + lang, 'off'); } catch (err) {}
      box.parentNode.removeChild(box);
      var m = document.getElementById('main');
      if (m) { m.focus(); }
    });
    box.appendChild(document.createTextNode(' '));
    box.appendChild(off);

    main.insertBefore(box, main.firstChild);
  }

  onReady(function () {
    /* 1. Carry the edition and the language across every page of the manual. */
    tagLinks(state.tag);
    window.addEventListener('hashchange', function () {
      state = readMarkers();
      tagLinks(state.tag);
    });
    languageNotice(state.lang);

    /* 2. Landing page only: search, the Pro filter, and section jumps. */
    var q = document.getElementById('q');
    if (!q) { return; }

    var cards    = Array.prototype.slice.call(document.querySelectorAll('a.card'));
    var sections = Array.prototype.slice.call(document.querySelectorAll('section.group'));
    var counter  = document.getElementById('count');
    var none     = document.getElementById('noresults');
    var hidepro  = document.getElementById('hidepro');
    var slashkey = document.getElementById('slashkey');
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
      /* #count is a live region (role=status in the HTML), so this sentence is
         what a screen-reader user hears after they stop typing. Filtered-out
         cards are display:none, which takes them out of the accessibility tree
         as well as off the screen — the count and the list always agree. */
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

    /* Escape clears the box; "/" jumps into it from anywhere on the page.
     *
     * The "/" part needs the checkbox next to it. A shortcut bound to a bare
     * printing character is WCAG 2.1.4 (Level A) unless it can be turned off:
     * somebody driving this machine by voice says "slash" by accident all day,
     * and every one of those would have yanked the focus into the search box.
     * The preference is remembered where storage is allowed; where it is not
     * (file:// in a locked-down browser) it still turns off for this page,
     * which is what the success criterion actually asks for. */
    q.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { q.value = ''; apply(); }
    });
    if (slashkey) {
      try {
        if (window.localStorage && localStorage.getItem('dagric-slashkey') === 'off') {
          slashkey.checked = false;
        }
      } catch (err) {}
      slashkey.addEventListener('change', function () {
        try {
          localStorage.setItem('dagric-slashkey', slashkey.checked ? 'on' : 'off');
        } catch (err) {}
      });
    }
    document.addEventListener('keydown', function (e) {
      if (e.key !== '/' || e.ctrlKey || e.altKey || e.metaKey) { return; }
      if (slashkey && !slashkey.checked) { return; }
      var el = document.activeElement;
      var tag = el ? (el.tagName || '').toLowerCase() : '';
      if (tag === 'input' || tag === 'textarea' || tag === 'select' ||
          (el && el.isContentEditable)) { return; }
      e.preventDefault(); q.focus(); q.select();
    });

    /* Sidebar jumps scroll instead of navigating: letting the browser follow
       href="#g-files" would overwrite the #e= marker and the manual would
       forget the edition. The href is still the real section, so the link has
       a destination without JavaScript and reads as one to a screen reader —
       and because the browser is not moving focus for us, we move it, or a
       keyboard user would land back at the top of the sidebar on the next Tab. */
    var jumps = document.querySelectorAll('a[data-goto]');
    var smooth = !(window.matchMedia &&
                   window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    for (var j = 0; j < jumps.length; j++) {
      jumps[j].addEventListener('click', function (e) {
        var el = document.getElementById(this.getAttribute('data-goto'));
        if (!el) { return; }
        e.preventDefault();
        if (!el.hasAttribute('tabindex')) { el.setAttribute('tabindex', '-1'); }
        el.focus({ preventScroll: true });
        el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
      });
    }

    apply();
  });
})();
