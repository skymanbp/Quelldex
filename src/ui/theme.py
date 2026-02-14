"""
Quelldex Theme v5 — Multi-theme system with runtime switching
Dark · Light · Midnight palettes · QSS generator
Branch arrow PNGs generated at runtime for native Qt tree expansion
"""

import time as _time
import tempfile, os, struct, zlib

# ---- Minimal PNG generator (no Qt dependency needed) ----

_arrow_dir = None   # temp directory for arrow PNGs


def _write_png(path: str, width: int, height: int, rows: list):
    """Write a minimal RGBA PNG file from raw pixel rows.
    Each row is a list of (r, g, b, a) tuples of length width."""
    def _chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    raw = b""
    for row in rows:
        raw += b"\x00"  # filter byte
        for r, g, b, a in row:
            raw += struct.pack("BBBB", r, g, b, a)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    out = b"\x89PNG\r\n\x1a\n"
    out += _chunk(b"IHDR", ihdr)
    out += _chunk(b"IDAT", zlib.compress(raw))
    out += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(out)


def _generate_branch_arrows(fg_hex: str) -> tuple:
    """Generate ▸ (closed), ▾ (open), and 1x1 transparent PNGs.
    Returns (closed_path, open_path, transparent_path).
    Arrows are drawn small in center of 24x24 canvas to avoid stretch-blur."""
    global _arrow_dir
    if _arrow_dir is None:
        _arrow_dir = tempfile.mkdtemp(prefix="quelldex_arrows_")

    h = fg_hex.lstrip("#")
    cr, cg, cb = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    S = 24
    T = (0, 0, 0, 0)
    F = (cr, cg, cb, 200)

    def _line(grid, x0, y0, x1, y1):
        """Bresenham line — single pixel, no thickening."""
        dx = abs(x1 - x0); dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            if 0 <= x0 < S and 0 <= y0 < S:
                grid[y0][x0] = F
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy: err -= dy; x0 += sx
            if e2 < dx: err += dx; y0 += sy

    # ▸ Right chevron (closed) — small, centered
    closed = [[T] * S for _ in range(S)]
    #   from (9,7) -> (14,12) -> (9,17)
    _line(closed, 9, 7, 14, 12)
    _line(closed, 14, 12, 9, 17)

    # ▾ Down chevron (open) — small, centered
    opened = [[T] * S for _ in range(S)]
    #   from (7,9) -> (12,14) -> (17,9)
    _line(opened, 7, 9, 12, 14)
    _line(opened, 12, 14, 17, 9)

    cp = os.path.join(_arrow_dir, "closed.png")
    op = os.path.join(_arrow_dir, "open.png")
    tp = os.path.join(_arrow_dir, "transparent.png")
    _write_png(cp, S, S, closed)
    _write_png(op, S, S, opened)
    _write_png(tp, 1, 1, [[(0, 0, 0, 0)]])
    return cp, op, tp


# ================================================================
#  Palette Definitions
# ================================================================

