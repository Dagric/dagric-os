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
