# DocIndexer

**English** · [Italiano](README.it.md) · [Polski](README.pl.md)

Background document indexer for Windows. It starts with Windows, stays in the notification area and keeps
an index of the text of the files in the folders you choose: documents, spreadsheets, presentations, PDFs,
photos and scans (**OCR with RapidOCR**), e-mails, web pages, SQLite databases, graphs and more. Files
**stay where they are**: the database stores only their path and their text. Search is full-text (SQLite
FTS5), fuzzy, by file name or with **regular expressions**, with a preview that highlights the matches.

OCR runs on RapidOCR, the interface uses the PCSnex theme and is available in eight languages.

## How it works

1. **First start**: a setup wizard asks for the **working folders** to monitor, the tables of
   **included and excluded extensions** (with group buttons: Office, PDF, Images, E-mail, Databases,
   Web and data, Graphs, eBooks, Text and code, Archives, Audio and video, Programs; one click selects the
   whole group, another click deselects it) and the **folders to skip** by name (`$Recycle.Bin`, `.git`,
   `node_modules`...). It can also enable **start with Windows**.
2. **Count, then index**: DocIndexer first counts the files to analyse (included minus excluded
   extensions), then computes their SHA-256 and extracts the text. The **hash** identifies the content: a
   copy of a file already known is not analysed again.
3. **Changes in real time**: a folder watcher follows new, modified, **moved/renamed** (the path is
   updated, nothing is analysed again) and **deleted** files (removed from the index). A full check of
   the folders runs at start and every few hours, so changes made while the program was closed are found too.
4. **Discreet**: the process runs at low CPU and disk priority, with a CPU limit (25% by default) while
   you use the PC, a higher limit (60%) when the PC has been idle for a few minutes, a pause when other
   programs are already using a lot of CPU, a minimum pace on battery, and just 2 OCR threads, so it does
   not heat the processor.
5. **Monitor**: files to analyse, indexed, to do, skipped and errors; progress bar, pie chart, current
   file, log, pause/resume, "check folders now".

Closing the window hides it: DocIndexer keeps working, and the icon next to the clock offers Open,
Pause/Resume, Check folders now and Exit. Starting it a second time just shows the window already running.

| Type | Tool |
|---|---|
| PDF with text / scanned | PyMuPDF / page rendering + RapidOCR |
| Images (jpg, png, tiff, bmp, gif, webp, **heic/heif**, jp2...) | RapidOCR |
| Word .docx / .doc / .rtf | python-docx / Microsoft Word via COM or raw extraction |
| Excel .xlsx / .xls, OpenDocument .odt / .ods / .odp | openpyxl / xlrd / built-in parser |
| PowerPoint .pptx / .ppt | direct reading / PowerPoint via COM |
| **SQLite** databases (.sqlite, .db...) | one page per table: column names and text values (opened read-only) |
| **Graphs** (GraphML, GEXF, GML, DOT) | labels, attributes and edges |
| HTML, XML, JSON, text | visible text, values and attributes, key: value lines |
| **E-mail** .eml / .msg | headers, body, attachment names (.msg with extract-msg) |
| EPUB | one page per chapter |

## Importance and notes

In the preview, under the file name, every document can get an **importance colour** (light blue, green,
yellow, orange, red) and a **note**. They stay attached to the file even when it is moved, renamed or
edited. The **Important** tab lists the coloured documents (most important first, with the note), the
lists show the colour as a tinted row, and the search has an **only important documents** option.

All file lists show the **creation** and modification dates and can be sorted by clicking a column header
(A-Z, click again for Z-A). Besides folder names to skip everywhere, you can exclude **specific
subfolders** by path (e.g. `Documents\garbage`). The **interface size** is a setting (100% by default) and
does not follow the Windows zoom.

## Add-on modules

Each module can be switched on or off in **Settings > Configuration** and stores its data in a **dedicated
table** with its own search index; in **Search** you choose which data to search (document text, metadata,
files inside archives, database contents):

- **ExifTool** (downloaded from *External tools*): metadata of photos, documents, audio and video (author,
  dates, camera, GPS, software...). Files without readable text (audio, video, RAW photos) get their metadata
  indexed too.
- **7-Zip** (downloaded from *External tools*): the text of the files inside zip, rar, 7z, tar, gz archives,
  extracted to a temporary folder that is deleted right away.
- **Databases**: SQLite (built-in), dBASE/FoxPro `.dbf` (dbfread), Access `.mdb/.accdb` (Microsoft ODBC
  driver, installed with Office).

Search also has **filters** for a date range (modified or created) and a file size range.

## Search

Simple (all the words, also as prefixes, accents ignored), advanced (FTS5 syntax: `AND`, `OR`, `NOT`,
`"exact phrase"`, `stem*`, `NEAR(a b, 5)`), exact phrase, phrase in any order, fuzzy (1-4 typos), file name,
and **Regex**: a regular expression on the text. The **regex editor** offers ready-made patterns (e-mail,
Italian and international phone numbers, IBAN, Italian tax code, VAT number, licence plate, IP, URL, dates,
times, credit card, amounts, Bitcoin, IMEI, passport, GPS coordinates, hashtag, @user) and building blocks
(digit, letter, repetitions, "or", groups...), explains the regex in words and highlights the matches on a
test text as you type. On the left you choose which monitored folders to search, the date and size
filters and the **document language** (detected automatically for every document).

