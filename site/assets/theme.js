/* Dagric OS — the light/dark control.
   ─────────────────────────────────────────────────────────────────────────
   WHY THIS IS A FILE AND NOT AN INLINE SCRIPT: the site ships a strict CSP,
   script-src 'self'. There is no inline-script escape hatch here and there is
   not going to be one, so the no-flash trick that every theme-toggle article
   reaches for — a blocking inline script in <head> — is unavailable. This is
   the same-origin equivalent: ~1 KB, referenced with a normal src, and
   deliberately NOT deferred so it runs before first paint.

   WHY DARK IS STILL THE DEFAULT: prefers-color-scheme is not consulted, on
   purpose. Windows defaults to light and this site is written for people
   leaving Windows 10, so honouring the system preference would flip the front
   door for most visitors who never asked for it. Nothing changes for anybody
   until they press the button in the footer. That also means the failure mode
   with JavaScript off is the site exactly as it shipped: :root is dark, this
   file never runs, no attribute is ever stamped, and the button is never
   inserted — so a reader without JavaScript sees a working site rather than a
   dead control. That is why the button is BUILT here rather than sitting in
   the markup of seventeen pages.

   localStorage throws rather than returning null on some hardened and
   private-mode configurations, and it throws on file:// in more than one
   browser. Every access is wrapped: the toggle then still works for the life
   of the page and simply does not persist, which is a better outcome than a
   button that does nothing because the whole handler died on read. */
(function () {
  'use strict';

  var KEY  = 'dagric-theme';
  var root = document.documentElement;

  function read()   { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(v) { try { localStorage.setItem(KEY, v); }    catch (e) {} }

  /* The browser-chrome colour is READ BACK OFF THE PAGE rather than held as a
     constant here, and that is not cleverness for its own sake — this file is
     loaded by two documents with two different palettes. The marketing pages
     are #0C0F14 dark; /guide is #0a111c dark and #f3f6fa light, because the
     guide ships inside the OS with its own tokens. A hardcoded pair here would
     tint the phone's address bar a colour that appears nowhere on the guide.
     Taking the computed background of <body> makes it right on both by
     construction, and right again if either palette is ever re-struck.
     A media-scoped <meta> pair was the other option and it is wrong for a
     different reason: it follows the SYSTEM, so it would disagree with the
     page for exactly the visitors who used the button. site.webmanifest cannot
     express two values at all and stays dark. */
  function paintMeta() {
    var m = document.querySelector('meta[name="theme-color"]');
    if (!m || !document.body) return;
    var bg = getComputedStyle(document.body).backgroundColor;
    if (bg && bg !== 'transparent' && bg.indexOf('rgba(0, 0, 0, 0)') === -1)
      m.setAttribute('content', bg);
  }

  function apply(theme) {
    /* Transitions OFF across the swap — see the .theme-swap block in site.css.
       Without this, .btn and .themetog start a colour transition whose endpoint
       the engine never re-resolves when the value comes from a custom property
       that changed, and they keep the PREVIOUS theme's text colour: a measured
       1.03:1 on a ghost button, indefinitely. The reflow between add and remove
       is required — without it the two class changes coalesce into one style
       recalculation and the suppression never takes effect. */
    root.classList.add('theme-swap');

    /* Dark is the ABSENCE of the attribute, not data-theme="dark". That keeps
       the dark theme rendering off the untouched :root block, so it stays
       byte-identical to what shipped instead of depending on this file. */
    if (theme === 'light') root.setAttribute('data-theme', 'light');
    else                   root.removeAttribute('data-theme');

    void root.offsetWidth;
    if (window.requestAnimationFrame)
      requestAnimationFrame(function () { root.classList.remove('theme-swap'); });
    else
      root.classList.remove('theme-swap');

    paintMeta();
  }

  /* Runs at parse time, in <head>, before <body> exists — so this call stamps
     the attribute (which is all that matters for avoiding a flash) and
     paintMeta() no-ops until build() calls apply() again with a body present. */
  var current = read() === 'light' ? 'light' : 'dark';
  apply(current);

  function build() {
    paintMeta();   /* <body> exists now, so the chrome colour can be read */

    /* `footer .foot`, NOT `footer`. That selector is the site's own footer
       component, and it is the gate that keeps this control off /guide: the
       guide has a <footer class="colophon"> but loads guide.css, not site.css,
       so a button styled by .themetog would render there completely unstyled.
       The guide still gets the THEME — apply() ran above — it just does not
       host the switch, which is consistent with it being a document rather
       than a page of the site, and it carries a "← dagric.com" link back to
       where the control lives. If the guide is ever given the control, it
       needs .themebox/.themetog in guide.css first. */
    var foot = document.querySelector('footer .foot');
    if (!foot) return;
    var footer = foot.parentNode;
    if (!footer || footer.querySelector('.themetog')) return;

    var box = document.createElement('div');
    box.className = 'themebox';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'themetog';

    /* The label names the ACTION, not the current state — "Dark page" on a
       light page is ambiguous about which one you are about to get, and this
       audience should not have to guess. The visible text is a substring of
       the accessible name, which is what WCAG 2.5.3 Label in Name asks for. */
    function label() {
      var next = current === 'light' ? 'dark' : 'light';
      btn.textContent = next === 'light' ? 'Light page' : 'Dark page';
      btn.setAttribute('aria-label', 'Switch to the ' + next + ' page');
    }
    label();

    btn.addEventListener('click', function () {
      current = (current === 'light') ? 'dark' : 'light';
      apply(current);
      write(current);
      label();
    });

    box.appendChild(btn);
    /* Appended to <footer> as its own row rather than into .foot. .foot's
       phone layout is a measured three-row plateau with 44px targets; adding a
       third flex item to it would re-wrap that and invalidate the measurement
       the comment on .foot .links records. The nav is out of the question for
       the same reason, one step worse: --nav-h and the 487/615 breakpoints
       come from a scrollbar-inclusive 1px sweep from 320-1300px, and the bar
       already wraps to three rows at 118px on a phone. */
    footer.appendChild(box);
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', build);
  else
    build();
})();
