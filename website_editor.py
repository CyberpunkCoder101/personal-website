#!/usr/bin/env python3
"""
website_editor.py — a desktop editor for your personal website.

The website's *design/graphics are fixed*; this app lets you freely edit all the
TEXT and PICTURES, then writes them into the site with one click.

Tabs: Profile · Theme · Timeline · Experience · Projects · Publications ·
      Skills · Awards · Links · Settings · Contact

How it works
------------
* Content lives in `site_data.json` (this app reads & writes it).
* On Save, the app also regenerates `data.js`, which the website loads.
* Pictures you pick are copied into an `assets/` folder next to the site.

Run:  python website_editor.py
Needs: PyQt5   (pip install PyQt5)
"""

import sys, os, json, shutil, subprocess, webbrowser, socket
from copy import deepcopy

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QListWidget,
    QListWidgetItem, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QColorDialog, QFileDialog, QMessageBox, QSpinBox, QHeaderView,
    QSplitter, QToolBar, QAction, QStyle, QScrollArea
)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(HERE, "site_data.json")
DATA_JS = os.path.join(HERE, "data.js")
ASSETS = os.path.join(HERE, "assets")
PORT = 8123

TIMELINE_TYPES = ["education", "work", "research", "project", "award"]
ACCENT_PRESETS = ["#6366f1", "#10b981", "#f43f5e", "#f59e0b", "#06b6d4",
                  "#a855f7", "#ec4899", "#14b8a6", "#ef4444", "#3b82f6"]
FONT_PRESETS = {
    "Inter + Space Grotesk (default)":
        ("'Inter', system-ui, sans-serif", "'Space Grotesk', 'Inter', sans-serif"),
    "System UI":
        ("system-ui, -apple-system, sans-serif", "system-ui, sans-serif"),
    "Georgia (serif)":
        ("Georgia, 'Times New Roman', serif", "Georgia, serif"),
    "Monospace":
        ("'JetBrains Mono', ui-monospace, monospace", "'JetBrains Mono', monospace"),
}


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def lighten(hex_color, pct=30):
    try:
        c = QColor(hex_color)
        return QColor(min(255, c.red() + int(2.55 * pct)),
                      min(255, c.green() + int(2.55 * pct)),
                      min(255, c.blue() + int(2.55 * pct))).name()
    except Exception:
        return hex_color


def copy_into_assets(src_path):
    os.makedirs(ASSETS, exist_ok=True)
    base = os.path.basename(src_path)
    dst = os.path.join(ASSETS, base)
    if os.path.exists(dst) and os.path.abspath(src_path) != os.path.abspath(dst):
        stem, ext = os.path.splitext(base)
        i = 1
        while os.path.exists(dst):
            base = f"{stem}_{i}{ext}"; dst = os.path.join(ASSETS, base); i += 1
    if os.path.abspath(src_path) != os.path.abspath(dst):
        shutil.copy(src_path, dst)
    return f"assets/{base}"


# --------------------------------------------------------------------------- #
#  reusable widgets
# --------------------------------------------------------------------------- #
class ListEditor(QWidget):
    """Edit a simple list of strings (roles, skill items, tags, bullets)."""

    def __init__(self, placeholder="Add item…"):
        super().__init__()
        self.list = QListWidget(); self.list.setMaximumHeight(150)
        self.entry = QLineEdit(); self.entry.setPlaceholderText(placeholder)
        self.entry.returnPressed.connect(self.add)
        add_btn = QPushButton("Add"); add_btn.clicked.connect(self.add)
        del_btn = QPushButton("Remove"); del_btn.clicked.connect(self.remove)
        up = QPushButton("↑"); up.setFixedWidth(34); up.clicked.connect(lambda: self.move(-1))
        dn = QPushButton("↓"); dn.setFixedWidth(34); dn.clicked.connect(lambda: self.move(1))
        row = QHBoxLayout()
        for w in (self.entry, add_btn, del_btn, up, dn):
            row.addWidget(w)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.list); lay.addLayout(row)
        self.list.itemDoubleClicked.connect(self._edit_inline)

    def _edit_inline(self, item):
        item.setFlags(item.flags() | Qt.ItemIsEditable); self.list.editItem(item)

    def add(self):
        t = self.entry.text().strip()
        if t:
            it = QListWidgetItem(t); it.setFlags(it.flags() | Qt.ItemIsEditable)
            self.list.addItem(it); self.entry.clear()

    def remove(self):
        r = self.list.currentRow()
        if r >= 0:
            self.list.takeItem(r)

    def move(self, d):
        r = self.list.currentRow(); n = r + d
        if r < 0 or n < 0 or n >= self.list.count():
            return
        self.list.insertItem(n, self.list.takeItem(r)); self.list.setCurrentRow(n)

    def set_items(self, items):
        self.list.clear()
        for s in items or []:
            it = QListWidgetItem(str(s)); it.setFlags(it.flags() | Qt.ItemIsEditable)
            self.list.addItem(it)

    def get_items(self):
        return [self.list.item(i).text() for i in range(self.list.count())]


