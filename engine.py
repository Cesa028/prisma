"""Prisma - motore di conversione.

Usa ImageMagick come motore principale, ffmpeg come decoder di riserva (e per
estrarre fotogrammi dai video) e, se presente, texconv.exe (DirectXTex) per i
formati DDS BC4/BC5/BC6H/BC7.
"""
from __future__ import annotations

import datetime
import glob
import io
import os
import re
import shutil
import subprocess
import tempfile
import sys
import threading

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
FROZEN = getattr(sys, "frozen", False)
# cartella del programma: accanto a Prisma.exe se installato, altrimenti quella dei sorgenti
APP_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))
# strumenti inclusi nell'installer: bin/magick, bin/ffmpeg.exe, bin/texconv.exe
BIN_DIR = os.path.join(APP_DIR, "bin")
# cartella scrivibile per gli strumenti scaricati (Program Files può essere in sola lettura)
USER_TOOLS = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Prisma", "tools")


def _use_bundled_magick():
    """Rende autonomo l'ImageMagick incluso: configurazione e moduli dalla sua cartella."""
    home = os.path.join(BIN_DIR, "magick")
    exe = os.path.join(home, "magick.exe")
    if not os.path.isfile(exe):
        return None
    os.environ["MAGICK_HOME"] = home
    os.environ["MAGICK_CONFIGURE_PATH"] = home
    os.environ["MAGICK_CODER_MODULE_PATH"] = os.path.join(home, "modules", "coders")
    os.environ["MAGICK_CODER_FILTER_PATH"] = os.path.join(home, "modules", "filters")
    return exe


class Cancelled(Exception):
    pass


class ConvertError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Strumenti esterni
# --------------------------------------------------------------------------- #
def _find(*cands):
    for c in cands:
        if not c:
            continue
        if os.path.isabs(c) and os.path.isfile(c):
            return c
        if not os.path.isabs(c):
            w = shutil.which(c)
            if w:
                return w
    return None


class Tools:
    def __init__(self):
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        magicks = sorted(glob.glob(os.path.join(pf, "ImageMagick*", "magick.exe")), reverse=True)
        self.magick = _find("magick", *magicks)
        self.ffmpeg = _find(r"C:\ffmpeg\ffmpeg.exe", r"C:\ffmpeg\bin\ffmpeg.exe", "ffmpeg")
        self.texconv = _find(
            os.path.join(APP_DIR, "tools", "texconv.exe"),
            os.path.join(APP_DIR, "texconv.exe"),
            r"C:\ffmpeg\texconv.exe",
            r"C:\ffmpeg\bin\texconv.exe",
            "texconv",
        )

    def has(self, name):
        return bool(getattr(self, name, None))


def run(cmd, cancel=None, env=None, stdin=None):
    """Esegue un processo senza finestra; uccide il processo se `cancel` viene impostato."""
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW,
        env=env,
    )
    first = True
    while True:
        try:
            out, err = p.communicate(input=stdin if first else None, timeout=0.25)
            break
        except subprocess.TimeoutExpired:
            first = False
            if cancel is not None and cancel.is_set():
                p.kill()
                p.communicate()
                raise Cancelled()
    return p.returncode, out, err


def clean_error(err: bytes | str) -> str:
    if isinstance(err, bytes):
        err = err.decode("utf-8", "replace")
    lines = []
    for ln in err.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        ln = re.sub(r"\s*@\s*(error|warning)/\S+\.c/\S+\.?$", "", ln)
        ln = re.sub(r"^magick(\.exe)?:\s*", "", ln)
        lines.append(ln)
    return "\n".join(lines[:4]) or "Errore sconosciuto"


# --------------------------------------------------------------------------- #
# Formati
# --------------------------------------------------------------------------- #
class Fmt:
    def __init__(self, key, label, ext, coder, alpha=True, multi=False, desc="", popular=False, aliases=()):
        self.key, self.label, self.ext, self.coder = key, label, ext, coder
        self.alpha, self.multi, self.desc, self.popular = alpha, multi, desc, popular
        self.aliases = set(aliases) | {ext.lstrip(".")}


