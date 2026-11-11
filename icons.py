"""Icone vettoriali (stile Lucide) disegnate a runtime."""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QIconEngine, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer

from theme import P

PATHS = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>',
    "folder": '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>',
    "clipboard": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "trash": '<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "zap": '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "checks": '<path d="M18 6 7 17l-5-5M22 10l-7.5 7.5L13 16"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
    "external": '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "eye": '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "refresh": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    "skip": '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
    "star": '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2m-7.07-2.93 1.41-1.41m11.32-11.32 1.41-1.41M2 12h2m16 0h2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "monitor": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1ZM2 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1ZM7 21h10M12 3v18M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
}


def resolve(color):
    """Accetta un ruolo del tema ('text2', 'muted', 'dim', 'on_accent', ...) oppure un colore '#rrggbb'."""
    if isinstance(color, str) and not color.startswith("#") and hasattr(P, color):
        return getattr(P, color)
    return color


def svg(name, color="text2", width=2.0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{resolve(color)}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>')


def pixmap(name, color="text2", size=18, width=2.0, dpr=2.0):
    r = QSvgRenderer(QByteArray(svg(name, color, width).encode()))
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    r.render(p)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


_renderers = {}  # cache dei renderer SVG per (icona, colore, spessore)


class _ThemedEngine(QIconEngine):
    """Icona vettoriale che si ricolora da sola al cambio di tema (il colore è risolto a ogni disegno)."""

    def __init__(self, name, color, width):
        super().__init__()
        self.name, self.color, self.width = name, color, width

    def _renderer(self, mode):
        if mode == QIcon.Disabled and not str(self.color).startswith("#"):
            col = "dim"
        else:
            col = self.color
        key = (self.name, resolve(col), self.width)
        r = _renderers.get(key)
        if r is None:
            r = _renderers[key] = QSvgRenderer(QByteArray(svg(self.name, col, self.width).encode()))
        return r

    def paint(self, painter, rect, mode, state):
        self._renderer(mode).render(painter, QRectF(rect))

    def pixmap(self, size, mode, state):
        pm = QPixmap(size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        self._renderer(mode).render(p, QRectF(0, 0, size.width(), size.height()))
        p.end()
        return pm

    def clone(self):
        return _ThemedEngine(self.name, self.color, self.width)


def icon(name, color="text2", size=18, active=None, width=2.0):
    """QIcon tematizzata. `size` è mantenuto per compatibilità (l'icona è vettoriale)."""
    return QIcon(_ThemedEngine(name, color, width))


def app_icon_pixmap(size=256):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size
    g = QLinearGradient(0, 0, s, s)
    g.setColorAt(0, QColor("#8b5cf6"))
    g.setColorAt(1, QColor("#3b82f6"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(s * 0.04, s * 0.04, s * 0.92, s * 0.92), s * 0.22, s * 0.22)
    # prisma
    tri = QPainterPath()
    tri.moveTo(s * 0.42, s * 0.24)
    tri.lineTo(s * 0.66, s * 0.72)
    tri.lineTo(s * 0.18, s * 0.72)
    tri.closeSubpath()
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawPath(tri)
    # raggio d'ingresso e arcobaleno in uscita
    pen = QPen(QColor(255, 255, 255, 220), s * 0.035, Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(int(s * 0.10), int(s * 0.56), int(s * 0.33), int(s * 0.49))
    cols = ["#ff5c7a", "#ffb547", "#ffe066", "#2ecc8f", "#4fd1ff"]
    for i, c in enumerate(cols):
        pen = QPen(QColor(c), s * 0.032, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        y0 = s * 0.50
        p.drawLine(int(s * 0.53), int(y0), int(s * 0.88), int(s * (0.36 + i * 0.075)))
    p.end()
    return pm


def app_icon():
    ic = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(app_icon_pixmap(sz))
    return ic
