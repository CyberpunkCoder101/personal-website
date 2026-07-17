# Anish Patil — Personal Website

A fast, dependency-free personal site. **Everything is customizable from one file: [`data.js`](data.js).**
No build tools, no frameworks — just HTML, CSS, and vanilla JS.

---

## ✨ Easiest way to edit: the desktop editor

No code required. Run the visual editor and fill in forms:

```bash
python website_editor.py     # needs PyQt5:  pip install PyQt5
```

**11 tabs:** Profile · Theme · Timeline · Experience · Projects · Publications ·
Skills · Awards · Links · Settings · Contact.

- **Add pictures** with a file picker (profile photo, hero background, a picture
  per project, **a picture per timeline entry**, and **a logo/photo per award**)
  — images are copied into `assets/` automatically.
- **Theme**: pick an accent from 10 quick swatches or the full color wheel,
  choose a font preset, set light/dark default and corner radius.
- **Experience**: roles with company, dates, location and bullet points.
- **Publications**: title, authors, venue, year, paper/code links, abstract.
- **Awards & certifications**: title, issuer, year, link.
- **Links** table has extra columns — **Icon** and **Featured** (featured links
  become social buttons under your name in the hero).
- **Headline stats** now take an **emoji icon** column.
- **Settings**: browser/site title, meta description (SEO), emoji favicon,
  optional hero background image.
- **Add / delete / reorder** every list (timeline, experience, projects,
  publications, skills, awards).
- Hit **Save** (Ctrl+S — writes `site_data.json` + regenerates `data.js`), or
  **Save & Preview** (Ctrl+P) to open the live site in your browser.

Sections with no entries hide themselves automatically, and the section numbers
(01, 02, …) and nav links renumber to match. The design/graphics stay fixed —
you only edit text and pictures.

### Live-site extras (all automatic)
- **Animated aurora hero** with drifting color blobs and a fading dot-grid.
- **Count-up stats** that animate from 0 when the page loads.
- **Cursor-spotlight** glow that follows your mouse across project cards.
- **Project tag filter** — click a tag to filter the project grid.
- **Image lightbox** — click any project/timeline/award picture to enlarge it
  (Esc or click-outside to close).
- **Copy-email button** with a confirmation toast.
- **Gradient hero name**, staggered on-scroll reveals, scroll-progress bar,
  scrollspy nav, back-to-top button, and a typewriter tagline.
- **Smooth light/dark cross-fade**, and everything respects
  `prefers-reduced-motion`.

> Tip: the bundled `python -m http.server` doesn't send cache headers, so after
> editing do a hard refresh (Ctrl+Shift+R) if you don't see changes.

---

## Run it locally

The site loads `data.js` via a `<script>` tag, so opening `index.html` directly
(`file://`) works in most browsers. If your browser blocks it, run a tiny server:

```bash
cd personal-website
python -m http.server 8123
# then open http://localhost:8123
```

---

## Customize everything — edit `data.js`

Open [`data.js`](data.js) and edit the plain-English fields. Save, refresh. That's it.

| Section | What it controls |
|---------|------------------|
| `theme` | Accent color, light/dark default, fonts, corner radius, live theme picker on/off |
| `profile` | Your name, rotating role taglines, bio, location, avatar, resume link, headline stats |
| `links` | LinkedIn / GitHub / Email / Scholar (shown in nav + footer) |
| `timeline` | Your journey year-by-year from 2016 → now |
| `projects` | Deep-dive cards with metric pills and tech-tag chips |
| `skills` | Grouped skill chips |
| `contact` | Bottom call-to-action + email |

### Fill in the `TODO:` placeholders
Search `data.js` for `TODO:` — those are the spots only you can fill:
- Your real **2016–2022 timeline** (school, first projects, internships, degree).
- Your **GitHub** and **Google Scholar** URLs.
- **Location**, and optionally an **avatar image** and **resume PDF** (drop the files
  in this folder and point `avatar` / `resumeUrl` at them).
- Project **links** (paper / repo / demo URLs).

### Change the whole color scheme in 2 seconds
In `data.js` → `theme.accent`, pick any hex. Suggested palette:
`#6366f1` indigo · `#10b981` emerald · `#f43f5e` rose · `#f59e0b` amber · `#06b6d4` cyan · `#a855f7` violet.
Visitors can also switch the accent and light/dark live from the nav bar.

### Add a project / timeline entry
Copy any existing block in the `projects` or `timeline` array, paste it, and edit the text.
Set `highlight: true` on a project to make its card span the full width.

---

## Files
```
personal-website/
├── index.html   ← page structure (rarely needs editing)
├── styles.css   ← visual system, driven by CSS variables (rarely needs editing)
├── app.js       ← renders data.js into the page (no need to edit)
├── data.js      ← ★ YOUR CONTENT — edit this ★
└── README.md    ← this file
```

## Deploy it (free)
- **GitHub Pages**: push this folder to a repo → Settings → Pages → deploy from branch.
- **Netlify / Vercel / Cloudflare Pages**: drag-and-drop the folder, done.

No configuration needed — it's a plain static site.