FORMATS = [
    Fmt("png", "PNG", ".png", "PNG", desc="Senza perdita, trasparenza. Universale.", popular=True),
    Fmt("jpg", "JPG", ".jpg", "JPEG", alpha=False, desc="Foto, file piccoli. Nessuna trasparenza.", popular=True, aliases=("jpeg", "jpe", "jfif")),
    Fmt("webp", "WEBP", ".webp", "WEBP", multi=True, desc="Formato web moderno, con o senza perdita, animazioni.", popular=True),
    Fmt("avif", "AVIF", ".avif", "AVIF", desc="AV1: compressione eccellente, ideale per il web.", popular=True),
    Fmt("dds", "DDS", ".dds", "DDS", desc="DirectDraw Surface: texture compresse BCn per giochi e 3D.", popular=True),
    Fmt("ico", "ICO", ".ico", "ICO", desc="Icona Windows con più risoluzioni in un file.", popular=True),
    Fmt("gif", "GIF", ".gif", "GIF", multi=True, desc="256 colori, animazioni.", popular=True),
    Fmt("tiff", "TIFF", ".tif", "TIFF", multi=True, desc="Archiviazione e stampa, multipagina.", popular=True, aliases=("tiff",)),
    Fmt("bmp", "BMP", ".bmp", "BMP", desc="Bitmap Windows non compressa.", popular=True, aliases=("dib",)),
    Fmt("tga", "TGA", ".tga", "TGA", desc="Truevision Targa, molto usato nel game dev.", popular=True),
    Fmt("jxl", "JXL", ".jxl", "JXL", desc="JPEG XL: qualità altissima, anche senza perdita.", popular=True),
    Fmt("psd", "PSD", ".psd", "PSD", desc="Documento Photoshop.", popular=True),
    Fmt("exr", "EXR", ".exr", "EXR", desc="OpenEXR, HDR in virgola mobile."),
    Fmt("hdr", "HDR", ".hdr", "HDR", alpha=False, desc="Radiance RGBE, HDR."),
    Fmt("qoi", "QOI", ".qoi", "QOI", desc="Quite OK Image: senza perdita e velocissimo."),
    Fmt("jp2", "JPEG 2000", ".jp2", "JP2", desc="JPEG 2000."),
    Fmt("pdf", "PDF", ".pdf", "PDF", alpha=False, multi=True, desc="Documento PDF (una pagina per immagine)."),
    Fmt("apng", "APNG", ".apng", "APNG", multi=True, desc="PNG animato."),
    Fmt("cur", "CUR", ".cur", "CUR", desc="Cursore Windows."),
    Fmt("ppm", "PPM", ".ppm", "PPM", alpha=False, desc="Portable Pixmap (Netpbm)."),
    Fmt("pgm", "PGM", ".pgm", "PGM", alpha=False, desc="Portable Graymap, scala di grigi."),
    Fmt("pbm", "PBM", ".pbm", "PBM", alpha=False, desc="Portable Bitmap, bianco e nero."),
    Fmt("pam", "PAM", ".pam", "PAM", desc="Portable Arbitrary Map, con alpha."),
    Fmt("pfm", "PFM", ".pfm", "PFM", alpha=False, desc="Portable Float Map."),
    Fmt("pcx", "PCX", ".pcx", "PCX", alpha=False, desc="ZSoft Paintbrush."),
    Fmt("sgi", "SGI", ".sgi", "SGI", desc="Silicon Graphics RGB."),
    Fmt("xpm", "XPM", ".xpm", "XPM", desc="X PixMap."),
    Fmt("xbm", "XBM", ".xbm", "XBM", alpha=False, desc="X BitMap, bianco e nero."),
    Fmt("wbmp", "WBMP", ".wbmp", "WBMP", alpha=False, desc="Wireless Bitmap."),
    Fmt("dpx", "DPX", ".dpx", "DPX", alpha=False, desc="Digital Picture Exchange (cinema)."),
    Fmt("fits", "FITS", ".fits", "FITS", alpha=False, desc="Formato astronomico."),
    Fmt("ras", "SUN", ".ras", "SUN", alpha=False, desc="Sun Rasterfile."),
    Fmt("eps", "EPS", ".eps", "EPS", alpha=False, desc="Encapsulated PostScript."),
    Fmt("miff", "MIFF", ".miff", "MIFF", multi=True, desc="Formato nativo ImageMagick."),
]
FMT = {f.key: f for f in FORMATS}


# Spec. delle opzioni per formato (la UI le costruisce automaticamente)
def _slider(id, label, lo, hi, default, **kw):
    return dict(type="slider", id=id, label=label, min=lo, max=hi, default=default, **kw)


def _combo(id, label, items, default, **kw):
    return dict(type="combo", id=id, label=label, items=items, default=default, **kw)


def _check(id, label, default, **kw):
    return dict(type="check", id=id, label=label, default=default, **kw)


def _spin(id, label, lo, hi, default, **kw):
    return dict(type="spin", id=id, label=label, min=lo, max=hi, default=default, **kw)


def _chips(id, label, items, default, **kw):
    return dict(type="chips", id=id, label=label, items=items, default=default, **kw)


