# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Gestione configurazione (config.json accanto al programma).

Funziona sia da sorgente sia compilato con PyInstaller:
  BASE_DIR  cartella del programma (accanto all'exe): config.json, data\\, cache\\, tools\\
  RES_DIR   risorse incluse nella build (assets\\, docs\\manual\\): sys._MEIPASS quando compilato
I percorsi relativi in config.json sono risolti rispetto a BASE_DIR, così la cartella
del programma si può spostare o copiare su un altro PC e continua a funzionare.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent
RES_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
# cartella dei dati (config.json, data\, cache\): accanto al programma, oppure quella indicata
# dalla variabile d'ambiente DOCINDEXER_HOME (utile per prove o per più profili)
DATA_DIR = Path(os.environ["DOCINDEXER_HOME"]) if os.environ.get("DOCINDEXER_HOME") else BASE_DIR
CONFIG_PATH = DATA_DIR / "config.json"
ASSETS_DIR = RES_DIR / "assets"
MANUAL_DIR = RES_DIR / "docs" / "manual"   # manuale: docs/manual/<lingua>/MANUAL.md + immagini (incluso nella build)
TOOLS_DIR = BASE_DIR / "tools"
RAPIDOCR_DIR = TOOLS_DIR / "rapidocr"   # modelli OCR (.onnx)
CACHE_DIR = DATA_DIR / "cache"          # anteprime PDF dei documenti Office, file temporanei

# file che contengono testo da cercare: documenti, immagini (OCR), dati, grafi, posta
DEFAULT_INCLUDE = [
    # documenti
    ".pdf", ".doc", ".docx", ".docm", ".dot", ".dotx", ".rtf", ".odt", ".txt", ".md", ".epub",
    # fogli di calcolo e presentazioni
    ".xls", ".xlsx", ".xlsm", ".ods", ".csv", ".tsv", ".ppt", ".pptx", ".pptm", ".pps", ".ppsx", ".odp",
    # immagini (OCR)
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp",
    # pagine web e dati strutturati
    ".html", ".htm", ".xml", ".json", ".yaml", ".yml",
    # posta
    ".eml", ".msg",
    # database
    ".sqlite", ".sqlite3", ".db", ".db3", ".dbf", ".mdb", ".accdb",
    # archivi (testo dei file contenuti, con 7-Zip)
    ".zip", ".rar", ".7z", ".gz", ".tar", ".tgz", ".bz2", ".xz",
    # grafi
    ".graphml", ".gexf", ".gml", ".dot", ".gv",
    # testo vario
    ".log", ".ini", ".cfg", ".conf", ".vcf", ".ics", ".srt",
]
# gruppi di estensioni per i pulsanti delle tabelle incluse/escluse: (nome, estensioni).
# Alcune estensioni dei gruppi non hanno un lettore (es. .pages, .wpd): finiscono tra i "saltati".
EXT_GROUPS: list[tuple[str, list[str]]] = [
    ("Office", [
        # Microsoft Word, Excel, PowerPoint, Access, Publisher, Visio, OneNote, Works
        ".doc", ".docx", ".docm", ".dot", ".dotx", ".dotm", ".rtf", ".wps", ".wri",
        ".xls", ".xlsx", ".xlsm", ".xlsb", ".xlt", ".xltx", ".xltm", ".csv",
        ".ppt", ".pptx", ".pptm", ".pps", ".ppsx", ".ppsm", ".pot", ".potx", ".potm",
        ".mdb", ".accdb", ".pub", ".vsd", ".vsdx", ".one", ".xps",
        # OpenOffice / LibreOffice (ODF e vecchi StarOffice)
        ".odt", ".ott", ".ods", ".ots", ".odp", ".otp", ".odg", ".odf", ".fodt", ".fods", ".fodp",
        ".sxw", ".sxc", ".sxi",
        # altri programmi di videoscrittura e fogli di calcolo
        ".wpd", ".wp", ".abw", ".hwp", ".pages", ".numbers", ".key", ".tex", ".md", ".txt",
    ]),
    ("PDF", [".pdf"]),
    ("Immagini", [
        ".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".gif", ".bmp", ".dib", ".tif", ".tiff", ".webp",
        ".heic", ".heif", ".avif", ".jp2", ".j2k", ".jpx", ".ico", ".tga", ".pcx", ".ppm", ".pgm", ".pbm",
        ".psd", ".svg", ".emf", ".wmf", ".raw", ".cr2", ".nef", ".arw", ".dng",
    ]),
    ("Posta", [".eml", ".msg", ".emlx", ".mbox", ".vcf", ".ics"]),
    ("Database", [".sqlite", ".sqlite3", ".db", ".db3", ".s3db", ".sl3", ".mdb", ".accdb", ".dbf"]),
    ("Web e dati", [".html", ".htm", ".xhtml", ".mht", ".mhtml", ".xml", ".json", ".jsonl", ".yaml", ".yml",
                    ".csv", ".tsv", ".kml", ".gpx"]),
    ("Grafi", [".graphml", ".gexf", ".gml", ".dot", ".gv", ".net", ".pajek"]),
    ("eBook", [".epub", ".mobi", ".azw", ".azw3", ".fb2"]),
    ("Testo e codice", [".txt", ".md", ".log", ".ini", ".cfg", ".conf", ".srt", ".vtt", ".py", ".js", ".ts",
                        ".java", ".c", ".cpp", ".h", ".cs", ".php", ".sql", ".sh", ".ps1", ".bat", ".css"]),
    ("Archivi", [".zip", ".rar", ".7z", ".gz", ".tar", ".bz2", ".xz", ".cab", ".iso"]),
    ("Audio e video", [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".mp4", ".mkv", ".avi", ".mov",
                       ".wmv", ".webm", ".m4v", ".3gp"]),
    ("Programmi", [".exe", ".dll", ".sys", ".msi", ".com", ".scr", ".lnk", ".jar", ".class", ".pyc", ".pyd",
                   ".so", ".obj", ".lib", ".pdb", ".tmp", ".bak", ".part", ".crdownload"]),
]

# mai analizzate anche se aggiunte alle incluse (programmi, archivi, media senza testo)
DEFAULT_EXCLUDE = [
    ".exe", ".dll", ".sys", ".msi", ".bat", ".cmd", ".ps1", ".lnk", ".tmp", ".bak", ".part", ".crdownload",
    ".iso", ".cab",
    ".mp3", ".wav", ".flac", ".mp4", ".mkv", ".avi", ".mov", ".wmv",
    ".pyc", ".pyd", ".so", ".class", ".jar", ".obj", ".lib", ".pdb",
]
# cartelle saltate ovunque si trovino (nome della cartella, senza distinzione maiuscole/minuscole)
DEFAULT_EXCLUDE_DIRS = [
    "$Recycle.Bin", "System Volume Information", "Windows", "Program Files", "Program Files (x86)",
    "ProgramData", "AppData", "node_modules", ".git", ".svn", ".hg", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "Temp", "tmp", "cache", ".cache",
]


# slider "Risorse per l'indicizzazione" del Monitor: livello -> (nome, cpu_limit, cpu_limit_idle, ocr_threads).
# Ai livelli 1 e 2 i thread che indicizzano chiedono a Windows il risparmio energetico (EcoQoS: core
# efficienti e frequenza bassa, niente turbo); la priorità dei thread scende con il livello (1 = minima).
# Solo quei thread: finestra e ricerca non rallentano.
RESOURCE_LEVELS = {
    1: ("Minimo", 5, 5, 1),
    2: ("Basso", 10, 25, 1),
    3: ("Medio", 25, 60, 2),
    4: ("Alto", 50, 80, 3),
    5: ("Massimo", 90, 100, 4),
}
ECO_MAX_LEVEL = 2


def portable(p: str | Path) -> str:
    """Percorso da salvare in config: relativo alla cartella del programma se sta lì dentro."""
    path = Path(p)
    try:
        return path.resolve().relative_to(DATA_DIR).as_posix()
    except ValueError:
        return str(path)


def resolve(p: str) -> Path:
    path = Path(os.path.expandvars(p))
    return path if path.is_absolute() else DATA_DIR / path


def norm_ext(e: str) -> str:
    e = e.strip().lower()
    return e if not e or e.startswith(".") else "." + e


@dataclass
class AppConfig:
    db_path: str = "data/docindexer.db"
    # cartelle di lavoro monitorate (vuoto = primo avvio: si apre la configurazione guidata)
    watch_dirs: list = field(default_factory=list)
    include_ext: list = field(default_factory=lambda: list(DEFAULT_INCLUDE))
    exclude_ext: list = field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    exclude_dirs: list = field(default_factory=lambda: list(DEFAULT_EXCLUDE_DIRS))
    # sottocartelle escluse per percorso completo (es. C:\\Users\\me\\Documents\\garbage)
    exclude_paths: list = field(default_factory=list)
    # file più grandi di così non si analizzano (MB)
    max_file_mb: int = 200
    # modello OCR (alfabeto) di RapidOCR, vedi ocr.MODELS: "multi" = latino + cinese/giapponese,
    # "auto" = sceglie per ogni documento tra i modelli scaricati
    ocr_model: str = "auto"
    ocr_dpi: int = 300
    # sotto questa soglia di caratteri una pagina PDF è considerata scansionata
    ocr_min_chars_per_page: int = 25
    # ---- lavoro in background
    # tetto di CPU (percentuale di tutto il processore) mentre l'utente usa il PC
    cpu_limit: int = 25
    # con il PC inattivo da idle_minutes minuti il tetto sale a cpu_limit_idle
    idle_minutes: int = 3
    cpu_limit_idle: int = 60
    # se gli altri programmi usano già più di questa percentuale di CPU, l'indicizzazione aspetta
    busy_threshold: int = 70
    # thread OCR (onnxruntime); 1-2 bastano per non scaldare il processore
    ocr_threads: int = 2
    # livello dello slider "Risorse per l'indicizzazione" del Monitor (1 = minimo ... 5 = massimo),
    # vedi RESOURCE_LEVELS: imposta i tre valori qui sopra, la priorità e il risparmio energetico
    resource_level: int = 3
    # soglie di temperatura (°C) scelte nel Monitor: raggiunte, l'indicizzazione rallenta da sola
    temp_cpu_max: int = 82
    temp_gpu_max: int = 80
    # controllo completo delle cartelle ogni N ore (oltre al monitoraggio in tempo reale)
    rescan_hours: int = 6
    paused: bool = False
    # avvio con Windows e finestra nascosta all'avvio automatico
    autostart: bool = True
    # metadati con ExifTool (se scaricato in tools\\exiftool): autore, date, fotocamera, GPS, software...
    exif_enabled: bool = True
    # moduli di lettura attivabili: archivi (7-Zip), database SQLite, DBF, Access
    mod_archives: bool = True
    mod_sqlite: bool = True
    mod_dbf: bool = True
    mod_access: bool = True
    # scorciatoia globale della ricerca rapida (vuota = disattivata), es. ctrl+alt+d (D di DocIndexer)
    quick_hotkey: str = "ctrl+alt+d"
    # dimensione dell'interfaccia in %, indipendente dallo zoom di Windows (100 = come a zoom 100%)
    ui_scale: int = 100
    # lingua dell'interfaccia: it en fr de es el sq pl
    language: str = "it"
    # termini d'uso accettati alla prima apertura (terms.TERMS_VERSION; vuoto = mai) e quando
    terms_accepted: str = ""
    terms_accepted_at: str = ""

    # ------------------------------------------------------------ percorsi
    @property
    def db_file(self) -> Path:
        return resolve(self.db_path)

    def included(self) -> set[str]:
        return {norm_ext(e) for e in self.include_ext} - {norm_ext(e) for e in self.exclude_ext} - {""}

    def excluded_paths(self) -> set[str]:
        """Sottocartelle escluse, normalizzate (minuscolo, separatori di Windows, senza barra finale)."""
        return {os.path.normcase(os.path.normpath(p)) for p in self.exclude_paths if p.strip()}

    def excluded_dir_names(self) -> set[str]:
        return {d.strip().lower() for d in self.exclude_dirs if d.strip()}

    # ----------------------------------------------------------- persistenza
    def save(self) -> None:
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        return cls(**known)