When a search finds nothing, DocIndexer retries by itself tolerating one typing or OCR error; the fuzzy
search also accepts the usual OCR mix-ups (0/o, 1/l, rn/m, cl/d...), so `c0ntratto` finds `contratto`.

- **Quick search**: a search bar on top of any program, opened with a global shortcut (default
  `Ctrl+Alt+D`, change it in Settings > Configuration) or from the tray icon menu. It searches as you type;
  Enter opens the file, Ctrl+Enter opens the full search in DocIndexer, Alt+Enter shows it in its folder.
- **Saved searches**: save a search with a name; with notifications on, DocIndexer repeats it when new files
  are indexed and shows a Windows notification next to the clock for the new matches ("New only" lists them).
- **Export**: search results, the Documents and Important lists and the duplicates can be exported to
  Excel (.xlsx, rows coloured by importance), CSV (`;`, opens in Excel) or PDF, with importance and notes.

## Duplicates

The **Duplicates** tab lists identical files (same content in several folders, with the space taken by the
extra copies) and **similar documents** (almost the same text: corrected versions, the same text as PDF and
Word, a scan made again), with a minimum similarity of 97, 93, 90 or 87%. Similarity uses a 64-bit SimHash
of the text computed during indexing.

## Small database, fast search

- the same content found in several places is extracted and stored **once** (SHA-256);
- the text is stored **compressed with zstd** and decompressed only for the results shown;
- the FTS5 index is **contentless**: it holds only the index, not a second copy of the text;
- **incremental auto-vacuum** and index merging run when the PC is idle.

The index itself is not compressed, so searches stay fast.

## OCR (RapidOCR)

OCR runs inside the program (RapidOCR + ONNX Runtime). The default model (PP-OCRv6, ~30 MB) recognises
Italian, English, Turkish and every Latin-script language plus Chinese/Japanese; it ships with the program
and is copied to `tools\rapidocr` at the first start. Other scripts (Cyrillic, Greek, Arabic, Korean,
Thai, Devanagari, Tamil, Telugu) are downloaded from **Settings > External tools**.

With the **Automatic** model (default for new installations) the first scanned page of every document is
read with the Latin model; if the result is uncertain, the other downloaded models are tried and the one that
reads best is used for the whole document (for example a Russian scan uses the Cyrillic model).

## Start with Windows, backup

- **Start with Windows**: switch in the Monitor tab, tick in the tray icon menu, or Settings > Configuration.
  It takes effect immediately (HKCU Run key, no administrator rights).
- **Backup**: Settings > Backup creates a .zip with the database (index, notes, importance colours), the
  settings, the regex patterns and the saved searches, also while indexing runs. Restoring replaces them and
  restarts DocIndexer; the previous database is kept as `.before-restore`.

## Running from source

```bat
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

or double-click `avvia.bat`. `main.py --background` starts with the window hidden (only the icon): it is
the command written in the Windows "Run" key when start with Windows is enabled (current user only, no
administrator rights). The environment variable `DOCINDEXER_HOME` moves `config.json`, `data\` and `cache\`
to another folder (useful for tests or separate profiles).

## Building

`build.bat` builds a single executable `dist\DocIndexer.exe` with PyInstaller and copies `LICENSE`,
`NOTICE`, `THIRD_PARTY_NOTICES.md` and `LICENSES\` next to it. Next to the executable the program creates
`config.json`, `data\` (SQLite database), `cache\` (Office previews, can be deleted) and `tools\` (OCR
models).

## Configuration

`config.json` (also editable from **Settings**): monitored folders, included/excluded extensions, skipped
folders, maximum file size, CPU limits (in use / idle), idle time, busy threshold, OCR threads, full check
interval, OCR model and DPI, database path, start with Windows, language.

## Interface languages

Italiano, English, Français, Deutsch, Español, Ελληνικά, Shqip, Polski, from the **Language** menu at the top right.

## Manual

The user manual, with screenshots, is in `docs/manual/<language>/MANUAL.md` in seven languages, plus a Polish quick-start guide (index in
[MANUAL.md](MANUAL.md)). Inside the program it opens from **📖 Manual**, to the right of the tabs, or from the menu of
the icon next to the clock, in the chosen language. The screenshots were taken on a separate test profile,
with invented documents.

## License

© 2026 Andrea Cumini · andrea@osintinfo.net · www.osintinfo.net

DocIndexer is free software under the **GNU AGPL-3.0** (`LICENSE`), with the section 7 additional terms
described in `NOTICE`: anyone who distributes the program or a work based on it must **keep the author
attribution** in the source code, the documentation and the user interface, must mark modified versions as
such, and may not use the DocIndexer name and logo for a modified version. No warranty.

Third-party components and their licenses are listed in `THIRD_PARTY_NOTICES.md`.

On first launch the program asks for the language and then shows the terms of use and disclaimer of
liability, which must be accepted to use it; the text, in all eight languages, is in [TERMS.md](TERMS.md) and
can be read again from **Terms of use**, next to **📖 Manual**.
