"""
Quelldex App v4 — PySide6 Main Application
Multi-project workspace · Collapsible tree · Elegant minimalist UI
"""

import sys
import os
import json
from pathlib import Path
from functools import partial

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFrame, QLabel, QPushButton, QLineEdit, QComboBox,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTextEdit, QGroupBox,
    QFileDialog, QInputDialog, QMessageBox, QRadioButton, QButtonGroup,
    QScrollArea, QSizePolicy, QMenu, QStatusBar, QStackedWidget,
    QSpacerItem, QToolButton, QStyleFactory,
)
from PySide6.QtCore import Qt, QSize, QSettings, QThread, Signal, QTimer
from PySide6.QtGui import (
    QFont, QColor, QTextCharFormat, QAction, QShortcut,
    QKeySequence, QPainter, QPen, QLinearGradient, QPolygonF,
    QPalette,
)

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent
if str(_SRC.parent) not in sys.path:
    sys.path.insert(0, str(_SRC.parent))

from src.core.vcs import VCS
from src.core.project import (
    Project, classify_file, get_category_info, is_data_file, is_code_file,
    scan_directory,
)


# ================================================================
#  Background File Scanner Thread
# ================================================================

class _FileScanWorker(QThread):
    """Scans project directory in background thread.
    Emits finished signal with file list when done."""
    finished = Signal(str, list)  # (project_path, files)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = None
        self._project = None

    def scan(self, project: Project):
        """Start scanning a project. If already running, queue will
        be handled by checking _path on completion."""
        self._path = str(project.path)
        self._project = project
        if not self.isRunning():
            self.start()

    def run(self):
        try:
            files = scan_directory(Path(self._path))
            if self._project:
                self._project._cache.update(files)
            self.finished.emit(self._path, files)
        except Exception:
            self.finished.emit(self._path, [])
from src.viz.data_viewer import (
    load_data_file, compute_column_stats, compute_cross_file_stats,
    histogram_data, scatter_data, bar_data, line_data, multi_line_data,
    correlation_matrix,
)
from src.integrations.bridges import IDELauncher, ExternalToolBridge
from src.ui.theme import (
    C, PALETTE, QSS, MONO_FAMILY,
    format_size, format_time, set_theme, get_current_theme, get_theme_names,
)
from src.ui.widgets import (
    ChartWidget, TagChip, StatCard, IconFactory, LoadingSpinner, DiffViewer,
)


# ================================================================
#  Helpers
# ================================================================

def _btn(text, obj_name="", tooltip="") -> QPushButton:
    b = QPushButton(text)
    if obj_name: b.setObjectName(obj_name)
    if tooltip:  b.setToolTip(tooltip)
    return b

def _icon_btn(text, tooltip="") -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("icon_btn")
    b.setFixedSize(28, 28)
    if tooltip: b.setToolTip(tooltip)
    return b

def _label(text, color=None, size=None, bold=False, mono=False) -> QLabel:
    lbl = QLabel(text)
    s = ["background: transparent"]
    if color: s.append(f"color: {color}")
    if size:  s.append(f"font-size: {size}px")
    if bold:  s.append("font-weight: 600")
    if mono:  s.append(f"font-family: {MONO_FAMILY}")
    lbl.setStyleSheet("; ".join(s))
    return lbl

def _section_label(text) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {C['fg_gutter']}; font-size: 10px; font-weight: 700;"
        f" letter-spacing: 1px; background: transparent; padding: 0;")
    return lbl

def _divider() -> QFrame:
    f = QFrame()
    f.setObjectName("sidebar_divider")
    f.setFrameShape(QFrame.HLine)
    return f

def _spacer(h: int) -> QSpacerItem:
    return QSpacerItem(0, h, QSizePolicy.Minimum, QSizePolicy.Fixed)


