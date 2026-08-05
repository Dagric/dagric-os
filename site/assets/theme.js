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

    /* THE GUIDE NOW HOSTS THE SWITCH TOO, and the comment that used to sit
       here explained exactly why it did not: .themetog is styled in site.css
       and the guide loads guide.css, so the button would have rendered
       unstyled. It named its own prerequisite — "if the guide is ever given
       the control, it needs .themebox/.themetog in guide.css first" — and
       publish-guide.py now appends them to the published copy.
       Leaving it out stopped making sense the moment the site gained a light
       mode. A reader in light mode clicked Guide, got a guide that correctly
       followed their choice, and then had no way to change it without going
       back to a different page. apply() has always run above, so the theme
       was never the problem; the missing control was.
       The guide's own header bar is the mount — it is the component
       publish-guide.py injects for exactly this kind of site-level control,
       and it is at the top of the page rather than the end of an 11,000px
       document. The OFFLINE copy has no site bar, so it gets no switch, which
       is right: it follows the desktop's own light/dark setting through
       prefers-color-scheme and has no second preference to store. */
    var sitebar = document.querySelector('.sitebar .sitebar-in');
    var foot = document.querySelector('footer .foot');
    if (!foot && !sitebar) return;
    var footer = foot ? foot.parentNode : null;
    /* Guard on the DOCUMENT, not on one container. The old form was
       `if (!footer || footer.querySelector('.themetog')) return;`, which does
       two jobs badly once there is more than one possible mount: on the guide
       `footer` is null, so it returned before building anything, and even on
       the site it only ever checked the footer — so once the nav became a
       mount, a second run could have inserted a duplicate the check could not
       see. One control per page is the actual rule; this is the actual test. */
    if (document.querySelector('.themetog')) return;

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

    /* WHERE THIS LIVES, AND WHY IT MOVED.
       It was appended to <footer> and nowhere else, for a defensible reason:
       --nav-h and the 487/615 breakpoints come from a scrollbar-inclusive 1px
       sweep across 320-1300px, and the bar already wraps to three rows at
       118px on a phone, so adding an item risked a fourth row and every
       in-page anchor landing under the bar.
       The result was a control nobody could find. The owner scrolled the live
       site and reported not seeing it at all — and he is right: /faq is
       2,544px, the homepage 16,000px, and nobody scrolls to the bottom of a
       page looking for a theme switch. An undiscoverable control is not a
       safer control, it is an absent one.
       So it mounts in the NAV at >=641px, where the bar is a single row with
       the links right-aligned and horizontal room to spare, and stays in the
       FOOTER below that, where the measured three-row plateau is left exactly
       as it was. Nothing about the phone layout changes; nothing about the
       desktop measurements depends on a sweep, because one row does not wrap.
       ONE button, MOVED between two mounts rather than duplicated. Two copies
       hidden by CSS would put a second control in the accessibility tree and
       give a screen-reader user two switches for one setting. matchMedia's
       change event re-mounts it when the window crosses the breakpoint, so a
       reader who resizes does not lose it. */
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
        /* BEFORE the Download pill, not after it. .nav-links is a flex row
           pushed right by margin-left:auto, so appending would seat the
           toggle to the RIGHT of the one control on this bar that is supposed
           to be the last thing your eye reaches. The filled CTA stays the end
           of the row; the toggle joins the quiet links to its left. */
        var cta = navLinks.querySelector('.cta');
        if (cta) navLinks.insertBefore(box, cta);
        else navLinks.appendChild(box);
      } else {
        target.appendChild(box);
      }
      /* The nav copy sits inline with the links; the footer copy is its own
         row. One class, so site.css can style each context without this file
         knowing anything about layout. */
      box.className = 'themebox' + (target === navLinks ? ' themebox-nav' : '');
    }
    mount();

    /* addEventListener on the query, with the legacy addListener fallback —
       Safari did not support the modern form until 14 and this site is aimed
       at people running whatever their old machine came with. */
    if (wide.addEventListener) wide.addEventListener('change', mount);
    else if (wide.addListener) wide.addListener(mount);
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', build);
  else
    build();
})();
