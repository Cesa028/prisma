# Prisma

**Convertitore di immagini per Windows: veloce, completo e con un'interfaccia curata.**

Prisma converte, ridimensiona e ottimizza le immagini in blocco. Trascina file o cartelle (o incolla con `Ctrl+V`), scegli il formato di uscita e regola ogni dettaglio. Legge più di 90 formati e ne scrive oltre 30, comprese le texture DDS per giochi e grafica 3D. Sotto il cofano usa [ImageMagick](https://imagemagick.org), FFmpeg e Microsoft DirectXTex, tutti inclusi nell'installer.

![Licenza MIT](https://img.shields.io/badge/licenza-MIT-green) ![Piattaforma](https://img.shields.io/badge/piattaforma-Windows%2010%2F11-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-yellow)

---

## Indice

- [Download](#download)
- [Funzionalità](#funzionalità)
- [Formati](#formati)
- [Come si usa](#come-si-usa)
- [Eseguire dal codice sorgente](#eseguire-dal-codice-sorgente)
- [Creare l'installer](#creare-linstaller)
- [Struttura del progetto](#struttura-del-progetto)
- [Licenza e componenti di terze parti](#licenza-e-componenti-di-terze-parti)
- [English summary](#english-summary)

---

## Download

L'installer per Windows è nella sezione **[Releases](../../releases/latest)**: scarica `Prisma-Setup-1.1.1.exe` ed eseguilo. Tutti gli strumenti necessari (ImageMagick, FFmpeg, texconv) sono già inclusi.

## Funzionalità

- **Conversione in blocco**: coda di file con trascinamento di file e cartelle, incolla dagli appunti, anteprima e miniature.
- **Conversioni in parallelo**, con numero di processi configurabile nelle impostazioni.
- **Opzioni specifiche per ogni formato**: livello di compressione e interlacciamento per PNG, qualità e metodo per WEBP, qualità e velocità per AVIF, effort per JPEG XL, compressione BCn e mipmap per DDS, risoluzioni multiple per ICO e molto altro.
- **Ridimensionamento flessibile**: dimensioni originali, percentuale, adattamento a un riquadro, lato lungo, dimensioni esatte oppure riempimento con ritaglio centrale. Filtro di ricampionamento selezionabile.
- **Potenza di 2 per le texture**: arrotondamento automatico (più vicina, per eccesso, per difetto), utile per il formato DDS.
- **Rotazione** e gestione di **animazioni e pagine multiple** (GIF, WEBP, TIFF, PDF): puoi mantenerle, estrarre solo il primo fotogramma o salvare ogni fotogramma in un file separato.
- **Immagini vettoriali** (SVG, PDF) con DPI di rasterizzazione regolabile.
- **Fotogrammi dai video**: Prisma può estrarre un'immagine anche da un file video, grazie a FFmpeg.
- **Destinazione e nomi dei file**: cartella accanto all'originale, sottocartella o cartella a scelta; schema dei nomi con segnaposto; comportamento configurabile se il file esiste già.
- **Preset**: salva le tue impostazioni preferite e richiamale in un clic.
- **Interfaccia moderna** con tema **scuro e chiaro** (o quello del sistema, con cambio immediato), avanzamento nel titolo della finestra e menu contestuali (apri originale, apri convertito, copia percorso, riconverti).
- **Pensata per la tastiera**: scorciatoie per tutto (`Ctrl+O`, `Ctrl+V`, `Ctrl+Invio`, `Esc`, `Ctrl+F`, `Ctrl+Z` per riportare in lista i file rimossi, `F1` per le informazioni, `Ctrl+,` per le impostazioni), focus sempre visibile e nomi accessibili per i lettori di schermo.

## Formati

**Ingresso (oltre 90 formati):** PNG, JPG, WEBP, AVIF, HEIC/HEIF, JPEG XL, DDS, TGA, BMP, GIF, TIFF, ICO, PSD, EXR, SVG, PDF, formati RAW delle fotocamere e molti altri.

**Uscita (oltre 30 formati):**

| Uso comune | Formati |
|---|---|
| Web | PNG, JPG, WEBP, AVIF, JXL, GIF, APNG |
| Giochi e 3D | DDS (BC1–BC7 tramite texconv), TGA, QOI, EXR, HDR |
| Sistema e icone | ICO, CUR, BMP |
| Stampa e archivio | TIFF, PDF, PSD, JPEG 2000, EPS, DPX |
| Altri | PPM, PGM, PBM, PAM, PFM, PCX, SGI, XPM, XBM, WBMP, FITS, SUN, MIFF |

## Come si usa

1. Avvia **Prisma** e trascina nella finestra le immagini o le cartelle da convertire.
2. Scegli il **formato di uscita** e regola le opzioni nel pannello laterale.
3. Imposta, se serve, ridimensionamento, rotazione, destinazione e schema dei nomi.
4. Premi il pulsante di conversione e segui l'avanzamento nella lista.

## Eseguire dal codice sorgente

Requisiti: **Python 3.10 o superiore** e le librerie `PySide6` e `Pillow`. Servono inoltre **ImageMagick 7** e **FFmpeg**, installati sul sistema oppure copiati nella cartella `bin/` accanto ai sorgenti. Per i formati DDS BC4/BC5/BC6H/BC7 serve `texconv.exe` (incluso in `tools/`; Prisma può anche scaricarlo dalle impostazioni).

```bat
pip install PySide6 pillow
python Prisma.pyw
```

## Creare l'installer

Servono PyInstaller, PySide6, Pillow e [Inno Setup 6](https://jrsoftware.org/isinfo.php), oltre a ImageMagick installato in Program Files e a FFmpeg in `C:\ffmpeg`.

```bat
pip install pyinstaller PySide6 pillow
python build.py   :: crea dist\Prisma-Setup-<versione>.exe
```

## Struttura del progetto

```
Prisma/
├─ Prisma.pyw        avvio dell'applicazione
├─ ui.py             finestra principale e avvio
├─ dialogs.py        anteprima, impostazioni, informazioni e licenze
├─ widgets.py        lista file, drop zone, toast, form delle opzioni
├─ jobs.py           job di conversione e worker in background
├─ theme.py          design token e temi scuro/chiaro
├─ common.py         versione, percorsi e utilità condivise
├─ engine.py         motore di conversione (ImageMagick, FFmpeg, texconv)
├─ icons.py          icone vettoriali che seguono il tema
├─ build.py          build dell'eseguibile e dell'installer
├─ installer/        script Inno Setup e pagina della licenza
├─ tools/            texconv.exe (Microsoft DirectXTex)
├─ licenses/         testi delle licenze di terze parti
└─ LICENSE.txt       licenza MIT del progetto
```

## Licenza e componenti di terze parti

Il codice di Prisma è rilasciato con licenza **MIT** (vedi [`LICENSE.txt`](LICENSE.txt)), © 2026 Cesa028.

L'installer include software di terze parti, ciascuno con la propria licenza e usato come programma esterno senza modifiche:

- **ImageMagick** (licenza ImageMagick) e le sue librerie;
- **FFmpeg** (GPL-3.0);
- **texconv / DirectXTex** (MIT, Microsoft);
- **Qt 6 / PySide6** (LGPL-3.0), **Pillow** (HPND) e **Python** (PSF License).

L'elenco completo, con versioni e riferimenti ai sorgenti, è in [`licenses/THIRD-PARTY-NOTICES.txt`](licenses/THIRD-PARTY-NOTICES.txt). ImageMagick Studio LLC non è affiliata a Prisma e non lo approva.

---

## English summary

**Prisma** is a Windows 10/11 (64-bit) batch image converter. It reads 90+ formats and writes 30+, including DDS textures (BC1–BC7), AVIF, JPEG XL, WEBP, ICO and TIFF, with per-format options, flexible resizing, power-of-two rounding, animation/page handling, presets and parallel conversion. It is powered by ImageMagick, FFmpeg and DirectXTex, all bundled in the installer. To run from source: Python 3.10+, `pip install PySide6 pillow`, ImageMagick 7 and FFmpeg available, then `python Prisma.pyw`. Released under the MIT license.
