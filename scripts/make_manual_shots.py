# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Screenshot del manuale, in tutte le lingue: docs/manual/<lingua>/NN-nome.png

Avvia DocIndexer su un PROFILO DI PROVA separato (variabile DOCINDEXER_HOME), con una cartella di documenti di
esempio creata qui, con contenuti inventati e generici (relazioni, verbali, un foglio Excel, un avviso
scansionato, un CSV grande, copie identiche e simili): niente dati personali o sensibili, nemmeno finti. Il profilo vero (config.json, data\\, cache\\ del programma) non viene toccato: niente avvio con Windows,
niente scorciatoia globale, niente seconda icona vicino all'orologio.

Per ogni lingua apre le schede e le finestre del programma e salva un'immagine della finestra.
Mentre lavora la finestra resta in primo piano: non usare il PC finché non ha finito (qualche minuto).

    .venv\\Scripts\\python scripts\\make_manual_shots.py                 # tutte le lingue
    .venv\\Scripts\\python scripts\\make_manual_shots.py --lang it,en    # solo alcune
    .venv\\Scripts\\python scripts\\make_manual_shots.py --demo D:\\prova  # cartella di prova (predefinita C:\\DocIndexer-Demo)

La cartella di prova viene ricreata a ogni avvio e cancellata alla fine (--keep per tenerla).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
LANGS = ("it", "en", "fr", "de", "es", "el", "sq", "pl")
WIN_W, WIN_H = 1440, 900


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lang", default=",".join(LANGS), help="lingue separate da virgola (predefinito: tutte)")
    default_demo = Path("C:/DocIndexer-Demo") if os.name == "nt" else Path(tempfile.gettempdir()) / "DocIndexer-Demo"
    ap.add_argument("--demo", default=str(default_demo), help="cartella di prova (viene ricreata)")
    ap.add_argument("--out", default=str(ROOT / "docs" / "manual"), help="cartella del manuale")
    ap.add_argument("--keep", action="store_true", help="non cancellare la cartella di prova alla fine")
    ap.add_argument("--only", default="", help="solo questi screenshot delle Impostazioni, separati da virgola "
                                              "(es. 13-settings-config); gli altri file restano come sono")
    return ap.parse_args()


ARGS = parse_args()
SETTINGS_SHOTS = {"12-settings-folders", "13-settings-config", "14-settings-tools", "15-settings-backup"}
ONLY = {n.strip() for n in ARGS.only.split(",") if n.strip()}
if ONLY - SETTINGS_SHOTS:
    sys.exit(f"--only vale solo per: {', '.join(sorted(SETTINGS_SHOTS))}")
DEMO = Path(ARGS.demo)
HOME = DEMO / "profile"          # config.json, data\, cache\ del profilo di prova
DOCS = DEMO / "Documents"
OFFICE, ARCHIVE = DOCS / "Office", DOCS / "Archive"
MARK = DEMO / ".docindexer-demo"            # solo una cartella creata da questo script viene ricreata


def leftovers_only(folder: Path) -> bool:
    """Resti di un giro precedente (solo il database di prova rimasto bloccato): si possono cancellare."""
    files = [p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()]
    return bool(files) and all(f.startswith("profile/data/docindexer.db") for f in files)


if DEMO.exists():
    if not MARK.exists() and not leftovers_only(DEMO):
        sys.exit(f"La cartella {DEMO} esiste già e non è una cartella di prova di questo script: scegline un'altra "
                 "con --demo.")
    shutil.rmtree(DEMO)
HOME.mkdir(parents=True)
MARK.write_text("cartella di prova di scripts/make_manual_shots.py\n", encoding="utf-8")
os.environ["DOCINDEXER_HOME"] = str(HOME)     # prima di importare docindexer
sys.path.insert(0, str(ROOT))


