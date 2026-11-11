"""Prisma - interfaccia grafica (PySide6)."""
from __future__ import annotations

import ctypes
import datetime
import itertools
import json
import os
import subprocess
import sys
import threading
import time
import traceback

from PySide6.QtCore import (QEasingCurve, QMimeData, QObject, QPoint, QPropertyAnimation, QRectF, QRunnable, QSize, Qt,
                            QThreadPool, QTimer, QUrl, Signal)
from PySide6.QtGui import (QAction, QBrush, QColor, QDesktopServices, QFont, QFontMetrics, QGuiApplication, QImage,
                           QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut, QStandardItem,
                           QStandardItemModel)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QColorDialog, QComboBox,
                               QDialog, QFileDialog, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressBar,
                               QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter, QStackedWidget,
                               QStyle, QStyledItemDelegate, QSystemTrayIcon, QVBoxLayout, QWidget, QInputDialog)

import engine
import icons

APP_NAME = "Prisma"
APP_VERSION = "1.0"
APPDATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
os.makedirs(APPDATA, exist_ok=True)
CONFIG = os.path.join(APPDATA, "settings.json")

BG, SURF, SURF2, SURF3 = "#0e1014", "#14171e", "#1a1e27", "#222734"
BORDER, TEXT, MUTED, DIM = "#262b37", "#e6e9ef", "#8a92a3", "#5b6272"
ACCENT, ACCENT2, OK, ERR, WARN = "#7c5cff", "#4f8cff", "#2ecc8f", "#ff5c7a", "#ffb547"


def human(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            s = f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            return s.replace(".", ",")
        n /= 1024


def open_path(path):
    if path and os.path.exists(path):
        os.startfile(os.path.abspath(path))


def reveal(path):
    if path and os.path.exists(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(os.path.abspath(path))])


def dark_titlebar(widget):
    if os.name != "nt":
        return
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)  # dark mode
        color = ctypes.c_int(0x00140E0E)  # BGR di BG
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), 4)  # caption color (Win11)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Stile
# --------------------------------------------------------------------------- #
def write_ui_assets():
    d = os.path.join(APPDATA, "ui")
    os.makedirs(d, exist_ok=True)
    files = {
        "check.svg": icons.svg("check", "#ffffff", 3),
        "chev.svg": icons.svg("chevron-down", MUTED, 2.2),
        "dot.svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="6" fill="#fff"/></svg>',
    }
    for n, c in files.items():
        with open(os.path.join(d, n), "w", encoding="utf-8") as f:
            f.write(c)
    return d.replace("\\", "/")


def stylesheet(asset_dir):
    return f"""
* {{ font-family: 'Segoe UI Variable Text', 'Segoe UI'; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#panel {{ background: {SURF}; }}
QWidget#header {{ background: {BG}; border-bottom: 1px solid {BORDER}; }}
QWidget#footer {{ background: {SURF}; border-top: 1px solid {BORDER}; }}
QLabel#h1 {{ font-size: 13.5pt; font-weight: 600; }}
QLabel#h2 {{ font-size: 11pt; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#small {{ color: {MUTED}; font-size: 8.5pt; }}
QLabel#value {{ color: {TEXT}; font-weight: 600; background: {SURF3}; border-radius: 5px; padding: 1px 7px; }}
QLabel#version {{ color: {DIM}; font-size: 8.5pt; }}
QLabel#warn {{ color: {WARN}; background: rgba(255,181,71,0.08); border: 1px solid rgba(255,181,71,0.25);
               border-radius: 8px; padding: 8px 10px; font-size: 9pt; }}
QLabel#info {{ color: #b9c3ff; background: rgba(124,92,255,0.08); border: 1px solid rgba(124,92,255,0.25);
               border-radius: 8px; padding: 8px 10px; font-size: 9pt; }}
QPushButton {{ background: {SURF2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px 12px; }}
QPushButton:hover {{ background: {SURF3}; border-color: #343b4c; }}
QPushButton:pressed {{ background: #181b23; }}
QPushButton:disabled {{ color: {DIM}; background: {SURF}; }}
QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2});
    border: none; font-weight: 600; font-size: 10.5pt; padding: 10px 26px; color: white; }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8e72ff, stop:1 #6a9dff); }}
QPushButton#primary:disabled {{ background: {SURF3}; color: {DIM}; }}
QPushButton#danger {{ background: #2e1820; border: 1px solid #5a2635; color: #ffb3c1; font-weight: 600;
    font-size: 10.5pt; padding: 10px 26px; }}
QPushButton#danger:hover {{ background: #3a1d28; }}
QPushButton#ghost {{ background: transparent; border: 1px solid transparent; padding: 6px 9px; border-radius: 7px; color: #c9cfdb; }}
QPushButton#ghost:hover {{ background: {SURF3}; border-color: {BORDER}; }}
QPushButton#chip {{ padding: 8px 0px; font-weight: 600; border-radius: 8px; background: {SURF2}; }}
QPushButton#chip:hover {{ border-color: #3a4152; }}
QPushButton#chip:checked {{ background: rgba(124,92,255,0.20); border: 1px solid {ACCENT}; color: white; }}
QPushButton#mini {{ padding: 4px 9px; font-size: 8.5pt; border-radius: 6px; }}
QPushButton#mini:checked {{ background: rgba(124,92,255,0.22); border: 1px solid {ACCENT}; color: white; }}
QPushButton#section {{ background: transparent; border: none; text-align: left; padding: 6px 0px; color: {MUTED};
    font-size: 8.5pt; font-weight: 700; }}
QPushButton#section:hover {{ color: {TEXT}; }}
QPushButton#swatch {{ border-radius: 6px; padding: 0; min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; }}
QLineEdit, QSpinBox, QComboBox {{ background: #0f1218; border: 1px solid {BORDER}; border-radius: 7px; padding: 6px 9px;
    selection-background-color: {ACCENT}; }}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{ border-color: #343b4c; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ color: {DIM}; background: {SURF}; }}
QLineEdit#search {{ padding-left: 30px; border-radius: 8px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url({asset_dir}/chev.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {SURF2}; border: 1px solid {BORDER}; selection-background-color: #2c2550;
    outline: 0; padding: 4px; }}
QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 0 6px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; border: none; }}
QCheckBox, QRadioButton {{ spacing: 9px; }}
QCheckBox:disabled, QRadioButton:disabled, QLabel:disabled {{ color: {DIM}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px; border: 1px solid #3a4152; background: #0f1218; }}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url({asset_dir}/check.svg); }}
QCheckBox::indicator:checked:disabled {{ background: #3a3360; border-color: #3a3360; }}
QSlider::groove:horizontal {{ height: 4px; background: {SURF3}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2}); border-radius: 2px; }}
QSlider::sub-page:horizontal:disabled {{ background: #3a3f4d; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::handle:horizontal:hover {{ background: #dcd4ff; }}
QSlider::handle:horizontal:disabled {{ background: #5b6272; }}
QProgressBar {{ background: {SURF3}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 3px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2}); }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2a303d; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #394052; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QScrollBar:horizontal {{ height: 0px; }}
QToolTip {{ background: {SURF2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px 8px; border-radius: 6px; }}
QMenu {{ background: {SURF2}; border: 1px solid {BORDER}; padding: 5px; }}
QMenu::item {{ padding: 7px 26px 7px 10px; border-radius: 5px; }}
QMenu::item:selected {{ background: #2c2550; }}
QMenu::item:disabled {{ color: {DIM}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QMenu::icon {{ padding-left: 8px; }}
QListWidget {{ background: transparent; border: none; outline: 0; }}
QSplitter::handle {{ background: {BORDER}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QFrame#sep {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#card {{ background: {SURF2}; border: 1px solid {BORDER}; border-radius: 10px; }}
"""


# --------------------------------------------------------------------------- #
# Job e worker
# --------------------------------------------------------------------------- #
_ids = itertools.count(1)


class Job:
    def __init__(self, path, rel="", temp=False):
        self.id = next(_ids)
        self.path = path
        self.rel = rel
        self.temp = temp
        self.name = os.path.basename(path)
        self.ext = engine.ext_of(path)
        try:
            self.size = os.path.getsize(path)
        except OSError:
            self.size = 0
        self.w = self.h = 0
        self.fmt = self.ext.upper()
        self.alpha = False
        self.frames = 1
        self.thumb = None
        self.probed = False
        self.probe_error = None
        self.status = "pending"
        self.out = None
        self.outs = []
        self.out_size = 0
        self.msg = ""
        self.elapsed = 0.0
        self.target = None

    def snapshot(self):
        return dict(path=self.path, rel=self.rel, w=self.w, h=self.h, alpha=self.alpha, frames=self.frames)


class Emitter(QObject):
    probed = Signal(int, object)
    started = Signal(int)
    done = Signal(int, object)
    preview = Signal(str, object)
    message = Signal(str)


class ProbeTask(QRunnable):
    def __init__(self, job_id, path, tools, emitter, size=160, kind="probe"):
        super().__init__()
        self.job_id, self.path, self.tools, self.emitter, self.size, self.kind = job_id, path, tools, emitter, size, kind

    def run(self):
        try:
            info = engine.probe(self.path, self.tools, self.size)
        except Exception as e:  # noqa
            info = dict(w=0, h=0, fmt="", alpha=False, frames=1, thumb=None, error=str(e))
        if self.kind == "preview":
            self.emitter.preview.emit(self.path, info)
        else:
            self.emitter.probed.emit(self.job_id, info)


class ConvertTask(QRunnable):
    def __init__(self, job_id, snap, settings, tools, emitter, cancel, index, tpj):
        super().__init__()
        self.job_id, self.snap, self.s, self.tools = job_id, snap, settings, tools
        self.emitter, self.cancel, self.index, self.tpj = emitter, cancel, index, tpj

    def run(self):
        if self.cancel.is_set():
            self.emitter.done.emit(self.job_id, dict(status="cancelled", msg="Annullato"))
            return
        self.emitter.started.emit(self.job_id)
        t0 = time.perf_counter()
        try:
            res = engine.convert(self.snap, self.s, self.tools, self.cancel, self.index, self.tpj)
        except engine.Cancelled:
            res = dict(status="cancelled", msg="Annullato")
        except engine.ConvertError as e:
            res = dict(status="error", msg=str(e))
        except Exception as e:  # noqa
            res = dict(status="error", msg=f"{type(e).__name__}: {e}")
        res["elapsed"] = time.perf_counter() - t0
        self.emitter.done.emit(self.job_id, res)


# --------------------------------------------------------------------------- #
# Lista file
# --------------------------------------------------------------------------- #
def checker_brush(size=8):
    pm = QPixmap(size * 2, size * 2)
    pm.fill(QColor("#2a2f3a"))
    p = QPainter(pm)
    p.fillRect(0, 0, size, size, QColor("#353b48"))
    p.fillRect(size, size, size, size, QColor("#353b48"))
    p.end()
    return QBrush(pm)