DDS_COMPRESSIONS = [
    ("Automatica (BC1 se opaca, BC3 se trasparente)", "auto"),
    ("BC1 / DXT1 - RGB, alpha 1 bit (4 bpp)", "dxt1"),
    ("BC2 / DXT3 - alpha netto (8 bpp)", "dxt3"),
    ("BC3 / DXT5 - alpha sfumato (8 bpp)", "dxt5"),
    ("BC7 - qualità massima RGBA (8 bpp)", "bc7", "texconv"),
    ("BC4 - canale singolo (maschere, roughness)", "bc4", "texconv"),
    ("BC5 - due canali (normal map)", "bc5", "texconv"),
    ("BC6H - HDR", "bc6h", "texconv"),
    ("Non compressa (RGBA8)", "none"),
]

MIP_LEVELS = [("Catena completa", "0")] + [(str(i), str(i)) for i in range(2, 14)]

FORMAT_OPTIONS = {
    "jpg": [
        _slider("quality", "Qualità", 1, 100, 90),
        _combo("sampling", "Sottocampionamento colore",
               [("4:2:0 - file più piccolo", "4:2:0"), ("4:2:2", "4:2:2"), ("4:4:4 - massima fedeltà", "4:4:4")], "4:2:0"),
        _check("progressive", "JPEG progressivo (caricamento graduale sul web)", True),
        _spin("extent", "Dimensione massima del file", 0, 100000, 0, suffix=" KB", special="Nessun limite",
              hint="Riduce la qualità automaticamente fino a stare sotto il limite."),
    ],
    "png": [
        _combo("depth", "Profondità colore",
               [("Automatica", "auto"), ("8 bit con palette (PNG8)", "PNG8"), ("24 bit RGB", "PNG24"),
                ("32 bit RGBA", "PNG32"), ("48 bit RGB", "PNG48"), ("64 bit RGBA", "PNG64")], "auto"),
        _slider("level", "Livello compressione", 0, 9, 9, hint="Senza perdita: incide solo su dimensione e velocità."),
        _check("interlace", "Interlacciato (Adam7)", False),
    ],
    "webp": [
        _check("lossless", "Senza perdita (lossless)", False),
        _slider("quality", "Qualità", 1, 100, 85, enabled_if=("lossless", False)),
        _slider("method", "Sforzo di compressione", 0, 6, 5, hint="Più alto = file più piccolo ma più lento."),
    ],
    "avif": [
        _slider("quality", "Qualità", 1, 100, 70),
        _slider("speed", "Velocità encoder", 0, 9, 6, hint="Più basso = file più piccolo ma molto più lento."),
    ],
    "jxl": [
        _slider("quality", "Qualità", 1, 100, 90, hint="100 = senza perdita."),
        _slider("effort", "Sforzo", 1, 9, 7),
    ],
    "dds": [
        _combo("compression", "Compressione", DDS_COMPRESSIONS, "auto"),
        _check("mipmaps", "Genera mipmap", True),
        _combo("mip_levels", "Livelli mipmap", MIP_LEVELS, "0", enabled_if=("mipmaps", True)),
        _check("cluster", "Alta qualità (cluster fit)", True, enabled_if=("compression", ("auto", "dxt1", "dxt3", "dxt5")),
               hint="Compressione più lenta ma con meno artefatti."),
        _check("alpha_weight", "Pesa i colori in base all'alpha", False,
               enabled_if=("compression", ("auto", "dxt1", "dxt3", "dxt5"))),
        _combo("bc_quality", "Qualità BC7/BC6H", [("Veloce", "quick"), ("Bilanciata", "normal"), ("Massima (lenta)", "max")],
               "normal", enabled_if=("compression", ("bc7", "bc6h"))),
        _check("srgb", "Texture sRGB (colore)", False, enabled_if=("compression", ("bc7",)),
               hint="Usa il formato _SRGB: attivalo per texture di colore se il tuo motore lo richiede."),
    ],
    "ico": [
        _chips("sizes", "Risoluzioni incluse", ["256", "128", "64", "48", "32", "24", "16"], ["256", "64", "48", "32", "16"],
               hint="Limite del formato ICO: massimo 256×256. Le immagini più grandi vengono ridotte."),
    ],
    "cur": [
        _chips("sizes", "Risoluzioni incluse", ["128", "64", "48", "32", "16"], ["32"],
               hint="Limite del formato CUR: le immagini vengono ridotte alle risoluzioni scelte."),
    ],
    "gif": [
        _slider("colors", "Numero di colori", 2, 256, 256),
        _check("dither", "Dithering (sfumature più morbide)", True),
        _check("optimize", "Ottimizza animazioni", True),
    ],
    "tiff": [
        _combo("compress", "Compressione",
               [("LZW (senza perdita)", "LZW"), ("ZIP / Deflate (senza perdita)", "Zip"), ("ZSTD (senza perdita)", "ZSTD"),
                ("JPEG (con perdita)", "JPEG"), ("Nessuna", "None")], "LZW"),
        _slider("quality", "Qualità JPEG", 1, 100, 90, enabled_if=("compress", ("JPEG",))),
    ],
    "tga": [_check("rle", "Compressione RLE", True)],
    "bmp": [_combo("version", "Versione", [("BMP v4/v5 (supporta alpha)", "BMP"), ("BMP v3 (massima compatibilità)", "BMP3")], "BMP")],
    "jp2": [_slider("quality", "Qualità", 1, 100, 85)],
    "pdf": [
        _combo("compress", "Compressione immagini", [("JPEG", "JPEG"), ("ZIP (senza perdita)", "Zip")], "JPEG"),
        _slider("quality", "Qualità", 1, 100, 90, enabled_if=("compress", ("JPEG",))),
    ],
    "exr": [_combo("compress", "Compressione", [("ZIP", "Zip"), ("PIZ", "Piz"), ("Nessuna", "None")], "Zip")],
}