# =========================================================================== documenti di esempio
# Solo contenuti inventati e generici: niente persone, indirizzi, contatti, codici o dati bancari, nemmeno finti.
# Per ogni lingua: (titolo della relazione, testo, titolo del verbale, testo, parola cercata nella relazione,
#                   parola cercata nel verbale, nota per il documento importante)
SAMPLES = {
    "it": ("Relazione progetto giardino", "Relazione sul progetto del giardino didattico. Nella prima fase sono state "
           "preparate le aiuole, scelte le piante aromatiche e installato l'impianto di irrigazione a goccia. "
           "Il progetto prosegue in primavera con la semina degli ortaggi.",
           "Verbale riunione di marzo", "Verbale della riunione mensile. Argomenti: calendario delle attività, acquisto "
           "degli attrezzi, turni per l'irrigazione. La prossima riunione è fissata per aprile.",
           "progetto", "riunione", "Da rivedere prima della riunione"),
    "en": ("Garden project report", "Report on the teaching garden project. In the first phase the flower beds were "
           "prepared, the herbs were chosen and the drip irrigation was installed. The project continues in spring "
           "with the sowing of vegetables.", "March meeting minutes", "Minutes of the monthly meeting. Topics: activity "
           "calendar, purchase of tools, watering shifts. The next meeting is planned for April.",
           "project", "meeting", "Review before the meeting"),
    "fr": ("Rapport projet jardin", "Rapport sur le projet de jardin pédagogique. Lors de la première phase, les "
           "parterres ont été préparés, les plantes aromatiques choisies et l'arrosage goutte à goutte installé. Le "
           "projet continue au printemps avec les semis de légumes.", "Compte rendu réunion de mars", "Compte rendu "
           "de la réunion mensuelle. Sujets : calendrier des activités, achat des outils, tours d'arrosage. La "
           "prochaine réunion est prévue en avril.", "projet", "réunion", "À revoir avant la réunion"),
    "de": ("Projektbericht Garten", "Bericht über das Projekt Lerngarten. In der ersten Phase wurden die Beete "
           "vorbereitet, die Kräuter ausgewählt und die Tropfbewässerung installiert. Das Projekt geht im Frühling "
           "mit der Aussaat des Gemüses weiter.", "Protokoll Besprechung März", "Protokoll der monatlichen "
           "Besprechung. Themen: Terminplan der Aktivitäten, Kauf der Werkzeuge, Gießdienste. Die nächste "
           "Besprechung ist für April geplant.", "Projekt", "Besprechung", "Vor der Besprechung prüfen"),
    "es": ("Informe proyecto jardín", "Informe sobre el proyecto del jardín didáctico. En la primera fase se "
           "prepararon los parterres, se eligieron las plantas aromáticas y se instaló el riego por goteo. El "
           "proyecto continúa en primavera con la siembra de hortalizas.", "Acta reunión de marzo", "Acta de la "
           "reunión mensual. Temas: calendario de actividades, compra de herramientas, turnos de riego. La próxima "
           "reunión está prevista para abril.", "proyecto", "reunión", "Revisar antes de la reunión"),
    "el": ("Έκθεση έργου κήπου", "Έκθεση για το έργο του εκπαιδευτικού κήπου. Στην πρώτη φάση ετοιμάστηκαν τα "
           "παρτέρια, επιλέχθηκαν τα αρωματικά φυτά και εγκαταστάθηκε το πότισμα με σταγόνες. Το έργο συνεχίζεται "
           "την άνοιξη με τη σπορά των λαχανικών.", "Πρακτικά σύσκεψης Μαρτίου", "Πρακτικά της μηνιαίας σύσκεψης. "
           "Θέματα: πρόγραμμα δραστηριοτήτων, αγορά εργαλείων, βάρδιες ποτίσματος. Η επόμενη σύσκεψη έχει οριστεί "
           "για τον Απρίλιο.", "έργο", "σύσκεψη", "Έλεγχος πριν από τη σύσκεψη"),
    "sq": ("Raport projekti kopshti", "Raport për projektin e kopshtit didaktik. Në fazën e parë u përgatitën lehet, "
           "u zgjodhën bimët aromatike dhe u instalua ujitja me pika. Projekti vazhdon në pranverë me mbjelljen e "
           "perimeve.", "Procesverbal mbledhja e marsit", "Procesverbali i mbledhjes mujore. Tema: kalendari i "
           "aktiviteteve, blerja e veglave, turnet e ujitjes. Mbledhja e ardhshme është caktuar për prill.",
           "projekti", "mbledhja", "Të rishikohet para mbledhjes"),
    "pl": ("Raport z projektu ogrodu", "Raport z projektu ogrodu dydaktycznego. W pierwszym etapie przygotowano "
           "grządki, wybrano zioła i zainstalowano nawadnianie kropelkowe. Projekt będzie kontynuowany wiosną "
           "wysiewem warzyw.", "Protokół zebrania marcowego", "Protokół z comiesięcznego zebrania. Tematy: kalendarz "
           "zajęć, zakup narzędzi, dyżury podlewania. Następne zebranie zaplanowano na kwiecień.",
           "projektu", "zebrania", "Do przejrzenia przed zebraniem"),
}
# testo lungo e comune per i documenti simili: due versioni di una guida (una sezione cambiata)
SECTIONS = [
    "Sezione {n}. Le piante aromatiche vanno annaffiate la mattina presto o la sera, evitando le ore più calde; "
    "il terreno deve restare umido ma non bagnato e le foglie non vanno bagnate.",
    "Sezione {n}. Gli attrezzi si puliscono dopo ogni uso e si ripongono nel capanno; le lame delle forbici si "
    "affilano a inizio stagione e si proteggono con un velo d'olio.",
    "Sezione {n}. Il compost si prepara alternando strati di foglie secche e scarti verdi, rigirandolo ogni due "
    "settimane perché riceva aria e non produca cattivi odori.",
    "Sezione {n}. Le aiuole si coprono con uno strato di paglia per trattenere l'umidità e limitare le erbe "
    "spontanee; la paglia si rinnova quando si assottiglia.",
]