class JobDelegate(QStyledItemDelegate):
    ROW_H = 66

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.checker = checker_brush(5)
        self.f_name = QFont()
        self.f_name.setPointSizeF(10)
        self.f_name.setWeight(QFont.DemiBold)
        self.f_meta = QFont()
        self.f_meta.setPointSizeF(8.6)
        self.f_ext = QFont()
        self.f_ext.setPointSizeF(8)
        self.f_ext.setWeight(QFont.Bold)

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, p: QPainter, opt, index):
        job: Job = index.data(Qt.UserRole)
        if job is None:
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(opt.rect).adjusted(8, 3, -8, -3)
        sel = bool(opt.state & QStyle.State_Selected)
        hov = bool(opt.state & QStyle.State_MouseOver)
        bg = QColor("#1f1b38") if sel else QColor(SURF2) if hov else QColor(SURF)
        p.setPen(QPen(QColor(ACCENT if sel else BORDER), 1))
        p.setBrush(bg)
        p.drawRoundedRect(r, 10, 10)

        # miniatura
        tr = QRectF(r.left() + 9, r.top() + 8, r.height() - 16, r.height() - 16)
        path = QPainterPath()
        path.addRoundedRect(tr, 7, 7)
        p.setClipPath(path)
        if job.thumb is not None and not job.thumb.isNull():
            if job.alpha:
                p.fillRect(tr, self.checker)
            else:
                p.fillRect(tr, QColor("#0b0d11"))
            pm = job.thumb
            sz = pm.deviceIndependentSize()
            sc = min(tr.width() / max(1, sz.width()), tr.height() / max(1, sz.height()))
            sc = min(sc, 4)
            w, h = sz.width() * sc, sz.height() * sc
            p.drawPixmap(QRectF(tr.center().x() - w / 2, tr.center().y() - h / 2, w, h), pm, QRectF(pm.rect()))
        else:
            p.fillRect(tr, QColor(SURF3))
            p.setFont(self.f_ext)
            p.setPen(QColor(MUTED))
            p.drawText(tr, Qt.AlignCenter, (job.ext or "?").upper()[:5])
        p.setClipping(False)

        # testo
        right_w = 150
        tx = tr.right() + 12
        tw = r.right() - tx - right_w - 10
        p.setFont(self.f_name)
        p.setPen(QColor(TEXT))
        fm = QFontMetrics(self.f_name)
        p.drawText(QRectF(tx, r.top() + 11, tw, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   fm.elidedText(job.name, Qt.ElideMiddle, int(tw)))
        p.setFont(self.f_meta)
        fm2 = QFontMetrics(self.f_meta)
        if job.status in ("error",) and job.msg:
            p.setPen(QColor(ERR))
            meta = job.msg.splitlines()[0]
        elif job.probe_error and not job.w:
            p.setPen(QColor(WARN))
            meta = job.probe_error.splitlines()[0]
        else:
            p.setPen(QColor(MUTED))
            parts = []
            resized = job.w and job.target and tuple(job.target) != (job.w, job.h) and job.status != "done"
            if job.w and not resized:
                parts.append(f"{job.w}×{job.h}")
            parts.append(job.fmt or job.ext.upper())
            parts.append(human(job.size))
            if job.frames > 1:
                parts.append(f"{job.frames} frame")
            if job.alpha:
                parts.append("alpha")
            if job.status == "done" and job.out:
                parts.append("→ " + os.path.basename(job.out))
            meta = "  ·  ".join(parts)
            if resized:
                dim = f"{job.w}×{job.h} → {job.target[0]}×{job.target[1]}"
                dw = fm2.horizontalAdvance(dim)
                p.setPen(QColor(WARN))
                p.drawText(QRectF(tx, r.top() + 32, tw, 18), Qt.AlignLeft | Qt.AlignVCenter, dim)
                p.setPen(QColor(MUTED))
                tx2 = tx + dw
                p.drawText(QRectF(tx2, r.top() + 32, tw - dw, 18), Qt.AlignLeft | Qt.AlignVCenter,
                           fm2.elidedText("  ·  " + meta, Qt.ElideRight, int(tw - dw)))
                meta = None
        if meta is not None:
            p.drawText(QRectF(tx, r.top() + 32, tw, 18), Qt.AlignLeft | Qt.AlignVCenter,
                       fm2.elidedText(meta, Qt.ElideRight, int(tw)))

        # stato
        sr = QRectF(r.right() - right_w - 10, r.top(), right_w, r.height())
        st = job.status
        if st == "working":
            bar = QRectF(sr.left() + 10, sr.center().y() + 4, sr.width() - 10, 4)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(SURF3))
            p.drawRoundedRect(bar, 2, 2)
            seg = bar.width() * 0.35
            x = bar.left() + (bar.width() + seg) * (self.phase % 1.0) - seg
            seg_r = QRectF(max(bar.left(), x), bar.top(), min(seg, bar.right() - x, x + seg - bar.left()), 4)
            if seg_r.width() > 0:
                p.setBrush(QColor(ACCENT))
                p.drawRoundedRect(seg_r, 2, 2)
            p.setPen(QColor("#b9c3ff"))
            p.drawText(QRectF(sr.left(), sr.top() + 14, sr.width(), 18), Qt.AlignRight | Qt.AlignVCenter, "Conversione…")
        else:
            label, color, sub = {
                "pending": ("Pronto", DIM, ""),
                "queued": ("In attesa…", MUTED, ""),
                "cancelled": ("Annullato", MUTED, ""),
                "skipped": ("Saltato", WARN, ""),
                "error": ("Errore", ERR, "passa sopra per i dettagli"),
            }.get(st, ("", MUTED, ""))
            if st == "done":
                label = "✓  " + human(job.out_size)
                color = OK
                if job.size:
                    d = (job.out_size - job.size) / job.size * 100
                    sub = (f"−{abs(d):.0f}%" if d < 0 else f"+{d:.0f}%") + f"  ·  {job.elapsed:.1f}s".replace(".", ",")
            if st == "skipped":
                sub = job.msg
            p.setFont(self.f_name)
            p.setPen(QColor(color))
            p.drawText(QRectF(sr.left(), r.top() + 11, sr.width(), 20), Qt.AlignRight | Qt.AlignVCenter, label)
            if sub:
                p.setFont(self.f_meta)
                p.setPen(QColor(MUTED))
                p.drawText(QRectF(sr.left() - 40, r.top() + 32, sr.width() + 40, 18), Qt.AlignRight | Qt.AlignVCenter,
                           fm2.elidedText(sub, Qt.ElideLeft, int(sr.width() + 40)))
        p.restore()


class QueueList(QListWidget):
    preview_requested = Signal()
    delete_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setAcceptDrops(False)
        self.setMouseTracking(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setUniformItemSizes(True)
        self.setSpacing(0)

    def mimeData(self, items):
        md = QMimeData()
        urls = []
        for it in items:
            j: Job = it.data(Qt.UserRole)
            for p in (j.outs if j.status == "done" and j.outs else [j.path]):
                urls.append(QUrl.fromLocalFile(p))
        md.setUrls(urls)
        return md

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            self.preview_requested.emit()
            return
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_requested.emit()
            return
        super().keyPressEvent(e)

    def viewportEvent(self, e):
        if e.type() == e.Type.ToolTip:
            it = self.itemAt(e.pos())
            if it:
                j: Job = it.data(Qt.UserRole)
                lines = [j.path]
                if j.status == "done" and j.out:
                    lines.append("→ " + j.out)
                if j.msg and j.status in ("error", "skipped"):
                    lines.append("")
                    lines.append(j.msg)
                self.setToolTip("\n".join(lines))
            else:
                self.setToolTip("")
        return super().viewportEvent(e)


# --------------------------------------------------------------------------- #
# Widget di supporto
# --------------------------------------------------------------------------- #
class DropZone(QWidget):
    def __init__(self, on_files, on_folder):
        super().__init__()
        self.hover = False
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("upload", "#9b87ff", 46, 1.6))
        ic.setAlignment(Qt.AlignCenter)
        t = QLabel("Trascina qui immagini o cartelle")
        t.setObjectName("h2")
        t.setAlignment(Qt.AlignCenter)
        st = QLabel("oppure incolla con Ctrl+V  ·  PNG, JPG, WEBP, AVIF, HEIC, DDS, PSD, TGA, EXR, SVG, PDF, RAW e altri 90+ formati")
        st.setObjectName("muted")
        st.setWordWrap(True)
        st.setAlignment(Qt.AlignCenter)
        st.setMaximumWidth(460)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        b1 = QPushButton(icons.icon("file"), "  Scegli file")
        b1.clicked.connect(on_files)
        b2 = QPushButton(icons.icon("folder"), "  Scegli cartella")
        b2.clicked.connect(on_folder)
        for b in (b1, b2):
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b)
        lay.addStretch()
        lay.addWidget(ic)
        lay.addSpacing(4)
        lay.addWidget(t)
        lay.addWidget(st, 0, Qt.AlignCenter)
        lay.addSpacing(10)
        lay.addLayout(row)
        lay.addStretch()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(18, 18, -18, -18)
        pen = QPen(QColor("#343a4a"), 1.6, Qt.DashLine)
        pen.setDashPattern([6, 5])
        p.setPen(pen)
        p.setBrush(QColor(255, 255, 255, 4))
        p.drawRoundedRect(r, 16, 16)


class DropOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.text = ""
        self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(10, 11, 16, 215))
        r = QRectF(self.rect()).adjusted(24, 24, -24, -24)
        pen = QPen(QColor(ACCENT), 2.2, Qt.DashLine)
        pen.setDashPattern([7, 5])
        p.setPen(pen)
        p.setBrush(QColor(124, 92, 255, 22))
        p.drawRoundedRect(r, 18, 18)
        pm = icons.pixmap("upload", "#b9a8ff", 54, 1.6)
        p.drawPixmap(int(r.center().x() - 27), int(r.center().y() - 70), pm)
        f = QFont()
        f.setPointSizeF(15)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(TEXT))
        p.drawText(QRectF(r.left(), r.center().y() - 6, r.width(), 30), Qt.AlignCenter, "Rilascia per aggiungere")
        f.setPointSizeF(10)
        f.setWeight(QFont.Normal)
        p.setFont(f)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(r.left(), r.center().y() + 26, r.width(), 22), Qt.AlignCenter, self.text)


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(f"background: {SURF3}; border: 1px solid #353c4d; border-radius: 10px; padding: 10px 16px; color: {TEXT};")
        self.eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.eff)
        self.anim = QPropertyAnimation(self.eff, b"opacity", self)
        self.anim.setDuration(220)
        self.timer = QTimer(self, singleShot=True)
        self.timer.timeout.connect(self._fade_out)
        self._fading = False
        self.anim.finished.connect(lambda: self._fading and self.hide())
        self.hide()

    def show_msg(self, text, ms=2600):
        self.setText(text)
        self.adjustSize()
        par = self.parentWidget()
        self.move((par.width() - self.width()) // 2, par.height() - self.height() - 96)
        self.raise_()
        self.show()
        self.anim.stop()
        self._fading = False
        self.anim.setStartValue(self.eff.opacity() if self.isVisible() else 0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.timer.start(ms)

    def _fade_out(self):
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self._fading = True
        self.anim.start()


class Section(QWidget):
    def __init__(self, title, content: QWidget, expanded=True):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.btn = QPushButton(title.upper())
        self.btn.setObjectName("section")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.toggle)
        self.content = content
        lay.addWidget(self.btn)
        lay.addWidget(content)
        self.set_expanded(expanded)

    def toggle(self):
        self.set_expanded(not self.content.isVisible())

    def set_expanded(self, v):
        self.content.setVisible(v)
        self.btn.setIcon(icons.icon("chevron-down" if v else "chevron-right", MUTED, 14))
        self.btn.setIconSize(QSize(14, 14))


def sep():
    f = QFrame()
    f.setObjectName("sep")
    return f


def label(text, obj=None, wrap=False):
    l = QLabel(text)
    if obj:
        l.setObjectName(obj)
    l.setWordWrap(wrap)
    return l


class OptionForm(QWidget):
    changed = Signal()

    def __init__(self, specs, tools):
        super().__init__()
        self.specs = specs
        self.widgets = {}
        self.rows = {}
        self._loading = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        if not specs:
            lay.addWidget(label("Nessuna opzione aggiuntiva: il formato viene salvato con le impostazioni migliori.",
                                "small", True))
        for sp in specs:
            row = QWidget()
            rl = QVBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
            t = sp["type"]
            if t == "check":
                w = QCheckBox(sp["label"])
                w.toggled.connect(self._changed)
                rl.addWidget(w)
            elif t == "slider":
                top = QHBoxLayout()
                val = label("", "value")
                top.addWidget(QLabel(sp["label"]))
                top.addStretch()
                top.addWidget(val)
                rl.addLayout(top)
                w = QSlider(Qt.Horizontal)
                w.setRange(sp["min"], sp["max"])
                w.setPageStep(5 if sp["max"] > 20 else 1)
                w.valueChanged.connect(lambda v, val=val: val.setText(str(v)))
                w.valueChanged.connect(self._changed)
                rl.addWidget(w)
            elif t == "combo":
                rl.addWidget(QLabel(sp["label"]))
                w = QComboBox()
                model = QStandardItemModel(w)
                for it in sp["items"]:
                    text, value = it[0], it[1]
                    item = QStandardItem(text)
                    item.setData(value, Qt.UserRole)
                    if len(it) > 2 and not tools.has(it[2]):
                        item.setEnabled(False)
                        item.setText(text + "   ·  richiede texconv")
                    model.appendRow(item)
                w.setModel(model)
                w.currentIndexChanged.connect(self._changed)
                rl.addWidget(w)
            elif t == "spin":
                rl.addWidget(QLabel(sp["label"]))
                w = QSpinBox()
                w.setRange(sp["min"], sp["max"])
                w.setSuffix(sp.get("suffix", ""))
                if sp.get("special"):
                    w.setSpecialValueText(sp["special"])
                w.setSingleStep(50)
                w.valueChanged.connect(self._changed)
                rl.addWidget(w)
            elif t == "chips":
                rl.addWidget(QLabel(sp["label"]))
                box = QHBoxLayout()
                box.setSpacing(5)
                w = []
                for v in sp["items"]:
                    b = QPushButton(v)
                    b.setObjectName("mini")
                    b.setCheckable(True)
                    b.setCursor(Qt.PointingHandCursor)
                    b.toggled.connect(self._changed)
                    box.addWidget(b)
                    w.append(b)
                box.addStretch()
                rl.addLayout(box)
            if sp.get("hint"):
                rl.addWidget(label(sp["hint"], "small", True))
            lay.addWidget(row)
            self.widgets[sp["id"]] = w
            self.rows[sp["id"]] = row
        self.set({})

    def value(self, sid):
        sp = next(s for s in self.specs if s["id"] == sid)
        w = self.widgets[sid]
        t = sp["type"]
        if t == "check":
            return w.isChecked()
        if t in ("slider", "spin"):
            return w.value()
        if t == "combo":
            return w.currentData(Qt.UserRole)
        if t == "chips":
            return [b.text() for b in w if b.isChecked()]

    def get(self):
        return {sp["id"]: self.value(sp["id"]) for sp in self.specs}

    def set(self, d):
        self._loading = True
        for sp in self.specs:
            v = d.get(sp["id"], sp["default"])
            w = self.widgets[sp["id"]]
            t = sp["type"]
            if t == "check":
                w.setChecked(bool(v))
            elif t in ("slider", "spin"):
                w.setValue(int(v))
                if t == "slider":
                    w.valueChanged.emit(w.value())
            elif t == "combo":
                idx = w.findData(v, Qt.UserRole)
                m = w.model()
                if idx < 0 or not m.item(idx).isEnabled():
                    idx = max(0, w.findData(sp["default"], Qt.UserRole))
                w.setCurrentIndex(idx)
            elif t == "chips":
                for b in w:
                    b.setChecked(b.text() in v)
        self._loading = False
        self._update_enabled()

    def _update_enabled(self):
        for sp in self.specs:
            dep = sp.get("enabled_if")
            if dep:
                cur = self.value(dep[0])
                ok = cur in dep[1] if isinstance(dep[1], tuple) else cur == dep[1]
                self.rows[sp["id"]].setEnabled(ok)

    def _changed(self, *a):
        if self._loading:
            return
        self._update_enabled()
        self.changed.emit()


class ImageView(QWidget):
    def __init__(self):
        super().__init__()
        self.pm = None
        self.text = "Caricamento…"
        self.checker = checker_brush(8)
        self.setMinimumSize(400, 300)

    def set_pixmap(self, pm, text=""):
        self.pm = pm
        self.text = text
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor("#0b0d11"))
        if self.pm and not self.pm.isNull():
            sz = self.pm.size()
            sc = min(self.width() / sz.width(), self.height() / sz.height(), 1.0 if max(sz.width(), sz.height()) > 64 else 8.0)
            w, h = sz.width() * sc, sz.height() * sc
            r = QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)
            p.fillRect(r, self.checker)
            if sc > 2:
                p.setRenderHint(QPainter.SmoothPixmapTransform, False)
            p.drawPixmap(r, self.pm, QRectF(self.pm.rect()))
        else:
            p.setPen(QColor(MUTED))
            p.drawText(self.rect(), Qt.AlignCenter, self.text)


class PreviewDialog(QDialog):
    def __init__(self, parent, job: Job, tools):
        super().__init__(parent)
        self.setWindowTitle(f"Anteprima - {job.name}")
        self.resize(980, 720)
        self.job, self.tools = job, tools
        self.cache = {}
        self.emitter = Emitter()
        self.emitter.preview.connect(self._loaded)
        self.pool = QThreadPool(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 16)
        top = QHBoxLayout()
        self.b_src = QPushButton("Originale")
        self.b_out = QPushButton("Convertito")
        g = QButtonGroup(self)
        for b in (self.b_src, self.b_out):
            b.setObjectName("mini")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            g.addButton(b)
            top.addWidget(b)
        self.b_src.setChecked(True)
        has_out = job.status == "done" and job.out and os.path.exists(job.out)
        self.b_out.setEnabled(bool(has_out))
        self.b_src.clicked.connect(lambda: self.show_path(job.path))
        self.b_out.clicked.connect(lambda: self.show_path(job.out))
        top.addSpacing(10)
        self.info = label("", "muted")
        top.addWidget(self.info, 1)
        hint = label("1 / 2 per alternare  ·  Esc per chiudere", "small")
        top.addWidget(hint)
        lay.addLayout(top)
        self.view = ImageView()
        lay.addWidget(self.view, 1)
        QShortcut(QKeySequence("1"), self, activated=self.b_src.click)
        QShortcut(QKeySequence("2"), self, activated=lambda: self.b_out.isEnabled() and self.b_out.click())
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.close)
        self.current = None
        self.show_path(job.out if has_out else job.path)
        if has_out:
            self.b_out.setChecked(True)

    def showEvent(self, e):
        dark_titlebar(self)
        super().showEvent(e)

    def show_path(self, path):
        self.current = path
        if path in self.cache:
            self._apply(path)
            return
        self.view.set_pixmap(None, "Caricamento…")
        self.info.setText(os.path.basename(path))
        self.pool.start(ProbeTask(0, path, self.tools, self.emitter, 2048, "preview"))

    def _loaded(self, path, info):
        pm = QPixmap()
        if info.get("thumb"):
            pm.loadFromData(info["thumb"])
        self.cache[path] = (pm, info)
        if path == self.current:
            self._apply(path)

    def _apply(self, path):
        pm, info = self.cache[path]
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        parts = [os.path.basename(path)]
        if info.get("w"):
            parts.append(f"{info['w']}×{info['h']}")
        parts += [info.get("fmt", ""), human(size)]
        self.info.setText("   ·   ".join(p for p in parts if p))
        self.view.set_pixmap(pm, info.get("error") or "Anteprima non disponibile")


# --------------------------------------------------------------------------- #
# Finestra impostazioni
# --------------------------------------------------------------------------- #
def create_shortcut(where):
    """where: 'SendTo' | 'Desktop'"""
    pyw = sys.executable
    if engine.FROZEN:  # versione installata: il collegamento punta direttamente a Prisma.exe
        args, ico = "", pyw
    else:
        if pyw.lower().endswith("python.exe"):
            cand = pyw[:-10] + "pythonw.exe"
            if os.path.exists(cand):
                pyw = cand
        args = '"' + os.path.join(engine.APP_DIR, "Prisma.pyw") + '"'
        ico = os.path.join(APPDATA, "prisma.ico")
        icons.app_icon_pixmap(256).save(ico, "ICO")
    name = "Prisma - Converti immagini.lnk" if where == "SendTo" else "Prisma.lnk"
    q = lambda s: s.replace("'", "''")  # noqa
    ps = (f"$l=Join-Path ([Environment]::GetFolderPath('{where}')) '{q(name)}';"
          f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut($l);"
          f"$s.TargetPath='{q(pyw)}';$s.Arguments='{q(args)}';$s.WorkingDirectory='{q(engine.APP_DIR)}';"
          f"$s.IconLocation='{q(ico)}';$s.Description='Prisma Image Converter';$s.Save()")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       capture_output=True, creationflags=engine.CREATE_NO_WINDOW)
    return r.returncode == 0


class SettingsDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("Impostazioni - Prisma")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(14)
        lay.addWidget(label("Impostazioni", "h1"))

        lay.addWidget(label("PRESTAZIONI", "small"))
        row = QHBoxLayout()
        row.addWidget(QLabel("Conversioni in parallelo"))
        row.addStretch()
        self.threads = QSpinBox()
        self.threads.setRange(1, max(1, os.cpu_count() or 4))
        self.threads.setValue(main.prefs.get("threads", main.default_threads()))
        self.threads.setFixedWidth(90)
        row.addWidget(self.threads)
        lay.addLayout(row)
        lay.addWidget(label(f"Il tuo processore ha {os.cpu_count()} thread logici.", "small"))

        lay.addWidget(sep())
        lay.addWidget(label("NOTIFICHE", "small"))
        self.notify = QCheckBox("Notifica di sistema al termine se la finestra non è in primo piano")
        self.notify.setChecked(main.prefs.get("notify", True))
        lay.addWidget(self.notify)
        self.sound = QCheckBox("Suono al termine")
        self.sound.setChecked(main.prefs.get("sound", False))
        lay.addWidget(self.sound)

        lay.addWidget(sep())
        lay.addWidget(label("INTEGRAZIONE CON WINDOWS", "small"))
        r2 = QHBoxLayout()
        b1 = QPushButton(icons.icon("external"), "  Aggiungi a «Invia a»")
        b1.setToolTip("Tasto destro su qualsiasi immagine in Esplora risorse → Invia a → Prisma")
        b1.clicked.connect(lambda: self._shortcut("SendTo"))
        b2 = QPushButton(icons.icon("plus"), "  Collegamento sul Desktop")
        b2.clicked.connect(lambda: self._shortcut("Desktop"))
        r2.addWidget(b1)
        r2.addWidget(b2)
        r2.addStretch()
        lay.addLayout(r2)

        lay.addWidget(sep())
        lay.addWidget(label("MOTORI DI CONVERSIONE", "small"))
        t = main.tools
        for name, path, desc in (("ImageMagick", t.magick, "motore principale, 100+ formati"),
                                 ("ffmpeg", t.ffmpeg, "decoder di riserva e fotogrammi dai video"),
                                 ("texconv", t.texconv, "DDS BC4 / BC5 / BC6H / BC7")):
            r = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {OK if path else WARN};")
            r.addWidget(dot)
            r.addWidget(label(f"<b>{name}</b>  <span style='color:{MUTED}'>- {desc}</span>"))
            r.addStretch()
            lay.addLayout(r)
            pl = label(path or "Non trovato", "small")
            pl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            pl.setContentsMargins(22, 0, 0, 0)
            lay.addWidget(pl)
        if not t.texconv:
            b = QPushButton(icons.icon("download"), "  Scarica texconv (Microsoft DirectXTex, ~1 MB)")
            b.clicked.connect(main.download_texconv)
            b.clicked.connect(self.accept)
            lay.addWidget(b, 0, Qt.AlignLeft)

        lay.addWidget(sep())
        r3 = QHBoxLayout()
        bdata = QPushButton(icons.icon("folder"), "  Cartella dati")
        bdata.setObjectName("ghost")
        bdata.clicked.connect(lambda: open_path(APPDATA))
        r3.addWidget(bdata)
        r3.addStretch()
        ok = QPushButton("Fatto")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        r3.addWidget(ok)
        lay.addLayout(r3)

    def showEvent(self, e):
        dark_titlebar(self)
        super().showEvent(e)

    def _shortcut(self, where):
        ok = create_shortcut(where)
        self.main.toast.show_msg("Collegamento creato ✓" if ok else "Impossibile creare il collegamento")

    def accept(self):
        self.main.prefs["threads"] = self.threads.value()
        self.main.prefs["notify"] = self.notify.isChecked()
        self.main.prefs["sound"] = self.sound.isChecked()
        self.main.save_config()
        super().accept()


