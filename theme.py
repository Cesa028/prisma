"""Prisma - design token e temi (scuro / chiaro).

Tutti i colori, i raggi, le spaziature e le durate dell'interfaccia vivono qui.
Gli altri moduli leggono sempre `P.<nome>` al momento del disegno, così il cambio di tema
è immediato (nessun riavvio): `apply("dark" | "light" | "system")` aggiorna `P` sul posto.
"""
from __future__ import annotations

import ctypes
import os
from types import SimpleNamespace

from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtCore import Qt

# --------------------------------------------------------------------------- #
# Token non cromatici
# --------------------------------------------------------------------------- #
R_XS, R_SM, R_MD, R_LG, R_XL = 5, 7, 8, 10, 16        # raggi (px)
SP_1, SP_2, SP_3, SP_4, SP_5, SP_6 = 4, 8, 12, 16, 20, 24   # spaziature su griglia da 4 px
DUR_FAST, DUR_BASE, DUR_SLOW = 120, 220, 320           # animazioni (ms)
FONT_FAMILY = "'Segoe UI Variable Text', 'Segoe UI'"
FS_BASE, FS_SMALL, FS_H2, FS_H1 = 10, 8.5, 11, 13.5    # corpi in pt

THEMES = ("system", "dark", "light")
THEME_LABELS = {"system": "Come il sistema", "dark": "Scuro", "light": "Chiaro"}

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
DARK = dict(
    dark=True,
    bg="#0e1014", surf="#14171e", surf2="#1a1e27", surf3="#222734",
    border="#262b37", border_hover="#343b4c", border_strong="#3a4152",
    text="#e6e9ef", text2="#c9cfdb", muted="#8a92a3", dim="#6c7487",
    accent="#7c5cff", accent2="#4f8cff",
    btn1="#6540f0", btn2="#3568d8", btn_hi1="#7653ff", btn_hi2="#3d6fe0", control="#7a8396",
    on_accent="#ffffff", accent_text="#b9a8ff",
    ok="#2ecc8f", err="#ff5c7a", warn="#ffb547",
    field="#0f1218", pressed="#181b23",
    sel="#2c2550", sel_card="#1f1b38",
    accent_soft="rgba(124,92,255,0.20)", accent_soft2="rgba(124,92,255,0.22)",
    warn_bg="rgba(255,181,71,0.08)", warn_bd="rgba(255,181,71,0.25)",
    info_bg="rgba(124,92,255,0.08)", info_bd="rgba(124,92,255,0.25)", info_text="#b9c3ff",
    danger_bg="#2e1820", danger_bd="#5a2635", danger_text="#ffb3c1", danger_hover="#3a1d28",
    check_disabled="#3a3360", slider_off="#3a3f4d", handle_hover="#dcd4ff", handle_off="#5b6272",
    scroll="#2a303d", scroll_hover="#394052",
    checker_a="#2a2f3a", checker_b="#353b48", preview_bg="#0b0d11",
    drop_border="#343a4a", drop_fill="rgba(255,255,255,0.016)", drop_icon="#9b87ff",
    overlay="rgba(10,11,16,215)", overlay_fill="rgba(124,92,255,22)",
    toast_bg="#222734", toast_border="#353c4d",
    swatch_border="#4a5163",
    titlebar=0x00140E0E,
)

LIGHT = dict(
    dark=False,
    bg="#f4f5f9", surf="#ffffff", surf2="#f1f3f8", surf3="#e5e8f0",
    border="#d8dce6", border_hover="#bcc3d2", border_strong="#aab2c4",
    text="#1a1f2e", text2="#3d4558", muted="#566077", dim="#7a8296",
    accent="#6540f0", accent2="#2f64d9",
    btn1="#6540f0", btn2="#3568d8", btn_hi1="#7653ff", btn_hi2="#3d6fe0", control="#6f788c",
    on_accent="#ffffff", accent_text="#5a38dc",
    ok="#0b7f55", err="#c8203f", warn="#98590a",
    field="#ffffff", pressed="#dde1ec",
    sel="#e6defe", sel_card="#efeaff",
    accent_soft="rgba(101,64,240,0.14)", accent_soft2="rgba(101,64,240,0.16)",
    warn_bg="rgba(184,110,0,0.10)", warn_bd="rgba(184,110,0,0.35)",
    info_bg="rgba(101,64,240,0.07)", info_bd="rgba(101,64,240,0.28)", info_text="#4a2fc2",
    danger_bg="#fdecef", danger_bd="#f0b3bf", danger_text="#a91833", danger_hover="#fbdce2",
    check_disabled="#c9bff5", slider_off="#c3c9d6", handle_hover="#f1ecff", handle_off="#aab2c4",
    scroll="#c5cad6", scroll_hover="#a9b0c0",
    checker_a="#e4e7ee", checker_b="#f7f8fb", preview_bg="#e9ecf2",
    drop_border="#b6bdcc", drop_fill="rgba(101,64,240,0.025)", drop_icon="#7c5cff",
    overlay="rgba(244,245,249,225)", overlay_fill="rgba(101,64,240,28)",
    toast_bg="#ffffff", toast_border="#c9cfdc",
    swatch_border="#aab2c4",
    titlebar=0x00F9F5F4,
)