def option_defaults(key):
    return {sp["id"]: sp["default"] for sp in FORMAT_OPTIONS.get(key, [])}


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #
RASTER_EXT = set("""png jpg jpeg jpe jfif webp avif heic heif hif jxl dds tga icb vda vst bmp dib gif tif tiff ico cur psd psb
exr hdr qoi jp2 j2k j2c jpc jpf jpx jpm ppm pgm pbm pam pnm pfm pcx dcx sgi rgb rgba bw xpm xbm wbmp dpx cin fits fts fit
miff mng jng apng pict pct ras sun xcf otb palm viff vips wpg pcd emf wmf""".split())
RAW_EXT = set("""dng cr2 cr3 crw nef nrw arw srf sr2 orf rw2 raf pef ptx raw rwl 3fr fff erf kdc dcr mrw iiq mef mos x3f srw""".split())
VECTOR_EXT = set("svg svgz pdf eps epsf ai ps".split())
VIDEO_EXT = set("mp4 mov mkv avi webm m4v wmv flv mpg mpeg ts m2ts 3gp".split())
INPUT_EXT = RASTER_EXT | RAW_EXT | VECTOR_EXT | VIDEO_EXT
PILLOW_SKIP = RAW_EXT | VECTOR_EXT | VIDEO_EXT | {"heic", "heif", "hif", "jxl", "avif", "exr", "xcf", "emf", "wmf"}


def ext_of(path):
    return os.path.splitext(path)[1].lower().lstrip(".")


def is_supported(path):
    return ext_of(path) in INPUT_EXT