# --------------------------------------------------------------------------- #
# Preset
# --------------------------------------------------------------------------- #
BUILTIN_PRESETS = {
    "Texture gioco - DDS BC3/DXT5 + mipmap": {
        "format": "dds", "fmt_opts": {"dds": {"compression": "dxt5", "mipmaps": True, "mip_levels": "0", "cluster": True}},
    },
    "Texture automatica - DDS BC1/BC3": {
        "format": "dds", "fmt_opts": {"dds": {"compression": "auto", "mipmaps": True, "mip_levels": "0", "cluster": True}},
    },
    "Web ottimizzato - WebP 82, max 2560 px": {
        "format": "webp", "fmt_opts": {"webp": {"quality": 82, "lossless": False, "method": 6}},
        "resize": {"mode": "long", "long": 2560, "only_shrink": True}, "strip": True,
    },
    "Web moderno - AVIF 65": {"format": "avif", "fmt_opts": {"avif": {"quality": 65, "speed": 6}}, "strip": True},
    "Foto - JPG alta qualità": {"format": "jpg", "fmt_opts": {"jpg": {"quality": 92, "sampling": "4:4:4", "progressive": True}}},
    "Icona Windows - ICO multi-risoluzione": {"format": "ico"},
    "Archivio - PNG senza perdita": {"format": "png", "fmt_opts": {"png": {"level": 9, "depth": "auto"}}},
}


def deep_merge(base, over):
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


DEFAULT_SETTINGS = {
    "format": "dds",
    "fmt_opts": {},
    "resize": {"mode": "none", "percent": 50, "w": 1920, "h": 1080, "long": 2048, "only_shrink": True,
               "pot": "none", "filter": "auto"},
    "auto_orient": True, "rotate": 0, "flip": False, "flop": False, "strip": False,
    "flatten": False, "bg": "#ffffff", "density": 150, "frames": "keep",
    "out_mode": "same", "subfolder": "convertiti", "out_dir": "", "recent_dirs": [],
    "pattern": "{name}", "conflict": "rename", "keep_structure": True, "keep_date": False,
    "open_when_done": False, "skip_same": False,
}


