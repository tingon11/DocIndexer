# DocIndexer

[English](README.md) · [Italiano](README.it.md) · **Polski**

DocIndexer to program dla Windows, który w tle indeksuje tekst plików w wybranych folderach. Obsługuje dokumenty, arkusze, prezentacje, PDF, zdjęcia i skany z **OCR**, pocztę, strony WWW, archiwa, bazy danych i grafy.

**Pliki pozostają na swoim miejscu.** Program przechowuje w lokalnej bazie ich ścieżki i wyodrębnioną treść. Umożliwia wyszukiwanie pełnotekstowe, przybliżone, według nazw plików i za pomocą wyrażeń regularnych. Podgląd wyróżnia znalezione dopasowania.

Autor programu: **Andrea Cumini** — andrea@osintinfo.net — [www.osintinfo.net](https://www.osintinfo.net).

## Polska wersja

Ta gałąź zawiera **518 polskich tekstów interfejsu**, polskie warunki użytkowania oraz [skróconą instrukcję](docs/manual/pl/MANUAL.md). Wybierz **Polski** podczas pierwszego uruchomienia albo z menu **Language / Język** u góry okna.

Jest to wkład tłumaczeniowy do projektu. Obecność tłumaczenia w tej gałęzi nie oznacza, że zostało już włączone do oficjalnego wydania autora. Starszy plik EXE wymaga ponownego zbudowania, aby zawierał polski język; skopiowanie plików tłumaczeń obok niego nie aktualizuje interfejsu.

## Jak działa program

1. **Wybór folderów.** Kreator pozwala wskazać foldery robocze, uwzględnione i wykluczone rozszerzenia oraz nazwy pomijanych katalogów, np. `.git` czy `node_modules`. Przyciski grup formatów ułatwiają zaznaczanie.
2. **Zliczanie i indeksowanie.** Program zlicza pliki, oblicza SHA-256 i wyodrębnia tekst. Kopia znanej zawartości nie wymaga ponownego odczytu.
3. **Śledzenie zmian.** Obserwator folderów wykrywa nowe i zmienione pliki, przeniesienia, zmiany nazw oraz usunięcia. Pełne sprawdzanie wykrywa też zmiany wykonane po zamknięciu programu.
4. **Praca w tle.** Limity CPU, kontrola bezczynności, liczba wątków OCR i progi temperatury regulują tempo indeksowania. Możesz wstrzymywać i wznawiać pracę.
5. **Monitor.** Pokazuje postęp, bieżący plik, pliki oczekujące, pominięte, błędy i dziennik.

Zamknięcie głównego okna zwykle ukrywa je przy zegarze, pozostawiając indeksowanie w tle. Aby całkowicie zakończyć działanie, wybierz **Zakończ** z menu ikony. Ponowne uruchomienie programu pokazuje już działającą instancję.

## Obsługiwane pliki

| Typ | Sposób odczytu |
|---|---|
| PDF z tekstem i skany | PyMuPDF; renderowanie stron i RapidOCR |
| Obrazy, m.in. JPG, PNG, TIFF, BMP, WebP, HEIC/HEIF | RapidOCR |
| Word `.docx`, `.doc`, `.rtf` | python-docx; Microsoft Word przez COM lub odczyt surowych danych |
| Excel `.xlsx`, `.xls` | openpyxl, xlrd |
| OpenDocument `.odt`, `.ods`, `.odp` | Wbudowany parser |
| PowerPoint `.pptx`, `.ppt` | Odczyt bezpośredni lub PowerPoint przez COM |
| SQLite | Nazwy kolumn i wartości tekstowe; baza źródłowa otwierana tylko do odczytu |
| Grafy GraphML, GEXF, GML, DOT | Etykiety, atrybuty i krawędzie |
| HTML, XML, JSON, zwykły tekst | Tekst widoczny, wartości i atrybuty |
| Poczta `.eml`, `.msg` | Nagłówki, treść i nazwy załączników |
| EPUB | Odczyt rozdziałów |

Starsze formaty Office mogą korzystać z zainstalowanego Worda lub PowerPointa. Dostępność dodatkowych formatów zależy od narzędzi opisanych poniżej.

## Wyszukiwanie

- **Proste:** wszystkie słowa z danego wiersza, również jako początki wyrazów. Oddzielne wiersze są łączone operatorem OR.
- **Zaawansowane:** składnia FTS5, np. `AND`, `OR`, `NOT`, `"dokładna fraza"`, `rdzeń*`, `NEAR(a b, 5)`.
- **Dokładna fraza i dowolna kolejność słów.**
- **Przybliżone:** toleruje literówki i część typowych pomyłek OCR, np. `0/o`, `1/l` czy `rn/m`. Po braku dokładnych wyników program może automatycznie ponowić wyszukiwanie z tolerancją jednego błędu.
- **Według nazwy pliku.**
- **Regex:** wyrażenia regularne z edytorem wzorców i tekstem testowym.

Po lewej wybierasz przeszukiwane foldery. Filtry pozwalają ograniczyć wyniki według daty utworzenia lub modyfikacji, rozmiaru, języka dokumentu oraz ważności. Naciśnij **Szukaj** lub **Ctrl+Enter**.

Edytor regex zawiera m.in. wzorce e-mail, telefonów, IBAN, adresów IP i WWW, dat, godzin oraz współrzędnych GPS. Wzorce opisane jako włoskie nadal dotyczą włoskich numerów i dokumentów — tłumaczenie nie zmienia ich znaczenia. Operatory zapytań pozostają angielskie.

### Szybkie i zapisane wyszukiwania

**Ctrl+Alt+D** otwiera pasek szybkiego wyszukiwania nad innymi programami. Skrót zmienisz w **Ustawienia > Konfiguracja**. Enter otwiera plik, Ctrl+Enter pełne wyszukiwanie, a Alt+Enter pokazuje plik w folderze.

Możesz zapisać zapytanie pod nazwą i włączyć powiadamianie o nowych pasujących plikach. Program ponawia takie wyszukiwanie po indeksowaniu nowych dokumentów.

## Podgląd, ważność i notatki

Wybranie wyniku pokazuje podgląd z wyróżnionymi dopasowaniami. Przyciskami **Wystąpienie ◀ ▶** przechodzisz między nimi. Możesz otworzyć oryginalny plik lub pokazać go w folderze.

Pod nazwą pliku ustawisz **kolor ważności** i **notatkę**. Oznaczenia pozostają związane z plikiem także po przeniesieniu lub zmianie nazwy. Karta **Ważne** zbiera oznaczone dokumenty.

Listy pokazują daty utworzenia i modyfikacji. Kliknięcie nagłówka kolumny zmienia sortowanie. Rozmiar interfejsu ustawia się niezależnie od powiększenia Windows.

## OCR po polsku

OCR działa lokalnie, za pomocą **RapidOCR i ONNX Runtime**. Model wielojęzyczny PP-OCRv6 dla alfabetu łacińskiego obejmuje również polski tekst. Nie wymaga osobnego modelu języka polskiego ani instalacji Tesseracta.

Model podstawowy jest dostarczany przez pakiet RapidOCR i kopiowany do `tools\rapidocr`. Po udostępnieniu modeli rozpoznawanie działa bez połączenia z internetem. Modele innych alfabetów pobierzesz w **Ustawienia > Narzędzia zewnętrzne**.

Tryb **Automatycznie** rozpoczyna od modelu podstawowego. Jeśli wynik jest mało pewny, może próbować innych pobranych modeli i wybrać najlepiej pasujący.

Jakość OCR zależy m.in. od rozdzielczości, kontrastu, kroju pisma i układu dokumentu. Zawsze porównuj istotne wyniki z oryginałem.

## Moduły dodatkowe

Moduły włączysz lub wyłączysz w **Ustawienia > Konfiguracja**. W wyszukiwaniu wybierasz źródła danych: tekst dokumentów, metadane, pliki w archiwach lub zawartość baz.

| Moduł | Zastosowanie |
|---|---|
| ExifTool | Metadane zdjęć, dokumentów, dźwięku i filmów: autor, daty, aparat, GPS, oprogramowanie |
| 7-Zip | Tekst plików wewnątrz archiwów ZIP, RAR, 7z, TAR, GZ i podobnych |
| Bazy danych | SQLite, dBASE/FoxPro `.dbf`, Access `.mdb/.accdb` |

ExifTool i 7-Zip pobierzesz w **Narzędziach zewnętrznych**. Access wymaga odpowiedniego sterownika Microsoft. Pliki z archiwów są rozpakowywane do folderu tymczasowego.

## Duplikaty i eksport

Karta **Duplikaty** pozwala wyszukiwać pliki o identycznej zawartości oraz dokumenty o podobnym tekście, np. poprawione wersje czy ten sam dokument zapisany w PDF i Wordzie. Można wybrać minimalne podobieństwo.

Wyniki wyszukiwania, listy dokumentów i duplikatów można eksportować do **Excel, CSV lub PDF**, z informacjami o ważności i notatkami.

## Baza danych i kopie zapasowe

Ta sama zawartość jest przechowywana jednokrotnie według SHA-256. Tekst jest kompresowany za pomocą zstd, a indeks FTS5 przechowuje dane potrzebne do wyszukiwania bez drugiej kopii tekstu. Porządkowanie bazy odbywa się również podczas bezczynności.

**Ustawienia > Kopie zapasowe i przywracanie** umożliwia zapis bazy, ustawień, notatek, kolorów, wzorców regex i zapisanych wyszukiwań. **Oryginalne dokumenty nie są dołączane do kopii.**

Przywracanie zastępuje bieżącą bazę i ustawienia oraz uruchamia program ponownie. Poprzednia baza pozostaje z rozszerzeniem `.before-restore`.

## Uruchamianie ze źródeł

Wymagany jest Windows, Python 3.10 lub nowszy oraz **SQLite 3.43 lub nowszy z obsługą FTS5**. Wersja SQLite zależy od użytego środowiska Pythona.

W folderze projektu wykonaj:

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -c "import sqlite3; print(sqlite3.sqlite_version)"
.venv\Scripts\python main.py
```

Po przygotowaniu środowiska można też użyć `avvia.bat`. Parametr `--background` uruchamia program z ukrytym oknem.

Błąd `unrecognized option: "contentless_delete"` oznacza, że biblioteka SQLite jest za stara dla obecnego schematu indeksu. W takim przypadku potrzebne jest środowisko z nowszym SQLite; sama zmiana ścieżki bazy nie rozwiązuje problemu.

Zmienna środowiskowa `DOCINDEXER_HOME` pozwala wskazać osobny folder konfiguracji, danych i pamięci podręcznej, np. na potrzeby testów.

## Budowanie EXE

Skrypt `build.bat` buduje `dist\DocIndexer.exe` za pomocą PyInstaller. Wymaga wcześniej przygotowanego środowiska `.venv`. Obok programu umieszcza informacje licencyjne. Podczas budowania należy sprawdzić, czy dołączana biblioteka SQLite spełnia wymagania opisane powyżej.

Przy programie powstają m.in. `config.json`, folder danych z bazą oraz `tools` z modelami OCR. Gotowe wydanie może działać bez osobnej instalacji Pythona.

## Instrukcja i języki

Interfejs tej gałęzi obsługuje: Italiano, English, Français, Deutsch, Español, Ελληνικά, Shqip i Polski.

- [Skrócona instrukcja po polsku](docs/manual/pl/MANUAL.md) — dostępna również z przycisku **Instrukcja** w programie; bez polskich zrzutów ekranu.
- [Spis instrukcji we wszystkich językach](MANUAL.md).
- [Warunki użytkowania](TERMS.md), wyświetlane przy pierwszym uruchomieniu i dostępne ponownie w programie.

## Licencja i autorstwo

© 2026 **Andrea Cumini** — andrea@osintinfo.net — [www.osintinfo.net](https://www.osintinfo.net).

Program jest udostępniany na licencji **GNU AGPL v3** z dodatkowymi warunkami opisanymi w [NOTICE](NOTICE). Należy zachować informacje o autorze i licencji oraz oznaczać zmodyfikowane wersje. Plik NOTICE określa też zasady używania nazwy i logo przy rozpowszechnianiu zmodyfikowanych wydań. Program jest dostarczany bez gwarancji.

- [Pełna licencja](LICENSE).
- [Warunki dodatkowe i autorstwo](NOTICE).
- [Informacje o składnikach zewnętrznych](THIRD_PARTY_NOTICES.md).

Polskie tłumaczenie i dokumentację dodano w tej gałęzi 20.11.2026. Nie zmieniają one autorstwa oryginalnego programu.
