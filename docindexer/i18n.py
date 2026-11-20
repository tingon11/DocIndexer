# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Traduzioni dell'interfaccia.

I testi nel codice sono in italiano e passano da tr():

    tr("Connessioni")                       -> "Connections" in inglese
    tr("fidata: {d}", d="example.com")      -> segnaposto con str.format

Le traduzioni stanno in i18n_strings*.py (ordine in ORDER); il catalogo polacco è in i18n_pl.py.
Se un testo non è tradotto si usa l'italiano.
"""
from __future__ import annotations

from .i18n_strings import ORDER, STRINGS
from .i18n_strings_daemon import STRINGS as _DAEMON
from .i18n_strings_extra import STRINGS as _EXTRA
from .i18n_pl import STRINGS as _POLISH

STRINGS = {**STRINGS, **_DAEMON, **_EXTRA}

LANGUAGES = {
    "it": "Italiano", "en": "English", "fr": "Français", "de": "Deutsch", "es": "Español",
    "el": "Ελληνικά", "sq": "Shqip", "pl": "Polski",
}
_current = "it"


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else "it"


def language() -> str:
    return _current


def tr(text: str, /, **kw) -> str:
    # "/": il testo è solo posizionale, così un segnaposto può chiamarsi {text} (es. tr("...{text}", text=x))
    if _current == "pl":
        text = _POLISH.get(text, text)
    elif _current != "it":
        row = STRINGS.get(text)
        if row:
            t = row[ORDER.index(_current)]
            if t:
                text = t
    return text.format(**kw) if kw else text
