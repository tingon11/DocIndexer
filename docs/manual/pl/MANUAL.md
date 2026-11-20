# DocIndexer — instrukcja po polsku

DocIndexer indeksuje tekst dokumentów w wybranych folderach. Wyszukuje także tekst rozpoznany na skanach i zdjęciach za pomocą OCR. Pliki pozostają na swoim miejscu; indeks jest przechowywany lokalnie.

## Pierwsze uruchomienie

1. Rozpakuj całą paczkę do osobnego folderu.
2. Uruchom program z wydania zawierającego język polski. Ze źródeł: utwórz środowisko `.venv`, zainstaluj zależności z `requirements.txt` i uruchom `.venv\Scripts\python main.py` (Python 3.10 lub nowszy).
3. W oknie wyboru języka wybierz **Polski**, przeczytaj warunki i podejmij decyzję o ich akceptacji.
4. Dodaj foldery do monitorowania, wybierz rozszerzenia plików i rozpocznij indeksowanie.

Jeśli program był już konfigurowany, wybierz **Polski** z listy języków w górnej części okna. Istniejący wybór języka jest zachowywany.

## Monitor

Monitor pokazuje postęp, pliki oczekujące, błędy i dziennik pracy. Przycisk **Wstrzymaj** zatrzymuje indeksowanie, **Wznów** je kontynuuje. **Sprawdź foldery teraz** uruchamia ponowne sprawdzenie zmian.

Zamknięcie głównego okna zwykle ukrywa program przy zegarze. Aby zakończyć działanie, wybierz **Zakończ** w menu jego ikony.

## Wyszukiwanie

Wybierz foldery po lewej stronie i wpisz szukane słowa. Każdy wiersz jest osobnym zapytaniem; wyniki z wierszy są łączone operatorem OR. W prostym wyszukiwaniu wszystkie słowa danego wiersza muszą wystąpić. Naciśnij **Szukaj** lub Ctrl+Enter.

Dostępne są: dokładna fraza, wyszukiwanie w nazwie pliku, dowolna kolejność słów, wyszukiwanie przybliżone oraz wyrażenia regularne. Tryb zaawansowany obsługuje `AND`, `OR`, `NOT`, `"dokładną frazę"`, `rdzeń*` i `NEAR(a b, 5)`. Nazwy tych operatorów pozostają angielskie.

Filtry ograniczają wyniki według daty, rozmiaru i języka dokumentu. Daty wpisuj w formacie `rrrr-mm-dd`, np. `2026-11-20`.

## Podgląd, ważność i notatki

Wybierz wynik, aby zobaczyć podgląd z wyróżnionymi dopasowaniami. Przyciski **Wystąpienie ◀ ▶** przechodzą między dopasowaniami. Kółko myszy przewija, +/− zmienia powiększenie, przeciągnięcie lewym przyciskiem przesuwa widok.

Pod nazwą pliku ustawisz kolor ważności i notatkę. Tak oznaczone pliki znajdziesz na karcie **Ważne**. **Otwórz oryginał** uruchamia plik w powiązanym programie.

## OCR i narzędzia

W **Ustawienia > Narzędzia zewnętrzne** sprawdzisz i pobierzesz wymagane składniki. Model dla alfabetu łacińskiego obejmuje również polski. Model OCR i jego rozdzielczość wybierzesz w konfiguracji; przyciskiem **Testuj OCR** sprawdzisz działanie.

ExifTool odczytuje metadane, 7-Zip umożliwia przeszukiwanie plików w archiwach. Niektóre starsze formaty Office oraz bazy Access wymagają dodatkowych składników Microsoft.

## Zapisane wyszukiwania i eksport

**Zapisz wyszukiwanie** zachowuje zapytanie. Możesz włączyć powiadamianie o nowych pasujących plikach. **Eksportuj wyniki** zapisuje wyniki do wybranego formatu.

## Duplikaty i duże pliki

Na karcie **Duplikaty** wybierz pliki identyczne lub podobne i naciśnij **Znajdź duplikaty**. Pliki identyczne mają tę samą zawartość; podobne mają zbliżony tekst.

Duże pliki oczekują na decyzję. **Analizuj** dodaje je do kolejki, **Zablokuj** odkłada je na bok, **Odblokuj** pozwala ponownie je rozpatrzyć.

## Wydajność

Ustawienia pracy w tle ograniczają użycie CPU podczas pracy i bezczynności komputera. Limity temperatury zmniejszają tempo po rozgrzaniu sprzętu. Niższy poziom zasobów oznacza wolniejsze indeksowanie.

## Kopie zapasowe

W **Ustawienia > Kopie zapasowe i przywracanie** utworzysz kopię indeksu, ustawień, notatek, wzorców regex i zapisanych wyszukiwań. Oryginalne dokumenty nie są dołączane. Przywrócenie zastępuje obecną bazę i ustawienia oraz ponownie uruchamia program.

## Informacje o tej wersji

Autor programu: Andrea Cumini — andrea@osintinfo.net — www.osintinfo.net.
Licencja: GNU AGPL v3 z dodatkowymi warunkami w pliku NOTICE.

Tłumaczenie z 20.11.2026 dodaje 518 polskich tekstów interfejsu, polskie warunki użytkowania i tę skróconą instrukcję. Instrukcja nie zawiera polskich zrzutów ekranu.
