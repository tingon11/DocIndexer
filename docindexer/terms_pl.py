# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net>
# GNU AGPL-3.0 with additional terms in NOTICE.
# Polish translation added 2026-11-20; original terms: terms.py.
TEXT = '''WARUNKI UŻYTKOWANIA I WYŁĄCZENIE ODPOWIEDZIALNOŚCI — DocIndexer
Wersja {v} z dnia {d}

Przeczytaj uważnie. Naciskając „Akceptuję”, oświadczasz, że przeczytałeś, zrozumiałeś i w całości akceptujesz te warunki. Jeśli ich nie akceptujesz, naciśnij „Odrzucam”: program zostanie zamknięty i nie możesz go używać.

1. CZYM JEST DOCINDEXER
DocIndexer to program dla Windows, który odczytuje pliki w wybranych folderach (dokumenty, arkusze kalkulacyjne, prezentacje, PDF, obrazy, pocztę, archiwa, bazy danych i inne), wyodrębnia ich tekst, także za pomocą optycznego rozpoznawania znaków (OCR), i przechowuje go w lokalnej bazie danych, umożliwiając wyszukiwanie. Może uruchamiać się z Windows i pracować w tle podczas bezczynności komputera, w granicach ustawionego użycia CPU i temperatury. Pliki pozostają na swoim miejscu: program ich nie zmienia, nie przenosi ani nie usuwa.

2. DOZWOLONE UŻYCIE I ODPOWIEDZIALNOŚĆ UŻYTKOWNIKA
Możesz indeksować wyłącznie pliki i foldery, które należą do Ciebie lub które masz prawo przeglądać i przetwarzać. Ponosisz wyłączną odpowiedzialność za: (a) sprawdzenie zgodności swojego użycia z prawem, zwłaszcza gdy pliki zawierają dane osobowe innych osób, dokumenty służbowe lub informacje objęte tajemnicą bądź poufnością; (b) uzyskanie wszystkich zgód lub upoważnień wymaganych prawem, w tym przepisami o ochronie danych osobowych; (c) zabezpieczenie bazy danych, kopii zapasowych, eksportów i podglądów, które zawierają tekst dokumentów i mogą zawierać dane osobowe, dane uwierzytelniające lub informacje poufne. Zabronione jest używanie oprogramowania do zbierania lub przeglądania cudzych danych bez upoważnienia lub w jakimkolwiek niezgodnym z prawem celu. Autor nie kontroluje i nie może kontrolować sposobu korzystania z programu.

3. BRAK GWARANCJI („AS IS”)
W MAKSYMALNYM ZAKRESIE DOZWOLONYM PRZEZ WŁAŚCIWE PRAWO OPROGRAMOWANIE JEST DOSTARCZANE „TAK JAK JEST” I „W MIARĘ DOSTĘPNOŚCI”, BEZ JAKICHKOLWIEK GWARANCJI, WYRAŹNYCH ANI DOROZUMIANYCH, W TYM MIĘDZY INNYMI DOROZUMIANYCH GWARANCJI PRZYDATNOŚCI HANDLOWEJ, PRZYDATNOŚCI DO OKREŚLONEGO CELU, NIENARUSZANIA PRAW OSÓB TRZECICH, DOKŁADNOŚCI, DOSTĘPNOŚCI I BRAKU BŁĘDÓW. CAŁE RYZYKO DOTYCZĄCE JAKOŚCI I DZIAŁANIA OPROGRAMOWANIA PONOSISZ TY. JEŚLI OPROGRAMOWANIE OKAŻE SIĘ WADLIWE, PONOSISZ KOSZTY WSZELKIEGO NIEZBĘDNEGO SERWISU, NAPRAW LUB POPRAWEK. W szczególności nie gwarantuje się, że: wyodrębniony tekst i wyniki OCR będą kompletne lub dokładne; wyszukiwanie znajdzie każdy dokument zawierający dane wyrażenie; wykrywanie języka, duplikatów i metadanych będzie poprawne; ograniczenia CPU i temperatury będą zawsze przestrzegane lub ochronią sprzęt; program nie spowolni komputera ani nie zakłóci działania innych programów; oprogramowanie będzie wolne od luk bezpieczeństwa. Nie używaj DocIndexer jako jedynego narzędzia do podejmowania decyzji prawnych, śledczych, medycznych lub finansowych: zawsze sprawdzaj oryginalny dokument.

4. OGRANICZENIE ODPOWIEDZIALNOŚCI
O ILE BEZWZGLĘDNIE OBOWIĄZUJĄCE PRAWO NIE STANOWI INACZEJ, AUTOR, WSPÓŁTWÓRCY ANI DYSTRYBUTORZY OPROGRAMOWANIA W ŻADNYM WYPADKU NIE ODPOWIADAJĄ WOBEC CIEBIE ANI OSÓB TRZECICH ZA SZKODY BEZPOŚREDNIE, POŚREDNIE, UBOCZNE, SZCZEGÓLNE, ODSZKODOWANIA PRZYKŁADOWE LUB KARNE ANI SZKODY NASTĘPCZE (W TYM MIĘDZY INNYMI UTRATĘ LUB USZKODZENIE DANYCH BĄDŹ BAZY DANYCH, UTRACONE ZYSKI, WARTOŚĆ FIRMY LUB MOŻLIWOŚCI, PRZERWY W DZIAŁALNOŚCI, AWARIE, PRZEGRZANIE LUB NIEPRAWIDŁOWE DZIAŁANIE KOMPUTERA, KOSZTY USŁUG ZASTĘPCZYCH, KARY LUB ROSZCZENIA OSÓB TRZECICH) WYNIKAJĄCE Z KORZYSTANIA LUB NIEMOŻNOŚCI KORZYSTANIA Z OPROGRAMOWANIA, DECYZJI PODJĘTYCH NA PODSTAWIE JEGO WYNIKÓW, OTWIERANIA USZKODZONYCH LUB ZŁOŚLIWYCH PLIKÓW PODCZAS INDEKSOWANIA, UŻYWANIA NARZĘDZI INNYCH PRODUCENTÓW POBIERANYCH LUB URUCHAMIANYCH PRZEZ PROGRAM (modele OCR, ExifTool, 7-Zip, Microsoft Office) ANI PRZYWRACANIA KOPII ZAPASOWYCH, NAWET JEŚLI POINFORMOWANO O MOŻLIWOŚCI TAKICH SZKÓD, NIEZALEŻNIE OD PODSTAWY ROSZCZENIA (UMOWA, CZYN NIEDOZWOLONY, ODPOWIEDZIALNOŚĆ NA ZASADZIE RYZYKA LUB INNA). W krajach niedopuszczających całkowitego wyłączenia odpowiedzialności jest ona ograniczona w maksymalnym dozwolonym zakresie.

5. DANE, PRYWATNOŚĆ I WITRYNY OSÓB TRZECICH
Oprogramowanie działa lokalnie i nie wysyła danych autorowi ani innym podmiotom: tekst dokumentów, baza danych i wyszukiwania pozostają na Twoim komputerze. Łączy się z internetem tylko wtedy, gdy wybierzesz pobranie opcjonalnych narzędzi (modele OCR, ExifTool, 7-Zip) z ich witryn lub serwerów lustrzanych, które otrzymują standardowe informacje o połączeniu (np. adres IP) i podlegają własnym warunkom. Autor nie odpowiada za te witryny, ich dostępność ani zawartość udostępnianych plików. Bazę danych może odczytać każdy, kto ma dostęp do Twojego komputera lub kopii zapasowych: chroń ją tak samo jak oryginalne dokumenty.

6. LICENCJE I SKŁADNIKI INNYCH PRODUCENTÓW
Oprogramowanie jest rozpowszechniane na licencji GNU AGPL v3 z dodatkowymi warunkami z pliku NOTICE (pliki LICENSE i NOTICE); licencje składników innych producentów (PyMuPDF, RapidOCR i modele PaddleOCR, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip i inne) znajdują się w THIRD_PARTY_NOTICES.md oraz folderze LICENSES. Masz obowiązek ich przestrzegać. Niniejsze warunki uzupełniają AGPL i nie ograniczają przyznanych przez nią praw do kopiowania, modyfikowania i dalszego rozpowszechniania kodu; punkty 3 i 4 odtwarzają i uzupełniają sekcje 15 i 16 AGPL v3.

7. ZMIANY, WŁAŚCIWE PRAWO I POSTANOWIENIA KOŃCOWE
Warunki mogą być aktualizowane w kolejnych wersjach oprogramowania; przy pierwszym uruchomieniu wersji z nowymi warunkami zostaną przedstawione ponownie. Jeśli którekolwiek postanowienie okaże się nieważne, pozostałe pozostają w mocy. Z zastrzeżeniem bezwzględnie obowiązujących przepisów chroniących użytkownika stosuje się prawo włoskie. Oprogramowanie nie jest przeznaczone dla osób niepełnoletnich ani do zastosowań, w których awaria mogłaby spowodować szkody na osobie lub mieniu.

Naciskając „Akceptuję”, potwierdzasz przeczytanie i przyjęcie wszystkich powyższych punktów, indeksowanie w DocIndexer wyłącznie plików, które masz prawo przetwarzać, oraz przyjęcie pełnej odpowiedzialności za sposób korzystania z programu.
'''
LABELS = ('Warunki użytkowania', 'Akceptuję', 'Odrzucam', 'Wybierz język',
          'Przeczytaj warunki do końca. Wybranie „Odrzucam” zamknie program.')
