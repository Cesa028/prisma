"""
Build di Prisma.

    python build.py              -> dist/Prisma-Setup-<versione>.exe  (installer)

Richiede: pip install pyinstaller PySide6 pillow  ·  Inno Setup 6
Include nel pacchetto: ImageMagick (installato in Program Files), ffmpeg (C:\\ffmpeg)
e texconv (tools\\texconv.exe, se presente).
"""
import glob
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

import engine  # noqa: E402
import icons  # noqa: E402
from ui import APP_VERSION  # noqa: E402

BUILD = HERE / "build"
DIST = HERE / "dist"

# file di ImageMagick non necessari al funzionamento da riga di comando
MAGICK_SKIP = {"images", "www", "uninstall", "unins000.exe", "unins000.dat", "index.html", "ChangeLog.md",
               "ImageMagick.ico", "compare.exe", "composite.exe", "conjure.exe", "identify.exe",
               "mogrify.exe", "montage.exe", "stream.exe"}


def make_icon(path: Path):
    QGuiApplication.instance() or QGuiApplication([])
    pngs = []
    for s in (256, 128, 64, 48, 32, 24, 16):
        buf = QByteArray()
        b = QBuffer(buf)
        b.open(QBuffer.WriteOnly)
        icons.app_icon_pixmap(s).toImage().save(b, "PNG")
        pngs.append((s, bytes(buf)))
    head = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, data = b"", b""
    for s, png in pngs:
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    path.write_bytes(head + entries + data)


def make_version_file(path: Path):
    v = [int(x) for x in APP_VERSION.split(".")] + [0, 0, 0]
    v = tuple(v[:4])
    path.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041004B0', [
      StringStruct('CompanyName', 'Cesa028'),
      StringStruct('FileDescription', 'Prisma Image Converter'),
      StringStruct('FileVersion', '{APP_VERSION}'),
      StringStruct('InternalName', 'Prisma'),
      StringStruct('LegalCopyright', '© 2026 Cesa028 — MIT License'),
      StringStruct('OriginalFilename', 'Prisma.exe'),
      StringStruct('ProductName', 'Prisma'),
      StringStruct('ProductVersion', '{APP_VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [0x0410, 1200])])
  ]
)
""", encoding="utf-8")


def find_iscc() -> str | None:
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if base and (p := Path(base) / "Inno Setup 6" / "ISCC.exe").is_file():
            return str(p)
    return shutil.which("ISCC")


def find_magick_home() -> Path:
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    for d in sorted(glob.glob(os.path.join(pf, "ImageMagick-7*")), reverse=True):
        if os.path.isfile(os.path.join(d, "magick.exe")):
            return Path(d)
    sys.exit("ImageMagick 7 non trovato in Program Files (winget install ImageMagick.ImageMagick)")


def pyinstaller(ico: Path, ver: Path):
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
        "--name", "Prisma", "--icon", str(ico), "--version-file", str(ver),
        "--paths", str(HERE),
        "--distpath", str(DIST), "--workpath", str(BUILD / "work"), "--specpath", str(BUILD),
    ]
    for m in ("tkinter", "unittest", "pydoc", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf",
              "PySide6.QtOpenGL", "PySide6.QtWebEngineCore", "PySide6.QtMultimedia", "PySide6.Qt3DCore"):
        args += ["--exclude-module", m]
    subprocess.run(args + [str(HERE / "Prisma.pyw")], check=True)


def main():
    iscc = find_iscc()
    if not iscc:
        sys.exit("Inno Setup 6 non trovato: installalo da https://jrsoftware.org/isdl.php "
                 "(oppure: winget install JRSoftware.InnoSetup)")
    tools = engine.Tools()
    if not tools.ffmpeg:
        sys.exit("ffmpeg non trovato")
    magick_home = find_magick_home()

    BUILD.mkdir(exist_ok=True)
    ico, ver = BUILD / "icon.ico", BUILD / "version.txt"
    make_icon(ico)
    make_version_file(ver)

    # Versione "a cartella": avvio immediato, meno falsi positivi antivirus, DLL Qt sostituibili (LGPL)
    pyinstaller(ico, ver)
    pkg = BUILD / "package"
    shutil.rmtree(pkg, ignore_errors=True)
    shutil.copytree(DIST / "Prisma", pkg)

    # motori di conversione
    bin_dir = pkg / "bin"
    shutil.copytree(magick_home, bin_dir / "magick", ignore=lambda d, names: [n for n in names if n in MAGICK_SKIP])
    shutil.copy2(tools.ffmpeg, bin_dir / "ffmpeg.exe")
    texconv = HERE / "tools" / "texconv.exe"
    if texconv.is_file():
        shutil.copy2(texconv, bin_dir / "texconv.exe")
    else:
        print("ATTENZIONE: tools\\texconv.exe non trovato, BC7/BC5/BC4/BC6H non saranno inclusi")

    shutil.copy2(HERE / "LICENSE.txt", pkg / "LICENSE.txt")
    shutil.copytree(HERE / "licenses", pkg / "licenses")
    # sorgente dell'app: permette di ricompilarla con un'altra versione di Qt (LGPL v3, sez. 4)
    src = pkg / "source"
    (src / "installer").mkdir(parents=True)
    for name in ("Prisma.pyw", "ui.py", "engine.py", "icons.py", "build.py", "LICENSE.txt"):
        shutil.copy2(HERE / name, src / name)
    for p in (HERE / "installer").iterdir():
        shutil.copy2(p, src / "installer" / p.name)
    shutil.copytree(HERE / "licenses", src / "licenses")

    # verifica: l'ImageMagick incluso deve funzionare da solo
    env = dict(os.environ, MAGICK_HOME=str(bin_dir / "magick"), MAGICK_CONFIGURE_PATH=str(bin_dir / "magick"),
               MAGICK_CODER_MODULE_PATH=str(bin_dir / "magick" / "modules" / "coders"),
               MAGICK_CODER_FILTER_PATH=str(bin_dir / "magick" / "modules" / "filters"))
    r = subprocess.run([str(bin_dir / "magick" / "magick.exe"), "-list", "format"], env=env,
                       capture_output=True, text=True)
    if r.returncode != 0 or "DDS" not in r.stdout:
        sys.exit("ImageMagick incluso non funziona:\n" + r.stderr)

    subprocess.run([iscc, f"/DAppVersion={APP_VERSION}", f"/DSrcDir={pkg}", "/Qp",
                    str(HERE / "installer" / "Prisma.iss")], check=True)
    setup = DIST / f"Prisma-Setup-{APP_VERSION}.exe"
    print(f"\nFatto: {setup}  ({setup.stat().st_size / 1_048_576:.0f} MB)")


if __name__ == "__main__":
    main()
