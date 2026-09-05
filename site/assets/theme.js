
(function () {
  'use strict';

  var KEY  = 'dagric-theme';
  var root = document.documentElement;

  function read()   { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(v) { try { localStorage.setItem(KEY, v); }    catch (e) {} }


  function paintMeta() {
    var m = document.querySelector('meta[name="theme-color"]');
    if (!m || !document.body) return;
    var bg = getComputedStyle(document.body).backgroundColor;
    if (bg && bg !== 'transparent' && bg.indexOf('rgba(0, 0, 0, 0)') === -1)
      m.setAttribute('content', bg);
  }

  function apply(theme) {

    root.classList.add('theme-swap');


    if (theme === 'light') root.setAttribute('data-theme', 'light');
    else                   root.removeAttribute('data-theme');

    void root.offsetWidth;
    if (window.requestAnimationFrame)
      requestAnimationFrame(function () { root.classList.remove('theme-swap'); });
    else
      root.classList.remove('theme-swap');

    paintMeta();
  }


  var preference = read();
  var systemLight = window.matchMedia('(prefers-color-scheme: light)');
  var current = preference === 'light' || (preference !== 'dark' && systemLight.matches) ? 'light' : 'dark';
  apply(current);

  function build() {
    paintMeta();   /* <body> exists now, so the chrome colour can be read */

    var primaryNav = document.querySelector('body > nav');
    if (primaryNav) {
      primaryNav.setAttribute('aria-label', 'Main navigation');
      var path = window.location.pathname.replace(/\/$|\.html$/g, '') || '/';
      primaryNav.querySelectorAll('a[href]').forEach(function (link) {
        if ((link.getAttribute('href').replace(/\/$|\.html$/g, '') || '/') === path)
          link.setAttribute('aria-current', 'page');
      });
      function measureNav() { root.style.setProperty('--nav-h', primaryNav.offsetHeight + 'px'); }
      measureNav();
      if (window.ResizeObserver) new ResizeObserver(measureNav).observe(primaryNav);
      else window.addEventListener('resize', measureNav);
    }

    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    function respectMotionPreference() {
      if (!reducedMotion.matches) return;
      document.querySelectorAll('video[autoplay]').forEach(function (video) {
        video.removeAttribute('autoplay');
        video.pause();
      });
    }
    respectMotionPreference();
    if (reducedMotion.addEventListener) reducedMotion.addEventListener('change', respectMotionPreference);


    var sitebar = document.querySelector('.sitebar .sitebar-in');
    var foot = document.querySelector('footer .foot');
    if (!foot && !sitebar) return;
    var footer = foot ? foot.parentNode : null;

    if (document.querySelector('.themetog')) return;

    var box = document.createElement('div');
    box.className = 'themebox';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'themetog';


    function label() {
      var next = current === 'light' ? 'dark' : 'light';
      btn.textContent = next === 'light' ? 'Light theme' : 'Dark theme';
      btn.setAttribute('aria-label', 'Use the ' + next + ' website theme');
    }
    label();

    btn.addEventListener('click', function () {
      current = (current === 'light') ? 'dark' : 'light';
      apply(current);
      write(current);
      label();
    });

    box.appendChild(btn);


    var wide = window.matchMedia('(min-width:641px)');
    var navLinks = document.querySelector('nav .nav-links');

    function mount() {
      /* The guide has no site nav and no .foot, so its bar is the only mount
         and the breakpoint does not apply — it is one row at every width. */
      var target = sitebar ? sitebar
                 : (wide.matches && navLinks) ? navLinks
                 : footer;
      if (!target || box.parentNode === target) return;
      if (target === sitebar) {
        box.className = 'themebox themebox-bar';
        sitebar.appendChild(box);
        return;
      }
      if (target === navLinks) {

        var cta = navLinks.querySelector('.cta');
        if (cta) navLinks.insertBefore(box, cta);
        else navLinks.appendChild(box);
      } else {
        target.appendChild(box);
      }

      box.className = 'themebox' + (target === navLinks ? ' themebox-nav' : '');
    }
    mount();


    if (wide.addEventListener) wide.addEventListener('change', mount);
    else if (wide.addListener) wide.addListener(mount);
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', build);
  else
    build();
})();