THEMES = {
    "dark": {
        "label": "Dark",
        "bg":           "#17181c",
        "bg_dark":      "#111215",
        "bg_float":     "#1c1d22",
        "bg_highlight": "#232429",
        "bg_sidebar":   "#141518",
        "bg_input":     "#1c1d22",
        "bg_hover":     "#27282f",
        "bg_selected":  "#2a3d6e",
        "bg_card":      "#1e1f25",
        "bg_card_hover":"#242530",
        "fg":           "#cdd1dc",
        "fg_dark":      "#a8adb8",
        "fg_dim":       "#555a68",
        "fg_gutter":    "#333742",
        "fg_muted":     "#3e4350",
        "border":       "#252730",
        "border_focus": "#6580c8",
        "border_subtle":"#1e2028",
        "accent":       "#6580c8",
        "accent_soft":  "#2e3a5e",
        "accent_dim":   "#3c4a70",
        "accent2":      "#9b82cc",
        "green":        "#7fb86a",
        "red":          "#d96070",
        "orange":       "#d0a050",
        "yellow":       "#ccbc60",
        "cyan":         "#58aec0",
        "teal":         "#5cb898",
        "magenta":      "#9b82cc",
        "blue":         "#6580c8",
        "blue2":        "#5faac8",
        "scrollbar":    "#2c303a",
        "scrollbar_bg": "#17181c",
        # Diff colors
        "diff_add_bg":  "#1a2e1a",
        "diff_add_fg":  "#7fb86a",
        "diff_del_bg":  "#2e1a1a",
        "diff_del_fg":  "#d96070",
        "diff_hdr_fg":  "#58aec0",
    },
    "light": {
        "label": "Light",
        "bg":           "#f5f6f8",
        "bg_dark":      "#e8eaef",
        "bg_float":     "#ffffff",
        "bg_highlight": "#eceef2",
        "bg_sidebar":   "#ebedf2",
        "bg_input":     "#ffffff",
        "bg_hover":     "#e0e3ea",
        "bg_selected":  "#c5d2f0",
        "bg_card":      "#f0f1f5",
        "bg_card_hover":"#e4e6ec",
        "fg":           "#2c2f3a",
        "fg_dark":      "#4a4e5c",
        "fg_dim":       "#8890a0",
        "fg_gutter":    "#c0c5d0",
        "fg_muted":     "#a0a6b4",
        "border":       "#d4d7e0",
        "border_focus": "#5070b8",
        "border_subtle":"#e0e2e8",
        "accent":       "#5070b8",
        "accent_soft":  "#dce3f4",
        "accent_dim":   "#b8c6e8",
        "accent2":      "#7b60b8",
        "green":        "#3d8c30",
        "red":          "#c44050",
        "orange":       "#b88030",
        "yellow":       "#a89820",
        "cyan":         "#2888a0",
        "teal":         "#309878",
        "magenta":      "#7b60b8",
        "blue":         "#5070b8",
        "blue2":        "#3888b0",
        "scrollbar":    "#c0c5d0",
        "scrollbar_bg": "#f5f6f8",
        "diff_add_bg":  "#ddf4dd",
        "diff_add_fg":  "#2a7020",
        "diff_del_bg":  "#fde0e0",
        "diff_del_fg":  "#b03030",
        "diff_hdr_fg":  "#2888a0",
    },
    "midnight": {
        "label": "Midnight",
        "bg":           "#0d0e12",
        "bg_dark":      "#08090c",
        "bg_float":     "#121318",
        "bg_highlight": "#181a20",
        "bg_sidebar":   "#0a0b0f",
        "bg_input":     "#121318",
        "bg_hover":     "#1c1e26",
        "bg_selected":  "#1e2d55",
        "bg_card":      "#13141a",
        "bg_card_hover":"#1a1c24",
        "fg":           "#b8bcc8",
        "fg_dark":      "#8a90a0",
        "fg_dim":       "#444858",
        "fg_gutter":    "#282c38",
        "fg_muted":     "#343848",
        "border":       "#1c1e28",
        "border_focus": "#5570b0",
        "border_subtle":"#151720",
        "accent":       "#5570b0",
        "accent_soft":  "#1e2848",
        "accent_dim":   "#303c60",
        "accent2":      "#8068b0",
        "green":        "#60a050",
        "red":          "#c05060",
        "orange":       "#b89040",
        "yellow":       "#b0a840",
        "cyan":         "#4898a8",
        "teal":         "#48a080",
        "magenta":      "#8068b0",
        "blue":         "#5570b0",
        "blue2":        "#4890b0",
        "scrollbar":    "#222630",
        "scrollbar_bg": "#0d0e12",
        "diff_add_bg":  "#102010",
        "diff_add_fg":  "#60a050",
        "diff_del_bg":  "#201010",
        "diff_del_fg":  "#c05060",
        "diff_hdr_fg":  "#4898a8",
    },
}

# ================================================================
#  Active State (module-level, switchable at runtime)
# ================================================================