# Palette corrente (aggiornata sul posto da apply())
P = SimpleNamespace(name="dark", **DARK)


def system_is_dark() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() != Qt.ColorScheme.Light
    except Exception:
        return True


def resolve(pref: str) -> str:
    if pref == "system" or pref not in ("dark", "light"):
        return "dark" if system_is_dark() else "light"
    return pref


def apply(pref: str) -> str:
    """Imposta la palette corrente. Ritorna il nome effettivo ('dark' | 'light')."""
    name = resolve(pref)
    for k, v in (DARK if name == "dark" else LIGHT).items():
        setattr(P, k, v)
    P.name = name
    return name


def qcolor(spec) -> QColor:
    """QColor da '#rrggbb' oppure 'rgba(r,g,b,a)' (a 0-1 oppure 0-255)."""
    if isinstance(spec, QColor):
        return QColor(spec)
    s = str(spec)
    if s.startswith("rgba"):
        r, g, b, a = [x.strip() for x in s[s.index("(") + 1:s.index(")")].split(",")]
        af = float(a)
        return QColor(int(r), int(g), int(b), int(round(af * 255)) if af <= 1 else int(af))
    return QColor(s)


def app_palette() -> QPalette:
    pal = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.Base, "field"), (QPalette.AlternateBase, "surf2"),
                      (QPalette.Button, "surf2"), (QPalette.ToolTipBase, "surf2"), (QPalette.WindowText, "text"),
                      (QPalette.Text, "text"), (QPalette.ButtonText, "text"), (QPalette.ToolTipText, "text"),
                      (QPalette.Highlight, "accent"), (QPalette.HighlightedText, "on_accent"),
                      (QPalette.PlaceholderText, "dim"), (QPalette.Link, "accent_text")):
        pal.setColor(role, qcolor(getattr(P, key)))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, qcolor(P.dim))
    return pal


