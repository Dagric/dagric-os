/* Dagric OS User Guide — sidebar highlighting. Lifted out of index.html so the
   English and German pages run identical code; it reads nothing but the DOM,
   so it needs no translating. */
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('nav.toc a'));
  var map = {};
  links.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
  var sections = Array.prototype.slice.call(document.querySelectorAll('main section'));
  function setActive(id) {
    links.forEach(function (a) { a.classList.remove('active'); });
    if (map[id]) map[id].classList.add('active');
  }
  if ('IntersectionObserver' in window) {
    var visible = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
      for (var i = 0; i < sections.length; i++) {
        if (visible[sections[i].id]) { setActive(sections[i].id); break; }
      }
    }, { rootMargin: '-15% 0px -70% 0px' });
    sections.forEach(function (s) { io.observe(s); });
  }
  /* A <section> is not focusable, so following one of these links moved the
     view but left the keyboard where it was: the next Tab went back to the top
     of the sidebar, and a screen reader carried on reading the sidebar. Give
     the target a programmatic focus stop and send focus there — the browser
     still does the scrolling. */
  sections.forEach(function (s) {
    if (!s.hasAttribute('tabindex')) { s.setAttribute('tabindex', '-1'); }
  });
  links.forEach(function (a) {
    a.addEventListener('click', function () {
      var id = a.getAttribute('href').slice(1);
      setActive(id);
      var el = document.getElementById(id);
      if (el) { el.focus({ preventScroll: true }); }
    });
  });
})();

/* ---------- search ----------
   Filters the guide's sections as you type. Every user-visible string comes
   from data attributes on the input, so this file stays identical for the
   English and German pages — the rule at the top of this file, kept.
   Sections are hidden with [hidden] rather than a class so the state is
   visible to assistive tech for free. */
(function () {
  var input = document.getElementById('gsearch');
  if (!input) { return; }
  var status = document.getElementById('gsearch-status');
  var sections = Array.prototype.slice.call(document.querySelectorAll('main section'));
  var toc = Array.prototype.slice.call(document.querySelectorAll('nav.toc a'));
  var tocFor = {};
  toc.forEach(function (a) { tocFor[a.getAttribute('href').slice(1)] = a; });
  /* Every direct child of the nav, in order: group headings and links mixed.
     Needed because hiding links leaves their heading standing over nothing —
     harmless when the headings are a faint desktop label, actively confusing
     once they also appear in the phone pill strip. */
  var navKids = Array.prototype.slice.call(document.querySelectorAll('nav.toc > *'));

  /* The searchable text is cached once. textContent on every keystroke over
     twenty sections is cheap, but doing it once is free. Synonyms travel in
     each section's data-syn attribute — that is where "task manager" finds
     the System Monitor section, and it is per-language by construction
     because it lives in the page, not here. */
  var hay = sections.map(function (s) {
    return ((s.textContent || '') + ' ' + (s.getAttribute('data-syn') || '')).toLowerCase();
  });

  function apply() {
    var q = input.value.trim().toLowerCase();
    var shown = 0;
    sections.forEach(function (s, i) {
      var hit = !q || hay[i].indexOf(q) !== -1;
      s.hidden = !hit;
      if (hit) { shown++; }
      var a = tocFor[s.id];
      if (a) { a.hidden = !hit; }
    });
    /* Walk the nav backwards: a group heading is worth showing only if at
       least one link below it, before the next heading, survived the filter. */
    for (var i = navKids.length - 1, live = false; i >= 0; i--) {
      var k = navKids[i];
      if (k.className.indexOf('navgroup') !== -1) { k.hidden = !live; live = false; }
      else if (!k.hidden) { live = true; }
    }
    if (status) {
      if (!q) { status.textContent = ''; }
      else if (shown === 0) { status.textContent = input.getAttribute('data-none') || ''; }
      else {
        /* One match is the commonest result this search returns, and the count
           string had no singular, so the first thing a reader saw when the
           search WORKED was "1 sections match". data-count-one is optional:
           a translation that has not been given one falls back to the plural
           string and behaves exactly as it does today. */
        var t = (shown === 1 && input.getAttribute('data-count-one'))
                || input.getAttribute('data-count') || '%1';
        status.textContent = t.replace('%1', String(shown));
      }
    }
  }
  input.addEventListener('input', apply);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { input.value = ''; apply(); }
  });

  /* THE CROSS-LINKS THE FILTER STRANDS. Hiding a section also breaks every
     in-content link pointing INTO it — the checklist's eight "More" links, the
     tips, "Text Size (above)". Search "checklist" and section 2 survives with
     all eight of its links aimed at sections that are no longer on the page;
     clicking one jumps to a display:none element and the page looks frozen.
     That is the exact defect `nav.toc a[hidden]` in guide.css fixes for the
     sidebar and that content links never got.
     Clearing the query beats disabling the link: the reader asked to be taken
     there, so take them there and drop the filter on the way. Delegated, so it
     covers links added to any section without further wiring. */
  document.addEventListener('click', function (e) {
    if (!input.value) { return; }
    var t = e.target;
    var a = (t && t.closest) ? t.closest('a[href^="#"]') : null;
    if (!a) { return; }
    var el = document.getElementById(a.getAttribute('href').slice(1));
    var sec = (el && el.closest) ? el.closest('section') : null;
    if (!sec || !sec.hidden) { return; }
    input.value = '';
    apply();
  });
})();

/* ---------- the first-day checklist ----------
   Checkbox state persists in localStorage so the list survives closing the
   page — that is the whole difference between a checklist and a paragraph
   with squares in it. Wrapped in try/catch because localStorage can throw on
   file:// in hardened configurations, and a checklist that forgets is still
   a checklist: everything but the remembering works without it. */
(function () {
  var list = document.getElementById('firstday-list');
  if (!list) { return; }
  var boxes = Array.prototype.slice.call(list.querySelectorAll('input[type=checkbox]'));
  var count = document.getElementById('ck-count');
  var KEY = 'dagric-guide-firstday';

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) { return; }
      var done = JSON.parse(raw);
      boxes.forEach(function (b) { if (done[b.getAttribute('data-ck')]) { b.checked = true; } });
    } catch (e) { /* remembering is optional */ }
  }
  function save() {
    try {
      var done = {};
      boxes.forEach(function (b) { if (b.checked) { done[b.getAttribute('data-ck')] = 1; } });
      localStorage.setItem(KEY, JSON.stringify(done));
    } catch (e) { /* remembering is optional */ }
  }
  function tally() {
    if (!count) { return; }
    var n = boxes.filter(function (b) { return b.checked; }).length;
    var t = list.getAttribute('data-done-template') || '%1/%2';
    count.textContent = t.replace('%1', String(n)).replace('%2', String(boxes.length));
  }
  boxes.forEach(function (b) {
    b.addEventListener('change', function () { save(); tally(); });
  });
  load();
  tally();
})();