# --------------------------------------------------------------------------- #
# Analisi / miniature
# --------------------------------------------------------------------------- #
def probe(path, tools: Tools, thumb=160):
    """Restituisce dimensioni, formato, alpha, frame e una miniatura PNG (bytes)."""
    info = dict(w=0, h=0, fmt=ext_of(path).upper(), alpha=False, frames=1, thumb=None, error=None)
    ext = ext_of(path)

    if ext in VIDEO_EXT:
        if not tools.ffmpeg:
            info["error"] = "ffmpeg non trovato"
            return info
        code, out, err = run([tools.ffmpeg, "-hide_banner", "-i", path, "-frames:v", "1",
                              "-vf", f"scale='min({thumb},iw)':-2", "-f", "image2pipe", "-c:v", "png", "-"])
        m = re.search(rb"Video:.*?(\d{2,5})x(\d{2,5})", err)
        if m:
            info["w"], info["h"] = int(m.group(1)), int(m.group(2))
        info["fmt"] = "VIDEO"
        info["thumb"] = out or None
        return info

    if ext not in PILLOW_SKIP:
        try:
            from PIL import Image, ImageOps
            Image.MAX_IMAGE_PIXELS = None
            with Image.open(path) as im:
                info["fmt"] = (im.format or info["fmt"]).upper()
                info["frames"] = getattr(im, "n_frames", 1)
                info["alpha"] = im.mode in ("RGBA", "LA", "PA", "RGBa", "La") or "transparency" in im.info
                info["w"], info["h"] = im.size
                if thumb:
                    if im.format == "JPEG":
                        im.draft("RGB", (thumb * 2, thumb * 2))
                    t = ImageOps.exif_transpose(im)
                    if t.size != im.size and im.format == "JPEG":
                        info["w"], info["h"] = info["h"], info["w"]
                    t.thumbnail((thumb, thumb))
                    if t.mode not in ("RGB", "RGBA"):
                        t = t.convert("RGBA")
                    buf = io.BytesIO()
                    t.save(buf, "PNG", compress_level=1)
                    info["thumb"] = buf.getvalue()
            return info
        except Exception:
            pass

    if not tools.magick:
        info["error"] = "ImageMagick non trovato"
        return info
    pre = ["-density", "72"] if ext in VECTOR_EXT else []
    code, out, err = run([tools.magick, "identify", "-ping", "-format", r"%w|%h|%m|%A\n", path])
    lines = [ln for ln in out.decode("utf-8", "replace").splitlines() if "|" in ln]
    if lines:
        w, h, m, a = (lines[0].split("|") + ["", "", "", ""])[:4]
        try:
            info["w"], info["h"] = int(w), int(h)
        except ValueError:
            pass
        info["fmt"] = m.upper() or info["fmt"]
        info["alpha"] = a.strip().lower() not in ("false", "undefined", "")
        info["frames"] = len(lines)
    elif code != 0:
        info["error"] = clean_error(err)
    if thumb:
        bg = ["-background", "none"] if ext in ("svg", "svgz") else []
        code, out, err = run([tools.magick, *pre, *bg, f"{path}[0]", "-auto-orient", "-thumbnail",
                              f"{thumb}x{thumb}>", "PNG32:-"])
        if code == 0 and out:
            info["thumb"] = out
        elif not info["error"] and not lines:
            info["error"] = clean_error(err)
        if not out and tools.ffmpeg:  # ultima spiaggia
            code, out, err = run([tools.ffmpeg, "-hide_banner", "-loglevel", "error", "-i", path, "-frames:v", "1",
                                  "-vf", f"scale='min({thumb},iw)':-2", "-f", "image2pipe", "-c:v", "png", "-"])
            if out:
                info["thumb"] = out
                info["error"] = None
    return info


def identify_dims(path, tools):
    if not tools.magick:
        return 0, 0
    code, out, _ = run([tools.magick, "identify", "-ping", "-format", r"%w|%h\n", path])
    try:
        w, h = out.decode().splitlines()[0].split("|")
        return int(w), int(h)
    except Exception:
        return 0, 0


