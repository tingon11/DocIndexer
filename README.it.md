# DocIndexer

[English](README.md) · **Italiano**

Indicizzatore di documenti in background per Windows. Parte con Windows, resta nell'area di notifica e tiene
un indice del testo dei file delle cartelle che scegli: documenti, fogli di calcolo, presentazioni, PDF, foto
e scansioni (**OCR con RapidOCR**), e-mail, pagine web, database SQLite, grafi e altro. I file **restano dove
sono**: nel database vanno solo il percorso e il testo. La ricerca è full-text (SQLite FTS5), fuzzy, per nome
file o con **espressioni regolari**, con un'anteprima che evidenzia i risultati.

L'OCR usa RapidOCR, l'interfaccia ha il tema di PCSnex ed è in otto lingue.

## Come funziona

1. **Primo avvio**: una configurazione guidata chiede le **cartelle di lavoro** da monitorare, le tabelle
   delle **estensioni incluse ed escluse** (con i pulsanti per gruppi: Office, PDF, Immagini, Posta,
   Database, Web e dati, Grafi, eBook, Testo e codice, Archivi, Audio e video, Programmi; un clic spunta tutto
   il gruppo, un altro clic lo toglie) e le **cartelle da saltare** per nome (`$Recycle.Bin`, `.git`,
   `node_modules`...). Si può anche attivare l'**avvio con Windows**.
2. **Prima conta, poi indicizza**: DocIndexer conta i file da analizzare (estensioni incluse meno escluse),
   poi ne calcola lo SHA-256 ed estrae il testo. L'**hash** identifica il contenuto: una copia di un file già
   noto non viene rianalizzata.
3. **Modifiche in tempo reale**: un watcher delle cartelle segue i file nuovi, modificati,
   **spostati/rinominati** (si aggiorna il percorso, senza rianalizzare) e **cancellati** (tolti dall'indice).
   Un controllo completo delle cartelle gira all'avvio e ogni qualche ora, così si trovano anche le modifiche
   fatte a programma chiuso.
4. **Discreto**: priorità bassa di CPU e disco, tetto di CPU (25% di base) mentre usi il PC, tetto più alto
   (60%) quando il PC è inattivo da qualche minuto, pausa se gli altri programmi usano già molta CPU, ritmo
   minimo a batteria e solo 2 thread OCR, per non scaldare il processore.
5. **Monitor**: file da analizzare, indicizzati, da fare, saltati ed errori; barra di avanzamento, grafico
   a torta, file corrente, registro, pausa/riprendi, "controlla subito le cartelle".

Chiudere la finestra la nasconde: DocIndexer continua a lavorare e l'icona vicino all'orologio offre Apri,
Pausa/Riprendi, Controlla subito le cartelle ed Esci. Avviarlo una seconda volta mostra solo la finestra di
quello già attivo.

| Tipo | Strumento |
|---|---|
| PDF con testo / scansionato | PyMuPDF / rendering della pagina + RapidOCR |
| Immagini (jpg, png, tiff, bmp, gif, webp, **heic/heif**, jp2...) | RapidOCR |
| Word .docx / .doc / .rtf | python-docx / Microsoft Word via COM o estrazione grezza |
| Excel .xlsx / .xls, OpenDocument .odt / .ods / .odp | openpyxl / xlrd / parser interno |
| PowerPoint .pptx / .ppt | lettura diretta / PowerPoint via COM |
| Database **SQLite** (.sqlite, .db...) | una pagina per tabella: nomi delle colonne e valori di testo (aperto in sola lettura) |
| **Grafi** (GraphML, GEXF, GML, DOT) | etichette, attributi e archi |
| HTML, XML, JSON, testo | testo visibile, valori e attributi, righe chiave: valore |
| **E-mail** .eml / .msg | intestazioni, corpo, nomi degli allegati (.msg con extract-msg) |
| EPUB | una pagina per capitolo |

## Importanza e note

Nell'anteprima, sotto il nome del file, ogni documento può avere un **colore di importanza** (azzurro,
verde, giallo, arancio, rosso) e una **nota**. Appartengono al contenuto del file (hash SHA-256), non al
percorso: seguono il file se viene spostato o rinominato (anche a DocIndexer chiuso o su un altro disco), le
copie identiche li condividono e restano se il file viene modificato. La scheda **Importanti** elenca i documenti colorati (prima i più importanti, con la nota), gli
elenchi mostrano il colore sulla riga e la ricerca ha l'opzione **solo documenti importanti**.

