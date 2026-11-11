"""Prisma - costanti e utilità condivise."""
from __future__ import annotations

import os
import subprocess

APP_NAME = "Prisma"
APP_VERSION = "1.1.1"
APP_AUTHOR = "Cesa028"
APP_URL = "https://github.com/Cesa028/prisma"
APPDATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
os.makedirs(APPDATA, exist_ok=True)
CONFIG = os.path.join(APPDATA, "settings.json")


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