# --------------------------------------------------------------------------- #
# Finestra principale
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self, initial_paths=()):
        super().__init__()
        self.tools = engine.Tools()
        self.jobs: dict[int, Job] = {}
        self.items: dict[int, QListWidgetItem] = {}
        self.emitter = Emitter()
        self.emitter.probed.connect(self.on_probed)
        self.emitter.started.connect(self.on_started)
        self.emitter.done.connect(self.on_done)
        self.emitter.message.connect(lambda m: self.toast.show_msg(m, 4000))
        self.probe_pool = QThreadPool(self)
        self.probe_pool.setMaxThreadCount(max(2, min(6, (os.cpu_count() or 4) // 2)))
        self.conv_pool = QThreadPool(self)
        self.running = False
        self.cancel = threading.Event()
        self.run_ids = []
        self.run_finished = 0
        self.last_out_dir = None
        self._loading = False

        self.load_config()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.app_icon())
        self.setAcceptDrops(True)
        self.setMinimumSize(980, 640)
        self.build_ui()
        self.apply_settings(self.settings)
        geo = self.prefs.get("geometry")
        if geo:
            self.restoreGeometry(bytes.fromhex(geo))
        else:
            self.resize(1280, 800)

        self.anim_timer = QTimer(self, interval=33)
        self.anim_timer.timeout.connect(self._tick)
        self.save_timer = QTimer(self, singleShot=True, interval=500)
        self.save_timer.timeout.connect(self.save_config)

        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(icons.app_icon(), self)
            self.tray.setToolTip(APP_NAME)
            self.tray.messageClicked.connect(self._bring_front)

        self.setup_shortcuts()
        if initial_paths:
            QTimer.singleShot(50, lambda: self.add_paths(list(initial_paths)))

    # ------------------------------------------------------------------ config
    def default_threads(self):
        return max(1, min(8, (os.cpu_count() or 4) // 2))

    def load_config(self):
        data = {}
        try:
            with open(CONFIG, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
        self.settings = deep_merge(DEFAULT_SETTINGS, data.get("settings", {}))
        # La risoluzione originale va sempre mantenuta all'avvio: la potenza di 2 si attiva solo
        # esplicitamente, per la sessione corrente, e non viene mai ricordata.
        self.settings["resize"]["pot"] = "none"
        self.prefs = data.get("prefs", {})
        self.user_presets = data.get("presets", {})

    def save_config(self):
        try:
            self.prefs["geometry"] = bytes(self.saveGeometry()).hex()
            self.prefs["splitter"] = bytes(self.splitter.saveState()).hex()
            st = self.get_settings()
            st["resize"]["pot"] = "none"
            data = dict(settings=st, prefs=self.prefs, presets=self.user_presets)
            tmp = CONFIG + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
            os.replace(tmp, CONFIG)
        except Exception:
            pass

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # header
        header = QWidget(objectName="header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 12, 14, 12)
        logo = QLabel()
        logo.setPixmap(icons.app_icon_pixmap(64).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        hl.addWidget(logo)
        hl.addSpacing(6)
        tl = QVBoxLayout()
        tl.setSpacing(0)
        tl.addWidget(label(APP_NAME, "h1"))
        tl.addWidget(label("Image Converter  ·  v" + APP_VERSION, "version"))
        hl.addLayout(tl)
        hl.addStretch()
        hl.addWidget(label("Preset", "muted"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(300)
        self.preset_combo.activated.connect(self.on_preset)
        hl.addWidget(self.preset_combo)
        b_save = QPushButton(icons.icon("save"), "")
        b_save.setObjectName("ghost")
        b_save.setToolTip("Salva le impostazioni correnti come preset")
        b_save.clicked.connect(self.save_preset)
        hl.addWidget(b_save)
        self.b_del_preset = QPushButton(icons.icon("trash"), "")
        self.b_del_preset.setObjectName("ghost")
        self.b_del_preset.setToolTip("Elimina un preset personale")
        self.b_del_preset.clicked.connect(self.delete_preset)
        hl.addWidget(self.b_del_preset)
        hl.addSpacing(8)
        b_set = QPushButton(icons.icon("settings"), "")
        b_set.setObjectName("ghost")
        b_set.setToolTip("Impostazioni")
        b_set.clicked.connect(lambda: SettingsDialog(self).exec())
        hl.addWidget(b_set)
        rl.addWidget(header)
        self.refresh_presets()

        # corpo
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setChildrenCollapsible(False)
        rl.addWidget(self.splitter, 1)

        # --- pannello sinistro: coda
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(14, 12, 10, 8)
        ll.setSpacing(8)
        tb = QHBoxLayout()
        tb.setSpacing(4)

        def tbtn(ic, text, tip, fn):
            b = QPushButton(icons.icon(ic), text)
            b.setObjectName("ghost")
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            tb.addWidget(b)
            return b

        tbtn("plus", " File", "Aggiungi file  (Ctrl+O)", self.pick_files)
        tbtn("folder", " Cartella", "Aggiungi una cartella, incluse le sottocartelle  (Ctrl+Shift+O)", self.pick_folder)
        tbtn("clipboard", " Incolla", "Incolla immagini o file dagli appunti  (Ctrl+V)", self.paste)
        tb.addStretch()
        self.b_clear_done = tbtn("checks", "", "Rimuovi i file completati", self.remove_done)
        self.b_remove = tbtn("x", "", "Rimuovi selezionati  (Canc)", self.remove_selected)
        self.b_clear = tbtn("trash", "", "Svuota la lista", self.clear_all)
        ll.addLayout(tb)

        self.search_wrap = QWidget()
        sw = QHBoxLayout(self.search_wrap)
        sw.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit(objectName="search")
        self.search.setPlaceholderText("Filtra per nome, formato o stato…   (Ctrl+F)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filter)
        sw.addWidget(self.search)
        sic = QLabel(self.search)
        sic.setPixmap(icons.pixmap("search", DIM, 15))
        sic.move(10, 10)
        ll.addWidget(self.search_wrap)

        self.stack = QStackedWidget()
        self.dropzone = DropZone(self.pick_files, self.pick_folder)
        self.queue = QueueList()
        self.delegate = JobDelegate(self.queue)
        self.queue.setItemDelegate(self.delegate)
        self.queue.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue.customContextMenuRequested.connect(self.context_menu)
        self.queue.itemDoubleClicked.connect(lambda it: self.preview(it.data(Qt.UserRole)))
        self.queue.preview_requested.connect(self.preview_selected)
        self.queue.delete_requested.connect(self.remove_selected)
        self.queue.itemSelectionChanged.connect(self.update_buttons)
        self.stack.addWidget(self.dropzone)
        self.stack.addWidget(self.queue)
        ll.addWidget(self.stack, 1)
        self.splitter.addWidget(left)

        # --- pannello destro: impostazioni
        panel = QWidget(objectName="panel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        self.form_l = QVBoxLayout(inner)
        self.form_l.setContentsMargins(20, 14, 20, 20)
        self.form_l.setSpacing(14)
        scroll.setWidget(inner)
        pl.addWidget(scroll)
        self.splitter.addWidget(panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        panel.setMinimumWidth(360)
        sp = self.prefs.get("splitter")
        if sp:
            self.splitter.restoreState(bytes.fromhex(sp))
        else:
            self.splitter.setSizes([820, 420])

        self.build_format_section()
        self.form_l.addWidget(sep())
        self.build_resize_section()
        self.form_l.addWidget(sep())
        self.build_adjust_section()
        self.form_l.addWidget(sep())
        self.build_output_section()
        self.form_l.addStretch()
        for c in inner.findChildren(QComboBox):
            c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(6)
            c.view().setMinimumWidth(320)
            c.view().setTextElideMode(Qt.ElideRight)

        # footer
        footer = QWidget(objectName="footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(18, 12, 18, 12)
        fl.setSpacing(14)
        info = QVBoxLayout()
        info.setSpacing(6)
        self.status = label("Nessun file in coda", "muted")
        info.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        info.addWidget(self.progress)
        fl.addLayout(info, 1)
        self.b_open_out = QPushButton(icons.icon("external"), "  Apri cartella")
        self.b_open_out.setToolTip("Apri la cartella con i file convertiti")
        self.b_open_out.clicked.connect(self.open_out_dir)
        self.b_open_out.hide()
        fl.addWidget(self.b_open_out)
        self.b_convert = QPushButton(icons.icon("zap", "#ffffff"), "  Converti")
        self.b_convert.setObjectName("primary")
        self.b_convert.setCursor(Qt.PointingHandCursor)
        self.b_convert.setToolTip("Avvia la conversione  (Ctrl+Invio)")
        self.b_convert.clicked.connect(self.toggle_run)
        self.b_convert.setMinimumWidth(170)
        fl.addWidget(self.b_convert)
        rl.addWidget(footer)

        self.overlay = DropOverlay(root)
        self.toast = Toast(root)
        self.update_buttons()

    # ---- sezione formato
    def build_format_section(self):
        box = QWidget()
        l = QVBoxLayout(box)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(6)
        self.fmt_group = QButtonGroup(self)
        self.fmt_group.setExclusive(True)
        self.fmt_buttons = {}
        pop = [f for f in engine.FORMATS if f.popular]
        for i, f in enumerate(pop):
            b = QPushButton(f.label)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(f.desc)
            b.clicked.connect(lambda _=False, k=f.key: self.set_format(k))
            self.fmt_group.addButton(b)
            self.fmt_buttons[f.key] = b
            grid.addWidget(b, i // 4, i % 4)
        l.addLayout(grid)
        self.more_fmt = QComboBox()
        self.more_fmt.addItem("Altri formati…", None)
        for f in engine.FORMATS:
            if not f.popular:
                self.more_fmt.addItem(f"{f.label}   ·   {f.desc}", f.key)
        self.more_fmt.activated.connect(lambda i: self.more_fmt.itemData(i) and self.set_format(self.more_fmt.itemData(i)))
        l.addWidget(self.more_fmt)
        self.fmt_desc = label("", "small", True)
        l.addWidget(self.fmt_desc)

        self.opt_forms = {}
        l.addSpacing(4)
        for f in engine.FORMATS:
            form = OptionForm(engine.FORMAT_OPTIONS.get(f.key, []), self.tools)
            form.changed.connect(self.on_changed)
            form.hide()
            self.opt_forms[f.key] = form
            l.addWidget(form)

        self.dds_warn = label("", "warn", True)
        self.dds_warn.hide()
        l.addWidget(self.dds_warn)
        self.dds_fix = QPushButton("Arrotonda a potenza di 2")
        self.dds_fix.setObjectName("mini")
        self.dds_fix.clicked.connect(lambda: (self.pot.setCurrentIndex(self.pot.findData("nearest")), self.on_changed()))
        self.dds_fix.hide()
        l.addWidget(self.dds_fix, 0, Qt.AlignLeft)
        self.texconv_info = QWidget()
        ti = QHBoxLayout(self.texconv_info)
        ti.setContentsMargins(0, 0, 0, 0)
        ti.addWidget(label("BC7, BC4, BC5 e BC6H richiedono texconv.", "small", True), 1)
        bdl = QPushButton(icons.icon("download"), " Scarica")
        bdl.setObjectName("mini")
        bdl.clicked.connect(self.download_texconv)
        ti.addWidget(bdl)
        l.addWidget(self.texconv_info)
        self.form_l.addWidget(Section("Formato di uscita", box))

    # ---- sezione ridimensiona
    def build_resize_section(self):
        box = QWidget()
        l = QVBoxLayout(box)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(10)
        self.rz_mode = QComboBox()
        for t, v in (("Dimensioni originali", "none"), ("Percentuale", "percent"), ("Adatta in un riquadro (L × A)", "fit"),
                     ("Lato lungo", "long"), ("Dimensioni esatte (deforma)", "exact"), ("Riempi e ritaglia al centro", "fill")):
            self.rz_mode.addItem(t, v)
        self.rz_mode.currentIndexChanged.connect(self.on_changed)
        l.addWidget(self.rz_mode)

        def spin(lo, hi, suffix, special=None):
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setSuffix(suffix)
            if special:
                s.setSpecialValueText(special)
            s.valueChanged.connect(self.on_changed)
            return s

        self.rz_percent = spin(1, 1000, " %")
        self.rz_w = spin(0, 32768, " px", "auto")
        self.rz_h = spin(0, 32768, " px", "auto")
        self.rz_long = spin(1, 32768, " px")
        self.row_percent = QWidget()
        rp = QHBoxLayout(self.row_percent)
        rp.setContentsMargins(0, 0, 0, 0)
        rp.addWidget(QLabel("Scala"))
        rp.addStretch()
        rp.addWidget(self.rz_percent)
        for v in (25, 50, 200):
            b = QPushButton(f"{v}%")
            b.setObjectName("mini")
            b.clicked.connect(lambda _=False, v=v: self.rz_percent.setValue(v))
            rp.addWidget(b)
        self.row_wh = QWidget()
        rw = QHBoxLayout(self.row_wh)
        rw.setContentsMargins(0, 0, 0, 0)
        rw.addWidget(QLabel("L"))
        rw.addWidget(self.rz_w, 1)
        swap = QPushButton("⇄")
        swap.setObjectName("mini")
        swap.setToolTip("Scambia larghezza e altezza")
        swap.clicked.connect(self._swap_wh)
        rw.addWidget(swap)
        rw.addWidget(QLabel("A"))
        rw.addWidget(self.rz_h, 1)
        self.row_wh_presets = QWidget()
        rwp = QHBoxLayout(self.row_wh_presets)
        rwp.setContentsMargins(0, 0, 0, 0)
        rwp.setSpacing(5)
        for a, b_ in ((512, 512), (1024, 1024), (2048, 2048), (1280, 720), (1920, 1080), (3840, 2160)):
            b = QPushButton(f"{a}×{b_}" if a != b_ else f"{a}²")
            b.setObjectName("mini")
            b.clicked.connect(lambda _=False, a=a, b_=b_: (self.rz_w.setValue(a), self.rz_h.setValue(b_)))
            rwp.addWidget(b)
        rwp.addStretch()
        self.row_long = QWidget()
        rlg = QHBoxLayout(self.row_long)
        rlg.setContentsMargins(0, 0, 0, 0)
        rlg.addWidget(QLabel("Lato lungo"))
        rlg.addStretch()
        rlg.addWidget(self.rz_long)
        for v in (1024, 2048, 4096):
            b = QPushButton(str(v))
            b.setObjectName("mini")
            b.clicked.connect(lambda _=False, v=v: self.rz_long.setValue(v))
            rlg.addWidget(b)
        for w in (self.row_percent, self.row_wh, self.row_wh_presets, self.row_long):
            l.addWidget(w)
        self.rz_shrink = QCheckBox("Solo riduci (non ingrandire le immagini piccole)")
        self.rz_shrink.toggled.connect(self.on_changed)
        l.addWidget(self.rz_shrink)

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        self.pot_label = QLabel("Potenza di 2")
        self.pot_label.setToolTip("Solo per texture DDS")
        g.addWidget(self.pot_label, 0, 0)
        self.pot = QComboBox()
        for t, v in (("Disattivata", "none"), ("Più vicina", "nearest"), ("Per eccesso", "up"), ("Per difetto", "down"),
                     ("Multiplo di 4", "mul4")):
            self.pot.addItem(t, v)
        self.pot.setToolTip("Utile per le texture: 1000×700 → 1024×512")
        self.pot.currentIndexChanged.connect(self.on_changed)
        g.addWidget(self.pot, 0, 1)
        g.addWidget(QLabel("Filtro"), 1, 0)
        self.rz_filter = QComboBox()
        for t, v in (("Automatico", "auto"), ("Lanczos (nitido)", "Lanczos"), ("Mitchell (morbido)", "Mitchell"),
                     ("Catrom", "Catrom"), ("Pixel art (vicino più prossimo)", "Point")):
            self.rz_filter.addItem(t, v)
        self.rz_filter.currentIndexChanged.connect(self.on_changed)
        g.addWidget(self.rz_filter, 1, 1)
        g.setColumnStretch(1, 1)
        l.addLayout(g)
        self.rz_preview = label("", "small", True)
        l.addWidget(self.rz_preview)
        self.form_l.addWidget(Section("Ridimensiona", box))

    def _swap_wh(self):
        w, h = self.rz_w.value(), self.rz_h.value()
        self.rz_w.setValue(h)
        self.rz_h.setValue(w)

    # ---- sezione regolazioni
    def build_adjust_section(self):
        box = QWidget()
        l = QVBoxLayout(box)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(9)
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        g.addWidget(QLabel("Rotazione"), 0, 0)
        self.rotate = QComboBox()
        for t, v in (("Nessuna", 0), ("90° orario", 90), ("180°", 180), ("90° antiorario", 270)):
            self.rotate.addItem(t, v)
        self.rotate.currentIndexChanged.connect(self.on_changed)
        g.addWidget(self.rotate, 0, 1)
        g.addWidget(QLabel("Frame / pagine"), 1, 0)
        self.frames = QComboBox()
        for t, v in (("Mantieni (GIF, WEBP, TIFF, PDF…)", "keep"), ("Solo il primo", "first"),
                     ("Ognuno in un file separato", "separate")):
            self.frames.addItem(t, v)
        self.frames.setToolTip("Come gestire GIF animate, TIFF/PDF multipagina, livelli PSD")
        self.frames.currentIndexChanged.connect(self.on_changed)
        g.addWidget(self.frames, 1, 1)
        g.addWidget(QLabel("DPI vettoriali"), 2, 0)
        self.density = QSpinBox()
        self.density.setRange(36, 1200)
        self.density.setSuffix(" dpi")
        self.density.setToolTip("Risoluzione di rasterizzazione per SVG, PDF, EPS, AI")
        self.density.valueChanged.connect(self.on_changed)
        g.addWidget(self.density, 2, 1)
        g.setColumnStretch(1, 1)
        l.addLayout(g)
        r = QHBoxLayout()
        self.flop = QCheckBox("Specchia ↔")
        self.flip = QCheckBox("Capovolgi ↕")
        for c in (self.flop, self.flip):
            c.toggled.connect(self.on_changed)
            r.addWidget(c)
        r.addStretch()
        l.addLayout(r)
        self.auto_orient = QCheckBox("Raddrizza automaticamente (orientamento EXIF)")
        self.strip = QCheckBox("Rimuovi metadati (EXIF, GPS, profili)")
        self.strip.setToolTip("File più leggeri e niente dati di posizione nelle foto")
        for c in (self.auto_orient, self.strip):
            c.toggled.connect(self.on_changed)
            l.addWidget(c)
        r2 = QHBoxLayout()
        self.flatten = QCheckBox("Elimina trasparenza, sfondo:")
        self.flatten.setToolTip("Per i formati senza alpha (JPG, BMP…) lo sfondo viene applicato sempre")
        self.flatten.toggled.connect(self.on_changed)
        r2.addWidget(self.flatten)
        self.bg_btn = QPushButton("")
        self.bg_btn.setObjectName("swatch")
        self.bg_btn.setCursor(Qt.PointingHandCursor)
        self.bg_btn.clicked.connect(self.pick_bg)
        r2.addWidget(self.bg_btn)
        for c in ("#ffffff", "#000000", "#808080"):
            b = QPushButton("")
            b.setObjectName("swatch")
            b.setFixedSize(20, 20)
            b.setStyleSheet(f"background:{c}; border:1px solid #3a4152; border-radius:5px; min-width:20px; max-width:20px; min-height:20px; max-height:20px;")
            b.clicked.connect(lambda _=False, c=c: self.set_bg(c))
            r2.addWidget(b)
        r2.addStretch()
        l.addLayout(r2)
        self.form_l.addWidget(Section("Regolazioni", box))

    def pick_bg(self):
        c = QColorDialog.getColor(QColor(self._bg), self, "Colore di sfondo")
        if c.isValid():
            self.set_bg(c.name())

    def set_bg(self, c):
        self._bg = c
        self.bg_btn.setStyleSheet(f"background:{c}; border:1px solid #4a5163;")
        self.on_changed()

    # ---- sezione destinazione
    def build_output_section(self):
        box = QWidget()
        l = QVBoxLayout(box)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(9)
        self.out_mode = QComboBox()
        for t, v in (("Stessa cartella dell'originale", "same"), ("Sottocartella accanto all'originale", "sub"),
                     ("Cartella a scelta", "custom")):
            self.out_mode.addItem(t, v)
        self.out_mode.currentIndexChanged.connect(self.on_changed)
        l.addWidget(self.out_mode)
        self.row_sub = QWidget()
        rs = QHBoxLayout(self.row_sub)
        rs.setContentsMargins(0, 0, 0, 0)
        rs.addWidget(QLabel("Nome sottocartella"))
        self.subfolder = QLineEdit()
        self.subfolder.textChanged.connect(self.on_changed)
        rs.addWidget(self.subfolder, 1)
        l.addWidget(self.row_sub)
        self.row_dir = QWidget()
        rd = QHBoxLayout(self.row_dir)
        rd.setContentsMargins(0, 0, 0, 0)
        rd.setSpacing(6)
        self.out_dir = QComboBox()
        self.out_dir.setEditable(True)
        self.out_dir.lineEdit().setPlaceholderText("Scegli o trascina qui una cartella…")
        self.out_dir.setInsertPolicy(QComboBox.NoInsert)
        self.out_dir.currentTextChanged.connect(self.on_changed)
        self.out_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.out_dir.setMinimumContentsLength(10)
        rd.addWidget(self.out_dir, 1)
        bdir = QPushButton(icons.icon("folder"), "")
        bdir.setToolTip("Sfoglia…")
        bdir.clicked.connect(self.pick_out_dir)
        rd.addWidget(bdir)
        l.addWidget(self.row_dir)
        self.keep_structure = QCheckBox("Ricrea la struttura delle sottocartelle")
        self.keep_structure.toggled.connect(self.on_changed)
        l.addWidget(self.keep_structure)

        l.addSpacing(4)
        l.addWidget(QLabel("Nome dei file"))
        self.pattern = QLineEdit()
        self.pattern.setPlaceholderText("{name}")
        self.pattern.textChanged.connect(self.on_changed)
        l.addWidget(self.pattern)
        tok = QHBoxLayout()
        tok.setSpacing(4)
        for t, tip in (("{name}", "Nome originale"), ("{w}", "Larghezza finale"), ("{h}", "Altezza finale"),
                       ("{n}", "Numero progressivo 001, 002…"), ("{date}", "Data di oggi"), ("{fmt}", "Formato di uscita"),
                       ("{parent}", "Nome della cartella di origine")):
            b = QPushButton(t)
            b.setObjectName("mini")
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, t=t: self._insert_token(t))
            tok.addWidget(b)
        tok.addStretch()
        l.addLayout(tok)
        self.name_preview = label("", "info", True)
        self.name_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l.addWidget(self.name_preview)

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.addWidget(QLabel("Se il file esiste"), 0, 0)
        self.conflict = QComboBox()
        for t, v in (("Rinomina - foto (2).png", "rename"), ("Sovrascrivi", "overwrite"), ("Salta", "skip")):
            self.conflict.addItem(t, v)
        self.conflict.currentIndexChanged.connect(self.on_changed)
        g.addWidget(self.conflict, 0, 1)
        g.setColumnStretch(1, 1)
        l.addLayout(g)
        self.keep_date = QCheckBox("Mantieni la data di modifica originale")
        self.skip_same = QCheckBox("Salta i file già nel formato di destinazione")
        self.open_when_done = QCheckBox("Apri la cartella al termine")
        for c in (self.keep_date, self.skip_same, self.open_when_done):
            c.toggled.connect(self.on_changed)
            l.addWidget(c)
        self.form_l.addWidget(Section("Destinazione", box))

    def _insert_token(self, t):
        self.pattern.insert(t)
        self.pattern.setFocus()

    def pick_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Cartella di destinazione", self.out_dir.currentText() or "")
        if d:
            self.out_dir.setCurrentText(os.path.normpath(d))
            self.out_mode.setCurrentIndex(self.out_mode.findData("custom"))

    # ------------------------------------------------------------------ settings <-> UI
    def current_format(self):
        return self._format

    def set_format(self, key):
        self._format = key
        f = engine.FMT[key]
        self.fmt_group.setExclusive(False)
        for k, b in self.fmt_buttons.items():
            b.setChecked(k == key)
        self.fmt_group.setExclusive(True)
        idx = self.more_fmt.findData(key)
        self.more_fmt.setCurrentIndex(idx if idx >= 0 else 0)
        for k, form in self.opt_forms.items():
            form.setVisible(k == key)
        alpha = "supporta la trasparenza" if f.alpha else "senza trasparenza"
        self.fmt_desc.setText(f"<b>{f.label}</b> ({f.ext}) - {f.desc}  <span style='color:{DIM}'>· {alpha}</span>")
        self.on_changed()

    def get_settings(self):
        s = {
            "format": self._format,
            "fmt_opts": dict(self._fmt_opts_store),
            "resize": {
                "mode": self.rz_mode.currentData(), "percent": self.rz_percent.value(), "w": self.rz_w.value(),
                "h": self.rz_h.value(), "long": self.rz_long.value(), "only_shrink": self.rz_shrink.isChecked(),
                "pot": self.pot.currentData(), "filter": self.rz_filter.currentData(),
            },
            "auto_orient": self.auto_orient.isChecked(), "rotate": self.rotate.currentData(),
            "flip": self.flip.isChecked(), "flop": self.flop.isChecked(), "strip": self.strip.isChecked(),
            "flatten": self.flatten.isChecked(), "bg": self._bg, "density": self.density.value(),
            "frames": self.frames.currentData(),
            "out_mode": self.out_mode.currentData(), "subfolder": self.subfolder.text().strip() or "convertiti",
            "out_dir": self.out_dir.currentText().strip().strip('"'), "recent_dirs": self._recent_dirs,
            "pattern": self.pattern.text() or "{name}", "conflict": self.conflict.currentData(),
            "keep_structure": self.keep_structure.isChecked(), "keep_date": self.keep_date.isChecked(),
            "open_when_done": self.open_when_done.isChecked(), "skip_same": self.skip_same.isChecked(),
        }
        for k, form in self.opt_forms.items():
            s["fmt_opts"][k] = form.get()
        return s

    def apply_settings(self, s):
        self._loading = True
        s = deep_merge(DEFAULT_SETTINGS, s)
        self._fmt_opts_store = dict(s.get("fmt_opts", {}))
        for k, form in self.opt_forms.items():
            form.set(self._fmt_opts_store.get(k, {}))
        r = s["resize"]

        def setc(c, v):
            i = c.findData(v)
            c.setCurrentIndex(i if i >= 0 else 0)

        setc(self.rz_mode, r["mode"])
        self.rz_percent.setValue(r["percent"])
        self.rz_w.setValue(r["w"])
        self.rz_h.setValue(r["h"])
        self.rz_long.setValue(r["long"])
        self.rz_shrink.setChecked(r["only_shrink"])
        setc(self.pot, r["pot"])
        setc(self.rz_filter, r["filter"])
        self.auto_orient.setChecked(s["auto_orient"])
        setc(self.rotate, s["rotate"])
        self.flip.setChecked(s["flip"])
        self.flop.setChecked(s["flop"])
        self.strip.setChecked(s["strip"])
        self.flatten.setChecked(s["flatten"])
        self._bg = s["bg"]
        self.bg_btn.setStyleSheet(f"background:{self._bg}; border:1px solid #4a5163;")
        self.density.setValue(s["density"])
        setc(self.frames, s["frames"])
        setc(self.out_mode, s["out_mode"])
        self.subfolder.setText(s["subfolder"])
        self._recent_dirs = [d for d in s.get("recent_dirs", []) if d][:10]
        self.out_dir.clear()
        self.out_dir.addItems(self._recent_dirs)
        self.out_dir.setCurrentText(s["out_dir"])
        self.pattern.setText(s["pattern"])
        setc(self.conflict, s["conflict"])
        self.keep_structure.setChecked(s["keep_structure"])
        self.keep_date.setChecked(s["keep_date"])
        self.open_when_done.setChecked(s["open_when_done"])
        self.skip_same.setChecked(s["skip_same"])
        self._loading = False
        self.set_format(s["format"] if s["format"] in engine.FMT else "png")

    def on_changed(self, *a):
        if self._loading:
            return
        mode = self.rz_mode.currentData()
        self.row_percent.setVisible(mode == "percent")
        self.row_wh.setVisible(mode in ("fit", "exact", "fill"))
        self.row_wh_presets.setVisible(mode in ("fit", "exact", "fill"))
        self.row_long.setVisible(mode == "long")
        self.rz_shrink.setVisible(mode in ("percent", "fit", "long"))
        om = self.out_mode.currentData()
        self.row_sub.setVisible(om == "sub")
        self.row_dir.setVisible(om == "custom")
        self.keep_structure.setVisible(om == "custom")
        is_dds = getattr(self, "_format", "") == "dds"
        self.pot.setVisible(is_dds)
        self.pot_label.setVisible(is_dds)
        self.texconv_info.setVisible(is_dds and not self.tools.texconv)
        self.refresh_previews()
        if hasattr(self, "save_timer"):
            self.save_timer.start()

    def refresh_previews(self):
        if not hasattr(self, "_format"):
            return
        s = self.get_settings()
        fmt = engine.FMT[s["format"]]
        sample = None
        for i in range(self.queue.count()):
            j = self.queue.item(i).data(Qt.UserRole)
            if j.w:
                sample = j
                break
        if sample is None and self.queue.count():
            sample = self.queue.item(0).data(Qt.UserRole)
        if sample:
            dims = engine.predict_dims(sample.w, sample.h, s) if sample.w else (0, 0)
            name = engine.output_name(sample.snapshot(), s, fmt, 0, dims)
            folder = engine.output_folder(sample.snapshot(), s)
            self.name_preview.setText(f"<b>{name}</b><br><span style='color:{MUTED}'>{folder}</span>")
            if sample.w:
                self.rz_preview.setText(f"Esempio: {sample.w}×{sample.h} → <b>{dims[0]}×{dims[1]}</b>  ({sample.name})")
            else:
                self.rz_preview.setText("")
        else:
            dummy = dict(path=os.path.join("C:\\", "Immagini", "foto.png"), rel="")
            name = engine.output_name(dummy, s, fmt, 0, engine.predict_dims(1920, 1080, s))
            self.name_preview.setText(f"Esempio: <b>{name}</b>")
            self.rz_preview.setText("")
        # avvisi DDS
        warn = ""
        for j in self.jobs.values():
            j.target = engine.predict_dims(j.w, j.h, s) if j.w else None
        self.queue.viewport().update()
        if s["format"] == "dds" and s["resize"]["pot"] in ("none", "mul4"):
            dims = [engine.predict_dims(j.w, j.h, s) for j in self.jobs.values() if j.w]
            bad = [d for d in dims if d[0] % 4 or d[1] % 4]
            npot = [d for d in dims if d[0] & (d[0] - 1) or d[1] & (d[1] - 1)]
            dds_o = s["fmt_opts"].get("dds", {})
            mip_by_magick = dds_o.get("mipmaps") and dds_o.get("compression") not in engine.TEXCONV_FMT
            if npot and mip_by_magick:
                warn = (f"{len(npot)} immagini non hanno lati potenza di 2: per queste le mipmap non verranno "
                        f"generate. Arrotonda le dimensioni (es. 1000×700 → 1024×512).")
            elif bad:
                warn = (f"{len(bad)} immagini hanno lati non multipli di 4: molti motori grafici non accettano "
                        f"texture compresse con queste dimensioni.")
        self.dds_warn.setText("⚠  " + warn)
        self.dds_warn.setVisible(bool(warn))
        self.dds_fix.setVisible(bool(warn))
        if s["out_mode"] == "custom" and not s["out_dir"]:
            self.name_preview.setText(f"<span style='color:{WARN}'>Scegli una cartella di destinazione</span>")

    # ------------------------------------------------------------------ preset
    def refresh_presets(self):
        self.preset_combo.clear()
        self.preset_combo.addItem("Scegli un preset…", None)
        for n in BUILTIN_PRESETS:
            self.preset_combo.addItem(n, ("b", n))
        for n in self.user_presets:
            self.preset_combo.addItem("★  " + n, ("u", n))
        self.b_del_preset.setEnabled(bool(self.user_presets))

    def on_preset(self, i):
        d = self.preset_combo.itemData(i)
        if not d:
            return
        kind, name = d
        p = BUILTIN_PRESETS[name] if kind == "b" else self.user_presets[name]
        cur = self.get_settings()
        if kind == "b":
            # i preset predefiniti toccano solo formato e qualità, non la destinazione
            base = deep_merge(cur, {"resize": DEFAULT_SETTINGS["resize"]}) if "resize" in p else cur
            new = deep_merge(base, p)
        else:
            new = deep_merge(cur, p)
        self.apply_settings(new)
        self.preset_combo.setCurrentIndex(0)
        self.toast.show_msg(f"Preset applicato: {name}")

    def save_preset(self):
        name, ok = QInputDialog.getText(self, "Salva preset", "Nome del preset:")
        name = (name or "").strip()
        if ok and name:
            s = self.get_settings()
            s.pop("recent_dirs", None)
            s["resize"]["pot"] = "none"
            self.user_presets[name] = s
            self.refresh_presets()
            self.save_config()
            self.toast.show_msg(f"Preset «{name}» salvato")

    def delete_preset(self):
        if not self.user_presets:
            return
        name, ok = QInputDialog.getItem(self, "Elimina preset", "Preset da eliminare:", list(self.user_presets), 0, False)
        if ok and name:
            self.user_presets.pop(name, None)
            self.refresh_presets()
            self.save_config()

    # ------------------------------------------------------------------ aggiunta file
    def pick_files(self):
        exts = " ".join(f"*.{e}" for e in sorted(engine.INPUT_EXT))
        files, _ = QFileDialog.getOpenFileNames(self, "Aggiungi immagini", self.prefs.get("last_dir", ""),
                                                f"Immagini supportate ({exts});;Tutti i file (*.*)")
        if files:
            self.prefs["last_dir"] = os.path.dirname(files[0])
            self.add_paths(files)

    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Aggiungi cartella", self.prefs.get("last_dir", ""))
        if d:
            self.prefs["last_dir"] = d
            self.add_paths([d])

    def paste(self):
        md = QGuiApplication.clipboard().mimeData()
        if md.hasUrls() and any(u.isLocalFile() for u in md.urls()):
            self.add_paths([u.toLocalFile() for u in md.urls() if u.isLocalFile()])
        elif md.hasImage():
            img = QGuiApplication.clipboard().image()
            if img.isNull():
                return
            d = os.path.join(APPDATA, "appunti")
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, "appunti_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")
            img.save(p, "PNG")
            self.add_paths([p], temp=True)
        elif md.hasText():
            paths = [t.strip().strip('"') for t in md.text().splitlines() if t.strip()]
            paths = [p for p in paths if os.path.exists(p)]
            if paths:
                self.add_paths(paths)
            else:
                self.toast.show_msg("Negli appunti non ci sono immagini")
        else:
            self.toast.show_msg("Negli appunti non ci sono immagini")

    def add_paths(self, paths, temp=False):
        existing = {os.path.normcase(os.path.abspath(j.path)) for j in self.jobs.values()}
        added = dup = unsup = 0
        new = []
        for p in paths:
            p = os.path.abspath(p)
            if os.path.isdir(p):
                for dp, dns, fns in os.walk(p):
                    dns.sort()
                    for fn in sorted(fns):
                        fp = os.path.join(dp, fn)
                        if not engine.is_supported(fp):
                            continue
                        rel = os.path.relpath(dp, p)
                        new.append((fp, "" if rel == "." else rel))
            elif os.path.isfile(p):
                if engine.is_supported(p):
                    new.append((p, ""))
                else:
                    unsup += 1
        self.queue.setUpdatesEnabled(False)
        for fp, rel in new:
            key = os.path.normcase(fp)
            if key in existing or fp.endswith(".prisma-part"):
                dup += 1
                continue
            existing.add(key)
            job = Job(fp, rel, temp)
            self.jobs[job.id] = job
            it = QListWidgetItem()
            it.setData(Qt.UserRole, job)
            it.setSizeHint(QSize(100, JobDelegate.ROW_H))
            self.queue.addItem(it)
            self.items[job.id] = it
            self.probe_pool.start(ProbeTask(job.id, fp, self.tools, self.emitter))
            added += 1
        self.queue.setUpdatesEnabled(True)
        msg = []
        if added:
            msg.append(f"Aggiunti {added} file")
        if dup:
            msg.append(f"{dup} già in lista")
        if unsup:
            msg.append(f"{unsup} non supportati")
        if msg:
            self.toast.show_msg("  ·  ".join(msg))
        if added and self.search.text():
            self.apply_filter()
        self.update_buttons()
        self.refresh_previews()

    def on_probed(self, jid, info):
        job = self.jobs.get(jid)
        if not job:
            return
        job.w, job.h = info.get("w", 0), info.get("h", 0)
        job.fmt = info.get("fmt") or job.fmt
        job.alpha = info.get("alpha", False)
        job.frames = info.get("frames", 1)
        job.probe_error = info.get("error")
        job.probed = True
        if info.get("thumb"):
            img = QImage.fromData(info["thumb"])
            if not img.isNull():
                pm = QPixmap.fromImage(img.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                pm.setDevicePixelRatio(2.0)
                job.thumb = pm
        it = self.items.get(jid)
        if it:
            self.queue.update(self.queue.indexFromItem(it))
        if not hasattr(self, "_pv_timer"):
            self._pv_timer = QTimer(self, singleShot=True, interval=150)
            self._pv_timer.timeout.connect(self.refresh_previews)
        self._pv_timer.start()

    # ------------------------------------------------------------------ lista
    def selected_jobs(self):
        return [it.data(Qt.UserRole) for it in self.queue.selectedItems()]

    def _remove(self, jobs):
        busy = [j for j in jobs if j.status in ("queued", "working")]
        for j in jobs:
            if j.status in ("queued", "working"):
                continue
            it = self.items.pop(j.id, None)
            self.jobs.pop(j.id, None)
            if it:
                self.queue.takeItem(self.queue.row(it))
        if busy:
            self.toast.show_msg(f"{len(busy)} file in conversione non possono essere rimossi ora")
        self.update_buttons()
        self.refresh_previews()

    def remove_selected(self):
        self._remove(self.selected_jobs())

    def remove_done(self):
        self._remove([j for j in self.jobs.values() if j.status == "done"])

    def clear_all(self):
        self._remove(list(self.jobs.values()))

    def apply_filter(self):
        q = self.search.text().strip().lower()
        stat = {"errori": "error", "errore": "error", "fatti": "done", "completati": "done", "saltati": "skipped"}
        for i in range(self.queue.count()):
            it = self.queue.item(i)
            j: Job = it.data(Qt.UserRole)
            hay = f"{j.name} {j.fmt} {j.ext}".lower()
            it.setHidden(bool(q) and q not in hay and stat.get(q) != j.status)

    def update_buttons(self):
        n = len(self.jobs)
        self.stack.setCurrentWidget(self.queue if n else self.dropzone)
        self.search_wrap.setVisible(n > 0)
        self.b_remove.setEnabled(bool(self.queue.selectedItems()))
        self.b_clear.setEnabled(n > 0 and not self.running)
        self.b_clear_done.setEnabled(any(j.status == "done" for j in self.jobs.values()))
        if not self.running:
            self.b_convert.setEnabled(n > 0)
            if n:
                total = sum(j.size for j in self.jobs.values())
                pend = sum(1 for j in self.jobs.values() if j.status in ("pending", "error", "cancelled"))
                txt = f"{n} file  ·  {human(total)}"
                if pend and pend != n:
                    txt += f"  ·  {pend} da convertire"
                if not getattr(self, "_summary", None):
                    self.status.setText(txt)
            else:
                self._summary = None
                self.status.setText("Nessun file in coda  ·  trascina immagini o cartelle nella finestra")
                self.progress.setRange(0, 1)
                self.progress.setValue(0)
                self.b_open_out.hide()

    def context_menu(self, pos):
        it = self.queue.itemAt(pos)
        if not it:
            return
        if not it.isSelected():
            self.queue.clearSelection()
            it.setSelected(True)
        jobs = self.selected_jobs()
        j = jobs[0]
        m = QMenu(self)
        m.addAction(icons.icon("eye"), "Anteprima\tSpazio", lambda: self.preview(j))
        m.addSeparator()
        m.addAction(icons.icon("image"), "Apri originale", lambda: open_path(j.path))
        a = m.addAction(icons.icon("image"), "Apri convertito", lambda: open_path(j.out))
        a.setEnabled(j.status == "done")
        m.addAction(icons.icon("folder"), "Mostra originale in Esplora risorse", lambda: reveal(j.path))
        a = m.addAction(icons.icon("folder"), "Mostra convertito in Esplora risorse", lambda: reveal(j.out))
        a.setEnabled(j.status == "done")
        m.addSeparator()
        m.addAction(icons.icon("copy"), "Copia percorso", lambda: QGuiApplication.clipboard().setText(
            "\n".join(x.out if x.status == "done" and x.out else x.path for x in jobs)))
        if j.status == "error":
            m.addAction(icons.icon("copy"), "Copia messaggio di errore",
                        lambda: QGuiApplication.clipboard().setText(j.msg))
        a = m.addAction(icons.icon("refresh"), "Converti di nuovo i selezionati", lambda: self.start_run(jobs))
        a.setEnabled(not self.running)
        m.addSeparator()
        m.addAction(icons.icon("x"), "Rimuovi dalla lista\tCanc", self.remove_selected)
        m.exec(self.queue.viewport().mapToGlobal(pos))

    def preview_selected(self):
        jobs = self.selected_jobs() or ([self.queue.currentItem().data(Qt.UserRole)] if self.queue.currentItem() else [])
        if jobs:
            self.preview(jobs[0])

    def preview(self, job):
        PreviewDialog(self, job, self.tools).exec()

    # ------------------------------------------------------------------ conversione
    def toggle_run(self):
        if self.running:
            self.cancel.set()
            self.b_convert.setEnabled(False)
            self.b_convert.setText("  Annullamento…")
        else:
            self.start_run()

    def start_run(self, only=None):
        if self.running or not self.jobs:
            return
        s = self.get_settings()
        if s["out_mode"] == "custom":
            if not s["out_dir"]:
                self.toast.show_msg("Scegli prima una cartella di destinazione")
                self.pick_out_dir()
                s = self.get_settings()
                if not s["out_dir"]:
                    return
            try:
                os.makedirs(s["out_dir"], exist_ok=True)
            except OSError as e:
                QMessageBox.warning(self, APP_NAME, f"Impossibile creare la cartella di destinazione:\n{e}")
                return
            d = os.path.normpath(s["out_dir"])
            self._recent_dirs = [d] + [x for x in self._recent_dirs if os.path.normcase(x) != os.path.normcase(d)]
            self._recent_dirs = self._recent_dirs[:10]
            self._loading = True
            self.out_dir.clear()
            self.out_dir.addItems(self._recent_dirs)
            self.out_dir.setCurrentText(d)
            self._loading = False
            s["recent_dirs"] = self._recent_dirs
        if s["format"] == "dds":
            comp = s["fmt_opts"]["dds"]["compression"]
            if comp in engine.TEXCONV_FMT and not self.tools.texconv:
                self.toast.show_msg("Questa compressione richiede texconv: scaricalo dalle impostazioni")
                return

        order = [self.queue.item(i).data(Qt.UserRole) for i in range(self.queue.count())]
        if only:
            ids = {j.id for j in only}
            todo = [j for j in order if j.id in ids]
        else:
            todo = [j for j in order if j.status in ("pending", "error", "cancelled")]
            if not todo:
                todo = order  # tutto già fatto: riconverti tutto con le nuove impostazioni
        if not todo:
            return
        self.save_config()
        engine.reset_reservations()
        self.cancel = threading.Event()
        threads = self.prefs.get("threads", self.default_threads())
        self.conv_pool.setMaxThreadCount(threads)
        tpj = max(1, (os.cpu_count() or 4) // threads)
        self.running = True
        self._summary = None
        self.run_ids = [j.id for j in todo]
        self.run_finished = 0
        self.run_t0 = time.perf_counter()
        self.last_out_dir = None
        for i, j in enumerate(todo):
            j.status = "queued"
            j.msg = ""
            j.out = None
            j.outs = []
            self.conv_pool.start(ConvertTask(j.id, j.snapshot(), s, self.tools, self.emitter, self.cancel, i, tpj))
        self.progress.setRange(0, len(todo))
        self.progress.setValue(0)
        self.b_convert.setText("  Annulla")
        self.b_convert.setIcon(icons.icon("x", "#ffb3c1"))
        self.b_convert.setObjectName("danger")
        self.b_convert.setStyle(self.b_convert.style())
        self.b_convert.setToolTip("Interrompi la conversione  (Esc)")
        self.b_open_out.hide()
        self.status.setText(f"Conversione di {len(todo)} file in {engine.FMT[s['format']].label}…")
        self.anim_timer.start()
        self.update_buttons()
        self.queue.viewport().update()

    def on_started(self, jid):
        j = self.jobs.get(jid)
        if j:
            j.status = "working"

    def on_done(self, jid, res):
        j = self.jobs.get(jid)
        if j:
            j.status = res.get("status", "error")
            j.msg = res.get("msg", "")
            j.out = res.get("out")
            j.outs = res.get("outs", [])
            j.out_size = res.get("size", 0)
            j.elapsed = res.get("elapsed", 0)
            if j.out:
                self.last_out_dir = os.path.dirname(j.out)
            it = self.items.get(jid)
            if it:
                self.queue.update(self.queue.indexFromItem(it))
        self.run_finished += 1
        self.progress.setValue(self.run_finished)
        pct = int(self.run_finished / max(1, len(self.run_ids)) * 100)
        self.setWindowTitle(f"{pct}% - {APP_NAME}")
        if not self.cancel.is_set():
            self.status.setText(f"Conversione… {self.run_finished} di {len(self.run_ids)}")
        if self.run_finished >= len(self.run_ids):
            self.finish_run()

    def finish_run(self):
        self.running = False
        self.anim_timer.stop()
        self.setWindowTitle(APP_NAME)
        self.b_convert.setObjectName("primary")
        self.b_convert.setStyle(self.b_convert.style())
        self.b_convert.setIcon(icons.icon("zap", "#ffffff"))
        self.b_convert.setText("  Converti")
        self.b_convert.setToolTip("Avvia la conversione  (Ctrl+Invio)")
        self.b_convert.setEnabled(True)
        jobs = [self.jobs[i] for i in self.run_ids if i in self.jobs]
        ok = [j for j in jobs if j.status == "done"]
        err = [j for j in jobs if j.status == "error"]
        skp = [j for j in jobs if j.status == "skipped"]
        canc = [j for j in jobs if j.status == "cancelled"]
        dt = time.perf_counter() - self.run_t0
        src = sum(j.size for j in ok)
        dst = sum(j.out_size for j in ok)
        parts = [f"✓ {len(ok)} convertiti"]
        if err:
            parts.append(f"{len(err)} errori")
        if skp:
            parts.append(f"{len(skp)} saltati")
        if canc:
            parts.append(f"{len(canc)} annullati")
        if ok:
            d = (dst - src) / src * 100 if src else 0
            parts.append(f"{human(src)} → {human(dst)} ({'−' if d < 0 else '+'}{abs(d):.0f}%)")
        parts.append(f"{dt:.1f} s".replace(".", ","))
        self._summary = "  ·  ".join(parts)
        self.status.setText(self._summary)
        self.b_open_out.setVisible(bool(self.last_out_dir))
        self.update_buttons()
        self.queue.viewport().update()
        if err:
            self.toast.show_msg(f"{len(err)} file non convertiti: passa sopra per vedere il motivo", 4500)
        if not self.isActiveWindow():
            QApplication.alert(self)
            if self.prefs.get("notify", True) and self.tray:
                self.tray.show()
                self.tray.showMessage(f"{APP_NAME} - conversione completata", self._summary,
                                      icons.app_icon(), 5000)
        if self.prefs.get("sound", False):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass
        if self.get_settings().get("open_when_done") and ok and self.last_out_dir and not canc:
            self.open_out_dir()

    def open_out_dir(self):
        if self.last_out_dir:
            open_path(self.last_out_dir)

    def _tick(self):
        self.delegate.phase = (self.delegate.phase + 0.022) % 1.0
        self.queue.viewport().update()

    def _bring_front(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------ texconv
    def download_texconv(self):
        if QMessageBox.question(
                self, "Scarica texconv",
                "Verrà scaricato texconv.exe dalla release ufficiale Microsoft DirectXTex su GitHub\n"
                f"e salvato in:\n{engine.USER_TOOLS}\n\nProcedere?") != QMessageBox.Yes:
            return
        self.toast.show_msg("Download di texconv in corso…")

        def work():
            import urllib.request
            url = "https://github.com/microsoft/DirectXTex/releases/latest/download/texconv.exe"
            dst_dir = engine.USER_TOOLS
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, "texconv.exe")
            try:
                with urllib.request.urlopen(url, timeout=60) as r, open(dst + ".part", "wb") as f:
                    shutil_copy(r, f)
                os.replace(dst + ".part", dst)
                self.tools.texconv = dst
                self.emitter.message.emit("texconv installato ✓  Riavvia Prisma per abilitare BC7 / BC5 / BC4 / BC6H")
            except Exception as e:
                self.emitter.message.emit(f"Download non riuscito: {e}")

        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------ eventi
    def setup_shortcuts(self):
        QShortcut(QKeySequence.Open, self, activated=self.pick_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self.pick_folder)
        QShortcut(QKeySequence.Paste, self, activated=self.paste)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.toggle_run_shortcut)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.toggle_run_shortcut)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=lambda: self.running and self.toggle_run())
        QShortcut(QKeySequence.Find, self, activated=lambda: (self.search.setFocus(), self.search.selectAll()))
        QShortcut(QKeySequence.SelectAll, self.queue, activated=self.queue.selectAll)

    def toggle_run_shortcut(self):
        if not self.running:
            self.start_run()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.overlay.setGeometry(self.centralWidget().rect())

    def showEvent(self, e):
        dark_titlebar(self)
        super().showEvent(e)

    def dragEnterEvent(self, e):
        if e.source() is not None:  # trascinamento interno
            e.ignore()
            return
        md = e.mimeData()
        if md.hasUrls() and any(u.isLocalFile() for u in md.urls()):
            n = len(md.urls())
            self.overlay.text = f"{n} elemento" if n == 1 else f"{n} elementi"
            self.overlay.setGeometry(self.centralWidget().rect())
            self.overlay.raise_()
            self.overlay.show()
            e.acceptProposedAction()
        elif md.hasImage():
            self.overlay.text = "immagine"
            self.overlay.setGeometry(self.centralWidget().rect())
            self.overlay.raise_()
            self.overlay.show()
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self.overlay.hide()

    def dropEvent(self, e):
        self.overlay.hide()
        md = e.mimeData()
        if md.hasUrls():
            paths = [u.toLocalFile() for u in md.urls() if u.isLocalFile()]
            if paths:
                e.acceptProposedAction()
                self.activateWindow()
                QTimer.singleShot(0, lambda: self.add_paths(paths))
                return
        if md.hasImage():
            img = QImage(md.imageData())
            if not img.isNull():
                d = os.path.join(APPDATA, "appunti")
                os.makedirs(d, exist_ok=True)
                p = os.path.join(d, "trascinata_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")
                img.save(p, "PNG")
                self.add_paths([p], temp=True)
                e.acceptProposedAction()

    def closeEvent(self, e):
        if self.running:
            r = QMessageBox.question(self, APP_NAME, "Conversione in corso. Vuoi interromperla e uscire?")
            if r != QMessageBox.Yes:
                e.ignore()
                return
            self.cancel.set()
            self.conv_pool.waitForDone(3000)
        self.save_config()
        if self.tray:
            self.tray.hide()
        super().closeEvent(e)


def shutil_copy(src, dst, bufsize=1 << 16):
    while True:
        b = src.read(bufsize)
        if not b:
            break
        dst.write(b)


def excepthook(etype, value, tb):
    txt = "".join(traceback.format_exception(etype, value, tb))
    try:
        with open(os.path.join(APPDATA, "errori.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now()}]\n{txt}")
    except Exception:
        pass
    try:
        QMessageBox.critical(None, APP_NAME, f"Si è verificato un errore imprevisto:\n\n{value}\n\n"
                                             f"Dettagli in {os.path.join(APPDATA, 'errori.log')}")
    except Exception:
        pass


def main():
    sys.excepthook = excepthook
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Prisma.ImageConverter")
        except Exception:
            pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet(write_ui_assets()))
    app.setWindowIcon(icons.app_icon())
    paths = [a for a in sys.argv[1:] if os.path.exists(a)]
    w = MainWindow(paths)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