def long_guide(version: int) -> str:
    head = "Guida alla cura del giardino didattico: regole semplici per chi partecipa alle attività."
    body = [SECTIONS[i % len(SECTIONS)].format(n=i + 1) for i in range(12)]
    if version == 2:   # seconda versione: una sezione riscritta
        body[5] = ("Sezione 6. Prima dell'inverno le piante più delicate si spostano in vaso al riparo e le aiuole "
                   "vuote si seminano con piante da sovescio.")
    return head + "\n\n" + "\n\n".join(body)


def write_docx(path: Path, title: str, text: str) -> None:
    import docx

    d = docx.Document()
    d.add_heading(title, level=1)
    for par in text.split("\n\n"):
        d.add_paragraph(par)
    d.save(str(path))


def write_pdf(path: Path, title: str, text: str) -> None:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    fontname = "helv"
    if not all(ord(c) < 0x100 for c in title + text):      # greco, polacco: serve un carattere che li contenga
        for cand in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            if os.path.isfile(cand):
                page.insert_font(fontname="uni", fontfile=cand)
                fontname = "uni"
                break
    page.insert_text((72, 90), title, fontsize=20, fontname=fontname)
    page.insert_textbox(pymupdf.Rect(72, 120, 523, 770), text, fontsize=12, fontname=fontname)
    doc.save(str(path))
    doc.close()


