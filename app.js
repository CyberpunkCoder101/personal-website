/* ============================================================================
 *  app.js — renders the site from data.js and powers the interactions.
 *  You normally don't need to edit this. All content lives in data.js
 *  (edit it with website_editor.py or by hand).
 * ==========================================================================*/

(function () {
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const filled = (s) => s && typeof s === "string" && s.trim() !== "" && !s.startsWith("TODO");
  // escape user text so <, > & don't break markup
  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  // escape + turn newlines into paragraph breaks
  const multiline = (s) => esc(s).trim().replace(/\r?\n\s*\r?\n/g, "<br><br>").replace(/\r?\n/g, "<br>");

  /* map a link "icon" slug (or emoji) to an emoji glyph */
  const ICONS = {
    linkedin: "in", github: "GH", email: "✉", mail: "✉", scholar: "🎓",
    twitter: "𝕏", x: "𝕏", website: "🌐", globe: "🌐", youtube: "▶",
    instagram: "◈", medium: "✍", dribbble: "◐", behance: "Bē",
  };
  const iconGlyph = (icon) => {
    if (!icon) return "🔗";
    const k = icon.toLowerCase();
    if (ICONS[k]) return ICONS[k];
    return icon; // already an emoji / custom glyph
  };

  /* ---------- FEATURE HELPERS ---------- */
  let _toastT;
  function toast(msg) {
    const tEl = $("toast"); if (!tEl) return;
    tEl.textContent = msg; tEl.classList.add("show");
    clearTimeout(_toastT); _toastT = setTimeout(() => tEl.classList.remove("show"), 2200);
  }

  function openLightbox(src) {
    const lb = $("lightbox"); if (!lb) return;
    $("lightboxImg").src = src; lb.classList.add("open"); lb.setAttribute("aria-hidden", "false");
  }
  function closeLightbox() {
    const lb = $("lightbox"); if (!lb) return;
    lb.classList.remove("open"); lb.setAttribute("aria-hidden", "true"); $("lightboxImg").src = "";
  }

  // animate a number string ("98.1%", "~22 ms", "5+", "2016") from 0 to its value
  const reduceMotion = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  function countUp(node, str) {
    const m = String(str).match(/^(\D*)([\d.]+)(.*)$/);
    node.textContent = str;                 // correct value first (safe default)
    if (!m || reduceMotion) return;
    const pre = m[1], target = parseFloat(m[2]), suf = m[3];
    const decimals = (m[2].split(".")[1] || "").length;
    const dur = 1100, t0 = performance.now();
    let done = false;
    const finish = () => { if (!done) { done = true; node.textContent = pre + m[2] + suf; } };
    (function step(now) {
      const k = Math.min(1, (now - t0) / dur);
      node.textContent = pre + (target * (1 - Math.pow(1 - k, 3))).toFixed(decimals) + suf;
      if (k < 1) requestAnimationFrame(step); else finish();
    })(t0);
    setTimeout(finish, dur + 400);          // guarantee final value even if rAF is throttled
  }

  /* ---------- META ---------- */
  const meta = SITE.meta || {};
  if (filled(meta.siteTitle)) document.title = meta.siteTitle;
  if (filled(meta.description)) {
    let m = document.querySelector('meta[name="description"]');
    if (m) m.setAttribute("content", meta.description);
  }
  if (filled(meta.favicon)) {
    const link = document.querySelector("link[rel='icon']") || el("link");
    link.rel = "icon";
    link.href = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>" +
      encodeURIComponent(meta.favicon) + "</text></svg>";
    document.head.appendChild(link);
  }
  // Open Graph / Twitter tags so shared links get a rich preview
  const ogTitle = filled(meta.siteTitle) ? meta.siteTitle : (SITE.profile && SITE.profile.name) || "";
  const ogDesc = filled(meta.description) ? meta.description : (SITE.profile && SITE.profile.tagline) || "";
  const ogImg = SITE.profile && filled(SITE.profile.avatar) ? SITE.profile.avatar : "";
  const setMeta = (attr, key, val) => {
    if (!val) return;
    let m = document.querySelector(`meta[${attr}="${key}"]`);
    if (!m) { m = document.createElement("meta"); m.setAttribute(attr, key); document.head.appendChild(m); }
    m.setAttribute("content", val);
  };
  setMeta("property", "og:title", ogTitle);
  setMeta("property", "og:description", ogDesc);
  setMeta("property", "og:type", "website");
  setMeta("property", "og:image", ogImg);
  setMeta("name", "twitter:card", ogImg ? "summary_large_image" : "summary");
  setMeta("name", "twitter:title", ogTitle);
  setMeta("name", "twitter:description", ogDesc);

  /* ---------- THEME ---------- */
  const root = document.documentElement;
  const t = SITE.theme || {};
  const savedMode = localStorage.getItem("mode");
  const savedAccent = localStorage.getItem("accent");

  function applyAccent(hex, soft) {
    root.style.setProperty("--accent", hex);
    root.style.setProperty("--accent-soft", soft || hex);
  }
  if (t.radius) root.style.setProperty("--radius", t.radius);
  if (t.font) root.style.setProperty("--font", t.font);
  if (t.headingFont) root.style.setProperty("--font-head", t.headingFont);
  applyAccent(savedAccent || t.accent || "#6366f1",
              savedAccent ? shade(savedAccent, 30) : (t.accentSoft || "#818cf8"));
  root.setAttribute("data-mode", savedMode || t.defaultMode || "dark");

  function shade(hex, pct) {
    const n = parseInt(hex.slice(1), 16);
    let r = (n >> 16) + Math.round(2.55 * pct);
    let g = ((n >> 8) & 255) + Math.round(2.55 * pct);
    let b = (n & 255) + Math.round(2.55 * pct);
    r = Math.min(255, r); g = Math.min(255, g); b = Math.min(255, b);
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  /* ---------- THEME PICKER UI ---------- */
  if (t.showThemePicker !== false) {
    const palette = ["#6366f1", "#10b981", "#f43f5e", "#f59e0b", "#06b6d4", "#a855f7"];
    const wrap = $("themeControls");
    const swatches = el("div", "swatches");
    palette.forEach((c) => {
      const s = el("button", "swatch");
      s.style.background = c; s.title = "Accent color";
      if ((savedAccent || t.accent || "").toLowerCase() === c) s.classList.add("active");
      s.onclick = () => {
        applyAccent(c, shade(c, 30));
        localStorage.setItem("accent", c);
        document.querySelectorAll(".swatch").forEach((x) => x.classList.remove("active"));
        s.classList.add("active");
      };
      swatches.appendChild(s);
    });
    const toggle = el("button", "mode-toggle", root.getAttribute("data-mode") === "dark" ? "☀️" : "🌙");
    toggle.title = "Toggle light / dark";
    toggle.onclick = () => {
      root.classList.add("theme-anim");
      setTimeout(() => root.classList.remove("theme-anim"), 480);
      const next = root.getAttribute("data-mode") === "dark" ? "light" : "dark";
      root.setAttribute("data-mode", next);
      localStorage.setItem("mode", next);
      toggle.textContent = next === "dark" ? "☀️" : "🌙";
    };
    wrap.append(swatches, toggle);
  }

  /* ---------- PROFILE / HERO ---------- */
  const p = SITE.profile || {};
  const initials = (p.name || "AP").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  $("navBrand").textContent = initials;
  $("footerText").textContent = "© " + new Date().getFullYear() + " " + (SITE.footer || p.name || "");

  const av = $("heroAvatar");
  if (filled(p.avatar)) { av.style.backgroundImage = `url('${p.avatar}')`; av.textContent = ""; }
  else av.textContent = initials;

  if (filled(meta.heroBackground)) {
    $("heroBg").style.backgroundImage =
      `linear-gradient(color-mix(in srgb, var(--bg) 55%, transparent), var(--bg)), url('${meta.heroBackground}')`;
    $("heroBg").style.backgroundSize = "cover";
    $("heroBg").style.backgroundPosition = "center";
  }

  $("heroName").textContent = p.name || "";
  $("heroTagline").textContent = p.tagline || "";
  $("aboutName").textContent = (p.name || "").split(" ")[0];
  $("aboutText").textContent = p.tagline || "";
  if (filled(p.location)) $("heroLocation").textContent = p.location;

  // hero social buttons (featured links)
  const social = $("heroSocial");
  (SITE.links || []).forEach((l) => {
    if (!l.featured || !filled(l.url)) return;
    const a = el("a", "social-btn", `<span>${iconGlyph(l.icon)}</span>${l.label}`);
    a.href = l.url; a.target = l.url.startsWith("mailto") ? "" : "_blank"; a.title = l.label;
    social.appendChild(a);
  });

  // CTA buttons
  const cta = $("heroCta");
  const primary = el("a", "btn btn--primary", "Get in touch"); primary.href = "#contact";
  cta.appendChild(primary);
  if (filled(p.resumeUrl)) {
    const r = el("a", "btn btn--ghost", "⬇ Resume"); r.href = p.resumeUrl; r.target = "_blank";
    cta.appendChild(r);
  }
  const workBtn = el("a", "btn btn--ghost", "See my work"); workBtn.href = "#work";
  cta.appendChild(workBtn);

  // stats (with optional emoji icon + count-up animation)
  const hs = $("heroStats");
  (p.stats || []).forEach((s, i) => {
    const ico = filled(s.icon) ? `<div class="stat__icon">${s.icon}</div>` : "";
    const node = el("div", "stat", `${ico}<div class="stat__value"></div><div class="stat__label">${s.label}</div>`);
    hs.appendChild(node);
    const valEl = node.querySelector(".stat__value");
    valEl.textContent = s.value;
    setTimeout(() => countUp(valEl, s.value), 250 + i * 120);
  });

  // typewriter roles
  const roles = p.roles || [];
  if (roles.length) {
    const target = $("roleText");
    let ri = 0, ci = 0, deleting = false;
    (function type() {
      const cur = roles[ri];
      target.textContent = deleting ? cur.slice(0, ci--) : cur.slice(0, ci++);
      if (!deleting && ci > cur.length) { deleting = true; setTimeout(type, 1600); return; }
      if (deleting && ci < 0) { deleting = false; ri = (ri + 1) % roles.length; ci = 0; }
      setTimeout(type, deleting ? 40 : 75);
    })();
  }

  /* ---------- TIMELINE ---------- */
  const tl = $("timeline");
  (SITE.timeline || []).forEach((it) => {
    const node = el("div", "tl-item reveal");
    node.innerHTML =
      `<span class="tl-year">${it.year}</span>` +
      `<span class="tl-tag" data-t="${it.type || ""}">${it.type || ""}</span>` +
      `<div class="tl-title">${esc(it.title)}</div>` +
      (filled(it.org) ? `<div class="tl-org">${esc(it.org)}</div>` : "") +
      (filled(it.text) ? `<div class="tl-text">${multiline(it.text)}</div>` : "") +
      (filled(it.image) ? `<div class="tl-img"><img src="${it.image}" alt="${it.title || ""}" loading="lazy"></div>` : "");
    tl.appendChild(node);
  });

  /* ---------- EXPERIENCE ---------- */
  const exp = $("experience-list");
  (SITE.experience || []).forEach((e) => {
    const card = el("div", "exp-item reveal");
    const bullets = (e.bullets || []).filter(filled)
      .map((b) => `<li>${esc(b)}</li>`).join("");
    const period = [e.start, e.end].filter(Boolean).join(" – ");
    const company = filled(e.url) ? `<a href="${e.url}" target="_blank">${esc(e.company)}</a>` : esc(e.company);
    card.innerHTML =
      `<div class="exp-item__period">${esc(period)}</div>` +
      `<div class="exp-item__body">` +
        `<div class="exp-item__role">${esc(e.role)}</div>` +
        `<div class="exp-item__co">${company}${filled(e.location) ? ` · <span>${esc(e.location)}</span>` : ""}</div>` +
        (bullets ? `<ul class="exp-item__list">${bullets}</ul>` : "") +
      `</div>`;
    exp.appendChild(card);
  });

  /* ---------- PROJECTS ---------- */
  const pc = $("projects");
  (SITE.projects || []).forEach((pr) => {
    const card = el("div", "pcard reveal" + (pr.highlight ? " wide" : ""));
    card.dataset.tags = (pr.tags || []).join("|");
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty("--mx", (e.clientX - r.left) + "px");
      card.style.setProperty("--my", (e.clientY - r.top) + "px");
    });
    let html = `<div class="pcard__glow"></div>`;
    if (filled(pr.image)) {
      html += `<div class="pcard__img"><img src="${pr.image}" alt="${pr.title}" loading="lazy"></div>`;
    }
    html += `<div class="pcard__period">${pr.period || ""}</div>`;
    html += `<div class="pcard__title">${pr.title}</div>`;
    html += `<div class="pcard__blurb">${multiline(pr.blurb)}</div>`;
    if (pr.metrics && pr.metrics.length) {
      html += `<div class="pcard__metrics">` +
        pr.metrics.map((m) => `<div class="metric"><div class="metric__v">${m.value}</div><div class="metric__l">${m.label}</div></div>`).join("") +
        `</div>`;
    }
    if (pr.tags && pr.tags.length) {
      html += `<div class="pcard__tags">` + pr.tags.map((x) => `<span class="chip">${x}</span>`).join("") + `</div>`;
    }
    if (filled(pr.link)) html += `<a class="pcard__link" href="${pr.link}" target="_blank">View project</a>`;
    card.innerHTML = html;
    pc.appendChild(card);
  });

  /* ---------- PROJECT TAG FILTER ---------- */
  const fbar = $("projectFilters");
  const tagCount = {};
  (SITE.projects || []).forEach((pr) => (pr.tags || []).forEach((t) => {
    tagCount[t] = (tagCount[t] || 0) + 1;
  }));
  // keep tags shared by 2+ projects; if none, fall back to all tags (capped)
  let allTags = Object.keys(tagCount).filter((t) => tagCount[t] >= 2)
    .sort((a, b) => tagCount[b] - tagCount[a]);
  if (allTags.length < 2) allTags = Object.keys(tagCount).slice(0, 8);
  if (fbar && allTags.length > 1) {
    const chips = ["All", ...allTags];
    chips.forEach((tag, i) => {
      const chip = el("button", "filter-chip" + (i === 0 ? " active" : ""), tag);
      chip.onclick = () => {
        fbar.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        document.querySelectorAll("#projects .pcard").forEach((card) => {
          const tags = (card.dataset.tags || "").split("|");
          card.classList.toggle("hidden", tag !== "All" && !tags.includes(tag));
        });
      };
      fbar.appendChild(chip);
    });
  }

  /* ---------- PUBLICATIONS ---------- */
  const pubs = $("pubs");
  (SITE.publications || []).forEach((pb) => {
    const item = el("div", "pub reveal");
    const links = [];
    if (filled(pb.paper)) links.push(`<a href="${pb.paper}" target="_blank">📄 Paper</a>`);
    if (filled(pb.code)) links.push(`<a href="${pb.code}" target="_blank">💻 Code</a>`);
    item.innerHTML =
      `<div class="pub__year">${pb.year || ""}</div>` +
      `<div class="pub__body">` +
        `<div class="pub__title">${esc(pb.title)}</div>` +
        (filled(pb.authors) ? `<div class="pub__authors">${esc(pb.authors)}</div>` : "") +
        (filled(pb.venue) ? `<div class="pub__venue">${esc(pb.venue)}</div>` : "") +
        (filled(pb.abstract) ? `<div class="pub__abstract">${multiline(pb.abstract)}</div>` : "") +
        (links.length ? `<div class="pub__links">${links.join("")}</div>` : "") +
      `</div>`;
    pubs.appendChild(item);
  });

  /* ---------- SKILLS ---------- */
  const sg = $("skillsGrid");
  (SITE.skills || []).forEach((grp) => {
    const g = el("div", "skillgroup reveal");
    g.innerHTML = `<h3>${grp.group}</h3>` + (grp.items || []).map((s) => `<span class="chip">${s}</span>`).join("");
    sg.appendChild(g);
  });

  /* ---------- AWARDS ---------- */
  const aw = $("awards-list");
  (SITE.awards || []).forEach((a) => {
    const card = el("div", "award reveal");
    const title = filled(a.url)
      ? `<a href="${a.url}" target="_blank">${esc(a.title)}</a>` : esc(a.title);
    const head = filled(a.image)
      ? `<div class="award__logo"><img src="${a.image}" alt="${esc(a.title)}" loading="lazy"></div>`
      : `<div class="award__medal">🏅</div>`;
    card.innerHTML =
      head +
      `<div class="award__title">${title}</div>` +
      `<div class="award__meta">${[a.issuer, a.year].filter(filled).map(esc).join(" · ")}</div>`;
    aw.appendChild(card);
  });

  /* ---------- CONTACT ---------- */
  const c = SITE.contact || {};
  $("contactHeading").textContent = c.heading || "Get in touch.";
  $("contactText").textContent = c.text || "";
  const contactBtn = $("contactBtn");
  contactBtn.href = "mailto:" + (c.email || "");
  if (filled(c.email)) {
    const actions = el("div", "contact__actions");
    contactBtn.parentNode.insertBefore(actions, contactBtn);
    actions.appendChild(contactBtn);
    const copyBtn = el("button", "btn btn--ghost", "⧉ Copy email");
    copyBtn.onclick = () => {
      navigator.clipboard?.writeText(c.email).then(() => toast("Email copied to clipboard ✓"))
        .catch(() => toast(c.email));
    };
    actions.appendChild(copyBtn);
  }
  const cl = $("contactLinks");
  (SITE.links || []).forEach((l) => {
    if (!filled(l.url)) return;
    const a = el("a", null, `${iconGlyph(l.icon)}&nbsp; ${l.label}`);
    a.href = l.url; a.target = l.url.startsWith("mailto") ? "" : "_blank";
    cl.appendChild(a);
  });

  /* ---------- HIDE EMPTY SECTIONS + AUTO-NUMBER ---------- */
  const sectionHasContent = {
    about: filled(p.tagline),
    journey: (SITE.timeline || []).length,
    experience: (SITE.experience || []).length,
    work: (SITE.projects || []).length,
    publications: (SITE.publications || []).length,
    skills: (SITE.skills || []).length,
    awards: (SITE.awards || []).length,
    contact: true,
  };
  let num = 0;
  document.querySelectorAll("section[data-section]").forEach((sec) => {
    if (!sectionHasContent[sec.id]) { sec.style.display = "none"; return; }
    num++;
    const k = sec.querySelector(".section__kicker");
    if (k) k.textContent = String(num).padStart(2, "0") + " — " + (k.dataset.label || "");
  });
  // hide nav links whose section is hidden
  document.querySelectorAll("#navLinks a[data-sec]").forEach((a) => {
    if (!sectionHasContent[a.dataset.sec]) a.style.display = "none";
  });

  /* ---------- NAV: scroll state + mobile menu ---------- */
  const nav = $("nav");
  const navLinks = $("navLinks");
  const menuBtn = $("menuBtn");
  menuBtn.onclick = () => navLinks.classList.toggle("open");
  navLinks.querySelectorAll("a").forEach((a) => (a.onclick = () => navLinks.classList.remove("open")));

  /* ---------- SCROLL: progress bar, nav bg, back-to-top, scrollspy ---------- */
  const progress = $("progress");
  const toTop = $("toTop");
  const secEls = [...document.querySelectorAll("section[data-section]")].filter((s) => s.style.display !== "none");
  function onScroll() {
    const h = document.documentElement;
    const sc = h.scrollTop;
    const max = h.scrollHeight - h.clientHeight;
    progress.style.width = (max > 0 ? (sc / max) * 100 : 0) + "%";
    nav.classList.toggle("scrolled", sc > 20);
    toTop.classList.toggle("show", sc > 500);
    // scrollspy
    let active = "";
    secEls.forEach((s) => { if (s.getBoundingClientRect().top <= 120) active = s.id; });
    document.querySelectorAll("#navLinks a[data-sec]").forEach((a) =>
      a.classList.toggle("active", a.dataset.sec === active));
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  toTop.onclick = () => window.scrollTo({ top: 0, behavior: "smooth" });

  /* ---------- IMAGE LIGHTBOX ---------- */
  $("lightboxClose").onclick = closeLightbox;
  $("lightbox").addEventListener("click", (e) => { if (e.target.id === "lightbox") closeLightbox(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeLightbox(); });
  document.addEventListener("click", (e) => {
    const img = e.target.closest(".pcard__img img, .tl-img img, .award__logo img");
    if (img) openLightbox(img.src);
  });

  /* ---------- REVEAL ON SCROLL (staggered) ---------- */
  document.querySelectorAll(".projects, .skills, .pubs, .awards, .timeline, .exp").forEach((group) => {
    [...group.children].forEach((child, i) => {
      if (child.classList.contains("reveal")) child.style.transitionDelay = Math.min(i, 6) * 70 + "ms";
    });
  });
  const io = new IntersectionObserver(
    (entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }),
    { threshold: 0.12 }
  );
  document.querySelectorAll(".reveal").forEach((n) => io.observe(n));
})();
