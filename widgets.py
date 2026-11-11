"""Prisma - widget riutilizzabili: lista file, drop zone, toast, form delle opzioni."""
from __future__ import annotations

import os
import re
from PySide6.QtCore import QMimeData, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QBrush, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QLayout, QCheckBox, QComboBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QSlider, QSpinBox, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget

import icons
from common import human
from jobs import Job
from theme import DUR_BASE, P, R_LG, R_XL, qcolor


# --------------------------------------------------------------------------- #
# Lista file
# --------------------------------------------------------------------------- #
_checker_cache = {}


def checker_brush(size=8):
    """Scacchiera per le trasparenze, nei colori del tema corrente (in cache per tema)."""
    key = (size, P.checker_a, P.checker_b)
    if key not in _checker_cache:
        pm = QPixmap(size * 2, size * 2)
        pm.fill(qcolor(P.checker_a))
        p = QPainter(pm)
        p.fillRect(0, 0, size, size, qcolor(P.checker_b))
        p.fillRect(size, size, size, size, qcolor(P.checker_b))
        p.end()
        _checker_cache[key] = QBrush(pm)
    return _checker_cache[key]


class IconLabel(QWidget):
    """Icona vettoriale che si ricolora al cambio di tema. Trasparente al mouse."""

    def __init__(self, name, role="text2", size=16, width=2.0, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._ic = icons.icon(name, role, width=width)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._ic.paint(p, self.rect())


class JobDelegate(QStyledItemDelegate):
    ROW_H = 66

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
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
        bg = qcolor(P.sel_card) if sel else qcolor(P.surf2) if hov else qcolor(P.surf)
        focus = bool(opt.state & QStyle.State_HasFocus)
        p.setPen(QPen(qcolor(P.accent if (sel or focus) else P.border), 2 if focus else 1))
        p.setBrush(bg)
        p.drawRoundedRect(r, R_LG, R_LG)

        # miniatura
        tr = QRectF(r.left() + 9, r.top() + 8, r.height() - 16, r.height() - 16)
        path = QPainterPath()
        path.addRoundedRect(tr, 7, 7)
        p.setClipPath(path)
        if job.thumb is not None and not job.thumb.isNull():
            if job.alpha:
                p.fillRect(tr, checker_brush(5))
            else:
                p.fillRect(tr, qcolor(P.preview_bg))
            pm = job.thumb
            sz = pm.deviceIndependentSize()
            sc = min(tr.width() / max(1, sz.width()), tr.height() / max(1, sz.height()))
            sc = min(sc, 4)
            w, h = sz.width() * sc, sz.height() * sc
            p.drawPixmap(QRectF(tr.center().x() - w / 2, tr.center().y() - h / 2, w, h), pm, QRectF(pm.rect()))
        else:
            p.fillRect(tr, qcolor(P.surf3))
            p.setFont(self.f_ext)
            p.setPen(qcolor(P.muted))
            p.drawText(tr, Qt.AlignCenter, (job.ext or "?").upper()[:5])
        p.setClipping(False)

        # testo
        right_w = 150
        tx = tr.right() + 12
        tw = r.right() - tx - right_w - 10
        p.setFont(self.f_name)
        p.setPen(qcolor(P.text))
        fm = QFontMetrics(self.f_name)
        p.drawText(QRectF(tx, r.top() + 11, tw, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   fm.elidedText(job.name, Qt.ElideMiddle, int(tw)))
        p.setFont(self.f_meta)
        fm2 = QFontMetrics(self.f_meta)
        if job.status in ("error",) and job.msg:
            p.setPen(qcolor(P.err))
            meta = job.msg.splitlines()[0]
        elif job.probe_error and not job.w:
            p.setPen(qcolor(P.warn))
            meta = job.probe_error.splitlines()[0]
        else:
            p.setPen(qcolor(P.muted))
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
                p.setPen(qcolor(P.warn))
                p.drawText(QRectF(tx, r.top() + 32, tw, 18), Qt.AlignLeft | Qt.AlignVCenter, dim)
                p.setPen(qcolor(P.muted))
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
            p.setBrush(qcolor(P.surf3))
            p.drawRoundedRect(bar, 2, 2)
            seg = bar.width() * 0.35
            x = bar.left() + (bar.width() + seg) * (self.phase % 1.0) - seg
            seg_r = QRectF(max(bar.left(), x), bar.top(), min(seg, bar.right() - x, x + seg - bar.left()), 4)
            if seg_r.width() > 0:
                p.setBrush(qcolor(P.accent))
                p.drawRoundedRect(seg_r, 2, 2)
            p.setPen(qcolor(P.info_text))
            p.drawText(QRectF(sr.left(), sr.top() + 14, sr.width(), 18), Qt.AlignRight | Qt.AlignVCenter, "Conversione…")
        else:
            check_icon = False
            label, color, sub = {
                "pending": ("Pronto", P.dim, ""),
                "queued": ("In attesa…", P.muted, ""),
                "cancelled": ("Annullato", P.muted, ""),
                "skipped": ("Saltato", P.warn, ""),
                "error": ("Errore", P.err, "passa sopra per i dettagli"),
            }.get(st, ("", P.muted, ""))
            if st == "done":
                label = human(job.out_size)
                color = P.ok
                check_icon = True
                if job.size:
                    d = (job.out_size - job.size) / job.size * 100
                    sub = (f"−{abs(d):.0f}%" if d < 0 else f"+{d:.0f}%") + f"  ·  {job.elapsed:.1f}s".replace(".", ",")
            if st == "skipped":
                sub = job.msg
            p.setFont(self.f_name)
            p.setPen(qcolor(color))
            p.drawText(QRectF(sr.left(), r.top() + 11, sr.width(), 20), Qt.AlignRight | Qt.AlignVCenter, label)
            if check_icon:
                tw_ = QFontMetrics(self.f_name).horizontalAdvance(label)
                icons.icon("check", "ok", width=2.6).paint(
                    p, QRect(int(sr.right() - tw_ - 20), int(r.top() + 14), 14, 14))
            if sub:
                p.setFont(self.f_meta)
                p.setPen(qcolor(P.muted))
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
        ic = IconLabel("upload", "drop_icon", 46, 1.6)
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
        lay.addWidget(ic, 0, Qt.AlignCenter)
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
        pen = QPen(qcolor(P.drop_border), 1.6, Qt.DashLine)
        pen.setDashPattern([6, 5])
        p.setPen(pen)
        p.setBrush(qcolor(P.drop_fill))
        p.drawRoundedRect(r, R_XL, R_XL)


class DropOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.text = ""
        self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), qcolor(P.overlay))
        r = QRectF(self.rect()).adjusted(24, 24, -24, -24)
        pen = QPen(qcolor(P.accent), 2.2, Qt.DashLine)
        pen.setDashPattern([7, 5])
        p.setPen(pen)
        p.setBrush(qcolor(P.overlay_fill))
        p.drawRoundedRect(r, 18, 18)
        icons.icon("upload", "accent_text", width=1.6).paint(
            p, QRect(int(r.center().x() - 27), int(r.center().y() - 70), 54, 54))
        f = QFont()
        f.setPointSizeF(15)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(qcolor(P.text))
        p.drawText(QRectF(r.left(), r.center().y() - 6, r.width(), 30), Qt.AlignCenter, "Rilascia per aggiungere")
        f.setPointSizeF(10)
        f.setWeight(QFont.Normal)
        p.setFont(f)
        p.setPen(qcolor(P.muted))
        p.drawText(QRectF(r.left(), r.center().y() + 26, r.width(), 22), Qt.AlignCenter, self.text)


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setTextFormat(Qt.PlainText)
        self.eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.eff)
        self.anim = QPropertyAnimation(self.eff, b"opacity", self)
        self.anim.setDuration(DUR_BASE)
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
        self.btn.setIcon(icons.icon("chevron-down" if v else "chevron-right", "muted"))
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
                w.setAccessibleName(sp["label"])
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


def a11y_pass(root):
    """Rifinitura di accessibilità su un'intera finestra:
    - i pulsanti prendono il focus solo da tastiera (l'anello di focus non compare dopo un clic);
    - i pulsanti con la sola icona usano il suggerimento come nome accessibile;
    - combo, caselle numeriche, cursori e campi di testo prendono il nome dall'etichetta che li precede."""
    for b in root.findChildren(QPushButton):
        b.setFocusPolicy(Qt.TabFocus)
        if not b.text().strip() and not b.accessibleName():
            tip = b.toolTip().split("  (")[0].strip()
            if tip:
                b.setAccessibleName(tip)
    layouts = ([root.layout()] if root.layout() else []) + root.findChildren(QLayout)
    for lay in layouts:
        last = ""
        for i in range(lay.count()):
            w = lay.itemAt(i).widget()
            if isinstance(w, QLabel):
                txt = re.sub(r"<[^>]+>", "", w.text()).strip()
                if txt:
                    last = txt
            elif isinstance(w, (QComboBox, QSpinBox, QSlider, QLineEdit)) and not w.accessibleName():
                name = last or w.toolTip()
                if name:
                    w.setAccessibleName(name)
