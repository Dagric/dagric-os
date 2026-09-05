
(function () {
  "use strict";

  var main = document.querySelector("main:not(.wide)");
  if (!main) return;

  var heads = [];
  for (var i = 0; i < main.children.length; i++) {
    if (main.children[i].tagName === "H2") heads.push(main.children[i]);
  }

  if (heads.length < 3) return;


  function slug(s) {
    return s.toLowerCase()
            .replace(/[‘’“”']/g, "")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "")
            .slice(0, 40) || "section";
  }

  var nav = document.createElement("nav");
  nav.className = "pageindex";

  nav.setAttribute("aria-label", "On this page");

  var list = document.createElement("ol");

  for (var j = 0; j < heads.length; j++) {
    var h = heads[j];
    var id = h.id;
    if (!id) {
      id = slug(h.textContent);

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

  main.insertBefore(nav, heads[0]);
  main.className += (main.className ? " " : "") + "has-pageindex";
})();
