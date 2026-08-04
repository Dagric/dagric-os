/* Dagric OS — section index for the long document pages.
   ─────────────────────────────────────────────────────────────────────────
   WHY THIS EXISTS. Measured at 1920x1080, the eleven document pages are all
   the same shape: 772px of content in a 1920px window (0.402), 574px of empty
   gutter on each side — and because site.css rags the prose left inside that
   column, the TEXT is narrower still: 544px on /faq, 566px on /privacy, with
   780-802px of nothing to the right of it. That is the single largest area of
   dead space on the site, and it is specifically a large-monitor problem: the
   same pages measure 0.536 at 1440px and 0.603 at 1280px.
   The measure itself is NOT the thing to change — site.css derives 34rem from
   a real character count over real copy and explains at length why. What is
   worth changing is that the gutter carries nothing on the pages a school or a
   procurement officer reads end to end: /accessibility is 5,615px tall,
   /privacy 3,364px, /faq 2,544px, /licenses 2,520px, /terms 2,353px.

   WHY A SCRIPT AND NOT MARKUP. Every entry is a heading that is already on the
   page. Hand-written markup would copy 4-7 frozen strings per page into a
   second place and wait to drift — on a site whose entire claim is that its
   copy was checked. This reads the headings that are there, so the index
   cannot disagree with the page.

   WHAT IT COSTS WHEN IT IS NOT THERE. Nothing. The nav is display:none until
   min-width:1440px and absolutely positioned above it, so it never takes part
   in layout at any width; with JavaScript off the page is byte-for-byte what
   it is today. CSP is script-src 'self' and this is a same-origin file with no
   dependencies, exactly like assets/contact.js.

   THE ids IT ASSIGNS ARE PART OF THE DELIVERABLE, not a side effect: they give
   every section on these pages a linkable address, which is what somebody
   quoting a clause of /terms or a row of the ACR in a support thread needs. */
(function () {
  "use strict";

  var main = document.querySelector("main:not(.wide)");
  if (!main) return;

  var heads = [];
  for (var i = 0; i < main.children.length; i++) {
    if (main.children[i].tagName === "H2") heads.push(main.children[i]);
  }
  /* Three is the floor on purpose. An index of two entries is not navigation,
     it is a restatement of the page, and it would put a rail down the side of
     a page nobody needs help finding their way around. */
  if (heads.length < 3) return;

  /* Slugified from the heading's own text, so the URL a reader copies out of
     the address bar says what it points at. Existing ids win — /accessibility
     already carries four of them and they are what its in-page links use. */
  function slug(s) {
    return s.toLowerCase()
            .replace(/[‘’“”']/g, "")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "")
            .slice(0, 40) || "section";
  }

  var nav = document.createElement("nav");
  nav.className = "pageindex";
  /* A second navigation landmark on the page, so it needs a name that tells a
     screen-reader user which one it is — the site nav is already "navigation".
     aria-label rather than a heading: a heading here would insert an h2 (or
     worse, an h3) into an outline this site guarantees has no level skips. */
  nav.setAttribute("aria-label", "On this page");

  var list = document.createElement("ol");

  for (var j = 0; j < heads.length; j++) {
    var h = heads[j];
    var id = h.id;
    if (!id) {
      id = slug(h.textContent);
      /* Two headings can slugify to the same string — "Other" appears on more
         than one page and nothing stops it appearing twice on one. A duplicate
         id makes the second link point at the first section, silently. */
      var n = 2, base = id;
      while (document.getElementById(id)) { id = base + "-" + n; n++; }
      h.id = id;
    }
    var li = document.createElement("li");
    var a = document.createElement("a");
    a.href = "#" + id;
    a.textContent = h.textContent.trim();
    li.appendChild(a);
    list.appendChild(li);
  }

  nav.appendChild(list);
  /* Immediately before the first h2 — where a table of contents goes in a
     printed document, and after the h1 and the standfirst so the page still
     opens on what it is about. DOM order matters here even though the nav is
     positioned: focus order follows the DOM, and a control that reads first
     but tabs last is WCAG 2.4.3. */
  main.insertBefore(nav, heads[0]);
  main.className += (main.className ? " " : "") + "has-pageindex";
})();