class DictTable(QWidget):
    """Editable table over a list of dicts. columns = [(header, key, type)],
    type is 'text' or 'bool'."""

    def __init__(self, columns, max_h=200):
        super().__init__()
        self.columns = columns
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels([c[0] for c in columns])
        hdr = self.table.horizontalHeader()
        for i, (_, _, ty) in enumerate(columns):
            hdr.setSectionResizeMode(
                i, QHeaderView.ResizeToContents if ty == "bool" else QHeaderView.Stretch)
        self.table.setMaximumHeight(max_h)
        add = QPushButton("+ Row"); add.clicked.connect(self._add_row)
        rem = QPushButton("– Row"); rem.clicked.connect(self._rem)
        up = QPushButton("↑"); up.setFixedWidth(34); up.clicked.connect(lambda: self._move(-1))
        dn = QPushButton("↓"); dn.setFixedWidth(34); dn.clicked.connect(lambda: self._move(1))
        row = QHBoxLayout(); row.addWidget(add); row.addWidget(rem)
        row.addWidget(up); row.addWidget(dn); row.addStretch()
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.table); lay.addLayout(row)

    def _mk_cell(self, key, ty, value):
        it = QTableWidgetItem()
        if ty == "bool":
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if value else Qt.Unchecked)
        else:
            it.setText("" if value is None else str(value))
        return it

    def _add_row(self, values=None):
        values = values or {}
        r = self.table.rowCount(); self.table.insertRow(r)
        for ci, (_, key, ty) in enumerate(self.columns):
            self.table.setItem(r, ci, self._mk_cell(key, ty, values.get(key)))

    def _rem(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def _move(self, d):
        r = self.table.currentRow(); n = r + d
        if r < 0 or n < 0 or n >= self.table.rowCount():
            return
        rows = self.get_rows(); rows[r], rows[n] = rows[n], rows[r]
        self.set_rows(rows); self.table.selectRow(n)

    def set_rows(self, rows):
        self.table.setRowCount(0)
        for row in rows or []:
            self._add_row(row)

    def get_rows(self):
        out = []
        for r in range(self.table.rowCount()):
            d = {}
            has_text = False
            for ci, (_, key, ty) in enumerate(self.columns):
                it = self.table.item(r, ci)
                if ty == "bool":
                    d[key] = bool(it and it.checkState() == Qt.Checked)
                else:
                    val = it.text().strip() if it else ""
                    d[key] = val
                    if val:
                        has_text = True
            if has_text:
                out.append(d)
        return out


class ImagePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.rel = ""
        self.thumb = QLabel("No image"); self.thumb.setFixedSize(150, 100)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border:1px solid #888; border-radius:6px; color:#888;")
        pick = QPushButton("Choose picture…"); pick.clicked.connect(self.pick)
        clr = QPushButton("Clear"); clr.clicked.connect(lambda: self.set_path(""))
        btns = QVBoxLayout(); btns.addWidget(pick); btns.addWidget(clr); btns.addStretch()
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.thumb); lay.addLayout(btns); lay.addStretch()

    def pick(self):
        fn, _ = QFileDialog.getOpenFileName(
            self, "Choose a picture", HERE,
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp)")
        if fn:
            self.set_path(copy_into_assets(fn))

    def set_path(self, rel):
        self.rel = rel or ""
        if self.rel:
            pm = QPixmap(os.path.join(HERE, self.rel))
            if not pm.isNull():
                self.thumb.setPixmap(pm.scaled(150, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.thumb.setToolTip(self.rel); return
        self.thumb.clear(); self.thumb.setText("No image")

    def get_path(self):
        return self.rel


class ColorButton(QPushButton):
    def __init__(self, color="#6366f1"):
        super().__init__(); self.color = color
        self.setFixedSize(60, 30); self.clicked.connect(self.choose); self._paint()

    def _paint(self):
        self.setStyleSheet(f"background:{self.color}; border:1px solid #555; border-radius:6px;")

    def choose(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Pick accent color")
        if c.isValid():
            self.set_color(c.name())

    def set_color(self, c):
        self.color = c or "#6366f1"; self._paint()


def scrollable(widget):
    """Wrap a widget in a vertical scroll area (for long form tabs)."""
    sa = QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(widget)
    sa.setFrameShape(QScrollArea.NoFrame)
    return sa


# --------------------------------------------------------------------------- #
#  master/detail list section
# --------------------------------------------------------------------------- #
class ListSection(QWidget):
    """Reusable list + detail-form editor bound to a python list of dicts."""

    def __init__(self, items, label_fn, blank_fn, build_detail, load_fn, commit_fn):
        super().__init__()
        self.items = items
        self.label_fn = label_fn
        self.blank_fn = blank_fn
        self.load_fn = load_fn
        self.commit_fn = commit_fn
        self.idx = -1
        self.loading = False

        self.listw = QListWidget()
        add = QPushButton("+ Add"); add.clicked.connect(self.add)
        rem = QPushButton("– Delete"); rem.clicked.connect(self.delete)
        up = QPushButton("↑"); up.setFixedWidth(34); up.clicked.connect(lambda: self.move(-1))
        dn = QPushButton("↓"); dn.setFixedWidth(34); dn.clicked.connect(lambda: self.move(1))
        btns = QHBoxLayout()
        for w in (add, rem, up, dn):
            btns.addWidget(w)
        left = QVBoxLayout(); left.addWidget(self.listw); left.addLayout(btns)
        lw = QWidget(); lw.setLayout(left); lw.setMaximumWidth(280)

        self.detail = QWidget()
        build_detail(self.detail)
        split = QSplitter(); split.addWidget(lw); split.addWidget(scrollable(self.detail))
        split.setStretchFactor(1, 1)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(split)

        self.listw.currentRowChanged.connect(self._select)
        self.refresh()

    def refresh(self):
        self.listw.clear()
        for e in self.items:
            self.listw.addItem(self.label_fn(e))

    def _select(self, idx):
        self.commit_collections()
        self.idx = idx
        if 0 <= idx < len(self.items):
            self.loading = True
            self.load_fn(self.items[idx])
            self.loading = False

    def commit(self):
        if self.loading or not (0 <= self.idx < len(self.items)):
            return
        self.commit_fn(self.items[self.idx])
        it = self.listw.item(self.idx)
        if it:
            it.setText(self.label_fn(self.items[self.idx]))

    def commit_collections(self):
        """Override point: pull list/table widgets into current dict."""
        if 0 <= self.idx < len(self.items):
            self.commit_fn(self.items[self.idx])

    def add(self):
        self.commit_collections()
        self.items.append(self.blank_fn())
        self.refresh(); self.listw.setCurrentRow(len(self.items) - 1)

    def delete(self):
        if self.idx >= 0:
            self.items.pop(self.idx); self.idx = -1; self.refresh()

    def move(self, d):
        self.commit_collections()
        i = self.idx; n = i + d
        if i < 0 or n < 0 or n >= len(self.items):
            return
        self.items[i], self.items[n] = self.items[n], self.items[i]
        self.refresh(); self.listw.setCurrentRow(n)


# --------------------------------------------------------------------------- #
#  main window
# --------------------------------------------------------------------------- #
class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal Website Editor")
        self.resize(1000, 760)
        self.data = self.load_data()
        self.timeline = deepcopy(self.data.get("timeline", []))
        self.projects = deepcopy(self.data.get("projects", []))
        self.skills = deepcopy(self.data.get("skills", []))
        self.experience = deepcopy(self.data.get("experience", []))
        self.publications = deepcopy(self.data.get("publications", []))
        self.awards = deepcopy(self.data.get("awards", []))

        self._build_toolbar()
        self.sections = {}   # keep ListSection refs for commit-on-save
        tabs = QTabWidget()
        tabs.setMovable(True)
        tabs.addTab(scrollable(self._tab_profile()), "Profile")
        tabs.addTab(self._tab_theme(), "Theme")
        tabs.addTab(self._tab_timeline(), "Timeline")
        tabs.addTab(self._tab_experience(), "Experience")
        tabs.addTab(self._tab_projects(), "Projects")
        tabs.addTab(self._tab_publications(), "Publications")
        tabs.addTab(self._tab_skills(), "Skills")
        tabs.addTab(self._tab_awards(), "Awards")
        tabs.addTab(self._tab_links(), "Links")
        tabs.addTab(scrollable(self._tab_settings()), "Settings")
        tabs.addTab(self._tab_contact(), "Contact")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage(f"Loaded {DATA_JSON}")

    # ------------------------------------------------------------------ data
    def load_data(self):
        if os.path.exists(DATA_JSON):
            with open(DATA_JSON, encoding="utf-8") as f:
                return json.load(f)
        QMessageBox.critical(self, "Missing file",
                             f"Could not find {DATA_JSON}.\nRun this from the website folder.")
        sys.exit(1)

    # --------------------------------------------------------------- toolbar
    def _build_toolbar(self):
        tb = QToolBar(); tb.setMovable(False); self.addToolBar(tb)
        st = self.style()
        save = QAction(st.standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        save.setShortcut("Ctrl+S"); save.triggered.connect(self.save)
        prev = QAction(st.standardIcon(QStyle.SP_MediaPlay), "Save && Preview", self)
        prev.setShortcut("Ctrl+P"); prev.triggered.connect(self.save_and_preview)
        reload_ = QAction(st.standardIcon(QStyle.SP_BrowserReload), "Reload from disk", self)
        reload_.triggered.connect(self.reload_from_disk)
        tb.addAction(save); tb.addAction(prev); tb.addSeparator(); tb.addAction(reload_)

    # ------------------------------------------------------------- tab: profile
    def _tab_profile(self):
        w = QWidget(); form = QFormLayout(w)
        p = self.data.get("profile", {})
        self.p_name = QLineEdit(p.get("name", ""))
        self.p_location = QLineEdit(p.get("location", ""))
        self.p_tagline = QPlainTextEdit(p.get("tagline", "")); self.p_tagline.setMaximumHeight(90)
        self.p_resume = QLineEdit(p.get("resumeUrl", ""))
        resume_btn = QPushButton("Browse file…"); resume_btn.clicked.connect(self._pick_resume)
        rrow = QHBoxLayout(); rrow.addWidget(self.p_resume); rrow.addWidget(resume_btn)
        rw = QWidget(); rw.setLayout(rrow)
        self.p_roles = ListEditor("Add a role/tagline line…"); self.p_roles.set_items(p.get("roles", []))
        self.p_avatar = ImagePicker(); self.p_avatar.set_path(p.get("avatar", ""))
        self.p_stats = DictTable([("Icon (emoji)", "icon", "text"),
                                  ("Value", "value", "text"),
                                  ("Label", "label", "text")])
        self.p_stats.set_rows(p.get("stats", []))
        form.addRow("Full name", self.p_name)
        form.addRow("Location", self.p_location)
        form.addRow("Tagline / bio", self.p_tagline)
        form.addRow("Profile picture", self.p_avatar)
        form.addRow("Rotating roles", self.p_roles)
        form.addRow("Headline stats", self.p_stats)
        form.addRow("Résumé file/URL", rw)
        return w

    def _pick_resume(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Choose résumé", HERE, "Documents (*.pdf *.doc *.docx)")
        if fn:
            self.p_resume.setText(copy_into_assets(fn))

    # --------------------------------------------------------------- tab: theme
    def _tab_theme(self):
        w = QWidget(); form = QFormLayout(w)
        t = self.data.get("theme", {})
        self.t_accent = ColorButton(t.get("accent", "#6366f1"))
        presets = QHBoxLayout(); presets.setSpacing(6)
        for c in ACCENT_PRESETS:
            b = QPushButton(); b.setFixedSize(24, 24)
            b.setStyleSheet(f"background:{c}; border:1px solid #555; border-radius:12px;")
            b.clicked.connect(lambda _, col=c: self.t_accent.set_color(col))
            presets.addWidget(b)
        presets.addStretch()
        pw = QWidget(); pw.setLayout(presets)
        self.t_mode = QComboBox(); self.t_mode.addItems(["dark", "light"]); self.t_mode.setCurrentText(t.get("defaultMode", "dark"))
        self.t_fontpreset = QComboBox(); self.t_fontpreset.addItems(["— font preset —"] + list(FONT_PRESETS.keys()))
        self.t_fontpreset.currentTextChanged.connect(self._apply_font_preset)
        self.t_font = QLineEdit(t.get("font", ""))
        self.t_head = QLineEdit(t.get("headingFont", ""))
        self.t_radius = QSpinBox(); self.t_radius.setRange(0, 40); self.t_radius.setSuffix(" px")
        try:
            self.t_radius.setValue(int(str(t.get("radius", "16")).replace("px", "")))
        except ValueError:
            self.t_radius.setValue(16)
        self.t_picker = QCheckBox("Let visitors switch accent color & light/dark on the live site")
        self.t_picker.setChecked(bool(t.get("showThemePicker", True)))
        note = QLabel("Accent drives buttons, highlights and links site-wide; a lighter shade is auto-generated.\n"
                      "Custom Google Fonts must also be added to index.html's <link> tag.")
        note.setStyleSheet("color:#888;")
        form.addRow("Accent color", self.t_accent)
        form.addRow("Quick colors", pw)
        form.addRow("Opens in", self.t_mode)
        form.addRow("Font preset", self.t_fontpreset)
        form.addRow("Body font", self.t_font)
        form.addRow("Heading font", self.t_head)
        form.addRow("Corner radius", self.t_radius)
        form.addRow("", self.t_picker)
        form.addRow("", note)
        return scrollable(w)

    def _apply_font_preset(self, name):
        if name in FONT_PRESETS:
            body, head = FONT_PRESETS[name]
            self.t_font.setText(body); self.t_head.setText(head)

    # ------------------------------------------------------------ tab: timeline
    def _tab_timeline(self):
        def build(d):
            form = QFormLayout(d)
            self.tl_year = QLineEdit(); self.tl_type = QComboBox(); self.tl_type.addItems(TIMELINE_TYPES)
            self.tl_title = QLineEdit(); self.tl_org = QLineEdit()
            self.tl_text = QPlainTextEdit(); self.tl_text.setMaximumHeight(120)
            self.tl_image = ImagePicker()
            for wdg in (self.tl_year, self.tl_title, self.tl_org):
                wdg.textChanged.connect(lambda: self.sections["tl"].commit())
            self.tl_type.currentTextChanged.connect(lambda: self.sections["tl"].commit())
            self.tl_text.textChanged.connect(lambda: self.sections["tl"].commit())
            form.addRow("Year", self.tl_year); form.addRow("Type", self.tl_type)
            form.addRow("Title", self.tl_title); form.addRow("Organisation", self.tl_org)
            form.addRow("Description", self.tl_text)
            form.addRow("Picture (optional)", self.tl_image)

        def load(e):
            self.tl_year.setText(e.get("year", "")); self.tl_type.setCurrentText(e.get("type", "education"))
            self.tl_title.setText(e.get("title", "")); self.tl_org.setText(e.get("org", ""))
            self.tl_text.setPlainText(e.get("text", "")); self.tl_image.set_path(e.get("image", ""))

        def commit(e):
            e["year"] = self.tl_year.text(); e["type"] = self.tl_type.currentText()
            e["title"] = self.tl_title.text(); e["org"] = self.tl_org.text()
            e["text"] = self.tl_text.toPlainText(); e["image"] = self.tl_image.get_path()

        s = ListSection(self.timeline, lambda e: f"{e.get('year','')} — {e.get('title','')}",
                        lambda: {"year": "20XX", "type": "project", "title": "New entry", "org": "", "text": "", "image": ""},
                        build, load, commit)
        self.sections["tl"] = s
        return s

    # ---------------------------------------------------------- tab: experience
    def _tab_experience(self):
        def build(d):
            form = QFormLayout(d)
            self.ex_role = QLineEdit(); self.ex_company = QLineEdit(); self.ex_loc = QLineEdit()
            self.ex_start = QLineEdit(); self.ex_end = QLineEdit(); self.ex_url = QLineEdit()
            self.ex_bullets = ListEditor("Add an achievement bullet…")
            for wdg in (self.ex_role, self.ex_company, self.ex_loc, self.ex_start, self.ex_end, self.ex_url):
                wdg.textChanged.connect(lambda: self.sections["ex"].commit())
            form.addRow("Role / Title", self.ex_role)
            form.addRow("Company / Lab", self.ex_company)
            form.addRow("Location", self.ex_loc)
            form.addRow("Start", self.ex_start)
            form.addRow("End", self.ex_end)
            form.addRow("Link (optional)", self.ex_url)
            form.addRow("Bullets", self.ex_bullets)

        def load(e):
            self.ex_role.setText(e.get("role", "")); self.ex_company.setText(e.get("company", ""))
            self.ex_loc.setText(e.get("location", "")); self.ex_start.setText(e.get("start", ""))
            self.ex_end.setText(e.get("end", "")); self.ex_url.setText(e.get("url", ""))
            self.ex_bullets.set_items(e.get("bullets", []))

        def commit(e):
            e["role"] = self.ex_role.text(); e["company"] = self.ex_company.text()
            e["location"] = self.ex_loc.text(); e["start"] = self.ex_start.text()
            e["end"] = self.ex_end.text(); e["url"] = self.ex_url.text()
            e["bullets"] = self.ex_bullets.get_items()

        s = ListSection(self.experience,
                        lambda e: f"{e.get('role','(role)')} @ {e.get('company','')}",
                        lambda: {"role": "New Role", "company": "", "location": "",
                                 "start": "", "end": "", "url": "", "bullets": []},
                        build, load, commit)
        self.sections["ex"] = s
        return s

    # ------------------------------------------------------------ tab: projects
    def _tab_projects(self):
        def build(d):
            form = QFormLayout(d)
            self.pr_title = QLineEdit(); self.pr_period = QLineEdit()
            self.pr_blurb = QPlainTextEdit(); self.pr_blurb.setMaximumHeight(100)
            self.pr_link = QLineEdit()
            self.pr_highlight = QCheckBox("Feature this project (full-width card)")
            self.pr_image = ImagePicker()
            self.pr_metrics = DictTable([("Value", "value", "text"), ("Label", "label", "text")])
            self.pr_tags = ListEditor("Add a tech tag…")
            for wdg in (self.pr_title, self.pr_period, self.pr_link):
                wdg.textChanged.connect(lambda: self.sections["pr"].commit())
            self.pr_blurb.textChanged.connect(lambda: self.sections["pr"].commit())
            self.pr_highlight.stateChanged.connect(lambda: self.sections["pr"].commit())
            form.addRow("Title", self.pr_title); form.addRow("Period", self.pr_period)
            form.addRow("Picture", self.pr_image); form.addRow("Description", self.pr_blurb)
            form.addRow("Metrics", self.pr_metrics); form.addRow("Tech tags", self.pr_tags)
            form.addRow("Link (paper/repo)", self.pr_link); form.addRow("", self.pr_highlight)

        def load(e):
            self.pr_title.setText(e.get("title", "")); self.pr_period.setText(e.get("period", ""))
            self.pr_blurb.setPlainText(e.get("blurb", "")); self.pr_link.setText(e.get("link", ""))
            self.pr_highlight.setChecked(bool(e.get("highlight", False)))
            self.pr_image.set_path(e.get("image", ""))
            self.pr_metrics.set_rows(e.get("metrics", [])); self.pr_tags.set_items(e.get("tags", []))

        def commit(e):
            e["title"] = self.pr_title.text(); e["period"] = self.pr_period.text()
            e["blurb"] = self.pr_blurb.toPlainText(); e["link"] = self.pr_link.text()
            e["highlight"] = self.pr_highlight.isChecked()
            e["image"] = self.pr_image.get_path()
            e["metrics"] = self.pr_metrics.get_rows(); e["tags"] = self.pr_tags.get_items()

        s = ListSection(self.projects, lambda e: e.get("title", "Untitled"),
                        lambda: {"title": "New Project", "period": "", "image": "", "blurb": "",
                                 "metrics": [], "tags": [], "link": "", "highlight": False},
                        build, load, commit)
        self.sections["pr"] = s
        return s

    # -------------------------------------------------------- tab: publications
    def _tab_publications(self):
        def build(d):
            form = QFormLayout(d)
            self.pb_title = QLineEdit(); self.pb_authors = QLineEdit(); self.pb_venue = QLineEdit()
            self.pb_year = QLineEdit(); self.pb_paper = QLineEdit(); self.pb_code = QLineEdit()
            self.pb_abstract = QPlainTextEdit(); self.pb_abstract.setMaximumHeight(90)
            for wdg in (self.pb_title, self.pb_authors, self.pb_venue, self.pb_year,
                        self.pb_paper, self.pb_code):
                wdg.textChanged.connect(lambda: self.sections["pb"].commit())
            self.pb_abstract.textChanged.connect(lambda: self.sections["pb"].commit())
            form.addRow("Title", self.pb_title); form.addRow("Authors", self.pb_authors)
            form.addRow("Venue", self.pb_venue); form.addRow("Year", self.pb_year)
            form.addRow("Paper URL", self.pb_paper); form.addRow("Code URL", self.pb_code)
            form.addRow("Abstract", self.pb_abstract)

        def load(e):
            self.pb_title.setText(e.get("title", "")); self.pb_authors.setText(e.get("authors", ""))
            self.pb_venue.setText(e.get("venue", "")); self.pb_year.setText(e.get("year", ""))
            self.pb_paper.setText(e.get("paper", "")); self.pb_code.setText(e.get("code", ""))
            self.pb_abstract.setPlainText(e.get("abstract", ""))

        def commit(e):
            e["title"] = self.pb_title.text(); e["authors"] = self.pb_authors.text()
            e["venue"] = self.pb_venue.text(); e["year"] = self.pb_year.text()
            e["paper"] = self.pb_paper.text(); e["code"] = self.pb_code.text()
            e["abstract"] = self.pb_abstract.toPlainText()

        s = ListSection(self.publications,
                        lambda e: f"{e.get('year','')} — {e.get('title','Untitled')[:40]}",
                        lambda: {"title": "New Publication", "authors": "", "venue": "",
                                 "year": "2026", "paper": "", "code": "", "abstract": ""},
                        build, load, commit)
        self.sections["pb"] = s
        return s

    # -------------------------------------------------------------- tab: skills
    def _tab_skills(self):
        def build(d):
            form = QFormLayout(d)
            self.sk_group = QLineEdit()
            self.sk_group.textChanged.connect(lambda: self.sections["sk"].commit())
            self.sk_items = ListEditor("Add a skill…")
            form.addRow("Group name", self.sk_group); form.addRow("Skills", self.sk_items)

        def load(g):
            self.sk_group.setText(g.get("group", "")); self.sk_items.set_items(g.get("items", []))

        def commit(g):
            g["group"] = self.sk_group.text(); g["items"] = self.sk_items.get_items()

        s = ListSection(self.skills, lambda g: g.get("group", "Group"),
                        lambda: {"group": "New Group", "items": []}, build, load, commit)
        self.sections["sk"] = s
        return s

    # -------------------------------------------------------------- tab: awards
    def _tab_awards(self):
        def build(d):
            form = QFormLayout(d)
            self.aw_title = QLineEdit(); self.aw_issuer = QLineEdit()
            self.aw_year = QLineEdit(); self.aw_url = QLineEdit()
            self.aw_image = ImagePicker()
            for wdg in (self.aw_title, self.aw_issuer, self.aw_year, self.aw_url):
                wdg.textChanged.connect(lambda: self.sections["aw"].commit())
            form.addRow("Title", self.aw_title); form.addRow("Issuer", self.aw_issuer)
            form.addRow("Year", self.aw_year); form.addRow("Link (optional)", self.aw_url)
            form.addRow("Picture / Logo (optional)", self.aw_image)

        def load(a):
            self.aw_title.setText(a.get("title", "")); self.aw_issuer.setText(a.get("issuer", ""))
            self.aw_year.setText(a.get("year", "")); self.aw_url.setText(a.get("url", ""))
            self.aw_image.set_path(a.get("image", ""))

        def commit(a):
            a["title"] = self.aw_title.text(); a["issuer"] = self.aw_issuer.text()
            a["year"] = self.aw_year.text(); a["url"] = self.aw_url.text()
            a["image"] = self.aw_image.get_path()

        s = ListSection(self.awards, lambda a: f"{a.get('year','')} — {a.get('title','Award')[:36]}",
                        lambda: {"title": "New Award", "issuer": "", "year": "", "url": "", "image": ""},
                        build, load, commit)
        self.sections["aw"] = s
        return s

    # --------------------------------------------------------------- tab: links
    def _tab_links(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.links_table = DictTable([("Label", "label", "text"),
                                      ("URL", "url", "text"),
                                      ("Icon", "icon", "text"),
                                      ("Featured", "featured", "bool")], max_h=320)
        self.links_table.set_rows(self.data.get("links", []))
        note = QLabel("“Featured” links become buttons under your name in the hero.\n"
                      "Icon can be a slug (linkedin, github, email, scholar, twitter, website) or an emoji.\n"
                      "Rows with a TODO/empty URL are skipped on the live site.")
        note.setStyleSheet("color:#888;")
        lay.addWidget(self.links_table); lay.addWidget(note); lay.addStretch()
        return w

    # ------------------------------------------------------------ tab: settings
    def _tab_settings(self):
        w = QWidget(); form = QFormLayout(w)
        m = self.data.get("meta", {})
        self.m_title = QLineEdit(m.get("siteTitle", ""))
        self.m_desc = QPlainTextEdit(m.get("description", "")); self.m_desc.setMaximumHeight(70)
        self.m_favicon = QLineEdit(m.get("favicon", "")); self.m_favicon.setMaximumWidth(80)
        self.m_hero = ImagePicker(); self.m_hero.set_path(m.get("heroBackground", ""))
        note = QLabel("Site title & description show in the browser tab and search results.\n"
                      "Favicon is a single emoji shown on the browser tab.\n"
                      "Hero background is an optional image behind your name (kept subtle & dimmed).")
        note.setStyleSheet("color:#888;")
        form.addRow("Browser/site title", self.m_title)
        form.addRow("Meta description", self.m_desc)
        form.addRow("Favicon (emoji)", self.m_favicon)
        form.addRow("Hero background", self.m_hero)
        form.addRow("", note)
        return w

    # ------------------------------------------------------------- tab: contact
    def _tab_contact(self):
        w = QWidget(); form = QFormLayout(w)
        c = self.data.get("contact", {})
        self.c_heading = QLineEdit(c.get("heading", ""))
        self.c_text = QPlainTextEdit(c.get("text", "")); self.c_text.setMaximumHeight(80)
        self.c_email = QLineEdit(c.get("email", ""))
        self.c_footer = QLineEdit(self.data.get("footer", ""))
        form.addRow("Heading", self.c_heading); form.addRow("Text", self.c_text)
        form.addRow("Email", self.c_email); form.addRow("Footer name", self.c_footer)
        return w

    # ---------------------------------------------------------------- collect
    def collect(self):
        for s in self.sections.values():   # flush pending list/table edits
            s.commit_collections()

        accent = self.t_accent.color
        self.data["meta"] = {
            "siteTitle": self.m_title.text(),
            "description": self.m_desc.toPlainText(),
            "favicon": self.m_favicon.text(),
            "heroBackground": self.m_hero.get_path(),
        }
        self.data["theme"] = {
            "accent": accent, "accentSoft": lighten(accent, 30),
            "defaultMode": self.t_mode.currentText(),
            "font": self.t_font.text(), "headingFont": self.t_head.text(),
            "radius": f"{self.t_radius.value()}px",
            "showThemePicker": self.t_picker.isChecked(),
        }
        self.data["profile"] = {
            "name": self.p_name.text(), "roles": self.p_roles.get_items(),
            "tagline": self.p_tagline.toPlainText(), "location": self.p_location.text(),
            "avatar": self.p_avatar.get_path(), "resumeUrl": self.p_resume.text(),
            "stats": self.p_stats.get_rows(),
        }
        links = []
        for row in self.links_table.get_rows():
            lab = row.get("label", "").strip(); url = row.get("url", "").strip()
            if lab or url:
                links.append({"label": lab, "url": url,
                              "icon": row.get("icon", "").strip() or lab.lower(),
                              "featured": bool(row.get("featured"))})
        self.data["links"] = links
        self.data["timeline"] = self.timeline
        self.data["experience"] = self.experience
        self.data["projects"] = self.projects
        self.data["publications"] = self.publications
        self.data["skills"] = self.skills
        self.data["awards"] = self.awards
        self.data["contact"] = {
            "heading": self.c_heading.text(), "text": self.c_text.toPlainText(),
            "email": self.c_email.text(),
        }
        self.data["footer"] = self.c_footer.text()
        return self.data

    # ------------------------------------------------------------------- save
    def save(self):
        data = self.collect()
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        header = ("/* AUTO-GENERATED from site_data.json by website_editor.py.\n"
                  "   Use the editor app (python website_editor.py) to change content. */\n")
        with open(DATA_JS, "w", encoding="utf-8") as f:
            f.write(header + "const SITE = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n")
        self.statusBar().showMessage("Saved  →  site_data.json + data.js", 4000)
        return True

    def reload_from_disk(self):
        if QMessageBox.question(self, "Reload", "Discard changes and reload from disk?") == QMessageBox.Yes:
            QMessageBox.information(self, "Reloaded",
                                    "Close and reopen the editor to load the file again.")

    # ---------------------------------------------------------------- preview
    def _server_running(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.3)
        try:
            return s.connect_ex(("127.0.0.1", PORT)) == 0
        finally:
            s.close()

    def save_and_preview(self):
        if not self.save():
            return
        if not self._server_running():
            try:
                subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)],
                                 cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                QMessageBox.warning(self, "Server", f"Could not start preview server:\n{e}"); return
        webbrowser.open(f"http://localhost:{PORT}/index.html")


def main():
    app = QApplication(sys.argv)
    Editor().show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
