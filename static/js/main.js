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

    // ── Motion helpers ─────────────────────────────────────────
    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var finePointer = window.matchMedia("(pointer: fine)").matches;
    function isDark() { return document.documentElement.getAttribute("data-theme") === "dark"; }
    var supportsIO = "IntersectionObserver" in window;

    // ── Reveal on scroll (fade + rise, staggered) ──────────────
    // Stagger children of any [data-reveal-group] by their index.
    var groups = document.querySelectorAll("[data-reveal-group]");
    for (var g = 0; g < groups.length; g++) {
        var kids = groups[g].children;
        for (var k = 0; k < kids.length; k++) {
            if (kids[k].classList.contains("reveal")) {
                kids[k].style.setProperty("--rd", (k % 12) * 65 + "ms");
            }
        }
    }

    var reveals = document.querySelectorAll(".reveal");

    function settle(el) {
        // After the entrance finishes, drop the animation so the element's
        // own hover transitions (transform, shadow) are free again.
        el.classList.add("revealed");
        el.classList.remove("reveal", "is-visible");
    }

    if (reveals.length) {
        if (!supportsIO || reduceMotion) {
            // No observer or reduced motion: just show everything.
            for (var r = 0; r < reveals.length; r++) { settle(reveals[r]); }
        } else {
            var revealIO = new IntersectionObserver(function (entries, obs) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;
                    var el = entry.target;
                    obs.unobserve(el);
                    el.classList.add("is-visible");
                    el.addEventListener("animationend", function onEnd() {
                        el.removeEventListener("animationend", onEnd);
                        settle(el);
                    });
                });
            }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
            for (var s = 0; s < reveals.length; s++) { revealIO.observe(reveals[s]); }
        }
    }

    // ── Headline word reveal ───────────────────────────────────
    var title = document.querySelector(".hero-title[data-splitwords]");
    if (title) {
        if (!isDark() || reduceMotion) {
            title.classList.add("is-visible"); // static, fully visible
        } else {
            var words = title.textContent.trim().split(/\s+/);
            title.textContent = "";
            for (var w = 0; w < words.length; w++) {
                var word = document.createElement("span");
                word.className = "word";
                var inner = document.createElement("span");
                inner.className = "word-i";
                inner.textContent = words[w];
                inner.style.setProperty("--wd", w * 60 + "ms");
                word.appendChild(inner);
                title.appendChild(word);
                if (w < words.length - 1) { title.appendChild(document.createTextNode(" ")); }
            }
            title.classList.add("is-visible");
        }
    }

    // ── Hero parallax + pointer drift (dark, fine pointer only) ─
    var heroFx = document.querySelector(".hero [data-parallax]");
    if (heroFx && !reduceMotion && finePointer && window.innerWidth > 640) {
        var factor = parseFloat(heroFx.getAttribute("data-parallax")) || 0.12;
        var hero = heroFx.closest(".hero");
        var scrollY = 0, mx = 0, my = 0, ticking = false;

        function renderFx() {
            ticking = false;
            if (!isDark()) { heroFx.style.transform = ""; return; }
            heroFx.style.transform =
                "translate3d(" + mx + "px," + (scrollY * factor + my) + "px,0)";
        }
        function requestFx() {
            if (!ticking) { ticking = true; requestAnimationFrame(renderFx); }
        }
        window.addEventListener("scroll", function () {
            scrollY = window.pageYOffset || 0;
            requestFx();
        }, { passive: true });
        if (hero) {
            hero.addEventListener("pointermove", function (e) {
                var rect = hero.getBoundingClientRect();
                mx = ((e.clientX - rect.left) / rect.width - 0.5) * 18;
                my = ((e.clientY - rect.top) / rect.height - 0.5) * 12;
                requestFx();
            });
            hero.addEventListener("pointerleave", function () {
                mx = 0; my = 0; requestFx();
            });
        }
    }

    // ── Animated counters ──────────────────────────────────────
    var counters = document.querySelectorAll("[data-count]");
    function runCount(el) {
        var target = parseFloat(el.getAttribute("data-count")) || 0;
        var prefix = el.getAttribute("data-count-prefix") || "";
        var suffix = el.getAttribute("data-count-suffix") || "";
        if (reduceMotion) { el.textContent = prefix + target.toLocaleString() + suffix; return; }
        var start = null, dur = 1400;
        function step(ts) {
            if (start === null) start = ts;
            var p = Math.min((ts - start) / dur, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = prefix + Math.round(target * eased).toLocaleString() + suffix;
            if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }
    if (counters.length && supportsIO) {
        var countIO = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                obs.unobserve(entry.target);
                runCount(entry.target);
            });
        }, { threshold: 0.4 });
        for (var c = 0; c < counters.length; c++) { countIO.observe(counters[c]); }
    } else {
        for (var c2 = 0; c2 < counters.length; c2++) { runCount(counters[c2]); }
    }
})();