def write_xlsx(path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario"
    ws.append(["Materiale", "Quantità", "Unità"])
    for row in (("Vasi di terracotta", 40, "pz"), ("Terriccio universale", 25, "sacchi"), ("Semi di basilico", 6,
                "bustine"), ("Annaffiatoi", 4, "pz"), ("Paglia", 3, "balle"), ("Guanti da giardino", 12, "paia")):
        ws.append(list(row))
    wb.save(str(path))


def write_scan(path: Path) -> None:
    """Una "scansione": un avviso stampato, letto dall'OCR."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 900), "white")
    d = ImageDraw.Draw(img)
    font = None
    for cand in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.isfile(cand):
            font = ImageFont.truetype(cand, 34)
            break
    lines = ["AVVISO", "", "Il giardino didattico resta chiuso", "per la semina primaverile.",
             "Le attività riprendono la prossima settimana.", "", "Grazie per la collaborazione."]
    y = 80
    for line in lines:
        d.text((90, y), line, fill="black", font=font or ImageFont.load_default())
        y += 70
    img.save(str(path))


def make_documents() -> None:
    OFFICE.mkdir(parents=True)
    ARCHIVE.mkdir(parents=True)
    for code, (rname, rtext, mname, mtext, *_rest) in SAMPLES.items():
        write_docx(OFFICE / f"{rname} ({code}).docx", rname, rtext)
        write_pdf(OFFICE / f"{mname} ({code}).pdf", mname, mtext)
    write_docx(OFFICE / "Guida al giardino.docx", "Guida al giardino", long_guide(1))
    write_docx(ARCHIVE / "Guida al giardino - v2.docx", "Guida al giardino", long_guide(2))
    write_xlsx(OFFICE / "Inventario materiali.xlsx")
    write_scan(ARCHIVE / "Avviso chiusura.png")
    (OFFICE / "Idee per le attività.txt").write_text(
        "Idee per le prossime attività\n- laboratorio di semina\n- percorso delle piante aromatiche\n"
        "- giornata del compost\n", encoding="utf-8")
    # copie identiche (Duplicati > Identici)
    shutil.copy2(OFFICE / "Verbale riunione di marzo (it).pdf", ARCHIVE / "Verbale riunione di marzo (it).pdf")
    shutil.copy2(OFFICE / "Inventario materiali.xlsx", ARCHIVE / "Inventario materiali (copia).xlsx")
    # un file "grande" (oltre il limite del profilo di prova, 1 MB): finisce in Documenti > File grandi
    with open(ARCHIVE / "Catalogo semi.csv", "w", encoding="utf-8") as fh:
        fh.write("codice;varietà;stagione;giorni alla raccolta\n")
        kinds = ("basilico", "lattuga", "pomodoro", "zucchina", "carota", "prezzemolo", "fagiolo", "rucola")
        seasons = ("primavera", "estate", "autunno")
        for i in range(40000):
            fh.write(f"S{i:06d};{kinds[i % len(kinds)]} {i % 50};{seasons[i % 3]};{30 + i % 90}\n")


make_documents()
from docindexer import terms  # noqa: E402  (dopo DOCINDEXER_HOME)

(HOME / "config.json").write_text(json.dumps({
    "watch_dirs": [str(OFFICE), str(ARCHIVE)], "language": "it", "max_file_mb": 1, "autostart": False,
    "resource_level": 4, "cpu_limit": 50, "cpu_limit_idle": 80, "ocr_threads": 3,
    "terms_accepted": terms.TERMS_VERSION,       # i termini d'uso si fotografano a parte, senza bloccare l'avvio
}, indent=2), encoding="utf-8")

# =========================================================================== programma (profilo di prova)
import tkinter as tk  # noqa: E402

from PIL import Image, ImageGrab  # noqa: E402

from docindexer import daemon_ui, gui, manual, quick, saved_ui, shellmenu, welcome  # noqa: E402
from docindexer.i18n import LANGUAGES, tr  # noqa: E402
from docindexer.regexlib import RegexEditor  # noqa: E402
from manual_callouts import BG, CALLOUTS, PAD, draw, overflow, rects, visible  # noqa: E402  (frecce e numeri sugli screenshot)

# solo per questo profilo di prova: nessun effetto su Windows né sul DocIndexer già aperto
daemon_ui.set_autostart = lambda enabled: True
# niente modifiche al registro di Windows: la voce del tasto destro di Esplora file resta com'è
shellmenu.register = shellmenu.unregister = lambda: True
shellmenu.set_enabled = lambda enabled: True
shellmenu.enabled = lambda: False
shellmenu.refresh = lambda: None
daemon_ui.autostart_enabled = lambda: False
daemon_ui.Tray.start = lambda self: None
gui.App.start_hotkey = lambda self: None
gui.App.check_tools = lambda self: None
gui.App.maximize = lambda self: self.geometry(f"{WIN_W}x{WIN_H}+0+0")

OUT = Path(ARGS.out)
DISPLAY = os.environ.get("DISPLAY") if os.name != "nt" else None


def grab(win, path: Path, widgets=None, marks=None) -> None:
    """Immagine della finestra (o del riquadro che contiene i widget indicati), con i riferimenti numerati."""
    win.update_idletasks()
    win.update()
    if widgets:
        xs = [w.winfo_rootx() for w in widgets]
        ys = [w.winfo_rooty() for w in widgets]
        x0, y0 = min(xs) - 8, min(ys) - 8
        x1 = max(w.winfo_rootx() + w.winfo_width() for w in widgets) + 8
        y1 = max(w.winfo_rooty() + w.winfo_height() for w in widgets) + 8
    else:
        x0, y0 = win.winfo_rootx(), win.winfo_rooty()
        x1, y1 = x0 + win.winfo_width(), y0 + win.winfo_height()
    img = ImageGrab.grab(bbox=(x0, y0, x1, y1), all_screens=True) if os.name == "nt" else \
        ImageGrab.grab(bbox=(x0, y0, x1, y1), xdisplay=DISPLAY)
    pad = PAD.get(path.stem, 0)
    if pad:
        framed = Image.new("RGB", (img.width + 2 * pad, img.height + 2 * pad), BG)
        framed.paste(img, (pad, pad))
        img, x0, y0 = framed, x0 - pad, y0 - pad
    if marks:
        boxes = rects(marks, x0, y0, img.size)
        missing = [str(n) for n, b in enumerate(boxes, 1) if b is None]
        if missing:
            print(f"   attenzione: {path.name}: riferimenti non trovati: {', '.join(missing)}", flush=True)
        img = draw(img, boxes)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, optimize=True)
    print("  ", path.relative_to(OUT.parent.parent) if OUT.parent.parent in path.parents else path, flush=True)


def fit(win, widgets) -> str:
    """Allunga la finestra (fino all'altezza dello schermo) finché i widget non sono più tagliati dal loro
    riquadro scorrevole. Restituisce la geometria di prima, da rimettere dopo lo screenshot."""
    old = win.tk.call("wm", "geometry", win._w)
    max_h = win.winfo_screenheight() - 60
    for _ in range(8):
        win.update_idletasks()
        win.update()
        over = max((overflow(w) for w in widgets if w is not None and visible(w)), default=0)
        h = min(win.winfo_height() + over + 24, max_h)
        if over <= 0 or h <= win.winfo_height():
            break
        win.tk.call("wm", "geometry", win._w, f"{win.winfo_width()}x{h}+0+0")
    return old


def front(win) -> None:
    try:
        win.deiconify()
        win.lift()
        win.attributes("-topmost", True)
    except tk.TclError:
        pass


class Shots:
    """Sequenza degli screenshot: un generatore che "dorme" con yield <secondi> senza bloccare la finestra."""

    def __init__(self, app, langs):
        self.app = app
        self.langs = langs
        self.gen = self.run()
        self.failed = []
        app.after(1500, self.step)

    def step(self):
        try:
            delay = next(self.gen)
        except StopIteration:
            self.app.after(200, self.app.quit_app)
            return
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            self.failed.append("?")
            self.app.after(200, self.app.quit_app)
            return
        self.app.after(int(delay * 1000), self.step)

    # ------------------------------------------------------------------ attese
    def wait_indexed(self, timeout=600):
        app = self.app
        t0 = time.time()
        while time.time() - t0 < timeout:
            if app._db_ready and app.indexer is not None:
                s = app.db.stats()
                if s["total"] and s["pending"] + s["processing"] == 0 and app.indexer.status.phase == "idle":
                    return
            yield 1.0
        print("   attenzione: indicizzazione non finita entro il tempo massimo", flush=True)

    def toplevel(self, cls, master=None):
        for w in (master or self.app).winfo_children():
            if isinstance(w, cls) and w.winfo_exists():
                return w
        return None

    # ------------------------------------------------------------------ sequenza
    def run(self):
        app = self.app
        app.maximize()
        front(app)
        yield 2
        print("Indicizzazione dei documenti di esempio...", flush=True)
        yield from self.wait_indexed()
        for code in self.langs:
            print(f"[{code}] {LANGUAGES[code]}", flush=True)
            try:
                yield from self.language(code)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                self.failed.append(code)

    def shot(self, win, name, widgets=None):
        if ONLY and name not in ONLY:
            return
        try:
            win.update_idletasks()
            marks = CALLOUTS[name](self, win) if name in CALLOUTS else None
            grab(win, OUT / self.code / f"{name}.png", widgets, marks)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            self.failed.append(f"{self.code}/{name}")

    def language(self, code):
        app = self.app
        self.code = code
        if gui.language() != code:
            app._set_language(LANGUAGES[code])
        app.maximize()
        front(app)
        yield 1.5
        cname, _ct, iname, _it, word_c, word_i, note = SAMPLES[code]   # relazione, verbale
        self._annotate(code, note)
        if ONLY:                          # --only: solo le schede delle Impostazioni richieste
            yield from self.settings(app)
            return

        # --- prima apertura: scelta della lingua e termini d'uso (finte: nessuna risposta, nessun salvataggio)
        for name, need_language in (("18-welcome-language", True), ("19-terms", False)):
            win = welcome.WelcomeWindow(app, SimpleNamespace(language=code), need_language=need_language)
            yield 1.5
            front(win)
            yield 0.5
            self.shot(win, name)
            win._close()
            yield 0.5

        # --- configurazione guidata del primo avvio
        wiz = daemon_ui.SetupWizard(app, app.cfg, app.fonts, lambda ok: None)
        front(wiz)
        yield 1
        try:
            wiz.state("normal")         # la configurazione guidata si apre ingrandita: qui a dimensione fissa
        except tk.TclError:
            pass
        wiz.geometry("1360x860+20+20")
        yield 1.5
        self.shot(wiz, "01-setup")
        wiz.destroy()
        yield 0.5

        # --- Monitor
        app.show("monitor")
        front(app)
        yield 3
        self.shot(app, "02-monitor")
        mon = app.pages["monitor"]
        self.shot(app, "03-resources", [mon.res_control, mon.resources])

        # --- Ricerca
        app.show("search")
        page = app.pages["search"]
        page.query.delete("1.0", "end")
        page.query.insert("1.0", f"{word_c}\n{word_i}")
        page.color_query()
        page.search()
        yield 1
        pdf = next((iid for iid, p in zip(page.tree._items, page.tree._paths) if p.lower().endswith(f"({code}).pdf")),
                   None)
        if pdf:
            page.tree.selection_set(pdf)
        yield 4
        self.shot(app, "04-search")

        # --- nessun risultato esatto: avviso rosso e risultati con 1 errore di battitura
        typo = word_c[:len(word_c) // 2] + word_c[len(word_c) // 2 + 1:]      # una lettera in meno
        page.query.delete("1.0", "end")
        page.query.insert("1.0", typo)
        page.color_query()
        page.search()
        yield 3                          # il lampeggio finisce sul rosso pieno
        self.shot(app, "20-near-miss")

        # --- editor regex
        page.open_regex_editor()
        yield 1.5
        ed = self.toplevel(RegexEditor, page)
        if ed is not None:
            ed.geometry("1100x760+60+40")
            front(ed)
            yield 1.5
            self.shot(ed, "05-regex-editor")
            ed.destroy()
        yield 0.5

        # --- ricerche salvate
        app.saved.items = []
        spec = page.spec()
        app.saved.add(cname, {**spec, "query": word_c}, True)
        app.saved.add(iname, {**spec, "query": word_i}, False)
        win = saved_ui.SavedSearchesWindow.open(app)
        front(win)
        yield 1.5
        self.shot(win, "06-saved-searches")
        win.destroy()
        saved_ui.SavedSearchesWindow._instance = None

        # --- Importanti
        app.show("important")
        front(app)
        yield 1
        imp = app.pages["important"]
        kids = imp.tree.get_children()
        if kids:
            imp.tree.selection_set(kids[0])
            imp.tree.focus(kids[0])
        yield 4
        self.shot(app, "07-important")

        # --- Documenti e File grandi
        app.show("documents")
        yield 1
        docs = app.pages["documents"]
        target = next((iid for iid, r in docs.rows.items() if r.get("name", "").endswith(f"({code}).pdf")), None)
        if target:
            docs.tree.selection_set(target)
            docs.tree.see(target)
        yield 4
        self.shot(app, "08-documents")
        docs.toggle_big()
        yield 1.5
        self.shot(app, "09-big-files")
        docs.toggle_big()

        # --- Duplicati: identici e simili
        app.show("duplicates")
        dup = app.pages["duplicates"]
        dup.mode.set(tr("Identici"))
        dup.find()
        yield 3
        self.shot(app, "10-duplicates")
        dup.mode.set(tr("Simili"))
        dup.find()
        yield 4
        self.shot(app, "11-similar")

        # --- Impostazioni
        yield from self.settings(app)

        # --- ricerca rapida
        yield from self.rest(app, code, word_i)

    def settings(self, app):
        app.show("settings")
        st = app.pages["settings"]
        for name, tab in (("12-settings-folders", "Cartelle ed estensioni"), ("13-settings-config", "Configurazione"),
                          ("14-settings-tools", "Strumenti esterni"), ("15-settings-backup", "Backup")):
            if ONLY and name not in ONLY:
                continue
            st.tabs.set(tr(tab))
            yield 2.5 if tab == "Strumenti esterni" else 1
            old = None
            if tab == "Configurazione":       # le ultime righe del modulo devono vedersi intere
                try:
                    rows = [w for t in CALLOUTS[name](self, app) for w in (t if isinstance(t, list) else [t])]
                    old = fit(app, rows)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
                yield 1
            self.shot(app, name)
            if old:
                app.tk.call("wm", "geometry", app._w, old)
                yield 0.5
        app.show("monitor")

    def rest(self, app, code, word_i):
        qs = quick.QuickSearch.toggle(app)
        yield 1
        qs = quick.QuickSearch._instance
        if qs is not None:
            front(qs)
            qs.var.set(word_i)
            qs.search()
            yield 2
            self.shot(qs, "16-quick-search")
            qs.destroy()
            quick.QuickSearch._instance = None

        # --- manuale (se il testo in questa lingua c'è già)
        path = manual.manual_path(code)
        if path and os.path.basename(os.path.dirname(path)) == code:
            app.open_manual()
            yield 2.5
            win = app.manual_win
            if win is not None:
                front(win)
                yield 1
                self.shot(win, "17-manual")
                win.close()
        yield 0.5

    def _annotate(self, code, note):
        """Colori di importanza e note (nella lingua degli screenshot) su alcuni documenti di esempio."""
        db = self.app.db
        rows = db.conn.execute("SELECT id, name FROM paths").fetchall()
        for r in rows:
            db.set_annotation(r["id"], 0, "")
        marks = {f"({code}).pdf": (5, note), f"({code}).docx": (3, ""), "Inventario materiali.xlsx": (2, ""),
                 "Avviso chiusura.png": (1, "")}
        for r in rows:
            for suffix, (level, text) in marks.items():
                if r["name"].endswith(suffix):
                    db.set_annotation(r["id"], level, text)


def remove_demo(app) -> None:
    """Cancella la cartella di prova; il file marcatore per ultimo, così un giro successivo la riconosce."""
    try:
        app.db.conn.close()             # altrimenti su Windows il database resta bloccato
    except Exception:  # noqa: BLE001
        pass
    for _ in range(10):
        time.sleep(1)
        for child in DEMO.iterdir() if DEMO.exists() else []:
            if child != MARK:
                shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink(missing_ok=True)
        if DEMO.exists() and [c for c in DEMO.iterdir() if c != MARK]:
            continue
        shutil.rmtree(DEMO, ignore_errors=True)
        break
    if DEMO.exists():
        print(f"   attenzione: la cartella di prova {DEMO} non si è cancellata del tutto", flush=True)


def main():
    langs = [c.strip() for c in ARGS.lang.split(",") if c.strip() in LANGS]
    print(f"Profilo di prova: {DEMO}", flush=True)
    app = gui.App()
    runner = Shots(app, langs)
    app.mainloop()
    if not ARGS.keep:
        remove_demo(app)
    if runner.failed:
        print("Non riusciti:", ", ".join(runner.failed))
        sys.exit(1)
    print("Fatto.")


if __name__ == "__main__":
    main()