def titlebar(widget):
    """Barra del titolo di Windows allineata al tema (immersive dark mode + colore didascalia)."""
    if os.name != "nt":
        return
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1 if P.dark else 0)), 4)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(P.titlebar)), 4)  # Win11
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(ctypes.c_int(0x00E6E9EF if P.dark else 0x002E1F1A)), 4)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Foglio di stile
# --------------------------------------------------------------------------- #
def stylesheet(asset_dir: str) -> str:
    return f"""
* {{ font-family: {FONT_FAMILY}; font-size: {FS_BASE}pt; color: {P.text}; }}
QMainWindow, QDialog {{ background: {P.bg}; }}
QWidget#panel {{ background: {P.surf}; }}
QWidget#header {{ background: {P.bg}; border-bottom: 1px solid {P.border}; }}
QWidget#footer {{ background: {P.surf}; border-top: 1px solid {P.border}; }}
QLabel#h1 {{ font-size: {FS_H1}pt; font-weight: 600; }}
QLabel#h2 {{ font-size: {FS_H2}pt; font-weight: 600; }}
QLabel#muted {{ color: {P.muted}; }}
QLabel#small {{ color: {P.muted}; font-size: {FS_SMALL}pt; }}
QLabel#value {{ color: {P.text}; font-weight: 600; background: {P.surf3}; border-radius: {R_XS}px; padding: 1px 7px; }}
QLabel#version {{ color: {P.muted}; font-size: {FS_SMALL}pt; }}
QLabel#warn {{ color: {P.warn}; background: {P.warn_bg}; border: 1px solid {P.warn_bd};
               border-radius: {R_MD}px; padding: 8px 10px; font-size: 9pt; }}
QLabel#info {{ color: {P.info_text}; background: {P.info_bg}; border: 1px solid {P.info_bd};
               border-radius: {R_MD}px; padding: 8px 10px; font-size: 9pt; }}
QPushButton {{ background: {P.surf2}; border: 1px solid {P.border}; border-radius: {R_MD}px; padding: 7px 12px; }}
QPushButton:hover {{ background: {P.surf3}; border-color: {P.border_hover}; }}
QPushButton:pressed {{ background: {P.pressed}; }}
QPushButton:focus {{ border: 1px solid {P.accent}; }}
QPushButton:disabled {{ color: {P.dim}; background: {P.surf}; border-color: {P.border}; }}
QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {P.btn1}, stop:1 {P.btn2});
    border: 2px solid transparent; font-weight: 600; font-size: 10.5pt; padding: 8px 24px; color: {P.on_accent}; }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {P.btn_hi1}, stop:1 {P.btn_hi2}); }}
QPushButton#primary:focus {{ border: 2px solid {P.text}; }}
QPushButton#primary:disabled {{ background: {P.surf3}; color: {P.dim}; border: 2px solid transparent; }}
QPushButton#danger {{ background: {P.danger_bg}; border: 2px solid {P.danger_bd}; color: {P.danger_text}; font-weight: 600;
    font-size: 10.5pt; padding: 8px 24px; }}
QPushButton#danger:hover {{ background: {P.danger_hover}; }}
QPushButton#danger:focus {{ border: 2px solid {P.danger_text}; }}
QPushButton#ghost {{ background: transparent; border: 1px solid transparent; padding: 6px 9px; border-radius: {R_SM}px; color: {P.text2}; }}
QPushButton#ghost:hover {{ background: {P.surf3}; border-color: {P.border}; }}
QPushButton#ghost:focus {{ border: 1px solid {P.accent}; }}
QPushButton#chip {{ padding: 8px 0px; font-weight: 600; border-radius: {R_MD}px; background: {P.surf2}; }}
QPushButton#chip:hover {{ border-color: {P.border_strong}; }}
QPushButton#chip:checked {{ background: {P.accent_soft}; border: 1px solid {P.accent}; color: {P.text}; }}
QPushButton#chip:checked:focus, QPushButton#mini:checked:focus {{ border: 2px solid {P.text}; }}
QPushButton#mini {{ padding: 4px 9px; font-size: {FS_SMALL}pt; border-radius: 6px; }}
QPushButton#mini:checked {{ background: {P.accent_soft2}; border: 1px solid {P.accent}; color: {P.text}; }}
QPushButton#section {{ background: transparent; border: 1px solid transparent; text-align: left; padding: 6px 2px; color: {P.muted};
    font-size: {FS_SMALL}pt; font-weight: 700; }}
QPushButton#section:hover {{ color: {P.text}; background: transparent; border-color: transparent; }}
QPushButton#section:focus {{ border: 1px solid {P.accent}; }}
QPushButton#swatch {{ border-radius: 6px; padding: 0; min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; }}
QPushButton#swatch:focus {{ border: 2px solid {P.accent}; }}
QLineEdit, QSpinBox, QComboBox {{ background: {P.field}; border: 1px solid {P.border}; border-radius: {R_SM}px; padding: 6px 9px;
    selection-background-color: {P.accent}; selection-color: {P.on_accent}; }}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{ border-color: {P.border_hover}; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {P.accent}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ color: {P.dim}; background: {P.surf}; }}
QLineEdit#search {{ padding-left: 30px; border-radius: {R_MD}px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url({asset_dir}/chev.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {P.surf2}; border: 1px solid {P.border}; selection-background-color: {P.sel};
    selection-color: {P.text}; outline: 0; padding: 4px; }}
QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 0 6px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; border: none; }}
QCheckBox, QRadioButton {{ spacing: 9px; }}
QCheckBox:disabled, QRadioButton:disabled, QLabel:disabled {{ color: {P.dim}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: {R_XS}px; border: 1px solid {P.control}; background: {P.field}; }}
QCheckBox::indicator:hover {{ border-color: {P.accent}; }}
QCheckBox::indicator:focus {{ border: 2px solid {P.accent}; }}
QCheckBox::indicator:checked {{ background: {P.accent}; border-color: {P.accent}; image: url({asset_dir}/check.svg); }}
QCheckBox::indicator:checked:disabled {{ background: {P.check_disabled}; border-color: {P.check_disabled}; }}
QSlider::groove:horizontal {{ height: 4px; background: {P.surf3}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {P.accent}, stop:1 {P.accent2}); border-radius: 2px; }}
QSlider::sub-page:horizontal:disabled {{ background: {P.slider_off}; }}
QSlider::handle:horizontal {{ background: {P.surf}; border: 2px solid {P.accent}; width: 10px; height: 10px; margin: -5px 0; border-radius: 7px; }}
QSlider::handle:horizontal:hover {{ background: {P.handle_hover}; }}
QSlider::handle:horizontal:focus {{ background: {P.accent}; border-color: {P.text}; }}
QSlider::handle:horizontal:disabled {{ background: {P.handle_off}; border-color: {P.handle_off}; }}
QProgressBar {{ background: {P.surf3}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 3px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {P.accent}, stop:1 {P.accent2}); }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {P.scroll}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {P.scroll_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QScrollBar:horizontal {{ height: 0px; }}
QToolTip {{ background: {P.surf2}; color: {P.text}; border: 1px solid {P.border}; padding: 6px 8px; border-radius: 6px; }}
QMenu {{ background: {P.surf2}; border: 1px solid {P.border}; padding: 5px; }}
QMenu::item {{ padding: 7px 26px 7px 10px; border-radius: {R_XS}px; }}
QMenu::item:selected {{ background: {P.sel}; }}
QMenu::item:disabled {{ color: {P.dim}; }}
QMenu::separator {{ height: 1px; background: {P.border}; margin: 4px 8px; }}
QMenu::icon {{ padding-left: 8px; }}
QListWidget {{ background: transparent; border: none; outline: 0; }}
QSplitter::handle {{ background: {P.border}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QFrame#sep {{ background: {P.border}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#card {{ background: {P.surf2}; border: 1px solid {P.border}; border-radius: {R_LG}px; }}
QLabel#toast {{ background: {P.toast_bg}; border: 1px solid {P.toast_border}; border-radius: {R_LG}px;
                padding: 10px 16px; color: {P.text}; }}
"""


apply("dark")