Tutti gli elenchi di file mostrano la data di **creazione** e di modifica e si ordinano cliccando
l'intestazione della colonna (A-Z, un altro clic Z-A). Oltre ai nomi di cartella da saltare ovunque, si
possono escludere **sottocartelle precise** per percorso (es. `Documents\garbage`). La **dimensione
dell'interfaccia** è un'impostazione che si somma allo zoom di Windows (100% = come le altre app di Windows).
Un clic sulla cella **Cartella** in Ricerca, Documenti e Importanti apre Esplora file con il file selezionato.
Se si tolgono tutte le cartelle monitorate l'indice si svuota e il Monitor si azzera.

## Moduli aggiuntivi

Ogni modulo si attiva o disattiva in **Impostazioni > Configurazione** e salva i suoi dati in una **tabella
dedicata** con il suo indice di ricerca; in **Ricerca** scegli in quali dati cercare (testo dei documenti,
metadati, file dentro gli archivi, contenuto dei database):

- **ExifTool** (si scarica da *Strumenti esterni*): metadati di foto, documenti, audio e video (autore, date,
  fotocamera, GPS, software...). Anche i file senza testo leggibile (audio, video, foto RAW) vengono
  indicizzati con i loro metadati.
- **7-Zip** (si scarica da *Strumenti esterni*): il testo dei file dentro gli archivi zip, rar, 7z, tar, gz,
  estratti in una cartella temporanea cancellata subito dopo.
- **Database**: SQLite (incluso), dBASE/FoxPro `.dbf` (dbfread), Access `.mdb/.accdb` (driver ODBC di
  Microsoft, installato con Office).

La ricerca ha anche i **filtri** per periodo (data di modifica o di creazione) e per dimensione del file.

## Ricerca

Semplice (tutte le parole, anche come prefisso, accenti ignorati), avanzata (sintassi FTS5: `AND`, `OR`,
`NOT`, `"frase esatta"`, `radice*`, `NEAR(a b, 5)`), frase esatta, frase in qualsiasi ordine, fuzzy (1-4
errori), nome file e **Regex**: un'espressione regolare sul testo. L'**editor regex** offre pattern pronti
(e-mail, telefono italiano e internazionale, IBAN, codice fiscale, partita IVA, targa, IP, URL, date, ore,
carta di credito, importi, Bitcoin, IMEI, passaporto, coordinate GPS, hashtag, @utente) e blocchi da comporre
(cifra, lettera, ripetizioni, "oppure", gruppi...), spiega la regex in parole ed evidenzia i risultati su un
testo di prova mentre scrivi. A sinistra si scelgono le cartelle monitorate in cui cercare, i filtri di data
e dimensione e la **lingua del documento** (rilevata da sola per ogni documento).

Se una ricerca non trova nulla, DocIndexer riprova da solo tollerando un errore di battitura o di OCR; la
ricerca fuzzy accetta anche gli scambi tipici dell'OCR (0/o, 1/l, rn/m, cl/d...), così `c0ntratto` trova
`contratto`.

- **Ricerca rapida**: una barra di ricerca sopra qualsiasi programma, con una scorciatoia globale
  (predefinita `Ctrl+Alt+D`, si cambia in Impostazioni > Configurazione) o dal menu dell'icona. Cerca mentre
  scrivi; Invio apre il file, Ctrl+Invio apre la ricerca completa in DocIndexer, Alt+Invio lo mostra nella
  cartella.
- **Ricerche salvate**: salvi una ricerca con un nome; con l'avviso attivo DocIndexer la ripete quando
  indicizza file nuovi e mostra una notifica di Windows vicino all'orologio ("Solo i nuovi" li elenca).
- **Esportazione**: risultati, elenchi Documenti e Importanti e duplicati si esportano in Excel (.xlsx, righe
  colorate per importanza), CSV (`;`, si apre in Excel) o PDF, con importanza e note.

## Duplicati

La scheda **Duplicati** elenca i file identici (stesso contenuto in più cartelle, con lo spazio occupato
dalle copie in più) e i **documenti simili** (testo quasi uguale: versioni corrette, lo stesso testo in PDF e
in Word, una scansione rifatta), con somiglianza minima 97, 93, 90 o 87%. La somiglianza usa un'impronta
SimHash a 64 bit del testo, calcolata durante l'indicizzazione.

## Database piccolo, ricerca veloce

- lo stesso contenuto trovato in più posti si estrae e si salva **una volta sola** (SHA-256);
- il testo è salvato **compresso con zstd** e si decomprime solo per i risultati mostrati;
- l'indice FTS5 è **contentless**: contiene solo l'indice, non una seconda copia del testo;
- **auto-vacuum incrementale** e compattazione dell'indice girano quando il PC è inattivo.

L'indice non è compresso, quindi la ricerca resta veloce.

## OCR (RapidOCR)

L'OCR gira dentro il programma (RapidOCR + ONNX Runtime). Il modello predefinito (PP-OCRv6, ~30 MB) riconosce
italiano, inglese, turco e tutte le lingue in alfabeto latino più cinese/giapponese; è incluso nel programma e
viene copiato in `tools\rapidocr` al primo avvio. Gli altri alfabeti (cirillico, greco, arabo, coreano,
thailandese, devanagari, tamil, telugu) si scaricano da **Impostazioni > Strumenti esterni**.