_current_theme = "dark"
C = dict(THEMES["dark"])

PALETTE = [
    "#6580c8", "#7fb86a", "#d96070", "#d0a050", "#9b82cc",
    "#58aec0", "#d0a050", "#5cb898", "#cdd1dc", "#5faac8",
]

FONT_FAMILY = "Segoe UI, Inter, -apple-system, Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif"
MONO_FAMILY = "Cascadia Code, JetBrains Mono, Consolas, Menlo, monospace"


def get_current_theme() -> str:
    return _current_theme


def set_theme(name: str):
    """Switch active theme. Updates C dict, regenerates arrow PNGs, rebuilds QSS."""
    global _current_theme, C, QSS
    if name not in THEMES:
        return
    _current_theme = name
    C.clear()
    C.update(THEMES[name])
    # Generate branch arrow PNGs using current theme's fg_dim color
    arrow_closed, arrow_open, arrow_trans = _generate_branch_arrows(C["fg_dim"])
    QSS = _build_qss(C, arrow_closed, arrow_open, arrow_trans)


def get_theme_names() -> list:
    return [(k, v["label"]) for k, v in THEMES.items()]


# ================================================================
#  QSS Generator
# ================================================================

def _build_qss(c: dict, arrow_closed: str = "", arrow_open: str = "", arrow_trans: str = "") -> str:
    # Normalize paths for QSS url() — must use forward slashes
    ac = arrow_closed.replace("\\", "/")
    ao = arrow_open.replace("\\", "/")
    at = arrow_trans.replace("\\", "/")
    return f"""
/* === Foundation === */
* {{ margin: 0; padding: 0; }}
QWidget {{
    background-color: {c['bg']};
    color: {c['fg']};
    font-family: {FONT_FAMILY};
    font-size: 13px;
    border: none;
    outline: none;
}}
QMainWindow {{ background-color: {c['bg']}; }}

/* === Sidebar === */
QFrame#sidebar {{
    background-color: {c['bg_sidebar']};
    border-right: 1px solid {c['border_subtle']};
}}
QFrame#sidebar_divider {{
    background-color: {c['border']};
    max-height: 1px;
    margin: 6px 20px;
}}

/* === Cards / Panels === */
QFrame#card, QFrame#float_panel {{
    background-color: {c['bg_float']};
    border: 1px solid {c['border']};
    border-radius: 10px;
}}
QGroupBox {{
    background-color: {c['bg_float']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    margin-top: 18px;
    padding: 22px 16px 16px 16px;
    color: {c['fg_dim']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {c['fg_dim']};
}}
QLabel {{
    background: transparent;
    border: none;
    padding: 0;
    color: {c['fg']};
}}

/* === Buttons === */
QPushButton {{
    background-color: {c['bg_highlight']};
    color: {c['fg_dark']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: {c['bg_hover']};
    color: {c['fg']};
    border-color: {c['fg_gutter']};
}}
QPushButton:pressed {{ background-color: {c['bg_selected']}; }}
QPushButton:disabled {{
    color: {c['fg_gutter']};
    background-color: {c['bg_dark']};
}}
QPushButton#accent {{
    background-color: {c['accent']};
    color: #f0f0f5;
    border: none;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 22px;
}}
QPushButton#accent:hover {{ background-color: {c['accent_dim']}; }}
QPushButton#ghost {{
    background: transparent;
    color: {c['fg_dim']};
    border: 1px solid transparent;
    padding: 7px 14px;
}}
QPushButton#ghost:hover {{
    background-color: {c['bg_highlight']};
    color: {c['fg']};
}}
/* Planner — Kanban columns */
QFrame#plan_col {{
    background-color: {c['bg_dark']};
    border: 1px solid {c['border']};
    border-radius: 10px;
}}
/* Planner — Task cards */
QFrame#task_card {{
    background-color: {c['bg_float']};
    border: 1px solid {c['border']};
    border-radius: 8px;
}}
QFrame#task_card:hover {{
    border-color: {c['fg_gutter']};
    background-color: {c['bg_hover']};
}}
QPushButton#icon_btn {{
    background: transparent;
    color: {c['fg_dim']};
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 3px;
    min-height: 0;
    min-width: 0;
}}
QPushButton#icon_btn:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border']};
    color: {c['fg']};
}}
QPushButton#toolbar_btn {{
    background-color: {c['bg_highlight']};
    color: {c['fg_dim']};
    border: 1px solid {c['border']};
    border-radius: 7px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 500;
    min-height: 14px;
}}
QPushButton#toolbar_btn:hover {{
    background-color: {c['bg_hover']};
    color: {c['fg']};
    border-color: {c['fg_gutter']};
}}

/* Sidebar nav */
QPushButton#sidebar_btn {{
    background: transparent;
    color: {c['fg_dim']};
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    margin: 1px 12px;
}}
QPushButton#sidebar_btn:hover {{
    background-color: {c['bg_highlight']};
    color: {c['fg']};
}}
QPushButton#sidebar_active {{
    background-color: {c['accent_soft']};
    color: {c['fg']};
    border: none;
    border-left: 3px solid {c['accent']};
    border-radius: 0 8px 8px 0;
    padding: 9px 18px 9px 15px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    margin: 1px 12px 1px 0;
}}

/* Project cards */
QPushButton#proj_btn {{
    background: {c['bg_card']};
    color: {c['fg_dark']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 8px 14px;
    text-align: left;
    font-size: 12px;
    margin: 2px 10px;
}}
QPushButton#proj_btn:hover {{
    background-color: {c['bg_card_hover']};
    color: {c['fg']};
    border-color: {c['fg_gutter']};
}}
QPushButton#proj_active {{
    background-color: {c['accent_soft']};
    color: {c['fg']};
    border: 1px solid {c['accent_dim']};
    border-left: 3px solid {c['accent']};
    border-radius: 0 8px 8px 0;
    padding: 8px 14px 8px 11px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    margin: 2px 10px 2px 0;
}}

/* === Input === */
QLineEdit {{
    background-color: {c['bg_input']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 13px;
    selection-background-color: {c['bg_selected']};
}}
QLineEdit:focus {{ border-color: {c['border_focus']}; }}
QLineEdit#search {{
    background-color: {c['bg_highlight']};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 13px;
}}
QLineEdit#search:focus {{ border-color: {c['fg_gutter']}; }}
QTextEdit, QPlainTextEdit {{
    background-color: {c['bg_float']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 12px;
    font-family: {MONO_FAMILY};
    font-size: 12px;
    selection-background-color: {c['bg_selected']};
}}
QComboBox {{
    background-color: {c['bg_input']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 8px 14px;
    min-width: 110px;
}}
QComboBox:hover {{ border-color: {c['fg_gutter']}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['fg_dim']};
    margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {c['bg_float']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    selection-background-color: {c['bg_selected']};
    outline: none;
    padding: 4px;
}}

/* === Tree / List / Table === */
QTreeWidget, QTreeView, QListView, QTableView {{
    background-color: transparent;
    alternate-background-color: transparent;
    color: {c['fg']};
    border: none;
    outline: none;
    font-size: 13px;
}}
QTreeWidget::item, QTreeView::item, QListView::item {{
    padding: 5px 10px;
    border: none;
    border-radius: 6px;
    margin: 1px 4px;
    min-height: 22px;
}}
QTreeWidget::item:selected, QTreeView::item:selected {{
    background-color: {c['accent_soft']};
    color: {c['fg']};
}}
QTreeWidget::item:hover, QTreeView::item:hover {{
    background-color: {c['bg_highlight']};
}}
QTreeWidget::branch {{
    background: transparent;
    border: none;
    border-image: url({at}) 0;
    image: none;
    selection-background-color: transparent;
}}
QTreeWidget::branch:selected {{
    background: transparent;
    border-image: url({at}) 0;
}}
QTreeWidget::branch:has-siblings:!adjoins-item {{
    border-image: url({at}) 0;
    image: none;
}}
QTreeWidget::branch:has-siblings:adjoins-item {{
    border-image: url({at}) 0;
    image: none;
}}
QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
    border-image: url({at}) 0;
    image: none;
}}
QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {{
    border-image: url({at}) 0;
    image: url({ac});
    padding: 2px;
}}
QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {{
    border-image: url({at}) 0;
    image: url({ao});
    padding: 2px;
}}
QTreeWidget::branch:selected:has-children:!has-siblings:closed,
QTreeWidget::branch:selected:closed:has-children:has-siblings {{
    background: transparent;
    border-image: url({at}) 0;
    image: url({ac});
    padding: 2px;
}}
QTreeWidget::branch:selected:open:has-children:!has-siblings,
QTreeWidget::branch:selected:open:has-children:has-siblings {{
    background: transparent;
    border-image: url({at}) 0;
    image: url({ao});
    padding: 2px;
}}
QTreeWidget::branch:selected:has-siblings:!adjoins-item,
QTreeWidget::branch:selected:has-siblings:adjoins-item,
QTreeWidget::branch:selected:!has-children:!has-siblings:adjoins-item {{
    background: transparent;
    border-image: url({at}) 0;
    image: none;
}}
QHeaderView::section {{
    background-color: {c['bg_highlight']};
    color: {c['fg_dim']};
    border: none;
    border-right: 1px solid {c['border']};
    border-bottom: 1px solid {c['border']};
    padding: 8px 14px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* === Tabs === */
QTabWidget::pane {{
    background-color: {c['bg']};
    border: 1px solid {c['border']};
    border-radius: 0 0 10px 10px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {c['fg_dim']};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 22px;
    margin-right: 4px;
    font-size: 12px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {c['accent']};
    border-bottom: 2px solid {c['accent']};
}}
QTabBar::tab:hover:!selected {{
    color: {c['fg']};
    border-bottom: 2px solid {c['fg_gutter']};
}}

/* === Scrollbar === */
QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {c['scrollbar']};
    border-radius: 3px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['fg_dim']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 7px;
    margin: 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {c['scrollbar']};
    border-radius: 3px;
    min-width: 40px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* === Splitter === */
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 6px; }}
QSplitter::handle:vertical {{ height: 6px; }}
QSplitter::handle:hover {{ background-color: {c['border']}; border-radius: 2px; }}

/* === Misc === */
QToolTip {{
    background-color: {c['bg_float']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}}
QRadioButton, QCheckBox {{ background: transparent; spacing: 8px; }}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 2px solid {c['fg_gutter']};
    background: {c['bg_input']};
    border-radius: 4px;
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
}}
QMenu {{
    background-color: {c['bg_float']};
    color: {c['fg']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 28px 8px 14px;
    border-radius: 6px;
    font-size: 13px;
}}
QMenu::item:selected {{ background-color: {c['accent_soft']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 12px; }}
QStatusBar {{
    background-color: {c['bg_dark']};
    color: {c['fg_dim']};
    border-top: 1px solid {c['border_subtle']};
    font-size: 12px;
    padding: 3px 14px;
}}
QScrollArea {{ border: none; background: transparent; }}
"""


# Build initial QSS
_initial_closed, _initial_open, _initial_trans = _generate_branch_arrows(C["fg_dim"])
QSS = _build_qss(C, _initial_closed, _initial_open, _initial_trans)


# ================================================================
#  Utility Formatters
# ================================================================

def format_size(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}" if u != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"

def format_time(ts: float) -> str:
    try:
        return _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ts))
    except Exception:
        return "-"

def format_time_relative(ts: float) -> str:
    d = _time.time() - ts
    if d < 60: return "just now"
    if d < 3600: return f"{int(d // 60)}m ago"
    if d < 86400: return f"{int(d // 3600)}h ago"
    if d < 604800: return f"{int(d // 86400)}d ago"
    return format_time(ts)