# --------------------------------------------------------------------------- #
# Dimensioni
# --------------------------------------------------------------------------- #
def _pot(v, mode):
    if v <= 1:
        return 1
    lo = 1 << (v.bit_length() - 1)
    hi = lo if lo == v else lo << 1
    if mode == "up":
        return hi
    if mode == "down":
        return lo
    if mode == "mul4":
        return max(4, (v + 3) // 4 * 4)
    return lo if (v - lo) <= (hi - v) else hi


POT_FORMATS = {"dds"}


def pot_mode(s):
    """La potenza di 2 vale solo per le texture: non deve mai toccare foto o altri formati."""
    return s["resize"].get("pot", "none") if s.get("format") in POT_FORMATS else "none"


def predict_dims(w, h, s):
    """Dimensioni finali previste (dopo ridimensionamento e potenza di 2)."""
    if not w or not h:
        return 0, 0
    if s.get("rotate") in (90, 270):
        w, h = h, w
    r = s["resize"]
    m = r["mode"]
    shrink = r.get("only_shrink", True)
    nw, nh = w, h
    if m == "percent":
        p = r["percent"] / 100.0
        if shrink:
            p = min(p, 1.0)
        nw, nh = round(w * p), round(h * p)
    elif m in ("fit", "long"):
        W, H = (r["w"], r["h"]) if m == "fit" else (r["long"], r["long"])
        sc = min(W / w if W else 1e9, H / h if H else 1e9)
        if sc >= 1e9:
            sc = 1.0
        if shrink:
            sc = min(sc, 1.0)
        nw, nh = round(w * sc), round(h * sc)
    elif m == "exact":
        nw, nh = r["w"] or w, r["h"] or h
    elif m == "fill":
        nw, nh = r["w"] or w, r["h"] or h
    nw, nh = max(1, nw), max(1, nh)
    pm = pot_mode(s)
    if pm != "none":
        nw, nh = _pot(nw, pm), _pot(nh, pm)
    return nw, nh


def resize_ops(s, w, h):
    r = s["resize"]
    m = r["mode"]
    ops = []
    if r.get("filter", "auto") != "auto":
        ops += ["-filter", r["filter"]]
    shrink = ">" if r.get("only_shrink", True) else ""
    if m == "percent" and r["percent"] != 100:
        ops += ["-resize", f"{r['percent']}%{shrink}"]
    elif m == "fit" and (r["w"] or r["h"]):
        ops += ["-resize", f"{r['w'] or ''}x{r['h'] or ''}{shrink}"]
    elif m == "long" and r["long"]:
        ops += ["-resize", f"{r['long']}x{r['long']}{shrink}"]
    elif m == "exact" and (r["w"] or r["h"]):
        ops += ["-resize", f"{r['w'] or w}x{r['h'] or h}!"]
    elif m == "fill" and r["w"] and r["h"]:
        ops += ["-resize", f"{r['w']}x{r['h']}^", "-gravity", "center", "-background", "none",
                "-extent", f"{r['w']}x{r['h']}", "+gravity"]
    if pot_mode(s) != "none" and w and h:
        pw, ph = predict_dims(w, h, s)
        ops += ["-resize", f"{pw}x{ph}!"]
    return ops


# --------------------------------------------------------------------------- #
# Percorsi di uscita
# --------------------------------------------------------------------------- #
_reserve_lock = threading.Lock()
_reserved: set[str] = set()


def reset_reservations():
    with _reserve_lock:
        _reserved.clear()


class _SafeDict(dict):
    def __missing__(self, k):
        return "{" + k + "}"


_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def output_folder(job, s):
    src_dir = os.path.dirname(job["path"])
    mode = s["out_mode"]
    if mode == "sub":
        return os.path.join(src_dir, s.get("subfolder") or "convertiti")
    if mode == "custom" and s.get("out_dir"):
        base = s["out_dir"]
        if s.get("keep_structure") and job.get("rel"):
            base = os.path.join(base, job["rel"])
        return base
    return src_dir


def output_name(job, s, fmt, index, dims):
    src = job["path"]
    base = os.path.splitext(os.path.basename(src))[0]
    now = datetime.datetime.now()
    tokens = _SafeDict(
        name=base, ext=ext_of(src), fmt=fmt.ext.lstrip("."), w=dims[0] or "", h=dims[1] or "",
        n=f"{index + 1:03d}", date=now.strftime("%Y-%m-%d"), time=now.strftime("%H%M%S"),
        parent=os.path.basename(os.path.dirname(src)),
    )
    try:
        name = (s.get("pattern") or "{name}").format_map(tokens)
    except (ValueError, IndexError):
        name = s.get("pattern") or base
    name = _BAD.sub("_", name).strip(" .") or base
    return name + fmt.ext


def plan_output(job, s, fmt, index, dims):
    folder = output_folder(job, s)
    path = os.path.join(folder, output_name(job, s, fmt, index, dims))
    src_key = os.path.normcase(os.path.abspath(job["path"]))
    with _reserve_lock:
        key = os.path.normcase(os.path.abspath(path))
        clash = key == src_key or key in _reserved or os.path.exists(path)
        if clash:
            policy = s.get("conflict", "rename")
            if policy == "skip" and key != src_key and key not in _reserved:
                return None
            if not (policy == "overwrite" and key != src_key and key not in _reserved):
                stem, ext = os.path.splitext(path)
                i = 2
                while True:
                    cand = f"{stem} ({i}){ext}"
                    ck = os.path.normcase(os.path.abspath(cand))
                    if ck not in _reserved and ck != src_key and not os.path.exists(cand):
                        path, key = cand, ck
                        break
                    i += 1
        _reserved.add(key)
    return path


# --------------------------------------------------------------------------- #
# Conversione
# --------------------------------------------------------------------------- #
def _format_args(fmt, o):
    k = fmt.key
    a = []
    coder = fmt.coder
    if k == "jpg":
        a += ["-quality", str(o["quality"]), "-sampling-factor", o["sampling"]]
        if o["progressive"]:
            a += ["-interlace", "Plane"]
        if o["extent"]:
            a += ["-define", f"jpeg:extent={o['extent']}KB"]
    elif k == "png":
        a += ["-define", f"png:compression-level={o['level']}"]
        if o["interlace"]:
            a += ["-interlace", "PNG"]
        if o["depth"] != "auto":
            coder = o["depth"]
    elif k == "webp":
        a += ["-define", f"webp:method={o['method']}"]
        if o["lossless"]:
            a += ["-define", "webp:lossless=true", "-quality", "100"]
        else:
            a += ["-quality", str(o["quality"])]
    elif k == "avif":
        a += ["-quality", str(o["quality"]), "-define", f"heic:speed={o['speed']}"]
    elif k == "jxl":
        a += ["-quality", str(o["quality"]), "-define", f"jxl:effort={o['effort']}"]
    elif k == "tiff":
        a += ["-compress", o["compress"]]
        if o["compress"] == "JPEG":
            a += ["-quality", str(o["quality"])]
    elif k == "tga":
        a += ["-compress", "RLE" if o["rle"] else "None"]
    elif k == "bmp":
        coder = o["version"]
    elif k == "gif":
        a += ["-dither", "FloydSteinberg" if o["dither"] else "None"]
        if o["colors"] < 256:
            a += ["-colors", str(o["colors"])]
    elif k in ("ico", "cur"):
        sizes = [x for x in o["sizes"]] or ["32"]
        a += ["-define", "icon:auto-resize=" + ",".join(sorted(sizes, key=int, reverse=True))]
    elif k == "jp2":
        a += ["-quality", str(o["quality"])]
    elif k == "pdf":
        a += ["-compress", o["compress"]]
        if o["compress"] == "JPEG":
            a += ["-quality", str(o["quality"])]
    elif k == "exr":
        a += ["-compress", o["compress"]]
    return a, coder


def _is_opaque(args, tools, env, cancel):
    code, out, _ = run([tools.magick, *args, "-format", "%[opaque]", "info:"], cancel, env)
    return out.decode(errors="replace").strip().lower().startswith("true")


def _ffmpeg_frame(src, tmp, tools, cancel):
    if not tools.ffmpeg:
        raise ConvertError("ffmpeg non disponibile")
    dst = os.path.join(tmp, "ffmpeg_frame.png")
    code, _, err = run([tools.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", src,
                        "-frames:v", "1", dst], cancel)
    if code != 0 or not os.path.exists(dst):
        raise ConvertError("ffmpeg: " + clean_error(err))
    return dst


TEXCONV_FMT = {"bc7": "BC7_UNORM", "bc4": "BC4_UNORM", "bc5": "BC5_UNORM", "bc6h": "BC6H_UF16"}


def convert(job, s, tools: Tools, cancel=None, index=0, threads_per_job=None):
    """Converte un file. `job` è un dict (path, rel, w, h, alpha, frames). Ritorna un dict risultato."""
    if not tools.magick:
        raise ConvertError("ImageMagick non trovato: installalo da imagemagick.org")
    fmt = FMT[s["format"]]
    o = {**option_defaults(fmt.key), **s.get("fmt_opts", {}).get(fmt.key, {})}
    src = job["path"]
    ext = ext_of(src)

    if not os.path.exists(src):
        raise ConvertError("Il file originale non esiste più")
    if s.get("skip_same") and ext in fmt.aliases:
        return dict(status="skipped", msg=f"Già in formato {fmt.label}")

    w, h = job.get("w") or 0, job.get("h") or 0
    needs_dims = pot_mode(s) != "none" or "{w}" in s.get("pattern", "") or "{h}" in s.get("pattern", "")
    if needs_dims and not w and ext not in VIDEO_EXT:
        w, h = identify_dims(f"{src}[0]", tools)
    dims = predict_dims(w, h, s) if w else (0, 0)
    if not w:
        dims = (0, 0)
    out = plan_output(job, s, fmt, index, dims)
    if out is None:
        return dict(status="skipped", msg="Il file di destinazione esiste già")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    env = os.environ.copy()
    if threads_per_job:
        env["MAGICK_THREAD_LIMIT"] = str(threads_per_job)

    tmp = tempfile.mkdtemp(prefix="prisma_")
    try:
        inp = _ffmpeg_frame(src, tmp, tools, cancel) if ext in VIDEO_EXT else src
        try:
            outs = _produce(inp, ext, job, s, fmt, o, out, w, h, tmp, tools, env, cancel)
        except ConvertError as e:
            msg = str(e).lower()
            decode_issue = any(x in msg for x in ("decode delegate", "improper image header", "unable to open",
                                                  "not a valid", "corrupt", "unsupported", "no images defined"))
            if ext not in VIDEO_EXT and tools.ffmpeg and decode_issue:
                try:
                    inp = _ffmpeg_frame(src, tmp, tools, cancel)
                except ConvertError:
                    raise e
                outs = _produce(inp, "png", job, s, fmt, o, out, w, h, tmp, tools, env, cancel)
            else:
                raise
        if s.get("keep_date"):
            st = os.stat(src)
            for p in outs:
                os.utime(p, (st.st_atime, st.st_mtime))
        total = sum(os.path.getsize(p) for p in outs)
        msg = f"{len(outs)} file" if len(outs) > 1 else ""
        return dict(status="done", out=outs[0], outs=outs, size=total, msg=msg)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _produce(inp, ext, job, s, fmt, o, out, w, h, tmp, tools, env, cancel):
    frames_mode = s.get("frames", "keep")
    animated_src = ext in ("gif", "webp", "apng", "mng", "png")
    if frames_mode == "separate":
        read = inp
    elif frames_mode == "keep" and fmt.multi:
        read = inp
    else:
        read = f"{inp}[0]"
    reading_all = read == inp

    pre = []
    if ext in VECTOR_EXT:
        pre += ["-density", str(s.get("density", 150))]
        if ext in ("svg", "svgz"):
            pre += ["-background", "none"]

    ops = []
    if reading_all and animated_src and s["resize"]["mode"] != "none":
        ops += ["-coalesce"]
    if s.get("auto_orient", True):
        ops += ["-auto-orient"]
    if s.get("rotate"):
        ops += ["-background", "none", "-rotate", str(s["rotate"])]
    if s.get("flip"):
        ops += ["-flip"]
    if s.get("flop"):
        ops += ["-flop"]
    ops += resize_ops(s, w, h)
    if not fmt.alpha or s.get("flatten"):
        ops += ["-background", s.get("bg", "#ffffff"), "-alpha", "remove", "-alpha", "off"]
    if s.get("strip"):
        ops += ["-strip"]

    # ----- DDS -----
    if fmt.key == "dds":
        comp = o["compression"]
        levels = o["mip_levels"] if o["mipmaps"] else "1"
        if comp in TEXCONV_FMT:
            if not tools.texconv:
                raise ConvertError("Per BC4/BC5/BC6H/BC7 serve texconv.exe (DirectXTex) nella cartella tools di Prisma")
            png = os.path.join(tmp, "texture.png")
            code, _, err = run([tools.magick, *pre, f"{inp}[0]", *ops, "-depth", "8", f"PNG32:{png}"], cancel, env)
            if code != 0 or not os.path.exists(png):
                raise ConvertError(clean_error(err))
            tfmt = TEXCONV_FMT[comp]
            if comp == "bc7" and o.get("srgb"):
                tfmt = "BC7_UNORM_SRGB"
            cmd = [tools.texconv, "-nologo", "-y", "-f", tfmt, "-m", levels, "-o", tmp]
            if comp in ("bc7", "bc6h"):
                if o.get("bc_quality") == "quick":
                    cmd += ["-bc", "q"]
                elif o.get("bc_quality") == "max":
                    cmd += ["-bc", "x"]
            code, so, err = run(cmd + [png], cancel, env)
            res = os.path.join(tmp, "texture.dds")
            if code != 0 or not os.path.exists(res):
                raise ConvertError("texconv: " + clean_error(err or so))
            shutil.move(res, out)
            return [out]
        if comp == "auto":
            comp = "dxt1" if _is_opaque([*pre, f"{inp}[0]", *ops], tools, env, cancel) else "dxt5"
        fargs = ["-define", f"dds:compression={comp}"]
        if levels != "0":
            fargs += ["-define", f"dds:mipmaps={int(levels) - 1}"]
        if o["cluster"] and comp != "none":
            fargs += ["-define", "dds:cluster-fit=true"]
        if o["alpha_weight"] and comp != "none":
            fargs += ["-define", "dds:weight-by-alpha=true"]
        coder = "DDS"
        read = f"{inp}[0]"
    else:
        fargs, coder = _format_args(fmt, o)
        if fmt.key == "gif" and reading_all and o.get("optimize"):
            fargs += ["-layers", "Optimize"]

    # ----- frame separati -----
    if frames_mode == "separate" and fmt.key != "dds":
        pattern = os.path.join(tmp, "frame_%04d" + fmt.ext)
        code, _, err = run([tools.magick, *pre, read, *ops, *fargs, "+adjoin", f"{coder}:{pattern}"], cancel, env)
        produced = sorted(glob.glob(os.path.join(tmp, "frame_*" + fmt.ext)))
        if code != 0 or not produced:
            raise ConvertError(clean_error(err))
        if len(produced) == 1:
            shutil.move(produced[0], out)
            return [out]
        stem, e = os.path.splitext(out)
        outs = []
        for i, p in enumerate(produced, 1):
            dst = f"{stem}_{i:03d}{e}"
            k = 2
            while os.path.exists(dst) and s.get("conflict") != "overwrite":
                dst = f"{stem}_{i:03d} ({k}){e}"
                k += 1
            shutil.move(p, dst)
            outs.append(dst)
        return outs

    part = out + ".prisma-part"
    code, _, err = run([tools.magick, *pre, read, *ops, *fargs, f"{coder}:{part}"], cancel, env)
    if code != 0 or not os.path.exists(part):
        try:
            os.remove(part)
        except OSError:
            pass
        raise ConvertError(clean_error(err))
    os.replace(part, out)
    return [out]