Con il modello **Automatico** (predefinito nelle nuove installazioni) la prima pagina scansionata di ogni
documento si legge con il modello latino; se il risultato è incerto si provano gli altri modelli scaricati e si
usa quello che legge meglio per tutto il documento (per esempio una scansione in russo usa il cirillico).

## Avvio con Windows, backup

- **Avvio con Windows**: interruttore nella scheda Monitor, voce con la spunta nel menu dell'icona vicino
  all'orologio, oppure Impostazioni > Configurazione. Vale subito (chiave Run dell'utente, senza permessi di
  amministratore).
- **Aggiungi a DocIndexer** nel menu del tasto destro di Esplora file su cartelle e dischi (Impostazioni >
  Configurazione > Avvio): aggiunge la cartella a quelle monitorate e la indicizza. Registrata in HKCU, senza
  permessi di amministratore; su Windows 11 è in «Mostra altre opzioni».
- **Uso portatile**: programma, `config.json` e database stanno nella stessa cartella, quindi DocIndexer può
  girare da un disco esterno insieme alle cartelle che indicizza. Se su un altro PC il disco prende un'altra
  lettera (E: -> F:), all'avvio tutti i percorsi di quel disco (cartelle monitorate, esclusioni, ricerche
  salvate, database) vengono riscritti e una riga nel registro del Monitor lo segnala. L'avvio con Windows e
  la voce del tasto destro stanno nel registro di Windows: vanno riattivati su ogni PC.
- **Backup**: Impostazioni > Backup crea uno .zip con il database (indice, note, colori di importanza), le
  impostazioni, i pattern regex e le ricerche salvate, anche mentre l'indicizzazione lavora. Il ripristino li
  sostituisce e riavvia DocIndexer; il database precedente resta come `.before-restore`.

## Avvio da sorgente

```bat
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

oppure doppio clic su `avvia.bat`. `main.py --background` parte con la finestra nascosta (solo l'icona): è il
comando scritto nella chiave "Esegui" di Windows quando l'avvio con Windows è attivo (solo per l'utente
corrente, senza permessi di amministratore). La variabile d'ambiente `DOCINDEXER_HOME` sposta `config.json`,
`data\` e `cache\` in un'altra cartella (utile per prove o profili separati).

## Compilazione

`build.bat` crea con PyInstaller un unico eseguibile `dist\DocIndexer.exe` e gli copia accanto `LICENSE`,
`NOTICE`, `THIRD_PARTY_NOTICES.md` e `LICENSES\`. Accanto all'exe il programma crea `config.json`, `data\`
(database SQLite), `cache\` (anteprime Office, si può cancellare) e `tools\` (modelli OCR).

## Configurazione

`config.json` (modificabile anche da **Impostazioni**): cartelle monitorate, estensioni incluse/escluse,
cartelle saltate, dimensione massima dei file, tetti di CPU (in uso / inattivo), tempo di inattività, soglia
di carico, thread OCR, intervallo del controllo completo, modello OCR e DPI, percorso del database, avvio con
Windows, lingua.

## Lingue dell'interfaccia

Italiano, English, Français, Deutsch, Español, Ελληνικά, Shqip, Polski, dal menu **Lingua** in alto a destra.

## Manuale

Il manuale utente, con gli screenshot, è in `docs/manual/<lingua>/MANUAL.md` in tutte e otto le lingue (indice in
[MANUAL.md](MANUAL.md)). Nel programma si apre da **📖 Manuale**, a destra delle schede, o dal menu dell'icona
vicino all'orologio, nella lingua scelta. Gli screenshot sono stati fatti su un profilo di prova
separato, con documenti inventati.

## Licenza

© 2026 Andrea Cumini · andrea@osintinfo.net · www.osintinfo.net

DocIndexer è software libero con licenza **GNU AGPL-3.0** (`LICENSE`), con i termini aggiuntivi della
sezione 7 descritti in `NOTICE`: chi distribuisce il programma o un lavoro derivato deve **mantenere
l'attribuzione all'autore** nel codice, nella documentazione e nell'interfaccia, deve indicare le versioni
modificate e non può usare il nome e il logo DocIndexer per una versione modificata. Senza alcuna garanzia.

I componenti di terze parti e le loro licenze sono in `THIRD_PARTY_NOTICES.md`.

Alla prima apertura il programma chiede la lingua e poi mostra i termini d'uso e l'esclusione di
responsabilità, da accettare per usarlo; il testo, in tutte e otto le lingue, è in [TERMS.md](TERMS.md) e si
può rileggere da **Termini d'uso**, accanto a **📖 Manuale**.
