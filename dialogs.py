"""Prisma - finestre di dialogo: anteprima, impostazioni, informazioni."""
from __future__ import annotations

import os
import subprocess
import sys
from PySide6.QtCore import QRectF, Qt, QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QTextBrowser, QVBoxLayout, QWidget

import engine
import icons
from common import APP_AUTHOR, APP_NAME, APP_URL, APP_VERSION, APPDATA, human, open_path
from jobs import Job, Emitter, ProbeTask
from widgets import IconLabel, a11y_pass, checker_brush, sep, label
from theme import P, SP_1, SP_2, SP_3, SP_4, SP_5, SP_6, THEME_LABELS, THEMES, qcolor, titlebar


class ImageView(QWidget):
    def __init__(self):
        super().__init__()
        self.pm = None
        self.text = "Caricamento…"
        self.setMinimumSize(400, 300)

    def set_pixmap(self, pm, text=""):
        self.pm = pm
        self.text = text
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), qcolor(P.preview_bg))
        if self.pm and not self.pm.isNull():
            sz = self.pm.size()
            sc = min(self.width() / sz.width(), self.height() / sz.height(), 1.0 if max(sz.width(), sz.height()) > 64 else 8.0)
            w, h = sz.width() * sc, sz.height() * sc
            r = QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)
            p.fillRect(r, checker_brush(8))
            if sc > 2:
                p.setRenderHint(QPainter.SmoothPixmapTransform, False)
            p.drawPixmap(r, self.pm, QRectF(self.pm.rect()))
        else:
            p.setPen(qcolor(P.muted))
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
        titlebar(self)
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

        lay.addWidget(label("ASPETTO", "small"))
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("Tema dell'interfaccia"))
        row0.addStretch()
        self.theme_combo = QComboBox()
        for key in THEMES:
            self.theme_combo.addItem(icons.icon({"system": "monitor", "dark": "moon", "light": "sun"}[key]),
                                     THEME_LABELS[key], key)
        cur = main.prefs.get("theme", "system")
        self.theme_combo.setCurrentIndex(THEMES.index(cur) if cur in THEMES else 0)
        self.theme_combo.setFixedWidth(190)
        self.theme_combo.setAccessibleName("Tema dell'interfaccia")
        self.theme_combo.activated.connect(lambda _=0: main.set_theme(self.theme_combo.currentData()))
        row0.addWidget(self.theme_combo)
        lay.addLayout(row0)

        lay.addWidget(sep())
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
            r.addWidget(IconLabel("check" if path else "alert", "ok" if path else "warn", 16, 2.4))
            nm = label(name)
            nm.setStyleSheet("font-weight: 600;")
            r.addWidget(nm)
            r.addWidget(label("- " + desc, "muted"))
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
        babout = QPushButton(icons.icon("info"), "  Informazioni su Prisma")
        babout.setObjectName("ghost")
        babout.clicked.connect(lambda: AboutDialog(self).exec())
        r3.addWidget(babout)
        r3.addStretch()
        ok = QPushButton("Fatto")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        r3.addWidget(ok)
        lay.addLayout(r3)
        a11y_pass(self)

    def showEvent(self, e):
        titlebar(self)
        super().showEvent(e)

    def _shortcut(self, where):
        ok = create_shortcut(where)
        self.main.toast.show_msg("Collegamento creato" if ok else "Impossibile creare il collegamento")

    def accept(self):
        self.main.prefs["threads"] = self.threads.value()
        self.main.prefs["notify"] = self.notify.isChecked()
        self.main.prefs["sound"] = self.sound.isChecked()
        self.main.save_config()
        super().accept()


# --------------------------------------------------------------------------- #
# Informazioni e licenze
# --------------------------------------------------------------------------- #
def _app_file(*parts):
    """Percorso di un file distribuito con il programma (installer o sorgenti)."""
    return os.path.join(engine.APP_DIR, *parts)


class TextDialog(QDialog):
    """Mostra un file di testo (licenza, avvisi di terze parti) dentro l'app."""

    def __init__(self, parent, title, path):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(SP_5, SP_4, SP_5, SP_4)
        lay.setSpacing(SP_3)
        lay.addWidget(label(title, "h1"))
        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setAccessibleName(title)
        try:
            with open(path, encoding="utf-8-sig") as f:
                view.setPlainText(f.read())
        except OSError:
            view.setPlainText(f"File non trovato:\n{path}")
        mono = QFont("Cascadia Mono")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSizeF(9.5)
        view.setFont(mono)
        lay.addWidget(view, 1)
        row = QHBoxLayout()
        row.addStretch()
        ok = QPushButton("Chiudi")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)
        a11y_pass(self)

    def showEvent(self, e):
        titlebar(self)
        super().showEvent(e)


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Informazioni su Prisma")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(SP_6, SP_6, SP_6, SP_5)
        lay.setSpacing(SP_2)
        logo = QLabel()
        logo.setPixmap(icons.app_icon_pixmap(160).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        logo.setAccessibleName("Logo di Prisma")
        lay.addWidget(logo)
        for text, obj in ((APP_NAME, "h1"), (f"Versione {APP_VERSION}", "muted")):
            l = label(text, obj)
            l.setAlignment(Qt.AlignCenter)
            lay.addWidget(l)
        desc = label("Convertitore di immagini per Windows: veloce, completo e con un'interfaccia curata.", None, True)
        desc.setAlignment(Qt.AlignCenter)
        lay.addSpacing(SP_2)
        lay.addWidget(desc)
        lay.addSpacing(SP_2)
        cp = label(f"\u00a9 2026 {APP_AUTHOR}  \u00b7  Licenza MIT", "small")
        cp.setAlignment(Qt.AlignCenter)
        lay.addWidget(cp)
        note = label("Usa ImageMagick, FFmpeg e Microsoft DirectXTex, programmi separati con le proprie licenze.",
                     "small", True)
        note.setAlignment(Qt.AlignCenter)
        lay.addWidget(note)
        lay.addSpacing(SP_3)
        lay.addWidget(sep())
        lay.addSpacing(SP_1)

        grid = QGridLayout()
        grid.setSpacing(SP_2)
        items = (
            ("scale", "Licenza", lambda: TextDialog(self, "Licenza MIT di Prisma", _app_file("LICENSE.txt")).exec()),
            ("file", "Componenti di terze parti",
             lambda: TextDialog(self, "Componenti di terze parti",
                                _app_file("licenses", "THIRD-PARTY-NOTICES.txt")).exec()),
            ("link", "Sito del progetto", lambda: QDesktopServices.openUrl(QUrl(APP_URL))),
            ("folder", "Cartella dei dati", lambda: open_path(APPDATA)),
        )
        for i, (ic, text, fn) in enumerate(items):
            b = QPushButton(icons.icon(ic), "  " + text)
            b.clicked.connect(fn)
            b.setCursor(Qt.PointingHandCursor)
            grid.addWidget(b, i // 2, i % 2)
        lay.addLayout(grid)
        lay.addSpacing(SP_2)
        row = QHBoxLayout()
        row.addStretch()
        ok = QPushButton("Chiudi")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
        row.addWidget(ok)
        lay.addLayout(row)
        a11y_pass(self)

    def showEvent(self, e):
        titlebar(self)
        super().showEvent(e)
