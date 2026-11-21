# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Voce «Aggiungi a DocIndexer» nel menu del tasto destro di Esplora file.

Si registra nelle chiavi dell'utente (HKCU\\Software\\Classes), senza permessi di amministratore:
  Directory\\shell\\DocIndexer             clic destro su una cartella          -> --add-folder "%1"
  Directory\\Background\\shell\\DocIndexer  clic destro nel vuoto di una cartella -> --add-folder "%V"
  Drive\\shell\\DocIndexer                 clic destro su un disco (D:\\)        -> --add-folder "%1"
Su Windows 11 la voce è nel menu classico («Mostra altre opzioni» o Maiusc+F10).
Il comando punta all'exe attuale (o a pythonw + main.py da sorgenti): refresh() all'avvio lo aggiorna se il
programma è stato spostato o se è cambiata la lingua.
"""
from __future__ import annotations

import os
import re
import sys

from .config import ASSETS_DIR, BASE_DIR, FROZEN
from .i18n import tr

KEY_NAME = "DocIndexer"
ARG = "--add-folder"
# (chiave sotto Software\Classes, segnaposto di Esplora file per la cartella)
_TARGETS = (("Directory\\shell", "%1"), ("Directory\\Background\\shell", "%V"), ("Drive\\shell", "%1"))


def _program() -> str:
    """Programma da avviare, tra virgolette (exe compilato, oppure pythonw + main.py)."""
    if FROZEN:
        return f'"{sys.executable}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    return f'"{exe}" "{BASE_DIR / "main.py"}"'


def _icon() -> str:
    if FROZEN:
        return f'"{sys.executable}",0'
    ico = ASSETS_DIR / "docindexer.ico"
    return str(ico) if ico.exists() else ""


def command(placeholder: str = "%1") -> str:
    # il percorso va per ultimo: "D:\" finisce con \" e verrebbe letto come virgolette (vedi folder_from_argv)
    return f'{_program()} {ARG} "{placeholder}"'


def register() -> bool:
    """Crea (o aggiorna) la voce del menu. False se non è Windows o il registro rifiuta la scrittura."""
    if sys.platform != "win32":
        return False
    import winreg

    try:
        for base, ph in _TARGETS:
            path = f"Software\\Classes\\{base}\\{KEY_NAME}"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, tr("Aggiungi a DocIndexer"))
                icon = _icon()
                if icon:
                    winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon)
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path + "\\command", 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, command(ph))
        return True
    except OSError:
        return False


def unregister() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    ok = True
    for base, _ph in _TARGETS:
        path = f"Software\\Classes\\{base}\\{KEY_NAME}"
        for sub in (path + "\\command", path):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except FileNotFoundError:
                pass
            except OSError:
                ok = False
    return ok


def set_enabled(enabled: bool) -> bool:
    return register() if enabled else unregister()


def enabled() -> bool:
    """La voce è registrata (basta quella delle cartelle)."""
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\Directory\\shell\\{KEY_NAME}\\command"):
            return True
    except OSError:
        return False


def refresh() -> None:
    """All'avvio e al cambio di lingua: se la voce c'è, riscrive comando, icona e testo."""
    if enabled():
        register()


def folder_from_argv(argv: list[str]) -> str | None:
    """Cartella passata con --add-folder (None se manca). Corregge "D:\\" letto come D:" da Windows."""
    if ARG not in argv:
        return None
    i = argv.index(ARG)
    if i + 1 >= len(argv):
        return None
    p = " ".join(argv[i + 1:]).strip().strip('"').strip()
    if re.fullmatch(r"[A-Za-z]:", p):
        p += "\\"
    return os.path.normpath(p) if p else None