class _DiamondIcon(QWidget):
    """Minimal diamond icon for the welcome page."""
    def __init__(self, size=64, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._size = size

    def paintEvent(self, event):
        from PySide6.QtCore import QPointF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self._size
        cx, cy = s / 2, s / 2
        pts = QPolygonF([
            QPointF(cx, 4), QPointF(s - 4, cy),
            QPointF(cx, s - 4), QPointF(4, cy),
        ])
        grad = QLinearGradient(cx, 4, cx, s - 4)
        grad.setColorAt(0.0, QColor(C["accent"]))
        grad.setColorAt(1.0, QColor(C["accent2"]))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPolygon(pts)
        # Inner highlight
        pen = QPen(QColor(255, 255, 255, 35))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawLine(QPointF(cx, 12), QPointF(s - 14, cy))
        p.end()


# ================================================================
#  Workspace — multi-project state
# ================================================================

class Workspace:
    """Manages multiple projects with persistent recent list."""

    CONFIG_FILE = ".quelldex_workspace.json"

    def __init__(self):
        self.projects: dict[str, dict] = {}   # path -> {project, vcs}
        self.active_path: str | None = None
        self._config_path = Path.home() / self.CONFIG_FILE
        self._recent: list[str] = []
        self._load_recent()

    @property
    def project(self) -> Project | None:
        e = self.projects.get(self.active_path)
        return e["project"] if e else None

    @property
    def vcs(self) -> VCS | None:
        e = self.projects.get(self.active_path)
        return e["vcs"] if e else None

    @property
    def has_active(self) -> bool:
        return self.active_path is not None and self.active_path in self.projects

    @property
    def all_paths(self) -> list[str]:
        return list(self.projects.keys())

    @property
    def recent(self) -> list[str]:
        return self._recent[:10]

    def open(self, path: str) -> bool:
        path = str(Path(path).resolve())
        if path in self.projects:
            self.active_path = path
            return True
        try:
            proj = Project(path)
            vcs = VCS(path)
            vcs.init()
            proj.save()
            self.projects[path] = {"project": proj, "vcs": vcs}
            self.active_path = path
            self._add_recent(path)
            return True
        except Exception:
            return False

    def close(self, path: str):
        if path in self.projects:
            e = self.projects.pop(path)
            try:
                e["vcs"].close()
            except Exception:
                pass
        if self.active_path == path:
            self.active_path = next(iter(self.projects), None)

    def switch(self, path: str):
        if path in self.projects:
            self.active_path = path

    def name_of(self, path: str) -> str:
        return Path(path).name

    def get_project_summary(self, path: str) -> dict:
        """Get quick summary for sidebar display. Non-blocking: returns
        empty dict if cache not ready (will be populated by async scan)."""
        e = self.projects.get(path)
        if not e:
            return {}
        try:
            proj = e["project"]
            if proj._cache.is_valid:
                s = proj._cache.get_summary()
                return {"files": s.get("total_files", 0), "size": s.get("total_size", 0)}
            return {}  # Cache not ready; async scan will fill it
        except Exception:
            return {}

    def _load_recent(self):
        try:
            if self._config_path.exists():
                data = json.loads(self._config_path.read_text("utf-8"))
                self._recent = data.get("recent", [])
        except Exception:
            self._recent = []

    def _save_recent(self):
        try:
            self._config_path.write_text(
                json.dumps({"recent": self._recent[:10]}, ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            pass

    def _add_recent(self, path: str):
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        self._recent = self._recent[:10]
        self._save_recent()


# ================================================================
#  Main Window
# ================================================================

class QuelldexWindow(QMainWindow):

    APP_NAME = "Quelldex"
    VERSION = "5.0.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.APP_NAME)
        self.resize(1380, 880)
        self.setMinimumSize(1100, 700)

        self.ws = Workspace()
        self.ide = IDELauncher()
        self.tool_bridge = ExternalToolBridge()
        self.loaded_datasets = {}
        self._current_view = None
        self._tree_collapsed = {}  # path -> set of collapsed folder keys
        self._scan_pending = False

        # Background file scanner
        self._scanner = _FileScanWorker(self)
        self._scanner.finished.connect(self._on_scan_finished)

        # Restore saved theme
        saved_theme = QSettings("Quelldex", "Quelldex").value("theme", "dark")
        if saved_theme in ("dark", "light", "midnight"):
            set_theme(saved_theme)

        self._build_ui()
        self._bind_shortcuts()
        self._switch_view("welcome")

    # -- Build UI -------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = self._build_sidebar()
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.welcome_page = self._build_welcome()
        self.files_page = QWidget()
        self.vcs_page = QWidget()
        self.planner_page = QWidget()
        self.dataviz_page = QWidget()
        self.compare_page = QWidget()
        self.settings_page = QWidget()

        for p in [self.welcome_page, self.files_page, self.vcs_page,
                  self.planner_page, self.dataviz_page,
                  self.compare_page, self.settings_page]:
            self.stack.addWidget(p)

        # Loading spinner overlay
        self._spinner = LoadingSpinner(size=36, thickness=3, parent=self)
        self._spinner.hide()

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    # -- Sidebar --------------------------------------------------

    def _build_sidebar(self) -> QFrame:
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(240)
        layout = QVBoxLayout(sb)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo area
        logo = QWidget()
        ll = QVBoxLayout(logo)
        ll.setContentsMargins(22, 22, 22, 14)
        ll.setSpacing(3)
        ll.addWidget(_label("Quelldex", C["fg"], 18, bold=True))
        ll.addWidget(_label("v" + self.VERSION, C["fg_gutter"], 10))
        layout.addWidget(logo)

        layout.addWidget(_divider())
        layout.addSpacing(8)

        # Navigation
        self._nav_btns = {}
        nav_items = [
            ("files",    "Files"),
            ("vcs",      "Version Control"),
            ("planner",  "Planner"),
            ("dataviz",  "Data Viz"),
            ("compare",  "Compare"),
            ("settings", "Settings"),
        ]
        for vid, lbl in nav_items:
            btn = QPushButton(f"  {lbl}")
            btn.setObjectName("sidebar_btn")
            btn.clicked.connect(partial(self._switch_view, vid))
            layout.addWidget(btn)
            self._nav_btns[vid] = btn

        layout.addSpacing(10)
        layout.addWidget(_divider())
        layout.addSpacing(8)

        # Projects section header
        proj_hdr = QHBoxLayout()
        proj_hdr.setContentsMargins(22, 0, 14, 0)
        proj_hdr.addWidget(_section_label("PROJECTS"))
        proj_hdr.addStretch()
        add_btn = _icon_btn("+", "Open project folder")
        add_btn.clicked.connect(self._open_project)
        proj_hdr.addWidget(add_btn)
        layout.addLayout(proj_hdr)
        layout.addSpacing(6)

        # Project list (scrollable)
        self._proj_list_widget = QWidget()
        self._proj_list_layout = QVBoxLayout(self._proj_list_widget)
        self._proj_list_layout.setContentsMargins(0, 0, 0, 0)
        self._proj_list_layout.setSpacing(2)
        self._proj_list_layout.addStretch()

        proj_scroll = QScrollArea()
        proj_scroll.setWidget(self._proj_list_widget)
        proj_scroll.setWidgetResizable(True)
        proj_scroll.setFixedHeight(180)
        layout.addWidget(proj_scroll)

        # Recent section
        layout.addSpacing(4)
        layout.addWidget(_divider())
        layout.addSpacing(8)
        recent_hdr = QHBoxLayout()
        recent_hdr.setContentsMargins(22, 0, 14, 0)
        recent_hdr.addWidget(_section_label("RECENT"))
        layout.addLayout(recent_hdr)
        layout.addSpacing(6)

        self._recent_list_widget = QWidget()
        self._recent_list_layout = QVBoxLayout(self._recent_list_widget)
        self._recent_list_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_list_layout.setSpacing(2)
        self._recent_list_layout.addStretch()

        recent_scroll = QScrollArea()
        recent_scroll.setWidget(self._recent_list_widget)
        recent_scroll.setWidgetResizable(True)
        layout.addWidget(recent_scroll, 1)

        layout.addStretch()

        # Bottom open button
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(14, 0, 14, 16)
        open_btn = _btn("Open Folder", "accent")
        open_btn.clicked.connect(self._open_project)
        bl.addWidget(open_btn)
        layout.addWidget(bottom)

        self._refresh_sidebar_projects()
        return sb

    def _refresh_sidebar_projects(self):
        # Clear project list
        while self._proj_list_layout.count() > 1:
            item = self._proj_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for path in self.ws.all_paths:
            name = self.ws.name_of(path)
            is_active = (path == self.ws.active_path)
            summary = self.ws.get_project_summary(path)
            file_count = summary.get("files", 0)
            size_str = format_size(summary.get("size", 0))

            # Project card with info
            label = f"  {name}"
            if file_count > 0:
                label += f"   {file_count} files"

            btn = QPushButton(label)
            btn.setObjectName("proj_active" if is_active else "proj_btn")
            btn.setToolTip(f"{path}\n{file_count} files  |  {size_str}")
            btn.clicked.connect(partial(self._switch_project, path))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(partial(self._proj_context_menu, path, btn))
            self._proj_list_layout.insertWidget(self._proj_list_layout.count() - 1, btn)

        # Recent list
        while self._recent_list_layout.count() > 1:
            item = self._recent_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for path in self.ws.recent:
            if path in self.ws.projects:
                continue
            if not Path(path).exists():
                continue
            name = Path(path).name
            btn = QPushButton(f"  {name}")
            btn.setObjectName("proj_btn")
            btn.setToolTip(path)
            btn.clicked.connect(partial(self._open_recent_project, path))
            self._recent_list_layout.insertWidget(self._recent_list_layout.count() - 1, btn)

    def _proj_context_menu(self, path, btn, pos):
        menu = QMenu(self)
        menu.addAction("Open in IDE", lambda: self._open_project_in_ide(path))
        menu.addSeparator()
        menu.addAction("Close project", lambda: self._close_project(path))
        menu.exec(btn.mapToGlobal(pos))

    def _switch_project(self, path):
        self.ws.switch(path)
        self._on_project_changed()

    def _close_project(self, path):
        self.ws.close(path)
        self._on_project_changed()

    def _open_recent_project(self, path):
        if self.ws.open(path):
            self._on_project_changed()

    def _on_project_changed(self):
        self._refresh_sidebar_projects()
        # Tear down cached views so they rebuild for new project
        self._invalidate_all_views()
        if self.ws.has_active:
            p = self.ws.project
            self.setWindowTitle(f"{self.APP_NAME}  -  {p.name}")
            self._load_project_tools()
            if self._current_view in ("files", "vcs", "dataviz", "compare", "settings"):
                self._switch_view(self._current_view)
            else:
                self._switch_view("files")
            # Start async scan for fresh data
            self._start_async_scan()
        else:
            self.setWindowTitle(self.APP_NAME)
            self._switch_view("welcome")

    def _load_project_tools(self):
        if self.ws.has_active:
            tp = str(self.ws.project.path / ".quelldex" / "tools.json")
            self.tool_bridge.load_config(tp)
            ide_path = self.ws.project.get_ide_path()
            if ide_path:
                self.ide.custom_path = ide_path
            self.ide.detect_installed()

    # -- Async Scanning -------------------------------------------

    def _start_async_scan(self):
        """Start background file scan for active project."""
        if not self.ws.has_active:
            return
        proj = self.ws.project
        if proj._cache.is_valid:
            self._on_scan_finished(str(proj.path), proj._cache.get_files())
            return
        self._scan_pending = True
        self.status.showMessage("Scanning files...", 0)
        self._spinner.start("Scanning...")
        self._spinner.move(self.width() // 2 - 60, self.height() // 2 - 20)
        self._scanner.scan(proj)

    def _on_scan_finished(self, path: str, files: list):
        """Called when background scan completes."""
        self._scan_pending = False
        self._spinner.stop()
        if self.ws.active_path != path:
            return
        self.status.showMessage(
            f"Loaded {len(files)} files", 3000)
        if self._current_view == "files" and hasattr(self, '_file_tree'):
            self._refresh_file_tree()
        elif self._current_view == "settings":
            self._switch_view("settings")
        self._refresh_sidebar_projects()

    # -- Welcome --------------------------------------------------

    def _build_welcome(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.addStretch(2)

        diamond = _DiamondIcon()
        layout.addWidget(diamond, alignment=Qt.AlignCenter)
        layout.addSpacing(24)

        layout.addWidget(_label("Quelldex", C["fg"], 28, bold=True),
                         alignment=Qt.AlignCenter)
        layout.addSpacing(8)
        layout.addWidget(_label("Source & data, organized.", C["fg_dim"], 14),
                         alignment=Qt.AlignCenter)
        layout.addSpacing(40)

        btn = _btn("  Open Project Folder  ", "accent")
        btn.clicked.connect(self._open_project)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        layout.addSpacing(24)

        hint = _label(
            "Ctrl+O  Open    Ctrl+1-6  Views    Ctrl+Tab  Switch Project    F5  Refresh",
            C["fg_gutter"], 11)
        layout.addWidget(hint, alignment=Qt.AlignCenter)

        layout.addStretch(3)
        layout.addWidget(_label(f"v{self.VERSION}", C["fg_gutter"], 10),
                         alignment=Qt.AlignCenter)
        layout.addSpacing(16)
        return page

    # -- View Switching (cached — views built once, data refreshed) --

    def _switch_view(self, vid: str):
        self._current_view = vid

        for k, btn in self._nav_btns.items():
            btn.setObjectName("sidebar_active" if k == vid else "sidebar_btn")
            btn.setStyle(btn.style())

        if vid == "welcome":
            self.stack.setCurrentWidget(self.welcome_page)
            return

        # Settings is always accessible, even without a project
        if not self.ws.has_active and vid != "settings":
            self.stack.setCurrentWidget(self.welcome_page)
            return

        page_map = {
            "files":    self.files_page,
            "vcs":      self.vcs_page,
            "planner":  self.planner_page,
            "dataviz":  self.dataviz_page,
            "compare":  self.compare_page,
            "settings": self.settings_page,
        }
        page = page_map.get(vid, self.welcome_page)

        # Build structure only on first visit (or after project change)
        if not page.layout() or page.layout().count() == 0:
            self._build_view_structure(vid, page)

        # Lightweight data refresh
        self._refresh_view_data(vid)
        self.stack.setCurrentWidget(page)

    def _build_view_structure(self, vid: str, page: QWidget):
        """Build widget structure once. Called only on first visit."""
        builders = {
            "files":    self._build_files_view,
            "vcs":      self._build_vcs_view,
            "planner":  self._build_planner_view,
            "dataviz":  self._build_dataviz_view,
            "compare":  self._build_compare_view,
            "settings": self._build_settings_view,
        }
        builder = builders.get(vid)
        if builder:
            if not page.layout():
                QVBoxLayout(page)
            builder(page)

    def _refresh_view_data(self, vid: str):
        """Refresh only the data in an already-built view."""
        refreshers = {
            "files":    self._refresh_file_tree,
            "vcs":      self._refresh_vcs,
            "planner":  self._refresh_planner,
        }
        fn = refreshers.get(vid)
        if fn:
            fn()

    def _invalidate_all_views(self):
        """Tear down all view structures so they rebuild on next visit.
        Called when switching projects."""
        for page in [self.files_page, self.vcs_page, self.planner_page,
                     self.dataviz_page, self.compare_page,
                     self.settings_page]:
            old = page.layout()
            if old:
                while old.count():
                    item = old.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                    elif item.layout():
                        while item.layout().count():
                            sub = item.layout().takeAt(0)
                            if sub.widget():
                                sub.widget().deleteLater()

    # ============================================================
    #  FILES VIEW — collapsible folders with chevron indicators
    # ============================================================

    def _build_files_view(self, page: QWidget):
        layout = page.layout()
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(12)

        # Header row
        hdr = QHBoxLayout()
        hdr.addWidget(_label("Files", C["fg"], 18, bold=True))
        hdr.addSpacing(16)
        # Project badge (from cache — no scan)
        if self.ws.has_active:
            summary = self.ws.project.get_summary()
            if summary.get("total_files", 0) > 0:
                badge = _label(
                    f"{summary['total_files']} files  |  {format_size(summary['total_size'])}",
                    C["fg_dim"], 12)
            else:
                badge = _label("Scanning...", C["fg_dim"], 12)
            hdr.addWidget(badge)
        hdr.addStretch()

        # View mode toggle
        self._file_mode = QButtonGroup(page)
        for i, (text, _) in enumerate([
            ("Category", "cat"), ("Tree", "tree"), ("Flat", "flat")
        ]):
            rb = QRadioButton(text)
            rb.setChecked(i == 0)
            rb.toggled.connect(lambda *a: self._refresh_file_tree())
            self._file_mode.addButton(rb, i)
            hdr.addWidget(rb)
        layout.addLayout(hdr)

        # Search + collapse controls
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        self._file_search = QLineEdit()
        self._file_search.setObjectName("search")
        self._file_search.setPlaceholderText("Search files...")
        # Debounced search: 300ms delay after typing stops
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._refresh_file_tree)
        self._file_search.textChanged.connect(lambda: self._search_timer.start())
        ctrl.addWidget(self._file_search, 1)

        collapse_btn = QPushButton("  Collapse")
        collapse_btn.setObjectName("toolbar_btn")
        collapse_btn.setIcon(IconFactory.toolbar_icon("collapse_all", 18))
        collapse_btn.setIconSize(QSize(18, 18))
        collapse_btn.setToolTip("Collapse All Folders")
        collapse_btn.clicked.connect(self._collapse_all_folders)
        ctrl.addWidget(collapse_btn)

        expand_btn = QPushButton("  Expand")
        expand_btn.setObjectName("toolbar_btn")
        expand_btn.setIcon(IconFactory.toolbar_icon("expand_all", 18))
        expand_btn.setIconSize(QSize(18, 18))
        expand_btn.setToolTip("Expand All Folders")
        expand_btn.clicked.connect(self._expand_all_folders)
        ctrl.addWidget(expand_btn)
        layout.addLayout(ctrl)

        # File tree — let Qt handle expansion natively
        self._file_tree = QTreeWidget()
        # Force Fusion style: Windows native style ignores QSS branch rules
        # and draws blue connector lines. Fusion fully respects QSS.
        _fusion = QStyleFactory.create("Fusion")
        if _fusion:
            self._file_tree.setStyle(_fusion)
        # Kill the blue selection highlight on branch area —
        # Fusion paints branch bg using palette Highlight, QSS can't override it.
        # Set palette Highlight to transparent; QSS ::item:selected handles item bg.
        pal = self._file_tree.palette()
        pal.setColor(QPalette.Active, QPalette.Highlight, QColor(0, 0, 0, 0))
        pal.setColor(QPalette.Inactive, QPalette.Highlight, QColor(0, 0, 0, 0))
        pal.setColor(QPalette.Active, QPalette.HighlightedText, QColor(C["fg"]))
        pal.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor(C["fg"]))
        self._file_tree.setPalette(pal)
        self._file_tree.setHeaderLabels(["Name", "Category", "Size", "Modified"])
        self._file_tree.setColumnWidth(0, 400)
        self._file_tree.setColumnWidth(1, 110)
        self._file_tree.setColumnWidth(2, 90)
        self._file_tree.setAlternatingRowColors(False)
        self._file_tree.setIndentation(20)
        self._file_tree.setIconSize(QSize(18, 18))
        self._file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._file_tree.customContextMenuRequested.connect(self._file_context_menu)
        self._file_tree.itemDoubleClicked.connect(self._on_file_dblclick)
        self._file_tree.itemExpanded.connect(self._on_folder_expanded)
        self._file_tree.itemCollapsed.connect(self._on_folder_collapsed)
        # Single-click on text area toggles folders (branch area handled by Qt)
        self._file_tree.itemPressed.connect(self._on_tree_item_pressed)
        self._file_tree.itemClicked.connect(self._on_tree_item_clicked)
        layout.addWidget(self._file_tree, 1)
        # Note: _refresh_file_tree called by _refresh_view_data, not here

    # anti-double-toggle: track expand state at press time
    _press_was_expanded = None

    def _on_tree_item_pressed(self, item, column):
        """Record expand state before Qt processes the branch-area click."""
        key = item.data(0, Qt.UserRole + 1)
        if key:
            self._press_was_expanded = item.isExpanded()
        else:
            self._press_was_expanded = None

    def _get_collapsed_set(self) -> set:
        p = self.ws.active_path or ""
        if p not in self._tree_collapsed:
            self._tree_collapsed[p] = set()
        return self._tree_collapsed[p]

    def _on_folder_expanded(self, item):
        key = item.data(0, Qt.UserRole + 1)
        if key:
            self._get_collapsed_set().discard(key)

    def _on_folder_collapsed(self, item):
        key = item.data(0, Qt.UserRole + 1)
        if key:
            self._get_collapsed_set().add(key)

    def _on_tree_item_clicked(self, item, column):
        """Toggle folder on text-area click. Skip if Qt already toggled via branch arrow."""
        key = item.data(0, Qt.UserRole + 1)
        if not key:
            return  # not a folder
        # If expand state changed between press and click, Qt handled it (branch arrow click)
        if self._press_was_expanded is not None and item.isExpanded() != self._press_was_expanded:
            return  # Qt already toggled — don't double-toggle
        # User clicked text area — toggle manually
        item.setExpanded(not item.isExpanded())

    def _collapse_all_folders(self):
        if not hasattr(self, '_file_tree'):
            return
        self._file_tree.collapseAll()
        cs = self._get_collapsed_set()
        def _walk(item):
            key = item.data(0, Qt.UserRole + 1)
            if key:
                cs.add(key)
            for i in range(item.childCount()):
                _walk(item.child(i))
        for i in range(self._file_tree.topLevelItemCount()):
            _walk(self._file_tree.topLevelItem(i))

    def _expand_all_folders(self):
        if not hasattr(self, '_file_tree'):
            return
        self._get_collapsed_set().clear()
        self._file_tree.expandAll()

    # Max items to render in tree (prevents UI freeze)
    TREE_MAX_ITEMS = 2000
    # Process events interval during tree build
    _BATCH_SIZE = 80
    # Auto-collapse all categories when above this threshold
    _AUTO_COLLAPSE_THRESHOLD = 800

    def _refresh_file_tree(self):
        if not self.ws.has_active or not hasattr(self, '_file_tree'):
            return
        tree = self._file_tree
        proj = self.ws.project

        # Use cached files (fast) or show loading
        if not proj._cache.is_valid:
            tree.setUpdatesEnabled(False)
            tree.clear()
            loading = QTreeWidgetItem(tree, ["    Loading...", "", "", ""])
            loading.setForeground(0, QColor(C["fg_dim"]))
            loading.setIcon(0, IconFactory.loading_icon())
            tree.setUpdatesEnabled(True)
            self._start_async_scan()
            return

        files = proj.get_all_files()
        query = self._file_search.text().lower().strip() if hasattr(self, '_file_search') else ""
        if query:
            files = [f for f in files if query in f["path"].lower() or query in f["category"].lower()]

        total_count = len(files)
        capped = total_count > self.TREE_MAX_ITEMS and not query
        if capped:
            files = files[:self.TREE_MAX_ITEMS]

        # Show spinner for large sets
        large = len(files) > 500
        if large:
            self._spinner.start("Building tree...")
            self._spinner.move(self.width() // 2 - 60, self.height() // 2 - 20)

        # Suspend repaints during bulk update
        tree.setUpdatesEnabled(False)
        tree.clear()

        mode_id = self._file_mode.checkedId() if hasattr(self, '_file_mode') else 0
        mode = ["category", "tree", "flat"][mode_id]
        collapsed = self._get_collapsed_set()
        count = 0

        # Auto-collapse all categories on first load of large sets
        auto_collapse = len(files) > self._AUTO_COLLAPSE_THRESHOLD and not query

        if mode == "category":
            groups = {}
            for f in files:
                groups.setdefault(f["category"], []).append(f)
            for cat in sorted(groups.keys()):
                info = get_category_info(cat)
                folder_key = f"cat:{cat}"
                if auto_collapse:
                    collapsed.add(folder_key)
                is_expanded = folder_key not in collapsed
                parent = QTreeWidgetItem(tree, [
                    f"  {cat}  ({len(groups[cat])})", "", "", ""])
                parent.setIcon(0, IconFactory.category_icon(info["color"]))
                parent.setData(0, Qt.UserRole + 1, folder_key)
                parent.setForeground(0, QColor(info["color"]))
                parent.setExpanded(is_expanded)
                for f in groups[cat]:
                    item = QTreeWidgetItem(parent, [
                        f"  {f['path']}", cat,
                        format_size(f["size"]), format_time(f["mtime"])])
                    item.setIcon(0, IconFactory.file_icon(info["color"]))
                    item.setData(0, Qt.UserRole, f["path"])
                    count += 1
                    if count % self._BATCH_SIZE == 0:
                        QApplication.processEvents()

        elif mode == "tree":
            nodes = {}
            for f in files:
                parts = Path(f["path"]).parts
                for i, part in enumerate(parts[:-1]):
                    folder_path = str(Path(*parts[:i + 1]))
                    if folder_path not in nodes:
                        parent_path = str(Path(*parts[:i])) if i > 0 else ""
                        parent_node = nodes.get(parent_path, tree)
                        fkey = f"dir:{folder_path}"
                        is_exp = fkey not in collapsed
                        if isinstance(parent_node, QTreeWidget):
                            node = QTreeWidgetItem(tree, [f"  {part}", "", "", ""])
                        else:
                            node = QTreeWidgetItem(parent_node, [f"  {part}", "", "", ""])
                        node.setData(0, Qt.UserRole + 1, fkey)
                        node.setExpanded(is_exp)
                        node.setForeground(0, QColor(C["fg_dim"]))
                        nodes[folder_path] = node

                parent_path = str(Path(*parts[:-1])) if len(parts) > 1 else ""
                parent_node = nodes.get(parent_path, tree)
                cat_info = get_category_info(f["category"])
                if isinstance(parent_node, QTreeWidget):
                    item = QTreeWidgetItem(tree, [
                        f"  {f['name']}", f["category"],
                        format_size(f["size"]), format_time(f["mtime"])])
                else:
                    item = QTreeWidgetItem(parent_node, [
                        f"  {f['name']}", f["category"],
                        format_size(f["size"]), format_time(f["mtime"])])
                item.setIcon(0, IconFactory.file_icon(cat_info["color"]))
                item.setData(0, Qt.UserRole, f["path"])
                count += 1
                if count % self._BATCH_SIZE == 0:
                    QApplication.processEvents()
        else:
            for f in files:
                cat_info = get_category_info(f["category"])
                item = QTreeWidgetItem(tree, [
                    f"  {f['path']}", f["category"],
                    format_size(f["size"]), format_time(f["mtime"])])
                item.setIcon(0, IconFactory.file_icon(cat_info["color"]))
                item.setData(0, Qt.UserRole, f["path"])
                count += 1
                if count % self._BATCH_SIZE == 0:
                    QApplication.processEvents()

        # Cap notice
        if capped:
            hint = QTreeWidgetItem(tree, [
                f"    ... {total_count - self.TREE_MAX_ITEMS} more files (use search to filter)",
                "", "", ""])
            hint.setForeground(0, QColor(C["fg_gutter"]))

        # Resume repaints + hide spinner
        tree.setUpdatesEnabled(True)
        if large:
            self._spinner.stop()
        self.status.showMessage(
            f"{total_count} files" + (f" (showing {self.TREE_MAX_ITEMS})" if capped else ""),
            3000)

    def _on_file_dblclick(self, item, col):
        fp = item.data(0, Qt.UserRole)
        if not fp:
            # Toggle folder
            item.setExpanded(not item.isExpanded())
            return
        full = str(self.ws.project.path / fp)
        if is_data_file(fp):
            self._open_dataviz_for(full)
        elif is_code_file(fp):
            self._open_file_in_ide(full)
        else:
            self.ide._open_system_default(full)

    def _file_context_menu(self, pos):
        item = self._file_tree.itemAt(pos)
        menu = QMenu(self)
        if item:
            fp = item.data(0, Qt.UserRole)
            folder_key = item.data(0, Qt.UserRole + 1)
            if fp:
                full = str(self.ws.project.path / fp)
                if is_code_file(fp):
                    menu.addAction("Open in IDE", lambda: self._open_file_in_ide(full))
                if is_data_file(fp):
                    menu.addAction("Visualize data", lambda: self._open_dataviz_for(full))
                menu.addAction("Open with system default",
                               lambda: self.ide._open_system_default(full))
                menu.addSeparator()
                # Compare actions
                menu.addAction("Compare with another file...",
                               lambda: self._compare_with_file(fp))
                if self.ws.vcs:
                    menu.addAction("Compare with previous version...",
                                   lambda: self._compare_with_version(fp))
                menu.addSeparator()
                menu.addAction("Shelf: Move", lambda: self._shelf_add("move", fp))
                menu.addAction("Shelf: Copy", lambda: self._shelf_add("copy", fp))
                menu.addAction("Shelf: Delete", lambda: self._shelf_add("delete", fp))
            elif folder_key:
                is_exp = item.isExpanded()
                menu.addAction("Collapse" if is_exp else "Expand",
                               lambda: item.setExpanded(not is_exp))
                menu.addAction("Collapse All Below", lambda: self._collapse_subtree(item))
        menu.addSeparator()
        menu.addAction("Refresh", self._refresh_file_tree)
        menu.exec(self._file_tree.viewport().mapToGlobal(pos))

    def _collapse_subtree(self, item):
        """Recursively collapse all children."""
        cs = self._get_collapsed_set()
        def _walk(it):
            key = it.data(0, Qt.UserRole + 1)
            if key:
                it.setExpanded(False)
                cs.add(key)
            for i in range(it.childCount()):
                _walk(it.child(i))
        _walk(item)

    def _shelf_add(self, action, fp):
        dest = ""
        if action in ("move", "copy"):
            dest, ok = QInputDialog.getText(self, "Target path", "Enter target relative path:")
            if not ok or not dest:
                return
        self.ws.project.add_to_shelf(action, fp, dest)
        self.ws.project.save()
        self.status.showMessage(f"Added to shelf: {action} {fp}", 3000)

    # ============================================================
    #  VCS VIEW
    # ============================================================

    def _build_vcs_view(self, page: QWidget):
        layout = page.layout()
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_label("Version Control", C["fg"], 18, bold=True))
        hdr.addStretch()
        hdr.addWidget(_label("Branch:", C["fg_dim"], 12))
        self._branch_combo = QComboBox()
        self._branch_combo.setMinimumWidth(160)
        self._branch_combo.currentTextChanged.connect(self._on_branch_switch)
        hdr.addWidget(self._branch_combo)
        layout.addLayout(hdr)

        # Actions row
        ab = QHBoxLayout()
        ab.setSpacing(8)
        for text, obj, fn in [
            ("Commit", "accent", self._do_commit),
            ("New Branch", "", self._do_create_branch),
            ("Merge", "", self._do_merge),
            ("Tag", "", self._do_create_tag),
            ("Delete Branch", "ghost", self._do_delete_branch),
        ]:
            btn = _btn(text, obj)
            btn.clicked.connect(fn)
            ab.addWidget(btn)
        ab.addStretch()
        layout.addLayout(ab)

        # Working changes card
        changes_grp = QGroupBox("  Working Changes  ")
        cg_l = QVBoxLayout(changes_grp)
        self._changes_text = QTextEdit()
        self._changes_text.setReadOnly(True)
        self._changes_text.setMaximumHeight(110)
        self._changes_text.setFont(QFont(MONO_FAMILY.split(",")[0].strip(), 10))
        cg_l.addWidget(self._changes_text)
        layout.addWidget(changes_grp)

        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # History tab
        hw = QWidget()
        hl = QVBoxLayout(hw)
        hl.setContentsMargins(0, 10, 0, 0)
        self._hist_tree = QTreeWidget()
        self._hist_tree.setHeaderLabels(["Message", "Branch", "Author", "Time", "ID"])
        self._hist_tree.setColumnWidth(0, 340)
        self._hist_tree.setColumnWidth(1, 110)
        self._hist_tree.setColumnWidth(2, 70)
        self._hist_tree.setColumnWidth(3, 150)
        self._hist_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._hist_tree.customContextMenuRequested.connect(self._history_context_menu)
        hl.addWidget(self._hist_tree)
        tabs.addTab(hw, "  History  ")

        # Tags tab
        tw = QWidget()
        tl = QVBoxLayout(tw)
        tl.setContentsMargins(0, 10, 0, 0)
        self._tags_tree = QTreeWidget()
        self._tags_tree.setHeaderLabels(["Tag", "Description", "Commit", "Created"])
        self._tags_tree.setColumnWidth(0, 160)
        self._tags_tree.setColumnWidth(1, 320)
        self._tags_tree.itemDoubleClicked.connect(self._on_tag_dblclick)
        tl.addWidget(self._tags_tree)
        tabs.addTab(tw, "  Tags  ")

        # Diff tab
        dw = QWidget()
        dl = QVBoxLayout(dw)
        dl.setContentsMargins(0, 10, 0, 0)
        self._diff_text = QTextEdit()
        self._diff_text.setReadOnly(True)
        self._diff_text.setFont(QFont(MONO_FAMILY.split(",")[0].strip(), 10))
        dl.addWidget(self._diff_text)
        tabs.addTab(dw, "  Diff  ")
        # Note: _refresh_vcs called by _refresh_view_data, not here

    def _refresh_vcs(self):
        vcs = self.ws.vcs
        if not vcs or not hasattr(self, '_hist_tree'):
            return

        # Show spinner + keep UI alive during change detection
        self._spinner.start("Checking changes...")
        self._spinner.move(self.width() // 2 - 60, self.height() // 2 - 20)
        QApplication.processEvents()

        branches = vcs.get_branches()
        current = vcs.get_current_branch()
        self._branch_combo.blockSignals(True)
        self._branch_combo.clear()
        for b in branches:
            self._branch_combo.addItem(b["name"])
        if current:
            self._branch_combo.setCurrentText(current)
        self._branch_combo.blockSignals(False)

        changes = vcs.get_working_changes()
        QApplication.processEvents()

        na, nm, nr = len(changes["added"]), len(changes["modified"]), len(changes["removed"])
        self._changes_text.clear()
        if na + nm + nr == 0:
            self._changes_text.setPlainText("  No changes")
        else:
            lines = []
            if na: lines.append(f"  + {na} added")
            if nm: lines.append(f"  ~ {nm} modified")
            if nr: lines.append(f"  - {nr} removed")
            for fp in list(changes["added"])[:5]:   lines.append(f"    + {fp}")
            for fp in list(changes["modified"])[:5]: lines.append(f"    ~ {fp}")
            for fp in list(changes["removed"])[:5]:  lines.append(f"    - {fp}")
            self._changes_text.setPlainText("\n".join(lines))

        self._hist_tree.setUpdatesEnabled(False)
        self._hist_tree.clear()
        for c in vcs.get_history():
            QTreeWidgetItem(self._hist_tree, [
                c["message"], c["branch"], c["author"],
                format_time(c["timestamp"]), c["id"]])
        self._hist_tree.setUpdatesEnabled(True)

        self._tags_tree.setUpdatesEnabled(False)
        self._tags_tree.clear()
        for t in vcs.get_tags():
            QTreeWidgetItem(self._tags_tree, [
                t["name"], t["description"], t["commit_id"],
                format_time(t["created_at"])])
        self._tags_tree.setUpdatesEnabled(True)

        self._spinner.stop()

    def _on_branch_switch(self, name):
        if name and self.ws.vcs:
            self.ws.vcs.switch_branch(name)
            self._refresh_vcs()

    def _do_commit(self):
        msg, ok = QInputDialog.getText(self, "Commit", "Commit message:")
        if ok and msg and self.ws.vcs:
            cid = self.ws.vcs.commit(msg)
            if cid:
                self.ws.project.invalidate_cache()
                self._refresh_vcs()
                self.status.showMessage(f"Committed: {cid[:12]}", 3000)
            else:
                QMessageBox.information(self, "Info", "Nothing to commit")

    def _do_create_branch(self):
        name, ok = QInputDialog.getText(self, "New Branch", "Branch name:")
        if ok and name and self.ws.vcs:
            if self.ws.vcs.create_branch(name):
                self._refresh_vcs()
            else:
                QMessageBox.warning(self, "Error", "Branch already exists")

    def _do_delete_branch(self):
        name, ok = QInputDialog.getText(self, "Delete Branch", "Branch name to delete:")
        if ok and name and self.ws.vcs:
            if self.ws.vcs.delete_branch(name):
                self._refresh_vcs()
            else:
                QMessageBox.warning(self, "Error", "Cannot delete current branch")

    def _do_merge(self):
        vcs = self.ws.vcs
        branches = [b["name"] for b in vcs.get_branches()]
        current = vcs.get_current_branch()
        others = [b for b in branches if b != current]
        if not others:
            QMessageBox.information(self, "Info", "No other branches to merge")
            return
        name, ok = QInputDialog.getItem(self, "Merge",
                                         f"Merge into '{current}':", others, 0, False)
        if ok and name:
            result = vcs.merge_branch(name)
            if result["success"]:
                msg = f"Merged. {result['files_merged']} files."
                if result["conflicts"]:
                    msg += f"\n{len(result['conflicts'])} conflicts (used source version)"
                QMessageBox.information(self, "Merge Result", msg)
                self._refresh_vcs()
            else:
                QMessageBox.critical(self, "Error", result.get("error", "Unknown error"))

    def _do_create_tag(self):
        name, ok = QInputDialog.getText(self, "Create Tag", "Tag name:")
        if not ok or not name: return
        desc, _ = QInputDialog.getText(self, "Description", "Description (optional):")
        if self.ws.vcs.create_tag(name, description=desc or ""):
            self._refresh_vcs()
        else:
            QMessageBox.warning(self, "Error", "Tag exists or no commits")

    def _history_context_menu(self, pos):
        sel = self._hist_tree.selectedItems()
        menu = QMenu(self)
        if len(sel) == 2:
            a, b = sel[0].text(4), sel[1].text(4)
            menu.addAction("Diff these two", lambda: self._show_diff(a, b))
        elif len(sel) == 1:
            cid = sel[0].text(4)
            menu.addAction("Restore to this", lambda: self._restore_commit(cid))
            menu.addAction("Tag this commit", lambda: self._tag_commit(cid))
        menu.exec(self._hist_tree.viewport().mapToGlobal(pos))

    def _show_diff(self, cid_a, cid_b):
        diff = self.ws.vcs.diff_commits(cid_a, cid_b)
        self._diff_text.clear()
        cur = self._diff_text.textCursor()
        hdr_fmt = QTextCharFormat()
        hdr_fmt.setForeground(QColor(C["cyan"]))
        hdr_fmt.setFontWeight(QFont.Bold)
        add_fmt = QTextCharFormat()
        add_fmt.setForeground(QColor(C["green"]))
        add_fmt.setBackground(QColor("#1a2a1a"))
        rm_fmt = QTextCharFormat()
        rm_fmt.setForeground(QColor(C["red"]))
        rm_fmt.setBackground(QColor("#2a1a1a"))
        info_fmt = QTextCharFormat()
        info_fmt.setForeground(QColor(C["fg_dim"]))

        cur.insertText(f"Diff: {cid_a[:10]} vs {cid_b[:10]}\n\n", hdr_fmt)
        for fp in diff["added"]:
            cur.insertText(f"+ Added: {fp}\n", add_fmt)
        for fp in diff["removed"]:
            cur.insertText(f"- Removed: {fp}\n", rm_fmt)
        for fp, info in diff["modified"].items():
            cur.insertText(f"\n-- {fp} --\n", hdr_fmt)
            lines = self.ws.vcs.diff_file_content(info["old"]["hash"], info["new"]["hash"])
            for line in lines:
                if line.startswith("+"): cur.insertText(line + "\n", add_fmt)
                elif line.startswith("-"): cur.insertText(line + "\n", rm_fmt)
                elif line.startswith("@@"): cur.insertText(line + "\n", info_fmt)
                else: cur.insertText(line + "\n")

    def _restore_commit(self, cid):
        if QMessageBox.question(self, "Restore",
            "Restore to this commit? Unsaved changes will be lost.") == QMessageBox.Yes:
            snap = self.ws.vcs.get_commit_snapshot(cid)
            if snap:
                self.ws.vcs._restore_snapshot(snap)
                self._refresh_vcs()

    def _tag_commit(self, cid):
        name, ok = QInputDialog.getText(self, "Tag", "Tag name:")
        if ok and name:
            self.ws.vcs.create_tag(name, commit_id=cid)
            self._refresh_vcs()

    def _on_tag_dblclick(self, item, col):
        name = item.text(0)
        if QMessageBox.question(self, "Restore",
            f"Restore to tag '{name}'?") == QMessageBox.Yes:
            self.ws.vcs.goto_tag(name)
            self._refresh_vcs()

    # ============================================================
    #  DATA VIZ VIEW
    # ============================================================

    def _build_dataviz_view(self, page: QWidget):
        layout = page.layout()
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(12)

        hdr = QHBoxLayout()
        hdr.addWidget(_label("Data Visualization", C["fg"], 18, bold=True))
        hdr.addStretch()
        load_btn = _btn("Load File", "accent")
        load_btn.clicked.connect(self._load_data_dialog)
        hdr.addWidget(load_btn)
        proj_btn = _btn("From Project")
        proj_btn.clicked.connect(self._load_data_from_project)
        hdr.addWidget(proj_btn)
        clr_btn = _btn("Clear", "ghost")
        clr_btn.clicked.connect(self._clear_datasets)
        hdr.addWidget(clr_btn)
        layout.addLayout(hdr)

        # Chips
        self._chips_layout = QHBoxLayout()
        self._chips_layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(self._chips_layout)
        self._refresh_chips()

        # Controls | Chart
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        # Left: controls
        ctrl = QFrame()
        ctrl.setObjectName("float_panel")
        ctrl.setFixedWidth(260)
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(10)

        cl.addWidget(_label("Column", C["fg"], 13, bold=True))
        self._viz_col = QComboBox()
        self._viz_col.currentTextChanged.connect(self._on_viz_col_change)
        cl.addWidget(self._viz_col)

        cl.addWidget(_label("2nd Column (scatter)", C["fg_dim"], 11))
        self._viz_col2 = QComboBox()
        cl.addWidget(self._viz_col2)

        cl.addSpacing(6)
        cl.addWidget(_label("Chart Type", C["fg"], 13, bold=True))
        self._chart_type_group = QButtonGroup(page)
        charts = [("Auto", "auto"), ("Histogram", "histogram"), ("Line", "line"),
                  ("Bar", "bar"), ("Scatter", "scatter"), ("Correlation", "corr"),
                  ("Multi-file Line", "multi_line")]
        for i, (text, _) in enumerate(charts):
            rb = QRadioButton(text)
            rb.setChecked(i == 0)
            rb.toggled.connect(lambda *a: self._render_chart())
            self._chart_type_group.addButton(rb, i)
            cl.addWidget(rb)

        cl.addSpacing(6)
        draw_btn = _btn("Draw", "accent")
        draw_btn.clicked.connect(self._render_chart)
        cl.addWidget(draw_btn)

        cl.addSpacing(6)
        cl.addWidget(_label("Statistics", C["fg"], 13, bold=True))
        self._stats_text = QTextEdit()
        self._stats_text.setReadOnly(True)
        self._stats_text.setFont(QFont(MONO_FAMILY.split(",")[0].strip(), 10))
        cl.addWidget(self._stats_text, 1)
        splitter.addWidget(ctrl)

        # Right: chart
        self._chart = ChartWidget()
        splitter.addWidget(self._chart)
        splitter.setSizes([260, 800])

    def _refresh_chips(self):
        if not hasattr(self, '_chips_layout'):
            return
        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for i, name in enumerate(self.loaded_datasets):
            chip = TagChip(name, PALETTE[i % len(PALETTE)])
            self._chips_layout.addWidget(chip)
        if not self.loaded_datasets:
            self._chips_layout.addWidget(_label("No datasets loaded", C["fg_dim"], 12))

    def _load_data_dialog(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Load data file", "",
            "Data files (*.csv *.tsv *.json *.jsonl *.xml *.yaml *.yml *.log *.txt)")
        if fp:
            ds = load_data_file(fp)
            if ds["columns"]:
                self.loaded_datasets[ds["name"]] = ds
                self._refresh_chips()
                self._populate_viz_combos()
            else:
                QMessageBox.information(self, "Info", "Cannot parse as table data")

    def _load_data_from_project(self):
        if not self.ws.has_active:
            return
        data_files = [f for f in self.ws.project.get_all_files() if is_data_file(f["path"])]
        if not data_files:
            QMessageBox.information(self, "Info", "No data files found in project")
            return
        names = [f["path"] for f in data_files]
        name, ok = QInputDialog.getItem(self, "Load", "Select data file:", names, 0, False)
        if ok and name:
            full = str(self.ws.project.path / name)
            ds = load_data_file(full)
            if ds["columns"]:
                self.loaded_datasets[ds["name"]] = ds
                self._refresh_chips()
                self._populate_viz_combos()

    def _clear_datasets(self):
        self.loaded_datasets.clear()
        self._refresh_chips()
        if hasattr(self, '_chart'):
            self._chart.clear()
        if hasattr(self, '_viz_col'):
            self._viz_col.clear()
            self._viz_col2.clear()
        if hasattr(self, '_stats_text'):
            self._stats_text.clear()

    def _populate_viz_combos(self):
        if not hasattr(self, '_viz_col'):
            return
        self._viz_col.clear()
        self._viz_col2.clear()
        for ds in self.loaded_datasets.values():
            for col in ds["columns"]:
                self._viz_col.addItem(f"{ds['name']}: {col}")
                self._viz_col2.addItem(f"{ds['name']}: {col}")

    def _render_chart(self):
        if not self.loaded_datasets or not hasattr(self, '_chart'):
            return
        chart_types = ["auto", "histogram", "line", "bar", "scatter", "corr", "multi_line"]
        ct = chart_types[self._chart_type_group.checkedId()]
        col_text = self._viz_col.currentText()
        if not col_text:
            return
        parts = col_text.split(": ", 1)
        if len(parts) < 2:
            return
        ds_name, col = parts
        ds = self.loaded_datasets.get(ds_name)
        if not ds:
            return
        if ct == "auto":
            st = compute_column_stats(ds, col)
            ct = "histogram" if st.get("numeric") else "bar"
        if ct == "histogram":
            data = histogram_data(ds, col)
            self._chart.set_chart("histogram", data, f"{col} Distribution")
        elif ct == "line":
            data = line_data(ds, col)
            self._chart.set_chart("line", data, col)
        elif ct == "bar":
            data = bar_data(ds, col)
            self._chart.set_chart("bar", data, col)
        elif ct == "scatter":
            col2_text = self._viz_col2.currentText()
            if col2_text:
                p2 = col2_text.split(": ", 1)
                if len(p2) == 2:
                    ds2 = self.loaded_datasets.get(p2[0])
                    if ds2:
                        data = scatter_data(ds, col, ds2, p2[1])
                        self._chart.set_chart("scatter", data, f"{col} vs {p2[1]}")
        elif ct == "corr":
            data = correlation_matrix(ds)
            self._chart.set_chart("corr", data, "Correlation Matrix")
        elif ct == "multi_line":
            data = multi_line_data(list(self.loaded_datasets.values()), col)
            self._chart.set_chart("multi_line", data, f"{col} Across Files")

    def _on_viz_col_change(self, text):
        if not text or not hasattr(self, '_stats_text'):
            return
        parts = text.split(": ", 1)
        if len(parts) < 2:
            return
        ds = self.loaded_datasets.get(parts[0])
        if ds:
            st = compute_column_stats(ds, parts[1])
            lines = [f"Column: {parts[1]}", f"Count:   {st.get('count', 0)}",
                     f"Nulls:   {st.get('null_count', 0)}"]
            if st.get("numeric"):
                lines += [f"\nMean:    {st.get('mean', 0):.4f}", f"Std:     {st.get('std', 0):.4f}",
                          f"Min:     {st.get('min', 0):.4f}", f"Median:  {st.get('median', 0):.4f}",
                          f"Max:     {st.get('max', 0):.4f}", f"Q1:      {st.get('q1', 0):.4f}",
                          f"Q3:      {st.get('q3', 0):.4f}"]
            else:
                lines.append(f"\nDistinct: {st.get('distinct_count', 0)}")
                for val, cnt in st.get("top_values", [])[:10]:
                    lines.append(f"  {val}: {cnt}")
            self._stats_text.setPlainText("\n".join(lines))

    def _open_dataviz_for(self, filepath):
        ds = load_data_file(filepath)
        if ds["columns"]:
            self.loaded_datasets[ds["name"]] = ds
            self._switch_view("dataviz")
        else:
            QMessageBox.information(self, "Info", "Cannot parse as table data")

    # ============================================================
    #  COMPARE VIEW — side-by-side file diff
    # ============================================================

    def _build_compare_view(self, page: QWidget):
        layout = page.layout()
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_label("Compare", C["fg"], 18, bold=True))
        hdr.addStretch()
        layout.addLayout(hdr)

        # Controls row
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        ctrl.addWidget(_label("Left:", C["fg_dim"], 12))
        self._cmp_left = QComboBox()
        self._cmp_left.setMinimumWidth(260)
        ctrl.addWidget(self._cmp_left, 1)

        ctrl.addWidget(_label("Right:", C["fg_dim"], 12))
        self._cmp_right = QComboBox()
        self._cmp_right.setMinimumWidth(260)
        ctrl.addWidget(self._cmp_right, 1)

        run_btn = _btn("Compare", "accent")
        run_btn.clicked.connect(self._run_compare)
        ctrl.addWidget(run_btn)
        layout.addLayout(ctrl)

        # Version compare row
        ver_ctrl = QHBoxLayout()
        ver_ctrl.setSpacing(8)

        ver_ctrl.addWidget(_label("Compare file with version:", C["fg_dim"], 12))
        self._cmp_ver_file = QComboBox()
        self._cmp_ver_file.setMinimumWidth(260)
        ver_ctrl.addWidget(self._cmp_ver_file, 1)

        self._cmp_ver_commit = QComboBox()
        self._cmp_ver_commit.setMinimumWidth(200)
        ver_ctrl.addWidget(self._cmp_ver_commit)

        ver_btn = _btn("Compare Version", "ghost")
        ver_btn.clicked.connect(self._run_version_compare)
        ver_ctrl.addWidget(ver_btn)
        layout.addLayout(ver_ctrl)

        # Diff viewer
        self._diff_viewer = DiffViewer()
        layout.addWidget(self._diff_viewer, 1)

        # Populate combos
        self._populate_compare_combos()

    def _populate_compare_combos(self):
        """Fill compare dropdowns with project files and commits."""
        if not self.ws.has_active:
            return
        files = self.ws.project.get_all_files()
        text_exts = set()
        for cat_info in __import__('src.core.project', fromlist=['CATEGORIES']).CATEGORIES.values():
            text_exts |= cat_info["ext"]
        # Filter to text-likely files (not images)
        img_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
                    ".ico", ".tiff", ".psd", ".ai", ".eps"}
        text_files = [f["path"] for f in files if
                      Path(f["path"]).suffix.lower() not in img_exts]

        for combo in [self._cmp_left, self._cmp_right, self._cmp_ver_file]:
            combo.clear()
            for fp in text_files:
                combo.addItem(fp)

        # Populate commits
        if hasattr(self, '_cmp_ver_commit') and self.ws.vcs:
            self._cmp_ver_commit.clear()
            for c in self.ws.vcs.get_history(limit=50):
                label = f"{c['id'][:10]}  {c['message'][:40]}"
                self._cmp_ver_commit.addItem(label, c['id'])

    def _run_compare(self):
        """Compare two files side by side."""
        if not self.ws.has_active:
            return
        left_path = self._cmp_left.currentText()
        right_path = self._cmp_right.currentText()
        if not left_path or not right_path:
            return

        left_full = self.ws.project.path / left_path
        right_full = self.ws.project.path / right_path

        try:
            left_lines = left_full.read_text(encoding='utf-8', errors='replace').splitlines()
            right_lines = right_full.read_text(encoding='utf-8', errors='replace').splitlines()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot read files: {e}")
            return

        self._diff_viewer.set_diff(left_lines, right_lines, left_path, right_path)
        self.status.showMessage(
            f"Comparing: {left_path} vs {right_path}", 3000)

    def _run_version_compare(self):
        """Compare current file with its version from a commit."""
        if not self.ws.has_active or not self.ws.vcs:
            return
        file_path = self._cmp_ver_file.currentText()
        commit_id = self._cmp_ver_commit.currentData()
        if not file_path or not commit_id:
            return

        # Read current version
        full = self.ws.project.path / file_path
        try:
            current_lines = full.read_text(encoding='utf-8', errors='replace').splitlines()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot read file: {e}")
            return

        # Read old version from VCS snapshot
        snapshot = self.ws.vcs.get_commit_snapshot(commit_id)
        if not snapshot or file_path.replace("\\", "/") not in snapshot:
            QMessageBox.information(self, "Info",
                                    f"File not found in commit {commit_id[:10]}")
            return

        file_info = snapshot[file_path.replace("\\", "/")]
        old_content = self.ws.vcs._read_object(file_info["hash"])
        if old_content is None:
            QMessageBox.warning(self, "Error", "Cannot read object from VCS storage")
            return

        try:
            old_lines = old_content.decode('utf-8', errors='replace').splitlines()
        except Exception:
            old_lines = ["[Binary content]"]

        commit_label = f"{file_path} @ {commit_id[:10]}"
        self._diff_viewer.set_diff(old_lines, current_lines,
                                    commit_label, f"{file_path} (current)")
        self.status.showMessage(
            f"Comparing: {file_path} current vs {commit_id[:10]}", 3000)

    def _compare_with_file(self, fp: str):
        """Context menu: compare this file with another (switch to Compare view)."""
        self._switch_view("compare")
        if hasattr(self, '_cmp_left'):
            idx = self._cmp_left.findText(fp)
            if idx >= 0:
                self._cmp_left.setCurrentIndex(idx)

    def _compare_with_version(self, fp: str):
        """Context menu: compare file with VCS version (switch to Compare view)."""
        self._switch_view("compare")
        if hasattr(self, '_cmp_ver_file'):
            idx = self._cmp_ver_file.findText(fp)
            if idx >= 0:
                self._cmp_ver_file.setCurrentIndex(idx)

    # ============================================================
    #  PLANNER VIEW — Kanban board with branch-scoped tasks
    # ============================================================

    PRIORITY_COLORS = {
        "critical": "#d96070",
        "high":     "#d0a050",
        "medium":   "#6580c8",
        "low":      "#555a68",
    }
    STATUS_LABELS = [
        ("todo",     "To Do"),
        ("progress", "In Progress"),
        ("done",     "Done"),
    ]

    def _build_planner_view(self, page: QWidget):
        layout = page.layout()
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_label("Planner", C["fg"], 18, bold=True))
        hdr.addStretch()

        # Scope filter
        hdr.addWidget(_label("Scope:", C["fg_dim"], 12))
        self._plan_scope = QComboBox()
        self._plan_scope.setMinimumWidth(160)
        self._plan_scope.currentIndexChanged.connect(lambda: self._refresh_planner())
        hdr.addWidget(self._plan_scope)

        # Add task button
        add_btn = _btn("+ New Task", "accent")
        add_btn.clicked.connect(self._planner_add_task)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        # Stats bar
        self._plan_stats = _label("", C["fg_dim"], 11)
        layout.addWidget(self._plan_stats)

        # Kanban columns
        cols = QHBoxLayout()
        cols.setSpacing(12)
        self._plan_cols = {}
        for status_id, status_label in self.STATUS_LABELS:
            col = QFrame()
            col.setObjectName("plan_col")
            cl = QVBoxLayout(col)
            cl.setContentsMargins(10, 10, 10, 10)
            cl.setSpacing(6)

            # Column header with count
            col_hdr = QHBoxLayout()
            lbl = _label(status_label, C["fg"], 13, bold=True)
            col_hdr.addWidget(lbl)
            count_lbl = _label("0", C["fg_gutter"], 11)
            col_hdr.addWidget(count_lbl)
            col_hdr.addStretch()
            cl.addLayout(col_hdr)

            # Scrollable task list
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setFrameShape(QFrame.NoFrame)
            task_widget = QWidget()
            task_layout = QVBoxLayout(task_widget)
            task_layout.setContentsMargins(0, 0, 0, 0)
            task_layout.setSpacing(6)
            task_layout.addStretch()
            scroll.setWidget(task_widget)
            cl.addWidget(scroll, 1)

            cols.addWidget(col, 1)
            self._plan_cols[status_id] = {
                "frame": col, "layout": task_layout,
                "count_lbl": count_lbl, "scroll": scroll,
            }
        layout.addLayout(cols, 1)

        # Merge bar
        merge_bar = QHBoxLayout()
        merge_bar.setSpacing(8)
        merge_bar.addWidget(_label("Merge tasks:", C["fg_dim"], 12))
        merge_bar.addWidget(_label("from", C["fg_dim"], 12))
        self._plan_merge_src = QComboBox()
        self._plan_merge_src.setMinimumWidth(140)
        merge_bar.addWidget(self._plan_merge_src)
        merge_bar.addWidget(_label("into", C["fg_dim"], 12))
        self._plan_merge_dst = QComboBox()
        self._plan_merge_dst.setMinimumWidth(140)
        merge_bar.addWidget(self._plan_merge_dst)
        merge_btn = _btn("Merge")
        merge_btn.clicked.connect(self._planner_merge)
        merge_bar.addWidget(merge_btn)
        merge_bar.addStretch()
        layout.addLayout(merge_bar)

        self._refresh_planner()

    def _refresh_planner(self):
        if not self.ws.has_active or not hasattr(self, '_plan_cols'):
            return
        proj = self.ws.project

        # Update scope dropdown
        self._plan_scope.blockSignals(True)
        old_scope = self._plan_scope.currentData()
        self._plan_scope.clear()
        self._plan_scope.addItem("All Tasks", None)
        self._plan_scope.addItem("Shared (all branches)", "*")
        if self.ws.vcs:
            for b in self.ws.vcs.get_branches():
                self._plan_scope.addItem(f"Branch: {b['name']}", b['name'])
        # Restore selection
        for i in range(self._plan_scope.count()):
            if self._plan_scope.itemData(i) == old_scope:
                self._plan_scope.setCurrentIndex(i)
                break
        self._plan_scope.blockSignals(False)

        # Update merge combos
        if hasattr(self, '_plan_merge_src'):
            for combo in (self._plan_merge_src, self._plan_merge_dst):
                combo.clear()
                combo.addItem("Shared", "*")
                if self.ws.vcs:
                    for b in self.ws.vcs.get_branches():
                        combo.addItem(b['name'], b['name'])

        # Get filtered tasks
        scope = self._plan_scope.currentData()
        tasks = proj.get_tasks(scope=scope)

        # Sort: critical > high > medium > low, then by updated_at desc
        prio_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda t: (prio_order.get(t.get("priority"), 9), -t.get("updated_at", 0)))

        # Clear columns
        for sid, col in self._plan_cols.items():
            lay = col["layout"]
            while lay.count() > 1:
                item = lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Populate columns
        counts = {"todo": 0, "progress": 0, "done": 0}
        for t in tasks:
            status = t.get("status", "todo")
            if status not in self._plan_cols:
                continue
            card = self._make_task_card(t)
            col = self._plan_cols[status]
            col["layout"].insertWidget(col["layout"].count() - 1, card)
            counts[status] = counts.get(status, 0) + 1

        # Update counts
        for sid, col in self._plan_cols.items():
            col["count_lbl"].setText(str(counts.get(sid, 0)))

        # Stats
        total = sum(counts.values())
        done = counts.get("done", 0)
        pct = int(done / total * 100) if total > 0 else 0
        scope_txt = self._plan_scope.currentText()
        self._plan_stats.setText(
            f"{total} tasks  ·  {pct}% complete  ·  Showing: {scope_txt}")

    def _make_task_card(self, task: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("task_card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(5)

        # Top row: priority dot + title
        top = QHBoxLayout()
        top.setSpacing(8)
        pcolor = self.PRIORITY_COLORS.get(task.get("priority", "medium"), C["fg_dim"])
        dot = _label("●", pcolor, 10)
        dot.setFixedWidth(14)
        top.addWidget(dot)
        title = _label(task["title"], C["fg"], 13, bold=True)
        title.setWordWrap(True)
        top.addWidget(title, 1)
        cl.addLayout(top)

        # Description (if any)
        desc = task.get("description", "").strip()
        if desc:
            d = _label(desc[:120] + ("..." if len(desc) > 120 else ""),
                        C["fg_dark"], 11)
            d.setWordWrap(True)
            cl.addWidget(d)

        # Meta row: scope + tags + due
        meta_parts = []
        scope = task.get("scope", "*")
        scope_txt = "shared" if scope == "*" else scope
        meta_parts.append(scope_txt)
        if task.get("tags"):
            meta_parts.append(" ".join(f"#{t}" for t in task["tags"][:3]))
        if task.get("due_date"):
            meta_parts.append(f"due {task['due_date']}")
        meta_parts.append(task.get("priority", "medium"))
        meta = _label("  ·  ".join(meta_parts), C["fg_gutter"], 10)
        cl.addWidget(meta)

        # Action buttons row
        btns = QHBoxLayout()
        btns.setSpacing(4)

        status = task.get("status", "todo")
        tid = task["id"]

        # Move left/right buttons
        if status == "progress":
            b = _btn("← Todo", "ghost")
            b.clicked.connect(lambda _, t=tid: self._planner_move(t, "todo"))
            btns.addWidget(b)
            b = _btn("Done →", "ghost")
            b.clicked.connect(lambda _, t=tid: self._planner_move(t, "done"))
            btns.addWidget(b)
        elif status == "todo":
            b = _btn("Start →", "ghost")
            b.clicked.connect(lambda _, t=tid: self._planner_move(t, "progress"))
            btns.addWidget(b)
        elif status == "done":
            b = _btn("← Reopen", "ghost")
            b.clicked.connect(lambda _, t=tid: self._planner_move(t, "progress"))
            btns.addWidget(b)

        btns.addStretch()

        # Edit / Delete
        edit = _btn("Edit", "ghost")
        edit.clicked.connect(lambda _, t=tid: self._planner_edit_task(t))
        btns.addWidget(edit)

        delete = _btn("×", "ghost")
        delete.setFixedWidth(30)
        delete.clicked.connect(lambda _, t=tid: self._planner_delete(t))
        btns.addWidget(delete)

        cl.addLayout(btns)
        return card

    def _planner_add_task(self):
        if not self.ws.has_active:
            return
        dlg = QInputDialog(self)
        dlg.setWindowTitle("New Task")
        dlg.setLabelText("Task title:")
        dlg.setInputMode(QInputDialog.TextInput)
        if not dlg.exec():
            return
        title = dlg.textValue().strip()
        if not title:
            return

        # Determine scope
        scope = self._plan_scope.currentData() or "*"

        # Priority dialog
        prio, ok = QInputDialog.getItem(
            self, "Priority", "Select priority:",
            ["medium", "high", "critical", "low"], 0, False)
        if not ok:
            prio = "medium"

        # Optional description
        desc, _ = QInputDialog.getText(
            self, "Description", "Description (optional):")

        self.ws.project.add_task(title, scope=scope, priority=prio,
                                  description=desc or "")
        self._refresh_planner()
        self.status.showMessage(f"Task added: {title}", 3000)

    def _planner_move(self, task_id: str, new_status: str):
        if not self.ws.has_active:
            return
        self.ws.project.update_task(task_id, status=new_status)
        self._refresh_planner()

    def _planner_delete(self, task_id: str):
        if not self.ws.has_active:
            return
        r = QMessageBox.question(self, "Delete Task",
                                  "Delete this task permanently?",
                                  QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            self.ws.project.delete_task(task_id)
            self._refresh_planner()

    def _planner_edit_task(self, task_id: str):
        if not self.ws.has_active:
            return
        proj = self.ws.project
        task = None
        for t in proj.get_tasks():
            if t["id"] == task_id:
                task = t
                break
        if not task:
            return

        title, ok = QInputDialog.getText(self, "Edit Task", "Title:", text=task["title"])
        if not ok or not title.strip():
            return
        desc, _ = QInputDialog.getText(self, "Edit Task", "Description:",
                                         text=task.get("description", ""))
        prio, _ = QInputDialog.getItem(
            self, "Edit Task", "Priority:",
            ["medium", "high", "critical", "low"],
            ["medium", "high", "critical", "low"].index(task.get("priority", "medium")),
            False)

        # Scope selection
        scopes = ["* (shared)"]
        scope_vals = ["*"]
        if self.ws.vcs:
            for b in self.ws.vcs.get_branches():
                scopes.append(b['name'])
                scope_vals.append(b['name'])
        cur_idx = 0
        if task.get("scope") in scope_vals:
            cur_idx = scope_vals.index(task["scope"])
        scope_choice, _ = QInputDialog.getItem(
            self, "Edit Task", "Scope:", scopes, cur_idx, False)
        scope = scope_vals[scopes.index(scope_choice)] if scope_choice in scopes else "*"

        # Due date
        due, _ = QInputDialog.getText(self, "Edit Task", "Due date (YYYY-MM-DD or empty):",
                                        text=task.get("due_date", ""))

        # Tags
        tags_str, _ = QInputDialog.getText(
            self, "Edit Task", "Tags (comma-separated):",
            text=", ".join(task.get("tags", [])))
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        proj.update_task(task_id, title=title.strip(), description=desc or "",
                          priority=prio, scope=scope, due_date=due or "", tags=tags)
        self._refresh_planner()
        self.status.showMessage(f"Task updated: {title.strip()}", 3000)

    def _planner_merge(self):
        if not self.ws.has_active:
            return
        src = self._plan_merge_src.currentData()
        dst = self._plan_merge_dst.currentData()
        if not src or not dst:
            return
        if src == dst:
            QMessageBox.information(self, "Merge", "Source and target are the same.")
            return
        merged = self.ws.project.merge_tasks_from_branch(src, dst)
        self._refresh_planner()
        self.status.showMessage(f"Merged {merged} tasks from {src} into {dst}", 3000)

    # ============================================================
    #  SETTINGS VIEW
    # ============================================================

    def _build_settings_view(self, page: QWidget):
        layout = page.layout()
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(12)
        layout.addWidget(_label("Settings", C["fg"], 18, bold=True))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setSpacing(16)

        # Theme selector
        theme_grp = QGroupBox("  Appearance  ")
        theme_l = QHBoxLayout(theme_grp)
        theme_l.addWidget(_label("Theme:", C["fg_dark"], 12))
        theme_l.addSpacing(8)
        current = get_current_theme()
        self._theme_group = QButtonGroup(theme_grp)
        for i, (tid, tlabel) in enumerate(get_theme_names()):
            rb = QRadioButton(f"  {tlabel}  ")
            rb.setChecked(tid == current)
            rb.toggled.connect(lambda checked, t=tid: self._apply_theme(t) if checked else None)
            self._theme_group.addButton(rb, i)
            theme_l.addWidget(rb)
        theme_l.addStretch()
        il.addWidget(theme_grp)

        # IDE
        ide_grp = QGroupBox("  IDE Integration  ")
        ide_l = QVBoxLayout(ide_grp)
        self.ide.detect_installed()
        for a in self.ide.get_available():
            ide_l.addWidget(_label(f"  {a['name']}  ({a['path']})", C["green"], 12))
        if not self.ide.get_available():
            ide_l.addWidget(_label("  No IDE detected", C["orange"], 12))
        ide_l.addWidget(_label("Custom IDE path:", C["fg_dim"], 12))
        row = QHBoxLayout()
        self._ide_path_edit = QLineEdit(
            self.ws.project.get_ide_path() if self.ws.has_active else "")
        row.addWidget(self._ide_path_edit)
        browse = _btn("Browse")
        browse.clicked.connect(self._browse_ide_path)
        row.addWidget(browse)
        save = _btn("Save")
        save.clicked.connect(self._save_ide_path)
        row.addWidget(save)
        ide_l.addLayout(row)
        il.addWidget(ide_grp)

        # External tools
        tools_grp = QGroupBox("  External Tools  ")
        tl = QVBoxLayout(tools_grp)
        tl.addWidget(_label("Registered tools open matching files automatically.", C["fg_dim"], 12))
        tr = QHBoxLayout()
        for text, fn in [
            ("MarkVue", lambda: self._register_tool("markvue", [".md", ".markdown"], "MarkVue")),
            ("H5Lens", lambda: self._register_tool("h5lens", [".h5", ".hdf5"], "H5Lens")),
            ("Custom...", self._register_custom_tool),
        ]:
            btn = _btn(text)
            btn.clicked.connect(fn)
            tr.addWidget(btn)
        tr.addStretch()
        tl.addLayout(tr)
        for t in self.tool_bridge.get_registered_tools():
            exts = ", ".join(t.get("supported_ext", []))
            tl.addWidget(_label(f"  {t['name']}  ->  {exts}", C["green"], 12))
        il.addWidget(tools_grp)

        # Project info
        if self.ws.has_active:
            info_grp = QGroupBox("  Project Info  ")
            info_l = QVBoxLayout(info_grp)
            summary = self.ws.project.get_summary()
            vcs_stats = self.ws.vcs.get_stats() if self.ws.vcs else {}
            info_l.addWidget(_label(
                f"Path:     {self.ws.project.path}\n"
                f"Files:    {summary['total_files']}    Size: {format_size(summary['total_size'])}\n"
                f"Code:     {summary.get('code_files', 0)}    Data: {summary.get('data_files', 0)}\n"
                f"Commits:  {vcs_stats.get('commits', 0)}    Branches: {vcs_stats.get('branches', 0)}    "
                f"Tags: {vcs_stats.get('tags', 0)}\n"
                f"VCS size: {format_size(vcs_stats.get('storage_bytes', 0))}",
                C["fg_dark"], 12, mono=True))
            il.addWidget(info_grp)

        # All open projects summary
        if len(self.ws.all_paths) > 1:
            ws_grp = QGroupBox("  Workspace Overview  ")
            ws_l = QVBoxLayout(ws_grp)
            for path in self.ws.all_paths:
                name = self.ws.name_of(path)
                s = self.ws.get_project_summary(path)
                active_mark = "  *" if path == self.ws.active_path else "   "
                ws_l.addWidget(_label(
                    f"{active_mark} {name}  -  {s.get('files', 0)} files  |  "
                    f"{format_size(s.get('size', 0))}", C["fg_dark"], 12, mono=True))
            il.addWidget(ws_grp)

        # Shelf
        if self.ws.has_active and self.ws.project.data.get("shelf"):
            shelf_grp = QGroupBox("  Shelf  ")
            sl = QVBoxLayout(shelf_grp)
            for op in self.ws.project.data["shelf"]:
                act = {"move": "Move", "copy": "Copy", "delete": "Delete"}.get(op["action"], "?")
                txt = f"{act}: {op['source']}"
                if op["dest"]: txt += f" -> {op['dest']}"
                sl.addWidget(_label(txt, C["fg_dark"], 12))
            sr = QHBoxLayout()
            ex_btn = _btn("Execute Shelf", "accent")
            ex_btn.clicked.connect(self._execute_shelf)
            sr.addWidget(ex_btn)
            cl_btn = _btn("Clear", "ghost")
            cl_btn.clicked.connect(self._clear_shelf)
            sr.addWidget(cl_btn)
            sr.addStretch()
            sl.addLayout(sr)
            il.addWidget(shelf_grp)

        il.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

    def _browse_ide_path(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select IDE executable")
        if p: self._ide_path_edit.setText(p)

    def _save_ide_path(self):
        if self.ws.has_active:
            self.ws.project.set_ide_path(self._ide_path_edit.text())
            self.ws.project.save()
            self.ide.custom_path = self._ide_path_edit.text()
            self.ide.detect_installed()
            self.status.showMessage("IDE path saved", 3000)

    def _register_tool(self, tid, exts, name):
        p, _ = QFileDialog.getOpenFileName(self, f"Select {name} executable")
        if p:
            self.tool_bridge.register_tool(tid, {
                "name": name, "executable": p, "supported_ext": exts,
                "protocol": "cli", "args_template": "{exe} {file}"})
            if self.ws.has_active:
                self.tool_bridge.save_config(
                    str(self.ws.project.path / ".quelldex" / "tools.json"))
            self._switch_view("settings")

    def _register_custom_tool(self):
        name, ok = QInputDialog.getText(self, "Tool Name", "Name:")
        if not ok or not name: return
        exts, ok = QInputDialog.getText(self, "Extensions", "Supported extensions (comma-separated):")
        if not ok or not exts: return
        p, _ = QFileDialog.getOpenFileName(self, f"Select {name} executable")
        if p:
            tid = name.lower().replace(" ", "_")
            ext_list = [e.strip() for e in exts.split(",") if e.strip()]
            self.tool_bridge.register_tool(tid, {
                "name": name, "executable": p, "supported_ext": ext_list,
                "protocol": "cli", "args_template": "{exe} {file}"})
            if self.ws.has_active:
                self.tool_bridge.save_config(
                    str(self.ws.project.path / ".quelldex" / "tools.json"))
            self._switch_view("settings")

    def _execute_shelf(self):
        if self.ws.has_active:
            results = self.ws.project.execute_shelf()
            self.ws.project.save()
            self.ws.project.invalidate_cache()
            msg = "\n".join(f"{'OK' if r[0] == 'ok' else 'FAIL'} {r[1]}" for r in results)
            QMessageBox.information(self, "Result", msg or "No operations")
            self._switch_view("settings")

    def _clear_shelf(self):
        if self.ws.has_active:
            self.ws.project.clear_shelf()
            self.ws.project.save()
            self._switch_view("settings")

    # -- Theme Switching ------------------------------------------

    def _apply_theme(self, theme_id: str):
        """Apply new theme and refresh entire UI."""
        set_theme(theme_id)
        # Clear icon cache (colors changed)
        IconFactory.clear_cache()
        # Reload QSS
        from src.ui.theme import QSS as NEW_QSS
        QApplication.instance().setStyleSheet(NEW_QSS)
        # Rebuild all views with new colors
        self._invalidate_all_views()
        self._switch_view(self._current_view or "settings")
        # Persist choice
        settings = QSettings("Quelldex", "Quelldex")
        settings.setValue("theme", theme_id)
        self.status.showMessage(f"Theme: {theme_id.title()}", 2000)

    # ============================================================
    #  Project & IDE
    # ============================================================

    def _open_project(self):
        path = QFileDialog.getExistingDirectory(self, "Select project folder")
        if not path: return
        if self.ws.open(path):
            self._on_project_changed()
            self.status.showMessage(f"Opened: {path}", 5000)

    def _open_in_ide(self):
        if not self.ws.has_active: return
        avail = self.ide.get_available()
        if avail:
            self.ide.open_folder(str(self.ws.project.path), avail[0]["id"])
        else:
            QMessageBox.information(self, "Info", "No IDE detected. Configure in Settings.")

    def _open_project_in_ide(self, path):
        avail = self.ide.get_available()
        if avail:
            self.ide.open_folder(path, avail[0]["id"])

    def _open_file_in_ide(self, filepath):
        avail = self.ide.get_available()
        if avail:
            self.ide.open_file(filepath, avail[0]["id"])
        else:
            self.ide._open_system_default(filepath)

    # -- Shortcuts ------------------------------------------------

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_project)
        QShortcut(QKeySequence("Ctrl+S"), self, self._do_commit_safe)
        QShortcut(QKeySequence("F5"), self, self._force_refresh)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._switch_view("files"))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._switch_view("vcs"))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._switch_view("planner"))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self._switch_view("dataviz"))
        QShortcut(QKeySequence("Ctrl+5"), self, lambda: self._switch_view("compare"))
        QShortcut(QKeySequence("Ctrl+6"), self, lambda: self._switch_view("settings"))
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._cycle_project)

    def _do_commit_safe(self):
        if self.ws.vcs:
            self._do_commit()

    def _force_refresh(self):
        """F5: Invalidate cache, tear down views, force full rescan."""
        if self.ws.has_active:
            self.ws.project.invalidate_cache()
            self._invalidate_all_views()
            self._start_async_scan()
            if self._current_view:
                self._switch_view(self._current_view)

    def _cycle_project(self):
        """Ctrl+Tab: cycle through open projects."""
        paths = self.ws.all_paths
        if len(paths) < 2:
            return
        cur = self.ws.active_path
        idx = paths.index(cur) if cur in paths else -1
        next_idx = (idx + 1) % len(paths)
        self.ws.switch(paths[next_idx])
        self._on_project_changed()
        self.status.showMessage(f"Switched to: {self.ws.name_of(paths[next_idx])}", 2000)
