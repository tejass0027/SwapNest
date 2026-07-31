/* Ledger — global behaviour. Vanilla, progressive enhancement.
   Everything here is optional polish; the site works without it. */
(function () {
    "use strict";

    // Mobile nav toggle
    var toggle = document.querySelector(".nav-toggle");
    var links = document.querySelector(".nav-links");
    if (toggle && links) {
        toggle.addEventListener("click", function () {
            var open = links.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });
    }

    // Theme toggle: dark (default) <-> bright (previous UI).
    // Initial theme is set pre-paint by an inline script in base.html.
    function applyTheme(t) {
        document.documentElement.setAttribute("data-theme", t);
        document.documentElement.style.colorScheme = t;
        var dark = document.querySelectorAll('link[data-theme-css="dark"]');
        var light = document.querySelectorAll('link[data-theme-css="light"]');
        for (var i = 0; i < dark.length; i++) { dark[i].media = (t === "dark") ? "all" : "not all"; }
        for (var j = 0; j < light.length; j++) { light[j].media = (t === "light") ? "all" : "not all"; }
    }

    var themeToggle = document.querySelector(".theme-toggle");
    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            var cur = document.documentElement.getAttribute("data-theme") || "dark";
            var next = cur === "dark" ? "light" : "dark";
            applyTheme(next);
            try { localStorage.setItem("ledger-theme", next); } catch (e) {}
        });
    }
})();
