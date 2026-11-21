"""Riferimenti numerati sugli screenshot del manuale (usato da scripts/make_manual_shots.py).

Per ogni screenshot, l'elenco ordinato dei punti da indicare: il numero N disegnato sull'immagine
corrisponde alla voce N della legenda che segue l'immagine in docs/manual/<lingua>/MANUAL.md.
Se si cambia l'ordine o si aggiunge un punto qui, va aggiornata la legenda in tutte le lingue.

I punti si trovano dal testo tradotto dei widget (tr) o dagli attributi delle pagine, quindi
funzionano in tutte le lingue. Un punto che non si trova viene saltato con un avviso.
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageStat

from docindexer import daemon_ui, terms
from docindexer.i18n import language, tr

# finestre piccole e piene fino al bordo: un margine attorno all'immagine lascia posto ai numeri
PAD = {"19-terms": 60}
BG = (13, 15, 20)
COLOR = (255, 138, 31)        # arancione: si vede bene sul tema scuro
OUTLINE = (20, 20, 24)
RADIUS = 15


# --------------------------------------------------------------------------- ricerca dei widget
def walk(root):
    yield root
    for child in root.winfo_children():
        yield from walk(child)


def visible(w) -> bool:
    try:
        return bool(w.winfo_ismapped() and w.winfo_viewable())
    except tk.TclError:
        return False


def T(root, key, nth=0, mode="eq", up=0, cls=ctk.CTkBaseClass, raw=False):
    """Widget CTk visibile (della classe cls) il cui testo è tr(key) (mode: eq, prefix, contains).
    raw=True: key è già il testo da cercare (per i testi che non passano da tr, come i termini d'uso)."""
    want = (key if raw else tr(key)).strip().casefold()
    n = 0
    for w in walk(root):
        if not isinstance(w, cls) or not visible(w):
            continue
        try:
            text = str(w.cget("text")).strip().casefold()
        except (ValueError, tk.TclError, AttributeError):
            continue
        ok = text == want if mode == "eq" else text.startswith(want) if mode == "prefix" else want in text
        if ok:
            if n == nth:
                for _ in range(up):
                    w = w.master
                return w
            n += 1
    return None


def C(root, cls, nth=0):
    """N-esimo widget visibile della classe indicata."""
    found = [w for w in walk(root) if isinstance(w, cls) and visible(w)]
    return found[nth] if len(found) > nth else None


def after(w):
    """Il widget impacchettato subito dopo w (per esempio il campo accanto a un'etichetta)."""
    if w is None:
        return None
    slaves = w.master.pack_slaves()
    i = slaves.index(w) if w in slaves else -1
    return slaves[i + 1] if 0 <= i < len(slaves) - 1 else None


def gridrow(w):
    """Tutti i widget della stessa riga di griglia di w (etichetta + campo)."""
    if w is None:
        return None
    try:
        row = w.grid_info()["row"]
    except (KeyError, tk.TclError):
        return [w]
    return [s for s in w.master.grid_slaves() if s.grid_info().get("row") == row]


def outer(w):
    """Per i CTkScrollableFrame il riquadro visibile è il contenitore esterno."""
    return getattr(w, "_parent_frame", w)


# --------------------------------------------------------------------------- punti per screenshot
def _seg(root, nth=0):
    return C(root, ctk.CTkSegmentedButton, nth)


def setup(s, win):
    return [C(win, daemon_ui.FolderList, 0), C(win, daemon_ui.FolderList, 1), C(win, daemon_ui.ExtTable, 0),
            C(win, daemon_ui.ExtTable, 1), C(win, daemon_ui.ListEditor, 0),
            T(win, "Avvia DocIndexer con Windows (in background, icona vicino all'orologio)"),
            T(win, "Inizia l'indicizzazione")]


def monitor(s, app):
    mon = app.pages["monitor"]
    return [app.tabbar, T(app, "Manuale", mode="contains"), T(app, terms.labels(language())[0], raw=True), app.pulse, app.lang_menu, mon.pie, mon.btn_pause,
            T(mon, "Controlla subito le cartelle"), mon.res_control, mon.log]


def resources(s, app):
    rc, card = app.pages["monitor"].res_control, app.pages["monitor"].resources
    return [rc.slider, rc.btn_min, rc.info, rc.temp["temp_cpu_max"][2], rc.temp["temp_gpu_max"][2],
            card.cpu_graph, card.ram_graph]


def search(s, app):
    p = app.pages["search"]
    return [outer(p.cf_list), p.query, T(p, "Cerca", cls=ctk.CTkButton),   # in greco il titolo della pagina è uguale al pulsante
            [T(p, "Avanzata"), T(p, "Fuzzy (errori):", up=1)],
            [T(p, "Testo dei documenti"), T(p, "Contenuto dei database")],
            [T(p, "Filtri"), T(p, "Azzera filtri")],
            [T(p, "Salva ricerca..."), T(p, "Esporta risultati...")],
            p.tree, p.preview]


def regex_editor(s, ed):
    blocks = T(ed, "Blocchi")
    return [[outer(ed.lst), T(ed, "Nuovo pattern", mode="contains")], after(blocks), ed.entry, ed.sample,
            ed.count_lbl, T(ed, "Usa nella ricerca")]


def saved(s, win):
    # il primo ✕ è la chiusura della finestra: quello della ricerca è il secondo
    return [T(win, "Avviso"), T(win, "Apri", cls=ctk.CTkButton), T(win, "✕", nth=1), T(win, "Controlla adesso")]


def important(s, app):
    p = app.pages["important"]
    name = T(p, "Cerca nel nome:")
    folder = T(p, "Cartella:")
    return [[name, after(name)], [folder, after(folder)], p.tree, p.preview.notes,
            [T(p, "Mostra in Esplora risorse"), T(p, "Rianalizza")], T(p, "Esporta...")]


def documents(s, app):
    p = app.pages["documents"]
    return [p.btn_big, _seg(p), p.tree, T(p, "Rianalizza"), T(p, "Esporta..."), p.preview]


def big_files(s, app):
    p = app.pages["documents"]
    return [T(p, "Analizza"), T(p, "Blocca"), T(p, "Bloccati", mode="prefix"), p.btn_big]


def duplicates(s, app):
    p = app.pages["duplicates"]
    return [_seg(p, 0), _seg(p, 1), T(p, "Cerca duplicati"), p.tree,
            [T(p, "Apri"), T(p, "Mostra nella cartella"), T(p, "Esporta...")]]


def similar(s, app):
    p = app.pages["duplicates"]
    return [_seg(p, 0), _seg(p, 1), p.tree]


def settings_folders(s, app):
    st = app.pages["settings"]
    return [st.tabs._segmented_button, C(st, daemon_ui.FolderList, 0), C(st, daemon_ui.FolderList, 1),
            C(st, daemon_ui.ExtTable, 0), C(st, daemon_ui.ExtTable, 1), C(st, daemon_ui.ListEditor, 0),
            st.btn_save, T(st, "Ripristina impostazioni predefinite")]


def settings_config(s, app):
    st = app.pages["settings"]
    first = gridrow(T(st, "CPU massima mentre usi il PC (%)")) or []
    last = gridrow(T(st, "Aspetta se gli altri programmi usano più di (% CPU)")) or []
    return [T(st, "Avvia DocIndexer con Windows (in background, icona vicino all'orologio)"),
            T(st, "Aggiungi la voce «Aggiungi a DocIndexer» al menu del tasto destro delle cartelle in Esplora file"),
            gridrow(T(st, "Scorciatoia da tastiera")), first + last,
            gridrow(T(st, "Salta i file più grandi di (MB)")),
            gridrow(T(st, "Dimensione interfaccia (%) — non segue lo zoom di Windows"))]


def settings_tools(s, app):
    tp = app.pages["settings"].tools_panel
    return [outer(tp.rows_frame), tp.btn_all, T(tp, "Ricontrolla"), tp.log]


def settings_backup(s, app):
    st = app.pages["settings"]
    return [T(st, "Crea backup..."), T(st, "Ripristina da backup...")]


def quick_search(s, qs):
    return [qs.entry, qs.info, qs.tree]


def welcome_language(s, win):
    italiano = T(win, "Italiano", raw=True, cls=ctk.CTkButton)
    return [italiano.master if italiano is not None else None]


def terms_window(s, win):
    title, ok, no, _lang, _note = terms.labels(language())
    return [win.text, win.note, T(win, no, raw=True, cls=ctk.CTkButton), T(win, ok, raw=True, cls=ctk.CTkButton)]


def near_miss(s, app):
    p = app.pages["search"]
    return [p.query, p.notice, p.tree]


def manual_window(s, win):
    return [win.search, win.toc, win.text]


CALLOUTS = {
    "01-setup": setup, "02-monitor": monitor, "03-resources": resources, "04-search": search,
    "05-regex-editor": regex_editor, "06-saved-searches": saved, "07-important": important,
    "08-documents": documents, "09-big-files": big_files, "10-duplicates": duplicates, "11-similar": similar,
    "12-settings-folders": settings_folders, "13-settings-config": settings_config,
    "14-settings-tools": settings_tools, "15-settings-backup": settings_backup, "16-quick-search": quick_search,
    "17-manual": manual_window, "18-welcome-language": welcome_language, "19-terms": terms_window,
    "20-near-miss": near_miss,
}


# --------------------------------------------------------------------------- disegno
def rects(targets, x0, y0, size):
    """Rettangoli (nelle coordinate dell'immagine) dei punti; None per quelli non trovati."""
    out = []
    for t in targets:
        group = [w for w in (t if isinstance(t, (list, tuple)) else [t]) if w is not None]
        group = [w for w in group if visible(w)]
        if not group:
            out.append(None)
            continue
        ax = min(w.winfo_rootx() for w in group) - x0
        ay = min(w.winfo_rooty() for w in group) - y0
        bx = max(w.winfo_rootx() + w.winfo_width() for w in group) - x0
        by = max(w.winfo_rooty() + w.winfo_height() for w in group) - y0
        ax, ay = max(ax - 3, 1), max(ay - 3, 1)
        bx, by = min(bx + 3, size[0] - 2), min(by + 3, size[1] - 2)
        out.append((ax, ay, bx, by) if bx - ax > 4 and by - ay > 4 else None)
    return out


def _font(size):
    for name in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _overlaps(c, r, pad=4):
    x, y = c
    return r[0] - RADIUS - pad < x < r[2] + RADIUS + pad and r[1] - RADIUS - pad < y < r[3] + RADIUS + pad


def _busy(gray, c):
    """Quanto è "piena" la zona sotto il cerchio (deviazione standard dei grigi): meno copre, meglio è."""
    r = RADIUS + 4
    box = (int(c[0] - r), int(c[1] - r), int(c[0] + r), int(c[1] + r))
    return ImageStat.Stat(gray.crop(box)).stddev[0]


def _place(r, size, placed, boxes, gray):
    """Posizione del cerchio: fuori dal rettangolo, dentro l'immagine, lontana dagli altri cerchi e dagli altri
    punti, e dove copre meno testo possibile. Per i riquadri grandi va bene anche l'angolo interno."""
    x0, y0, x1, y1 = r
    cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
    big = (x1 - x0) > 420 or (y1 - y0) > 260
    cands = []
    for d in (RADIUS + 24, RADIUS + 46, RADIUS + 74):
        cands += [(x0 - d, cy), (cx, y0 - d), (x1 + d, cy), (cx, y1 + d),
                  (x0 + 24, y0 - d), (x1 - 24, y0 - d), (x0 + 24, y1 + d), (x1 - 24, y1 + d),
                  (x0 - d, y0 + 16), (x1 + d, y0 + 16)]
    inner = [(x0 + RADIUS + 8, y0 + RADIUS + 8), (x1 - RADIUS - 8, y0 + RADIUS + 8)]
    m = RADIUS + 3
    best, best_score = None, None
    for k, c in enumerate(cands + inner):
        is_inner = k >= len(cands)
        if not (m <= c[0] <= size[0] - m and m <= c[1] <= size[1] - m):
            continue
        if any((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 < (2 * RADIUS + 8) ** 2 for p in placed):
            continue
        if any(_overlaps(c, b, pad=2) for b in boxes if b is not r):
            continue
        if not is_inner and _overlaps(c, r, pad=0):
            continue
        score = _busy(gray, c) * 1.5 + k * 0.3 + (40 if is_inner and not big else 8 if is_inner else 0)
        if best_score is None or score < best_score:
            best, best_score = c, score
    if best is None:
        best = (min(max(x0 + RADIUS + 4, m), size[0] - m), min(max(y0 + RADIUS + 4, m), size[1] - m))
    return best


def _edge_point(c, r):
    """Punto del bordo del rettangolo più vicino al cerchio."""
    return (min(max(c[0], r[0]), r[2]), min(max(c[1], r[1]), r[3]))


def draw(img: Image.Image, boxes) -> Image.Image:
    """Rettangoli, frecce e cerchi numerati (il numero è la posizione nell'elenco, anche se un punto manca)."""
    img = img.convert("RGB")
    gray = img.convert("L")
    dr = ImageDraw.Draw(img)
    font = _font(17)
    others = [b for b in boxes if b]
    for b in boxes:
        if b:
            dr.rounded_rectangle(b, radius=5, outline=OUTLINE, width=5)
            dr.rounded_rectangle(b, radius=5, outline=COLOR, width=2)
    placed = []
    for n, b in enumerate(boxes, 1):
        if not b:
            continue
        c = _place(b, img.size, placed, others, gray)
        placed.append(c)
        inside = b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3]
        if not inside:
            e = _edge_point(c, b)
            dx, dy = e[0] - c[0], e[1] - c[1]
            dist = max((dx * dx + dy * dy) ** 0.5, 1)
            ux, uy = dx / dist, dy / dist
            start = (c[0] + ux * RADIUS, c[1] + uy * RADIUS)
            tip = (e[0] - ux * 2, e[1] - uy * 2)
            base = (tip[0] - ux * 10, tip[1] - uy * 10)
            wing = ((base[0] - uy * 6, base[1] + ux * 6), (base[0] + uy * 6, base[1] - ux * 6))
            dr.line([start, base], fill=OUTLINE, width=6)
            dr.line([start, base], fill=COLOR, width=3)
            dr.polygon([tip, wing[0], wing[1]], fill=COLOR, outline=OUTLINE)
        x, y = c
        dr.ellipse((x - RADIUS - 2, y - RADIUS - 2, x + RADIUS + 2, y + RADIUS + 2), fill=OUTLINE)
        dr.ellipse((x - RADIUS, y - RADIUS, x + RADIUS, y + RADIUS), fill=COLOR)
        dr.text((x, y), str(n), font=font, fill=(255, 255, 255), anchor="mm")
    return img
