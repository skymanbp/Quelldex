"""
Quelldex Widgets v4 — Polished custom PySide6 widgets
ChartWidget (QPainter) · Tag chips · Stat cards · Folder indicators
"""

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPainterPath, QLinearGradient

from src.ui.theme import C, PALETTE, MONO_FAMILY


class ChartWidget(QWidget):
    """QPainter-based chart renderer with refined visuals."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._chart_data = None
        self._chart_type = None
        self._title = ""
        self._margin = {"top": 48, "right": 32, "bottom": 52, "left": 76}

    def set_chart(self, chart_type: str, data: dict, title: str = ""):
        self._chart_type = chart_type
        self._chart_data = data
        self._title = title
        self.update()

    def clear(self):
        self._chart_data = None
        self._chart_type = None
        self._title = ""
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Rounded background with subtle border
        p.setPen(QPen(QColor(C["border"]), 1))
        p.setBrush(QColor(C["bg_float"]))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        if not self._chart_data or not self._chart_type:
            self._draw_empty(p)
            p.end()
            return

        fn = {
            "histogram": self._draw_histogram,
            "bar": self._draw_bar,
            "line": self._draw_line,
            "multi_line": self._draw_multi_line,
            "scatter": self._draw_scatter,
            "corr": self._draw_heatmap,
        }.get(self._chart_type)

        if fn:
            fn(p, self._chart_data)
        else:
            self._draw_empty(p)
        p.end()

    def _plot_rect(self) -> QRectF:
        m = self._margin
        return QRectF(m["left"], m["top"],
                      self.width() - m["left"] - m["right"],
                      self.height() - m["top"] - m["bottom"])

    def _draw_title(self, p: QPainter):
        if self._title:
            p.setPen(QColor(C["fg_dark"]))
            f = p.font()
            f.setPointSize(10)
            f.setWeight(QFont.DemiBold)
            p.setFont(f)
            p.drawText(QRectF(0, 6, self.width(), 34),
                       Qt.AlignHCenter | Qt.AlignVCenter, self._title)

    def _draw_grid(self, p: QPainter, r: QRectF, y_vals: list, fmt: str = ".1f"):
        pen = QPen(QColor(C["bg_highlight"]))
        pen.setStyle(Qt.DotLine)
        p.setPen(pen)
        p.setFont(_small_font())
        n = len(y_vals)
        for i, v in enumerate(y_vals):
            y = r.bottom() - (i / max(n - 1, 1)) * r.height()
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(QColor(C["fg_dim"]))
            p.drawText(QRectF(0, y - 10, r.left() - 8, 20),
                       Qt.AlignRight | Qt.AlignVCenter, f"{v:{fmt}}")
            p.setPen(pen)

    def _draw_axes(self, p: QPainter, r: QRectF):
        pen = QPen(QColor(C["fg_gutter"]))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.right(), r.bottom()))

    def _draw_empty(self, p: QPainter):
        p.setPen(QColor(C["fg_dim"]))
        f = p.font()
        f.setPointSize(11)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, "No data to visualize")

    # -- Histogram ------------------------------------------------

    def _draw_histogram(self, p, data):
        self._draw_title(p)
        r = self._plot_rect()
        counts = data.get("counts", [])
        bins = data.get("bins", [])
        if not counts:
            return self._draw_empty(p)
        max_c = max(counts) or 1
        n = len(counts)
        bw = r.width() / n
        self._draw_grid(p, r, [max_c * i / 4 for i in range(5)], ".0f")
        # Gradient bars
        for i, c in enumerate(counts):
            h = (c / max_c) * r.height()
            rect = QRectF(r.left() + i * bw + 2, r.bottom() - h, bw - 4, h)
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            grad.setColorAt(0.0, QColor(PALETTE[0]))
            grad.setColorAt(1.0, QColor(C["accent_soft"]))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(rect, 3, 3)
        p.setFont(_small_font())
        p.setPen(QColor(C["fg_dim"]))
        step = max(1, n // 6)
        for i in range(0, n, step):
            x = r.left() + (i + 0.5) * bw
            lbl = f"{bins[i]:.1f}" if isinstance(bins[i], float) else str(bins[i])
            p.drawText(QRectF(x - 30, r.bottom() + 6, 60, 16), Qt.AlignHCenter, lbl)
        self._draw_axes(p, r)

    # -- Bar ------------------------------------------------------

    def _draw_bar(self, p, data):
        self._draw_title(p)
        r = self._plot_rect()
        labels = data.get("labels", [])
        values = data.get("values", [])
        if not values:
            return self._draw_empty(p)
        max_v = max(values) or 1
        n = len(values)
        bw = r.width() / n
        self._draw_grid(p, r, [max_v * i / 4 for i in range(5)], ".0f")
        for i, v in enumerate(values):
            h = (v / max_v) * r.height()
            rect = QRectF(r.left() + i * bw + 4, r.bottom() - h, bw - 8, h)
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            color = QColor(PALETTE[i % len(PALETTE)])
            grad.setColorAt(0.0, color)
            color_dark = QColor(color)
            color_dark.setAlpha(120)
            grad.setColorAt(1.0, color_dark)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(rect, 4, 4)
        p.setPen(QColor(C["fg_dim"]))
        p.setFont(_small_font())
        for i, lbl in enumerate(labels):
            x = r.left() + (i + 0.5) * bw
            d = lbl[:8] + "..." if len(lbl) > 8 else lbl
            p.drawText(QRectF(x - 35, r.bottom() + 6, 70, 16), Qt.AlignHCenter, d)
        self._draw_axes(p, r)

    # -- Line -----------------------------------------------------

    def _draw_line(self, p, data):
        self._draw_title(p)
        r = self._plot_rect()
        values = [v for v in data.get("values", []) if v is not None]
        if len(values) < 2:
            return self._draw_empty(p)
        vmin, vmax = min(values), max(values)
        if vmin == vmax: vmax = vmin + 1
        n = len(values)
        self._draw_grid(p, r, [vmin + (vmax - vmin) * i / 4 for i in range(5)])
        # Area fill
        path = QPainterPath()
        points = []
        for i, v in enumerate(values):
            x = r.left() + (i / max(n - 1, 1)) * r.width()
            y = r.bottom() - ((v - vmin) / (vmax - vmin)) * r.height()
            points.append(QPointF(x, y))
        # Fill area under curve
        area = QPainterPath()
        area.moveTo(points[0].x(), r.bottom())
        for pt in points:
            area.lineTo(pt)
        area.lineTo(points[-1].x(), r.bottom())
        area.closeSubpath()
        grad = QLinearGradient(0, r.top(), 0, r.bottom())
        c = QColor(PALETTE[0])
        c.setAlpha(40)
        grad.setColorAt(0.0, c)
        c.setAlpha(5)
        grad.setColorAt(1.0, c)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(area)
        # Line
        line = QPainterPath()
        line.moveTo(points[0])
        for pt in points[1:]:
            line.lineTo(pt)
        pen = QPen(QColor(PALETTE[0]))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(line)
        self._draw_axes(p, r)

    # -- Multi-Line -----------------------------------------------

    def _draw_multi_line(self, p, data):
        self._draw_title(p)
        r = self._plot_rect()
        series = data.get("series", {})
        if not series:
            return self._draw_empty(p)
        all_v = [v for vs in series.values() for v in vs if v is not None]
        if not all_v:
            return self._draw_empty(p)
        vmin, vmax = min(all_v), max(all_v)
        if vmin == vmax: vmax = vmin + 1
        self._draw_grid(p, r, [vmin + (vmax - vmin) * i / 4 for i in range(5)])
        for si, (name, vals) in enumerate(series.items()):
            clean = [v for v in vals if v is not None]
            if len(clean) < 2: continue
            color = QColor(PALETTE[si % len(PALETTE)])
            pen = QPen(color); pen.setWidth(2); p.setPen(pen)
            path = QPainterPath()
            n = len(clean)
            for i, v in enumerate(clean):
                x = r.left() + (i / max(n - 1, 1)) * r.width()
                y = r.bottom() - ((v - vmin) / (vmax - vmin)) * r.height()
                path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
            p.drawPath(path)
            ly = r.top() + 4 + si * 18
            p.drawLine(QPointF(r.right() - 100, ly), QPointF(r.right() - 80, ly))
            p.setFont(_small_font())
            p.drawText(QPointF(r.right() - 76, ly + 4), name[:16])
        self._draw_axes(p, r)

    # -- Scatter --------------------------------------------------

    def _draw_scatter(self, p, data):
        self._draw_title(p)
        r = self._plot_rect()
        points = data.get("points", [])
        if not points: return self._draw_empty(p)
        xs, ys = [pt[0] for pt in points], [pt[1] for pt in points]
        xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
        if xmin == xmax: xmax = xmin + 1
        if ymin == ymax: ymax = ymin + 1
        self._draw_grid(p, r, [ymin + (ymax - ymin) * i / 4 for i in range(5)])
        color = QColor(PALETTE[2])
        for px, py in points:
            sx = r.left() + ((px - xmin) / (xmax - xmin)) * r.width()
            sy = r.bottom() - ((py - ymin) / (ymax - ymin)) * r.height()
            # Glow
            glow = QColor(color)
            glow.setAlpha(40)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(sx, sy), 7, 7)
            # Dot
            color.setAlpha(200)
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(sx, sy), 4, 4)
        self._draw_axes(p, r)

    # -- Heatmap --------------------------------------------------

    def _draw_heatmap(self, p, data):
        self._draw_title(p)
        cols = data.get("columns", [])
        matrix = data.get("matrix", [])
        if not cols: return self._draw_empty(p)
        n = len(cols)
        m = 80
        cell = min((self.width() - m * 2) / n, (self.height() - m * 2) / n, 50)
        ox, oy = m, m
        p.setFont(_small_font())
        for i in range(n):
            for j in range(n):
                v = matrix[i][j]
                if v >= 0:
                    cr = 255; cg = int(255 * (1 - v)); cb = cg
                else:
                    cr = int(255 * (1 + v)); cg = cr; cb = 255
                rect = QRectF(ox + j * cell, oy + i * cell, cell, cell)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(min(cr, 255), min(cg, 255), min(cb, 255)))
                p.drawRoundedRect(rect, 3, 3)
                tc = QColor("#14161b") if abs(v) > 0.3 else QColor(C["fg"])
                p.setPen(tc)
                p.drawText(rect, Qt.AlignCenter, f"{v:.2f}")
        p.setPen(QColor(C["fg_dim"]))
        for i, c in enumerate(cols):
            lbl = c[:7] + "..." if len(c) > 7 else c
            p.save()
            p.translate(ox + (i + 0.5) * cell, oy - 6)
            p.rotate(-40)
            p.drawText(0, 0, lbl)
            p.restore()
            p.drawText(QRectF(0, oy + (i + 0.15) * cell, ox - 6, cell * 0.7),
                       Qt.AlignRight | Qt.AlignVCenter, lbl)


# -- Tag Chip ----------------------------------------------------

class TagChip(QWidget):
    def __init__(self, text: str, color: str = PALETTE[0], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 600; background: transparent;")
        layout.addWidget(label)
        self.setStyleSheet(
            f"background-color: {C['bg_highlight']}; border: 1px solid {C['border']}; border-radius: 12px;")
        self.setFixedHeight(26)


# -- Stat Card ---------------------------------------------------

class StatCard(QWidget):
    def __init__(self, value: str, label: str, color: str = C["accent"], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)
        vl = QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: bold; background: transparent;")
        vl.setAlignment(Qt.AlignCenter)
        layout.addWidget(vl)
        dl = QLabel(label)
        dl.setStyleSheet(
            f"color: {C['fg_dim']}; font-size: 11px; background: transparent;")
        dl.setAlignment(Qt.AlignCenter)
        layout.addWidget(dl)
        self.setStyleSheet(
            f"background-color: {C['bg_float']}; border: 1px solid {C['border']}; border-radius: 10px;")


# -- Folder Arrow Indicator Widget --------------------------------

class FolderArrow(QWidget):
    """Minimal chevron indicator for tree items."""
    def __init__(self, expanded=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._expanded = expanded

    def set_expanded(self, val):
        self._expanded = val
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(C["fg_dim"]), 1.5))
        if self._expanded:
            # Down chevron
            p.drawLine(QPointF(4, 6), QPointF(8, 10))
            p.drawLine(QPointF(8, 10), QPointF(12, 6))
        else:
            # Right chevron
            p.drawLine(QPointF(6, 4), QPointF(10, 8))
            p.drawLine(QPointF(10, 8), QPointF(6, 12))
        p.end()


def _small_font() -> QFont:
    f = QFont()
    f.setPointSize(8)
    return f


# -- Icon Factory — cached circular icons for tree items ----------

from PySide6.QtGui import QPixmap, QIcon, QRadialGradient

class IconFactory:
    """Generates and caches small circular QIcons for file tree.
    All icons are 18x18 with antialiased QPainter rendering.
    """

    _cache: dict = {}  # class-level cache shared across instances
    SIZE = 18

    @classmethod
    def category_icon(cls, color: str) -> QIcon:
        """Filled circle with subtle gradient — for category group headers."""
        key = f"cat:{color}"
        if key not in cls._cache:
            s = cls.SIZE
            pm = QPixmap(s, s)
            pm.fill(QColor(0, 0, 0, 0))
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            c = QColor(color)
            # Radial gradient for depth
            grad = QRadialGradient(s * 0.4, s * 0.35, s * 0.5)
            lighter = QColor(c)
            lighter.setAlpha(255)
            grad.setColorAt(0.0, lighter.lighter(130))
            grad.setColorAt(1.0, c)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawEllipse(2, 2, s - 4, s - 4)
            p.end()
            cls._cache[key] = QIcon(pm)
        return cls._cache[key]

    @classmethod
    def folder_icon(cls, expanded: bool = False) -> QIcon:
        """Clear chevron arrow — ▸ closed, ▾ open. No circle background."""
        key = f"folder:{'open' if expanded else 'closed'}"
        if key not in cls._cache:
            s = cls.SIZE
            pm = QPixmap(s, s)
            pm.fill(QColor(0, 0, 0, 0))
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            fg = QColor(C["fg_dim"])
            p.setPen(QPen(fg, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            if expanded:
                # ▾ downward chevron
                path = QPainterPath()
                path.moveTo(4, 6)
                path.lineTo(9, 12)
                path.lineTo(14, 6)
                p.drawPath(path)
            else:
                # ▸ rightward chevron
                path = QPainterPath()
                path.moveTo(6, 4)
                path.lineTo(12, 9)
                path.lineTo(6, 14)
                p.drawPath(path)
            p.end()
            cls._cache[key] = QIcon(pm)
        return cls._cache[key]

    @classmethod
    def file_icon(cls, color: str) -> QIcon:
        """Small filled dot with ring — for individual files."""
        key = f"file:{color}"
        if key not in cls._cache:
            s = cls.SIZE
            pm = QPixmap(s, s)
            pm.fill(QColor(0, 0, 0, 0))
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            c = QColor(color)
            # Outer ring
            ring = QColor(c)
            ring.setAlpha(60)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(ring))
            p.drawEllipse(3, 3, s - 6, s - 6)
            # Inner filled dot
            p.setBrush(QBrush(c))
            p.drawEllipse(5, 5, s - 10, s - 10)
            p.end()
            cls._cache[key] = QIcon(pm)
        return cls._cache[key]

    @classmethod
    def loading_icon(cls) -> QIcon:
        """Dim pulsing dot for loading state."""
        key = "loading"
        if key not in cls._cache:
            s = cls.SIZE
            pm = QPixmap(s, s)
            pm.fill(QColor(0, 0, 0, 0))
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            c = QColor(C["fg_dim"])
            c.setAlpha(100)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(c))
            p.drawEllipse(4, 4, s - 8, s - 8)
            p.end()
            cls._cache[key] = QIcon(pm)
        return cls._cache[key]

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()

    @classmethod
    def toolbar_icon(cls, name: str, size: int = 18) -> QIcon:
        """Crisp toolbar icons rendered with QPainter.
        Names: 'collapse_all', 'expand_all', 'refresh'"""
        key = f"tb:{name}:{size}"
        if key not in cls._cache:
            pm = QPixmap(size, size)
            pm.fill(QColor(0, 0, 0, 0))
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)

            fg = QColor(C["fg_dark"])
            accent = QColor(C["accent"])
            s = size

            if name == "collapse_all":
                # Down-pointing chevron V — bold and clear
                p.setPen(QPen(accent, 2.2, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(int(s*0.2), int(s*0.35), int(s*0.5), int(s*0.65))
                p.drawLine(int(s*0.5), int(s*0.65), int(s*0.8), int(s*0.35))

            elif name == "expand_all":
                # Up-pointing chevron ^ — bold and clear
                p.setPen(QPen(accent, 2.2, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(int(s*0.2), int(s*0.6), int(s*0.5), int(s*0.3))
                p.drawLine(int(s*0.5), int(s*0.3), int(s*0.8), int(s*0.6))

            elif name == "refresh":
                # Circular arrow
                p.setPen(QPen(fg, 2.0, Qt.SolidLine, Qt.RoundCap))
                rect = QRectF(s*0.15, s*0.15, s*0.7, s*0.7)
                p.drawArc(rect, 60*16, 270*16)
                # Arrow tip
                p.drawLine(int(s*0.62), int(s*0.1), int(s*0.72), int(s*0.25))
                p.drawLine(int(s*0.72), int(s*0.1), int(s*0.72), int(s*0.25))

            p.end()
            cls._cache[key] = QIcon(pm)
        return cls._cache[key]


# ================================================================
#  Loading Spinner — animated ring indicator
# ================================================================

from PySide6.QtCore import QTimer

class LoadingSpinner(QWidget):
    """Smooth animated loading ring. Call start()/stop() to control."""

    def __init__(self, size=48, thickness=4, parent=None):
        super().__init__(parent)
        self._size = size
        self._thickness = thickness
        self._angle = 0
        self._active = False
        self._label_text = ""
        self.setFixedSize(size + 120, size + 28)

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)

    def start(self, label: str = "Loading..."):
        self._label_text = label
        self._active = True
        self._angle = 0
        self._timer.start()
        self.show()

    def stop(self):
        self._active = False
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 4) % 360
        self.update()

    def paintEvent(self, event):
        if not self._active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        s = self._size
        cx = s // 2 + 4
        cy = s // 2 + 4
        r = s // 2 - self._thickness

        # Background ring
        bg = QColor(C["fg_gutter"])
        bg.setAlpha(60)
        p.setPen(QPen(bg, self._thickness, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Spinning arc
        accent = QColor(C["accent"])
        p.setPen(QPen(accent, self._thickness, Qt.SolidLine, Qt.RoundCap))
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(rect, int(self._angle * 16), 90 * 16)

        # Label
        if self._label_text:
            p.setPen(QColor(C["fg_dim"]))
            f = QFont()
            f.setPointSize(10)
            p.setFont(f)
            p.drawText(s + 12, cy + 4, self._label_text)
        p.end()


# ================================================================
#  Diff Viewer — side-by-side or unified diff display
# ================================================================

from PySide6.QtWidgets import QTextEdit, QSplitter, QFrame
from PySide6.QtGui import QTextCharFormat

class DiffViewer(QWidget):
    """Side-by-side file comparison widget with syntax-highlighted diffs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QLabel()
        self._header.setStyleSheet(
            f"background:{C['bg_highlight']};color:{C['fg_dim']};"
            f"padding:8px 14px;font-size:11px;font-weight:600;")
        layout.addWidget(self._header)

        # Side-by-side splitter
        splitter = QSplitter(Qt.Horizontal)
        self._left = self._make_text_pane()
        self._right = self._make_text_pane()
        splitter.addWidget(self._left)
        splitter.addWidget(self._right)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter, 1)

        # Stats bar
        self._stats = QLabel()
        self._stats.setStyleSheet(
            f"background:{C['bg_dark']};color:{C['fg_dim']};"
            f"padding:6px 14px;font-size:11px;")
        layout.addWidget(self._stats)

    def _make_text_pane(self) -> QTextEdit:
        te = QTextEdit()
        te.setReadOnly(True)
        te.setFont(QFont(MONO_FAMILY.split(",")[0].strip(), 11))
        te.setStyleSheet(
            f"background:{C['bg_float']};color:{C['fg']};"
            f"border:none;padding:8px;")
        te.setLineWrapMode(QTextEdit.NoWrap)
        return te

    def set_diff(self, left_lines: list, right_lines: list,
                 left_label: str = "Original", right_label: str = "Modified"):
        """Show side-by-side diff of two line lists."""
        import difflib
        self._header.setText(f"  {left_label}    vs    {right_label}")

        sm = difflib.SequenceMatcher(None, left_lines, right_lines)
        left_doc = []
        right_doc = []
        n_add = 0
        n_del = 0
        n_mod = 0

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for line in left_lines[i1:i2]:
                    left_doc.append(("equal", line))
                    right_doc.append(("equal", line))
            elif tag == "replace":
                n_mod += max(i2 - i1, j2 - j1)
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    if i1 + k < i2:
                        left_doc.append(("del", left_lines[i1 + k]))
                    else:
                        left_doc.append(("pad", ""))
                    if j1 + k < j2:
                        right_doc.append(("add", right_lines[j1 + k]))
                    else:
                        right_doc.append(("pad", ""))
            elif tag == "delete":
                n_del += i2 - i1
                for line in left_lines[i1:i2]:
                    left_doc.append(("del", line))
                    right_doc.append(("pad", ""))
            elif tag == "insert":
                n_add += j2 - j1
                for line in right_lines[j1:j2]:
                    left_doc.append(("pad", ""))
                    right_doc.append(("add", line))

        self._render_pane(self._left, left_doc)
        self._render_pane(self._right, right_doc)

        self._stats.setText(
            f"  +{n_add} added    -{n_del} deleted    ~{n_mod} modified    "
            f"{len(left_lines)} / {len(right_lines)} lines")

        # Sync scrolling
        self._left.verticalScrollBar().valueChanged.connect(
            self._right.verticalScrollBar().setValue)
        self._right.verticalScrollBar().valueChanged.connect(
            self._left.verticalScrollBar().setValue)

    def _render_pane(self, pane: QTextEdit, doc: list):
        pane.clear()
        cursor = pane.textCursor()

        fmt_normal = QTextCharFormat()
        fmt_normal.setForeground(QColor(C["fg"]))

        fmt_add = QTextCharFormat()
        fmt_add.setBackground(QColor(C["diff_add_bg"]))
        fmt_add.setForeground(QColor(C["diff_add_fg"]))

        fmt_del = QTextCharFormat()
        fmt_del.setBackground(QColor(C["diff_del_bg"]))
        fmt_del.setForeground(QColor(C["diff_del_fg"]))

        fmt_pad = QTextCharFormat()
        fmt_pad.setForeground(QColor(C["fg_gutter"]))

        fmt_map = {"equal": fmt_normal, "add": fmt_add,
                   "del": fmt_del, "pad": fmt_pad}

        for i, (tag, line) in enumerate(doc):
            prefix = {
                "equal": "  ", "add": "+ ", "del": "- ", "pad": "  "
            }.get(tag, "  ")
            fmt = fmt_map.get(tag, fmt_normal)
            cursor.setCharFormat(fmt)
            text = f"{prefix}{line}"
            if i > 0:
                cursor.insertText("\n")
            cursor.insertText(text)

        pane.verticalScrollBar().setValue(0)

    def clear(self):
        self._left.clear()
        self._right.clear()
        self._header.setText("")
        self._stats.setText("")
