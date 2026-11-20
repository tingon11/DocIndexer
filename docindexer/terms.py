# DocIndexer — Copyright (C) 2026 Andrea Cumini <andrea@osintinfo.net> — www.osintinfo.net
# Licenza GNU AGPL-3.0 con i termini aggiuntivi del file NOTICE (attribuzione all'autore).
"""Termini d'uso ed esclusione di responsabilità, nelle 8 lingue dell'interfaccia (come in DroidSnex).

Vengono mostrati alla prima apertura (welcome.py), dopo la scelta della lingua; l'accettazione viene
salvata in config.json con la versione del testo (TERMS_VERSION) e la data: se la versione cambia,
vengono richiesti di nuovo. Il file TERMS.md del progetto è generato da questo modulo:

    python -m docindexer.terms > TERMS.md

    text(lang)    -> testo completo nella lingua (italiano se manca)
    labels(lang)  -> (titolo, Accetto, Rifiuto, Scegli la lingua, nota)
"""
from __future__ import annotations

from .terms_pl import TEXT as _PL, LABELS as _PL_LABELS

TERMS_VERSION = "1.0"            # da aumentare quando il testo cambia in modo sostanziale
TERMS_DATE = "2026-11-20"

_IT = """\
TERMINI D'USO ED ESCLUSIONE DI RESPONSABILITÀ — DocIndexer
Versione {v} del {d}

Leggi con attenzione. Premendo "Accetto" dichiari di aver letto, compreso e accettato integralmente questi termini. Se non li accetti, premi "Rifiuto": il programma si chiude e non puoi usarlo.

1. CHE COS'È DOCINDEXER
DocIndexer è un programma per Windows che legge i file delle cartelle che scegli (documenti, fogli di calcolo, presentazioni, PDF, immagini, posta, archivi, database e altro), ne estrae il testo, anche con il riconoscimento ottico dei caratteri (OCR), e lo conserva in un database locale per permetterti di cercarlo. Può avviarsi con Windows e lavorare in background, usando il tempo in cui il PC è inattivo entro i limiti di CPU e temperatura che imposti. I file restano dove sono: il programma non li modifica, non li sposta e non li cancella.

2. USO CONSENTITO E RESPONSABILITÀ DELL'UTENTE
Puoi indicizzare solo file e cartelle che ti appartengono o che hai il diritto di consultare e trattare. Sei l'unico responsabile di: (a) verificare che l'uso che ne fai sia lecito, in particolare quando i file contengono dati personali di altre persone, documenti di lavoro o informazioni coperte da segreto o riservatezza; (b) ottenere ogni consenso o autorizzazione richiesti dalla legge, incluse le norme sulla protezione dei dati personali; (c) custodire il database, le copie di sicurezza, le esportazioni e le anteprime, che contengono il testo dei tuoi documenti e possono quindi contenere dati personali, credenziali o informazioni riservate. È vietato usare il software per raccogliere o consultare dati altrui senza autorizzazione o per qualunque scopo illecito. L'autore non controlla e non può controllare l'uso che ne fai.

3. NESSUNA GARANZIA ("AS IS")
NEI LIMITI MASSIMI CONSENTITI DALLA LEGGE APPLICABILE, IL SOFTWARE È FORNITO "COSÌ COM'È" E "COME DISPONIBILE", SENZA GARANZIA DI ALCUN TIPO, ESPRESSA O IMPLICITA, INCLUSE, A TITOLO ESEMPLIFICATIVO E NON ESAUSTIVO, LE GARANZIE IMPLICITE DI COMMERCIABILITÀ, IDONEITÀ A UNO SCOPO PARTICOLARE, NON VIOLAZIONE DI DIRITTI DI TERZI, ACCURATEZZA, DISPONIBILITÀ E ASSENZA DI ERRORI. L'INTERO RISCHIO RELATIVO ALLA QUALITÀ E ALLE PRESTAZIONI DEL SOFTWARE È A TUO CARICO. SE IL SOFTWARE RISULTA DIFETTOSO, TI ASSUMI IL COSTO DI OGNI ASSISTENZA, RIPARAZIONE O CORREZIONE. In particolare non si garantisce che: il testo estratto e i risultati dell'OCR siano completi o esatti; la ricerca trovi tutti i documenti che contengono un termine; il riconoscimento della lingua, dei duplicati e dei metadati sia corretto; i limiti di CPU e di temperatura vengano sempre rispettati o proteggano l'hardware; il programma non rallenti il PC né interferisca con altri programmi; il software sia privo di vulnerabilità. Non usare DocIndexer come unico strumento per decisioni legali, investigative, sanitarie o economiche: verifica sempre il documento originale.

4. ESCLUSIONE DI RESPONSABILITÀ
IN NESSUN CASO, SALVO QUANTO IMPOSTO INDEROGABILMENTE DALLA LEGGE, L'AUTORE, I COLLABORATORI O I DISTRIBUTORI DEL SOFTWARE POTRANNO ESSERE RITENUTI RESPONSABILI VERSO DI TE O VERSO TERZI PER QUALSIASI DANNO DIRETTO, INDIRETTO, INCIDENTALE, SPECIALE, ESEMPLARE, PUNITIVO O CONSEQUENZIALE (INCLUSI, SENZA LIMITAZIONE, PERDITA O CORRUZIONE DI DATI O DEL DATABASE, PERDITA DI PROFITTI, DI AVVIAMENTO O DI OPPORTUNITÀ, INTERRUZIONE DI ATTIVITÀ, GUASTI, SURRISCALDAMENTO O MALFUNZIONAMENTI DEL PC, COSTI DI SERVIZI SOSTITUTIVI, SANZIONI, PRETESE DI TERZI) DERIVANTI DALL'USO O DALL'IMPOSSIBILITÀ DI USARE IL SOFTWARE, DA DECISIONI PRESE SULLA BASE DEI SUOI RISULTATI, DALL'APERTURA DI FILE DANNEGGIATI O MALEVOLI DURANTE L'INDICIZZAZIONE, DALL'USO DI STRUMENTI DI TERZE PARTI SCARICATI O AVVIATI DAL PROGRAMMA (modelli OCR, ExifTool, 7-Zip, Microsoft Office) O DAL RIPRISTINO DI COPIE DI SICUREZZA, ANCHE SE AVVISATI DELLA POSSIBILITÀ DI TALI DANNI E QUALUNQUE SIA IL TITOLO DELLA PRETESA (CONTRATTO, ILLECITO, RESPONSABILITÀ OGGETTIVA O ALTRO). Nei paesi che non ammettono l'esclusione totale, la responsabilità è limitata nella misura massima consentita.

5. DATI, PRIVACY E SITI DI TERZE PARTI
Il software funziona in locale e non invia dati all'autore né ad altri: il testo dei documenti, il database e le ricerche restano sul tuo PC. Si collega a Internet solo quando scegli di scaricare strumenti facoltativi (modelli OCR, ExifTool, 7-Zip) dai rispettivi siti o mirror, che ricevono le normali informazioni di una connessione (come l'indirizzo IP) e sono soggetti ai loro termini. L'autore non è responsabile per questi siti, per la loro disponibilità né per il contenuto dei file che distribuiscono. Il database può essere letto da chiunque abbia accesso al tuo PC o alle tue copie di sicurezza: proteggilo come proteggeresti i documenti originali.

6. LICENZE E COMPONENTI DI TERZE PARTI
Il software è distribuito sotto licenza GNU AGPL v3 con i termini aggiuntivi del file NOTICE (file LICENSE e NOTICE); le licenze delle componenti di terze parti (PyMuPDF, RapidOCR e modelli PaddleOCR, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip e altri) sono in THIRD_PARTY_NOTICES.md e nella cartella LICENSES. Sei tenuto a rispettarle. Questi termini si aggiungono alla AGPL e non ne limitano i diritti di copia, modifica e ridistribuzione del codice; le clausole 3 e 4 riproducono e integrano le sezioni 15 e 16 della AGPL v3.

7. MODIFICHE, LEGGE APPLICABILE E CLAUSOLE FINALI
Questi termini possono essere aggiornati nelle versioni successive del software; alla prima apertura di una versione con termini nuovi ti verranno riproposti. Se una clausola fosse invalida, le altre restano efficaci. Salvo norme inderogabili a tua tutela, si applica la legge italiana. Il software non è destinato a minori né a usi in cui un malfunzionamento potrebbe causare danni a persone o cose.

Premendo "Accetto" confermi di avere letto e accettato tutti i punti precedenti, di indicizzare con DocIndexer solo file che hai il diritto di trattare e di assumerti ogni responsabilità per l'uso che ne fai.
"""

_EN = """\
TERMS OF USE AND DISCLAIMER OF LIABILITY — DocIndexer
Version {v} of {d}

Please read carefully. By pressing "I accept" you declare that you have read, understood and fully accepted these terms. If you do not accept them, press "I decline": the program closes and you may not use it.

1. WHAT DOCINDEXER IS
DocIndexer is a Windows program that reads the files in the folders you choose (documents, spreadsheets, presentations, PDFs, images, e-mail, archives, databases and more), extracts their text, also through optical character recognition (OCR), and keeps it in a local database so that you can search it. It can start with Windows and work in the background, using the time when the PC is idle within the CPU and temperature limits you set. Files stay where they are: the program does not modify, move or delete them.

2. PERMITTED USE AND USER RESPONSIBILITY
You may index only files and folders that belong to you or that you have the right to consult and process. You alone are responsible for: (a) verifying that your use is lawful, in particular when the files contain other people's personal data, work documents or information covered by secrecy or confidentiality; (b) obtaining every consent or authorisation required by law, including the rules on personal-data protection; (c) safeguarding the database, backups, exports and previews, which contain the text of your documents and may therefore contain personal data, credentials or confidential information. Using the software to collect or consult other people's data without authorisation or for any unlawful purpose is forbidden. The author does not and cannot control how you use it.

3. NO WARRANTY ("AS IS")
TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE SOFTWARE IS PROVIDED "AS IS" AND "AS AVAILABLE", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT, ACCURACY, AVAILABILITY AND FREEDOM FROM ERRORS. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE SOFTWARE IS WITH YOU. SHOULD THE SOFTWARE PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION. In particular there is no guarantee that: the extracted text and the OCR results are complete or exact; the search finds every document that contains a term; the detection of language, duplicates and metadata is correct; the CPU and temperature limits are always respected or protect the hardware; the program does not slow down the PC or interfere with other programs; the software is free of vulnerabilities. Do not use DocIndexer as the only tool for legal, investigative, medical or financial decisions: always check the original document.

4. LIMITATION OF LIABILITY
IN NO EVENT, EXCEPT WHERE MANDATORY LAW PROVIDES OTHERWISE, SHALL THE AUTHOR, CONTRIBUTORS OR DISTRIBUTORS OF THE SOFTWARE BE LIABLE TO YOU OR TO ANY THIRD PARTY FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE OR CONSEQUENTIAL DAMAGES (INCLUDING, WITHOUT LIMITATION, LOSS OR CORRUPTION OF DATA OR OF THE DATABASE, LOSS OF PROFITS, GOODWILL OR OPPORTUNITIES, BUSINESS INTERRUPTION, FAILURE, OVERHEATING OR MALFUNCTION OF THE PC, COST OF SUBSTITUTE SERVICES, FINES, THIRD-PARTY CLAIMS) ARISING OUT OF THE USE OR INABILITY TO USE THE SOFTWARE, DECISIONS TAKEN ON THE BASIS OF ITS RESULTS, THE OPENING OF DAMAGED OR MALICIOUS FILES DURING INDEXING, THE USE OF THIRD-PARTY TOOLS DOWNLOADED OR LAUNCHED BY THE PROGRAM (OCR models, ExifTool, 7-Zip, Microsoft Office) OR THE RESTORING OF BACKUPS, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES AND WHATEVER THE LEGAL THEORY (CONTRACT, TORT, STRICT LIABILITY OR OTHERWISE). In jurisdictions that do not allow a total exclusion, liability is limited to the maximum extent permitted.

5. DATA, PRIVACY AND THIRD-PARTY SITES
The software runs locally and sends no data to the author or to anyone else: the text of your documents, the database and your searches stay on your PC. It connects to the Internet only when you choose to download optional tools (OCR models, ExifTool, 7-Zip) from their sites or mirrors, which receive the usual information of a connection (such as the IP address) and are subject to their own terms. The author is not responsible for these sites, their availability or the content of the files they distribute. The database can be read by anyone with access to your PC or to your backups: protect it as you would protect the original documents.

6. LICENCES AND THIRD-PARTY COMPONENTS
The software is distributed under the GNU AGPL v3 with the additional terms of the NOTICE file (files LICENSE and NOTICE); the licences of third-party components (PyMuPDF, RapidOCR and PaddleOCR models, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip and others) are in THIRD_PARTY_NOTICES.md and in the LICENSES folder. You must comply with them. These terms are in addition to the AGPL and do not limit its rights to copy, modify and redistribute the code; clauses 3 and 4 reproduce and supplement sections 15 and 16 of AGPL v3.

7. CHANGES, GOVERNING LAW AND FINAL CLAUSES
These terms may be updated in later versions of the software; on first launch of a version with new terms you will be asked again. If any clause is invalid, the others remain in force. Subject to mandatory rules protecting you, Italian law applies. The software is not intended for minors nor for uses in which a malfunction could cause injury to persons or damage to property.

By pressing "I accept" you confirm that you have read and accepted all the points above, that you index with DocIndexer only files you have the right to process, and that you take full responsibility for your use of it.
"""

_FR = """\
CONDITIONS D'UTILISATION ET EXCLUSION DE RESPONSABILITÉ — DocIndexer
Version {v} du {d}

Lisez attentivement. En appuyant sur « J'accepte », vous déclarez avoir lu, compris et accepté intégralement ces conditions. Si vous ne les acceptez pas, appuyez sur « Je refuse » : le programme se ferme et vous ne pouvez pas l'utiliser.

1. CE QU'EST DOCINDEXER
DocIndexer est un programme pour Windows qui lit les fichiers des dossiers que vous choisissez (documents, feuilles de calcul, présentations, PDF, images, courrier, archives, bases de données et autres), en extrait le texte, y compris par reconnaissance optique de caractères (OCR), et le conserve dans une base de données locale pour vous permettre de le rechercher. Il peut démarrer avec Windows et travailler en arrière-plan, en utilisant le temps où le PC est inactif dans les limites de processeur et de température que vous fixez. Les fichiers restent où ils sont : le programme ne les modifie pas, ne les déplace pas et ne les supprime pas.

2. USAGE AUTORISÉ ET RESPONSABILITÉ DE L'UTILISATEUR
Vous ne pouvez indexer que des fichiers et dossiers qui vous appartiennent ou que vous avez le droit de consulter et de traiter. Vous êtes seul responsable : (a) de vérifier que votre usage est licite, en particulier lorsque les fichiers contiennent des données personnelles d'autres personnes, des documents de travail ou des informations couvertes par le secret ou la confidentialité ; (b) d'obtenir tout consentement ou autorisation exigés par la loi, y compris les règles de protection des données personnelles ; (c) de protéger la base de données, les sauvegardes, les exports et les aperçus, qui contiennent le texte de vos documents et peuvent donc contenir des données personnelles, des identifiants ou des informations confidentielles. Il est interdit d'utiliser le logiciel pour collecter ou consulter les données d'autrui sans autorisation ou à toute fin illicite. L'auteur ne contrôle pas et ne peut pas contrôler l'usage que vous en faites.

3. ABSENCE DE GARANTIE (« EN L'ÉTAT »)
DANS TOUTE LA MESURE PERMISE PAR LA LOI APPLICABLE, LE LOGICIEL EST FOURNI « EN L'ÉTAT » ET « SELON DISPONIBILITÉ », SANS GARANTIE D'AUCUNE SORTE, EXPRESSE OU IMPLICITE, Y COMPRIS, SANS S'Y LIMITER, LES GARANTIES IMPLICITES DE QUALITÉ MARCHANDE, D'ADÉQUATION À UN USAGE PARTICULIER, D'ABSENCE DE CONTREFAÇON, D'EXACTITUDE, DE DISPONIBILITÉ ET D'ABSENCE D'ERREURS. VOUS ASSUMEZ L'INTÉGRALITÉ DU RISQUE QUANT À LA QUALITÉ ET AUX PERFORMANCES DU LOGICIEL. SI LE LOGICIEL S'AVÈRE DÉFECTUEUX, VOUS ASSUMEZ LE COÛT DE TOUTE ASSISTANCE, RÉPARATION OU CORRECTION. En particulier, il n'est pas garanti que : le texte extrait et les résultats de l'OCR soient complets ou exacts ; la recherche trouve tous les documents contenant un terme ; la détection de la langue, des doublons et des métadonnées soit correcte ; les limites de processeur et de température soient toujours respectées ou protègent le matériel ; le programme ne ralentisse pas le PC ni n'interfère avec d'autres programmes ; le logiciel soit exempt de vulnérabilités. N'utilisez pas DocIndexer comme seul outil pour des décisions juridiques, d'enquête, médicales ou financières : vérifiez toujours le document original.

4. EXCLUSION DE RESPONSABILITÉ
EN AUCUN CAS, SAUF DISPOSITION LÉGALE IMPÉRATIVE CONTRAIRE, L'AUTEUR, LES CONTRIBUTEURS OU LES DISTRIBUTEURS DU LOGICIEL NE POURRONT ÊTRE TENUS RESPONSABLES ENVERS VOUS OU ENVERS DES TIERS DE TOUT DOMMAGE DIRECT, INDIRECT, ACCESSOIRE, SPÉCIAL, EXEMPLAIRE, PUNITIF OU CONSÉCUTIF (Y COMPRIS, SANS LIMITATION, LA PERTE OU LA CORRUPTION DE DONNÉES OU DE LA BASE DE DONNÉES, LA PERTE DE PROFITS, DE CLIENTÈLE OU D'OPPORTUNITÉS, L'INTERRUPTION D'ACTIVITÉ, LA PANNE, LA SURCHAUFFE OU LE DYSFONCTIONNEMENT DU PC, LE COÛT DE SERVICES DE SUBSTITUTION, LES SANCTIONS, LES RÉCLAMATIONS DE TIERS) DÉCOULANT DE L'UTILISATION OU DE L'IMPOSSIBILITÉ D'UTILISER LE LOGICIEL, DE DÉCISIONS PRISES SUR LA BASE DE SES RÉSULTATS, DE L'OUVERTURE DE FICHIERS ENDOMMAGÉS OU MALVEILLANTS PENDANT L'INDEXATION, DE L'UTILISATION D'OUTILS TIERS TÉLÉCHARGÉS OU LANCÉS PAR LE PROGRAMME (modèles OCR, ExifTool, 7-Zip, Microsoft Office) OU DE LA RESTAURATION DE SAUVEGARDES, MÊME S'ILS ONT ÉTÉ INFORMÉS DE LA POSSIBILITÉ DE TELS DOMMAGES ET QUEL QUE SOIT LE FONDEMENT INVOQUÉ (CONTRAT, DÉLIT, RESPONSABILITÉ OBJECTIVE OU AUTRE). Dans les pays qui n'admettent pas une exclusion totale, la responsabilité est limitée dans la mesure maximale permise.

5. DONNÉES, VIE PRIVÉE ET SITES TIERS
Le logiciel fonctionne en local et n'envoie aucune donnée à l'auteur ni à personne d'autre : le texte de vos documents, la base de données et vos recherches restent sur votre PC. Il se connecte à Internet uniquement lorsque vous choisissez de télécharger des outils facultatifs (modèles OCR, ExifTool, 7-Zip) depuis leurs sites ou miroirs, qui reçoivent les informations habituelles d'une connexion (comme l'adresse IP) et sont soumis à leurs propres conditions. L'auteur n'est pas responsable de ces sites, de leur disponibilité ni du contenu des fichiers qu'ils distribuent. La base de données peut être lue par toute personne ayant accès à votre PC ou à vos sauvegardes : protégez-la comme vous protégeriez les documents originaux.

6. LICENCES ET COMPOSANTS TIERS
Le logiciel est distribué sous licence GNU AGPL v3 avec les conditions supplémentaires du fichier NOTICE (fichiers LICENSE et NOTICE) ; les licences des composants tiers (PyMuPDF, RapidOCR et modèles PaddleOCR, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip et autres) figurent dans THIRD_PARTY_NOTICES.md et dans le dossier LICENSES. Vous êtes tenu de les respecter. Ces conditions s'ajoutent à l'AGPL et ne limitent pas ses droits de copie, de modification et de redistribution du code ; les clauses 3 et 4 reproduisent et complètent les sections 15 et 16 de l'AGPL v3.

7. MODIFICATIONS, LOI APPLICABLE ET CLAUSES FINALES
Ces conditions peuvent être mises à jour dans les versions ultérieures du logiciel ; à la première ouverture d'une version comportant de nouvelles conditions, elles vous seront soumises de nouveau. Si une clause est invalide, les autres restent en vigueur. Sous réserve des règles impératives vous protégeant, la loi italienne s'applique. Le logiciel n'est pas destiné aux mineurs ni aux usages dans lesquels un dysfonctionnement pourrait causer des dommages aux personnes ou aux biens.

En appuyant sur « J'accepte », vous confirmez avoir lu et accepté tous les points précédents, n'indexer avec DocIndexer que des fichiers que vous avez le droit de traiter, et assumer l'entière responsabilité de l'usage que vous en faites.
"""

_DE = """\
NUTZUNGSBEDINGUNGEN UND HAFTUNGSAUSSCHLUSS — DocIndexer
Version {v} vom {d}

Bitte sorgfältig lesen. Mit "Ich akzeptiere" erklären Sie, diese Bedingungen gelesen, verstanden und vollständig akzeptiert zu haben. Wenn Sie sie nicht akzeptieren, drücken Sie "Ich lehne ab": das Programm wird beendet und Sie dürfen es nicht verwenden.

1. WAS DOCINDEXER IST
DocIndexer ist ein Windows-Programm, das die Dateien der von Ihnen gewählten Ordner liest (Dokumente, Tabellen, Präsentationen, PDFs, Bilder, E-Mails, Archive, Datenbanken und mehr), ihren Text extrahiert, auch mit optischer Zeichenerkennung (OCR), und ihn in einer lokalen Datenbank speichert, damit Sie ihn durchsuchen können. Es kann mit Windows starten und im Hintergrund arbeiten, wobei es die Leerlaufzeit des PCs innerhalb der von Ihnen festgelegten CPU- und Temperaturgrenzen nutzt. Die Dateien bleiben, wo sie sind: das Programm ändert, verschiebt oder löscht sie nicht.

2. ZULÄSSIGE NUTZUNG UND VERANTWORTUNG DES NUTZERS
Sie dürfen nur Dateien und Ordner indizieren, die Ihnen gehören oder die Sie einsehen und verarbeiten dürfen. Sie allein sind verantwortlich dafür: (a) zu prüfen, dass Ihre Nutzung rechtmäßig ist, insbesondere wenn die Dateien personenbezogene Daten anderer, Arbeitsdokumente oder geheime bzw. vertrauliche Informationen enthalten; (b) jede gesetzlich erforderliche Einwilligung oder Genehmigung einzuholen, einschließlich der Datenschutzvorschriften; (c) die Datenbank, Sicherungskopien, Exporte und Vorschauen sicher zu verwahren, die den Text Ihrer Dokumente enthalten und daher personenbezogene Daten, Zugangsdaten oder vertrauliche Informationen enthalten können. Es ist verboten, die Software zu verwenden, um Daten anderer ohne Erlaubnis zu sammeln oder einzusehen, oder für irgendeinen rechtswidrigen Zweck. Der Autor kontrolliert Ihre Nutzung nicht und kann sie nicht kontrollieren.

3. KEINE GEWÄHRLEISTUNG („AS IS")
SOWEIT NACH ANWENDBAREM RECHT ZULÄSSIG, WIRD DIE SOFTWARE „WIE BESEHEN" UND „WIE VERFÜGBAR" OHNE JEGLICHE AUSDRÜCKLICHE ODER STILLSCHWEIGENDE GEWÄHRLEISTUNG BEREITGESTELLT, EINSCHLIESSLICH, ABER NICHT BESCHRÄNKT AUF DIE STILLSCHWEIGENDEN GEWÄHRLEISTUNGEN DER MARKTGÄNGIGKEIT, DER EIGNUNG FÜR EINEN BESTIMMTEN ZWECK, DER NICHTVERLETZUNG VON RECHTEN DRITTER, DER GENAUIGKEIT, DER VERFÜGBARKEIT UND DER FEHLERFREIHEIT. DAS GESAMTE RISIKO HINSICHTLICH QUALITÄT UND LEISTUNG DER SOFTWARE LIEGT BEI IHNEN. SOLLTE SICH DIE SOFTWARE ALS FEHLERHAFT ERWEISEN, TRAGEN SIE DIE KOSTEN ALLER ERFORDERLICHEN WARTUNGS-, REPARATUR- ODER KORREKTURMASSNAHMEN. Insbesondere wird nicht garantiert, dass: der extrahierte Text und die OCR-Ergebnisse vollständig oder exakt sind; die Suche jedes Dokument findet, das einen Begriff enthält; die Erkennung von Sprache, Duplikaten und Metadaten korrekt ist; die CPU- und Temperaturgrenzen immer eingehalten werden oder die Hardware schützen; das Programm den PC nicht verlangsamt oder andere Programme nicht stört; die Software frei von Schwachstellen ist. Verwenden Sie DocIndexer nicht als einziges Werkzeug für rechtliche, ermittlungsbezogene, medizinische oder finanzielle Entscheidungen: prüfen Sie immer das Originaldokument.

4. HAFTUNGSAUSSCHLUSS
IN KEINEM FALL, SOFERN NICHT ZWINGENDES RECHT ETWAS ANDERES VORSCHREIBT, HAFTEN DER AUTOR, MITWIRKENDE ODER VERTREIBER DER SOFTWARE IHNEN ODER DRITTEN GEGENÜBER FÜR DIREKTE, INDIREKTE, ZUFÄLLIGE, BESONDERE, EXEMPLARISCHE, STRAF- ODER FOLGESCHÄDEN (EINSCHLIESSLICH, OHNE EINSCHRÄNKUNG, VERLUST ODER BESCHÄDIGUNG VON DATEN ODER DER DATENBANK, ENTGANGENER GEWINN, VERLUST VON GESCHÄFTSWERT ODER CHANCEN, BETRIEBSUNTERBRECHUNG, AUSFALL, ÜBERHITZUNG ODER FEHLFUNKTION DES PCS, KOSTEN FÜR ERSATZDIENSTE, BUSSGELDER, ANSPRÜCHE DRITTER), DIE SICH AUS DER NUTZUNG ODER DER UNMÖGLICHKEIT DER NUTZUNG DER SOFTWARE, AUS ENTSCHEIDUNGEN AUF GRUNDLAGE IHRER ERGEBNISSE, AUS DEM ÖFFNEN BESCHÄDIGTER ODER SCHÄDLICHER DATEIEN WÄHREND DER INDIZIERUNG, AUS DER NUTZUNG VON DURCH DAS PROGRAMM HERUNTERGELADENEN ODER GESTARTETEN WERKZEUGEN DRITTER (OCR-Modelle, ExifTool, 7-Zip, Microsoft Office) ODER AUS DER WIEDERHERSTELLUNG VON SICHERUNGSKOPIEN ERGEBEN, SELBST WENN AUF DIE MÖGLICHKEIT SOLCHER SCHÄDEN HINGEWIESEN WURDE UND UNABHÄNGIG VON DER RECHTSGRUNDLAGE (VERTRAG, UNERLAUBTE HANDLUNG, GEFÄHRDUNGSHAFTUNG ODER SONSTIGES). In Rechtsordnungen, die einen vollständigen Ausschluss nicht zulassen, ist die Haftung im größtmöglichen zulässigen Umfang beschränkt.

5. DATEN, DATENSCHUTZ UND WEBSITES DRITTER
Die Software läuft lokal und sendet keine Daten an den Autor oder an andere: der Text Ihrer Dokumente, die Datenbank und Ihre Suchen bleiben auf Ihrem PC. Sie verbindet sich nur dann mit dem Internet, wenn Sie optionale Werkzeuge (OCR-Modelle, ExifTool, 7-Zip) von deren Websites oder Spiegelservern herunterladen; diese erhalten die üblichen Verbindungsinformationen (etwa die IP-Adresse) und unterliegen ihren eigenen Bedingungen. Der Autor ist nicht verantwortlich für diese Websites, ihre Verfügbarkeit oder den Inhalt der von ihnen verteilten Dateien. Die Datenbank kann von jedem gelesen werden, der Zugriff auf Ihren PC oder Ihre Sicherungskopien hat: schützen Sie sie so, wie Sie die Originaldokumente schützen würden.

6. LIZENZEN UND KOMPONENTEN DRITTER
Die Software wird unter der GNU AGPL v3 mit den zusätzlichen Bedingungen der Datei NOTICE vertrieben (Dateien LICENSE und NOTICE); die Lizenzen der Komponenten Dritter (PyMuPDF, RapidOCR und PaddleOCR-Modelle, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip und andere) stehen in THIRD_PARTY_NOTICES.md und im Ordner LICENSES. Sie sind verpflichtet, diese einzuhalten. Diese Bedingungen ergänzen die AGPL und schränken deren Rechte zum Kopieren, Ändern und Weiterverbreiten des Codes nicht ein; die Klauseln 3 und 4 geben die Abschnitte 15 und 16 der AGPL v3 wieder und ergänzen sie.

7. ÄNDERUNGEN, ANWENDBARES RECHT UND SCHLUSSBESTIMMUNGEN
Diese Bedingungen können in späteren Versionen der Software aktualisiert werden; beim ersten Start einer Version mit neuen Bedingungen werden sie erneut vorgelegt. Sollte eine Klausel unwirksam sein, bleiben die übrigen wirksam. Vorbehaltlich zwingender Vorschriften zu Ihrem Schutz gilt italienisches Recht. Die Software ist nicht für Minderjährige und nicht für Anwendungen bestimmt, bei denen eine Fehlfunktion Personen- oder Sachschäden verursachen könnte.

Mit "Ich akzeptiere" bestätigen Sie, alle vorstehenden Punkte gelesen und akzeptiert zu haben, mit DocIndexer nur Dateien zu indizieren, die Sie verarbeiten dürfen, und die volle Verantwortung für Ihre Nutzung zu übernehmen.
"""

_ES = """\
TÉRMINOS DE USO Y EXCLUSIÓN DE RESPONSABILIDAD — DocIndexer
Versión {v} de {d}

Lea con atención. Al pulsar «Acepto» declara haber leído, comprendido y aceptado íntegramente estos términos. Si no los acepta, pulse «Rechazo»: el programa se cierra y no puede usarlo.

1. QUÉ ES DOCINDEXER
DocIndexer es un programa para Windows que lee los archivos de las carpetas que usted elige (documentos, hojas de cálculo, presentaciones, PDF, imágenes, correo, archivos comprimidos, bases de datos y más), extrae su texto, también mediante reconocimiento óptico de caracteres (OCR), y lo guarda en una base de datos local para que pueda buscarlo. Puede iniciarse con Windows y trabajar en segundo plano, aprovechando el tiempo en que el PC está inactivo dentro de los límites de CPU y temperatura que usted fija. Los archivos se quedan donde están: el programa no los modifica, no los mueve y no los borra.

2. USO PERMITIDO Y RESPONSABILIDAD DEL USUARIO
Solo puede indexar archivos y carpetas que le pertenecen o que tiene derecho a consultar y tratar. Usted es el único responsable de: (a) comprobar que el uso que hace es lícito, en particular cuando los archivos contienen datos personales de otras personas, documentos de trabajo o información amparada por secreto o confidencialidad; (b) obtener todo consentimiento o autorización exigidos por la ley, incluidas las normas de protección de datos personales; (c) custodiar la base de datos, las copias de seguridad, las exportaciones y las vistas previas, que contienen el texto de sus documentos y pueden por tanto contener datos personales, credenciales o información confidencial. Está prohibido usar el software para recopilar o consultar datos ajenos sin autorización o para cualquier fin ilícito. El autor no controla ni puede controlar el uso que usted hace.

3. SIN GARANTÍA («TAL CUAL»)
EN LA MÁXIMA MEDIDA PERMITIDA POR LA LEY APLICABLE, EL SOFTWARE SE SUMINISTRA «TAL CUAL» Y «SEGÚN DISPONIBILIDAD», SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O IMPLÍCITA, INCLUIDAS, A TÍTULO ENUNCIATIVO Y NO LIMITATIVO, LAS GARANTÍAS IMPLÍCITAS DE COMERCIABILIDAD, IDONEIDAD PARA UN FIN DETERMINADO, NO INFRACCIÓN, EXACTITUD, DISPONIBILIDAD Y AUSENCIA DE ERRORES. TODO EL RIESGO EN CUANTO A LA CALIDAD Y EL RENDIMIENTO DEL SOFTWARE ES SUYO. SI EL SOFTWARE RESULTA DEFECTUOSO, USTED ASUME EL COSTE DE TODA ASISTENCIA, REPARACIÓN O CORRECCIÓN. En particular no se garantiza que: el texto extraído y los resultados del OCR sean completos o exactos; la búsqueda encuentre todos los documentos que contienen un término; la detección del idioma, de los duplicados y de los metadatos sea correcta; los límites de CPU y temperatura se respeten siempre o protejan el hardware; el programa no ralentice el PC ni interfiera con otros programas; el software esté libre de vulnerabilidades. No use DocIndexer como única herramienta para decisiones legales, de investigación, médicas o económicas: compruebe siempre el documento original.

4. EXCLUSIÓN DE RESPONSABILIDAD
EN NINGÚN CASO, SALVO QUE LA LEY IMPERATIVA DISPONGA OTRA COSA, EL AUTOR, LOS COLABORADORES O LOS DISTRIBUIDORES DEL SOFTWARE SERÁN RESPONSABLES ANTE USTED O ANTE TERCEROS DE NINGÚN DAÑO DIRECTO, INDIRECTO, INCIDENTAL, ESPECIAL, EJEMPLAR, PUNITIVO O CONSECUENTE (INCLUIDOS, SIN LIMITACIÓN, PÉRDIDA O CORRUPCIÓN DE DATOS O DE LA BASE DE DATOS, PÉRDIDA DE BENEFICIOS, DE FONDO DE COMERCIO O DE OPORTUNIDADES, INTERRUPCIÓN DE LA ACTIVIDAD, AVERÍA, SOBRECALENTAMIENTO O MAL FUNCIONAMIENTO DEL PC, COSTE DE SERVICIOS SUSTITUTIVOS, SANCIONES, RECLAMACIONES DE TERCEROS) DERIVADO DEL USO O DE LA IMPOSIBILIDAD DE USAR EL SOFTWARE, DE DECISIONES TOMADAS SOBRE LA BASE DE SUS RESULTADOS, DE LA APERTURA DE ARCHIVOS DAÑADOS O MALICIOSOS DURANTE LA INDEXACIÓN, DEL USO DE HERRAMIENTAS DE TERCEROS DESCARGADAS O LANZADAS POR EL PROGRAMA (modelos OCR, ExifTool, 7-Zip, Microsoft Office) O DE LA RESTAURACIÓN DE COPIAS DE SEGURIDAD, AUNQUE SE HAYA ADVERTIDO DE LA POSIBILIDAD DE TALES DAÑOS Y CUALQUIERA QUE SEA EL FUNDAMENTO (CONTRATO, RESPONSABILIDAD EXTRACONTRACTUAL, OBJETIVA U OTRO). En los países que no admiten la exclusión total, la responsabilidad queda limitada en la máxima medida permitida.

5. DATOS, PRIVACIDAD Y SITIOS DE TERCEROS
El software funciona en local y no envía datos al autor ni a nadie más: el texto de sus documentos, la base de datos y sus búsquedas se quedan en su PC. Solo se conecta a Internet cuando usted decide descargar herramientas opcionales (modelos OCR, ExifTool, 7-Zip) desde sus sitios o espejos, que reciben la información habitual de una conexión (como la dirección IP) y están sujetos a sus propios términos. El autor no es responsable de esos sitios, de su disponibilidad ni del contenido de los archivos que distribuyen. La base de datos puede ser leída por cualquiera que tenga acceso a su PC o a sus copias de seguridad: protéjala como protegería los documentos originales.

6. LICENCIAS Y COMPONENTES DE TERCEROS
El software se distribuye bajo licencia GNU AGPL v3 con los términos adicionales del archivo NOTICE (archivos LICENSE y NOTICE); las licencias de los componentes de terceros (PyMuPDF, RapidOCR y modelos PaddleOCR, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip y otros) están en THIRD_PARTY_NOTICES.md y en la carpeta LICENSES. Está obligado a respetarlas. Estos términos se añaden a la AGPL y no limitan sus derechos de copia, modificación y redistribución del código; las cláusulas 3 y 4 reproducen y complementan las secciones 15 y 16 de la AGPL v3.

7. MODIFICACIONES, LEY APLICABLE Y CLÁUSULAS FINALES
Estos términos pueden actualizarse en versiones posteriores del software; en la primera apertura de una versión con términos nuevos se le volverán a presentar. Si alguna cláusula fuera inválida, las demás seguirán vigentes. Salvo normas imperativas que le protejan, se aplica la ley italiana. El software no está destinado a menores ni a usos en los que un mal funcionamiento pudiera causar daños a personas o bienes.

Al pulsar «Acepto» confirma haber leído y aceptado todos los puntos anteriores, indexar con DocIndexer solo archivos que tiene derecho a tratar, y asumir toda la responsabilidad por el uso que haga de él.
"""

_EL = """\
ΟΡΟΙ ΧΡΗΣΗΣ ΚΑΙ ΑΠΟΠΟΙΗΣΗ ΕΥΘΥΝΗΣ — DocIndexer
Έκδοση {v} της {d}

Διαβάστε προσεκτικά. Πατώντας «Αποδέχομαι» δηλώνετε ότι διαβάσατε, κατανοήσατε και αποδεχτήκατε πλήρως τους παρόντες όρους. Αν δεν τους αποδέχεστε, πατήστε «Απορρίπτω»: το πρόγραμμα κλείνει και δεν μπορείτε να το χρησιμοποιήσετε.

1. ΤΙ ΕΙΝΑΙ ΤΟ DOCINDEXER
Το DocIndexer είναι πρόγραμμα για Windows που διαβάζει τα αρχεία των φακέλων που επιλέγετε (έγγραφα, υπολογιστικά φύλλα, παρουσιάσεις, PDF, εικόνες, αλληλογραφία, συμπιεσμένα αρχεία, βάσεις δεδομένων και άλλα), εξάγει το κείμενό τους, και με οπτική αναγνώριση χαρακτήρων (OCR), και το διατηρεί σε μια τοπική βάση δεδομένων ώστε να μπορείτε να το αναζητάτε. Μπορεί να ξεκινά μαζί με τα Windows και να εργάζεται στο παρασκήνιο, αξιοποιώντας τον χρόνο αδράνειας του υπολογιστή εντός των ορίων CPU και θερμοκρασίας που ορίζετε. Τα αρχεία μένουν εκεί που είναι: το πρόγραμμα δεν τα τροποποιεί, δεν τα μετακινεί και δεν τα διαγράφει.

2. ΕΠΙΤΡΕΠΟΜΕΝΗ ΧΡΗΣΗ ΚΑΙ ΕΥΘΥΝΗ ΤΟΥ ΧΡΗΣΤΗ
Μπορείτε να ευρετηριάζετε μόνο αρχεία και φακέλους που σας ανήκουν ή που έχετε δικαίωμα να συμβουλεύεστε και να επεξεργάζεστε. Είστε ο μόνος υπεύθυνος για: (α) να ελέγξετε ότι η χρήση σας είναι νόμιμη, ιδίως όταν τα αρχεία περιέχουν προσωπικά δεδομένα άλλων, έγγραφα εργασίας ή πληροφορίες που καλύπτονται από απόρρητο ή εμπιστευτικότητα· (β) να λάβετε κάθε συγκατάθεση ή άδεια που απαιτεί ο νόμος, συμπεριλαμβανομένων των κανόνων για την προστασία των προσωπικών δεδομένων· (γ) να φυλάσσετε τη βάση δεδομένων, τα αντίγραφα ασφαλείας, τις εξαγωγές και τις προεπισκοπήσεις, που περιέχουν το κείμενο των εγγράφων σας και επομένως μπορεί να περιέχουν προσωπικά δεδομένα, διαπιστευτήρια ή εμπιστευτικές πληροφορίες. Απαγορεύεται η χρήση του λογισμικού για τη συλλογή ή την πρόσβαση σε δεδομένα τρίτων χωρίς άδεια ή για οποιονδήποτε παράνομο σκοπό. Ο δημιουργός δεν ελέγχει και δεν μπορεί να ελέγξει τη χρήση που κάνετε.

3. ΚΑΜΙΑ ΕΓΓΥΗΣΗ («ΩΣ ΕΧΕΙ»)
ΣΤΟ ΜΕΓΙΣΤΟ ΒΑΘΜΟ ΠΟΥ ΕΠΙΤΡΕΠΕΙ Ο ΙΣΧΥΩΝ ΝΟΜΟΣ, ΤΟ ΛΟΓΙΣΜΙΚΟ ΠΑΡΕΧΕΤΑΙ «ΩΣ ΕΧΕΙ» ΚΑΙ «ΩΣ ΔΙΑΘΕΣΙΜΟ», ΧΩΡΙΣ ΚΑΜΙΑ ΕΓΓΥΗΣΗ, ΡΗΤΗ Ή ΣΙΩΠΗΡΗ, ΣΥΜΠΕΡΙΛΑΜΒΑΝΟΜΕΝΩΝ, ΕΝΔΕΙΚΤΙΚΑ, ΤΩΝ ΣΙΩΠΗΡΩΝ ΕΓΓΥΗΣΕΩΝ ΕΜΠΟΡΕΥΣΙΜΟΤΗΤΑΣ, ΚΑΤΑΛΛΗΛΟΤΗΤΑΣ ΓΙΑ ΣΥΓΚΕΚΡΙΜΕΝΟ ΣΚΟΠΟ, ΜΗ ΠΡΟΣΒΟΛΗΣ ΔΙΚΑΙΩΜΑΤΩΝ ΤΡΙΤΩΝ, ΑΚΡΙΒΕΙΑΣ, ΔΙΑΘΕΣΙΜΟΤΗΤΑΣ ΚΑΙ ΑΠΟΥΣΙΑΣ ΣΦΑΛΜΑΤΩΝ. ΟΛΟΣ Ο ΚΙΝΔΥΝΟΣ ΩΣ ΠΡΟΣ ΤΗΝ ΠΟΙΟΤΗΤΑ ΚΑΙ ΤΗΝ ΑΠΟΔΟΣΗ ΤΟΥ ΛΟΓΙΣΜΙΚΟΥ ΒΑΡΥΝΕΙ ΕΣΑΣ. ΑΝ ΤΟ ΛΟΓΙΣΜΙΚΟ ΑΠΟΔΕΙΧΘΕΙ ΕΛΑΤΤΩΜΑΤΙΚΟ, ΑΝΑΛΑΜΒΑΝΕΤΕ ΤΟ ΚΟΣΤΟΣ ΚΑΘΕ ΑΠΑΡΑΙΤΗΤΗΣ ΥΠΟΣΤΗΡΙΞΗΣ, ΕΠΙΣΚΕΥΗΣ Ή ΔΙΟΡΘΩΣΗΣ. Ειδικότερα δεν εγγυάται ότι: το εξαγόμενο κείμενο και τα αποτελέσματα του OCR είναι πλήρη ή ακριβή· η αναζήτηση βρίσκει όλα τα έγγραφα που περιέχουν έναν όρο· η αναγνώριση γλώσσας, διπλοτύπων και μεταδεδομένων είναι σωστή· τα όρια CPU και θερμοκρασίας τηρούνται πάντα ή προστατεύουν το υλικό· το πρόγραμμα δεν επιβραδύνει τον υπολογιστή ούτε παρεμβαίνει σε άλλα προγράμματα· το λογισμικό είναι απαλλαγμένο από ευπάθειες. Μη χρησιμοποιείτε το DocIndexer ως το μόνο εργαλείο για νομικές, ερευνητικές, ιατρικές ή οικονομικές αποφάσεις: ελέγχετε πάντα το πρωτότυπο έγγραφο.

4. ΠΕΡΙΟΡΙΣΜΟΣ ΕΥΘΥΝΗΣ
ΣΕ ΚΑΜΙΑ ΠΕΡΙΠΤΩΣΗ, ΕΚΤΟΣ ΑΝ ΑΛΛΙΩΣ ΟΡΙΖΕΙ ΑΝΑΓΚΑΣΤΙΚΟ ΔΙΚΑΙΟ, Ο ΔΗΜΙΟΥΡΓΟΣ, ΟΙ ΣΥΝΕΡΓΑΤΕΣ Ή ΟΙ ΔΙΑΝΟΜΕΙΣ ΤΟΥ ΛΟΓΙΣΜΙΚΟΥ ΔΕΝ ΕΥΘΥΝΟΝΤΑΙ ΕΝΑΝΤΙ ΣΑΣ Ή ΕΝΑΝΤΙ ΤΡΙΤΩΝ ΓΙΑ ΟΠΟΙΑΔΗΠΟΤΕ ΑΜΕΣΗ, ΕΜΜΕΣΗ, ΤΥΧΑΙΑ, ΕΙΔΙΚΗ, ΠΑΡΑΔΕΙΓΜΑΤΙΚΗ, ΤΙΜΩΡΗΤΙΚΗ Ή ΑΠΟΘΕΤΙΚΗ ΖΗΜΙΑ (ΣΥΜΠΕΡΙΛΑΜΒΑΝΟΜΕΝΩΝ, ΧΩΡΙΣ ΠΕΡΙΟΡΙΣΜΟ, ΤΗΣ ΑΠΩΛΕΙΑΣ Ή ΑΛΛΟΙΩΣΗΣ ΔΕΔΟΜΕΝΩΝ Ή ΤΗΣ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ, ΑΠΩΛΕΙΑΣ ΚΕΡΔΩΝ, ΦΗΜΗΣ Ή ΕΥΚΑΙΡΙΩΝ, ΔΙΑΚΟΠΗΣ ΔΡΑΣΤΗΡΙΟΤΗΤΑΣ, ΒΛΑΒΗΣ, ΥΠΕΡΘΕΡΜΑΝΣΗΣ Ή ΔΥΣΛΕΙΤΟΥΡΓΙΑΣ ΤΟΥ ΥΠΟΛΟΓΙΣΤΗ, ΚΟΣΤΟΥΣ ΥΠΗΡΕΣΙΩΝ ΥΠΟΚΑΤΑΣΤΑΣΗΣ, ΠΡΟΣΤΙΜΩΝ, ΑΞΙΩΣΕΩΝ ΤΡΙΤΩΝ) ΠΟΥ ΠΡΟΚΥΠΤΕΙ ΑΠΟ ΤΗ ΧΡΗΣΗ Ή ΤΗΝ ΑΔΥΝΑΜΙΑ ΧΡΗΣΗΣ ΤΟΥ ΛΟΓΙΣΜΙΚΟΥ, ΑΠΟ ΑΠΟΦΑΣΕΙΣ ΠΟΥ ΛΗΦΘΗΚΑΝ ΜΕ ΒΑΣΗ ΤΑ ΑΠΟΤΕΛΕΣΜΑΤΑ ΤΟΥ, ΑΠΟ ΤΟ ΑΝΟΙΓΜΑ ΚΑΤΕΣΤΡΑΜΜΕΝΩΝ Ή ΚΑΚΟΒΟΥΛΩΝ ΑΡΧΕΙΩΝ ΚΑΤΑ ΤΗΝ ΕΥΡΕΤΗΡΙΑΣΗ, ΑΠΟ ΤΗ ΧΡΗΣΗ ΕΡΓΑΛΕΙΩΝ ΤΡΙΤΩΝ ΠΟΥ ΚΑΤΕΒΑΖΕΙ Ή ΕΚΚΙΝΕΙ ΤΟ ΠΡΟΓΡΑΜΜΑ (μοντέλα OCR, ExifTool, 7-Zip, Microsoft Office) Ή ΑΠΟ ΤΗΝ ΕΠΑΝΑΦΟΡΑ ΑΝΤΙΓΡΑΦΩΝ ΑΣΦΑΛΕΙΑΣ, ΑΚΟΜΗ ΚΑΙ ΑΝ ΕΙΧΑΝ ΕΝΗΜΕΡΩΘΕΙ ΓΙΑ ΤΗΝ ΠΙΘΑΝΟΤΗΤΑ ΤΕΤΟΙΩΝ ΖΗΜΙΩΝ ΚΑΙ ΟΠΟΙΑΔΗΠΟΤΕ ΚΑΙ ΑΝ ΕΙΝΑΙ Η ΝΟΜΙΚΗ ΒΑΣΗ (ΣΥΜΒΑΣΗ, ΑΔΙΚΟΠΡΑΞΙΑ, ΑΝΤΙΚΕΙΜΕΝΙΚΗ ΕΥΘΥΝΗ Ή ΑΛΛΗ). Στις χώρες που δεν επιτρέπουν πλήρη αποκλεισμό, η ευθύνη περιορίζεται στον μέγιστο επιτρεπόμενο βαθμό.

5. ΔΕΔΟΜΕΝΑ, ΙΔΙΩΤΙΚΟΤΗΤΑ ΚΑΙ ΙΣΤΟΤΟΠΟΙ ΤΡΙΤΩΝ
Το λογισμικό λειτουργεί τοπικά και δεν στέλνει δεδομένα στον δημιουργό ούτε σε κανέναν άλλον: το κείμενο των εγγράφων σας, η βάση δεδομένων και οι αναζητήσεις σας μένουν στον υπολογιστή σας. Συνδέεται στο Διαδίκτυο μόνο όταν επιλέγετε να κατεβάσετε προαιρετικά εργαλεία (μοντέλα OCR, ExifTool, 7-Zip) από τους ιστοτόπους ή τους καθρέφτες τους, οι οποίοι λαμβάνουν τις συνήθεις πληροφορίες μιας σύνδεσης (όπως τη διεύθυνση IP) και υπόκεινται στους δικούς τους όρους. Ο δημιουργός δεν ευθύνεται για αυτούς τους ιστοτόπους, για τη διαθεσιμότητά τους ούτε για το περιεχόμενο των αρχείων που διανέμουν. Η βάση δεδομένων μπορεί να διαβαστεί από οποιονδήποτε έχει πρόσβαση στον υπολογιστή σας ή στα αντίγραφα ασφαλείας σας: προστατέψτε τη όπως θα προστατεύατε τα πρωτότυπα έγγραφα.

6. ΑΔΕΙΕΣ ΚΑΙ ΣΤΟΙΧΕΙΑ ΤΡΙΤΩΝ
Το λογισμικό διανέμεται με την άδεια GNU AGPL v3 και τους πρόσθετους όρους του αρχείου NOTICE (αρχεία LICENSE και NOTICE)· οι άδειες των στοιχείων τρίτων (PyMuPDF, RapidOCR και μοντέλα PaddleOCR, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip και άλλα) βρίσκονται στο THIRD_PARTY_NOTICES.md και στον φάκελο LICENSES. Οφείλετε να τις τηρείτε. Οι παρόντες όροι προστίθενται στην AGPL και δεν περιορίζουν τα δικαιώματά της για αντιγραφή, τροποποίηση και αναδιανομή του κώδικα· οι ρήτρες 3 και 4 αναπαράγουν και συμπληρώνουν τις ενότητες 15 και 16 της AGPL v3.

7. ΑΛΛΑΓΕΣ, ΕΦΑΡΜΟΣΤΕΟ ΔΙΚΑΙΟ ΚΑΙ ΤΕΛΙΚΕΣ ΔΙΑΤΑΞΕΙΣ
Οι παρόντες όροι μπορεί να ενημερωθούν σε επόμενες εκδόσεις του λογισμικού· στο πρώτο άνοιγμα μιας έκδοσης με νέους όρους θα σας ζητηθούν ξανά. Αν μια ρήτρα είναι άκυρη, οι υπόλοιπες παραμένουν σε ισχύ. Με την επιφύλαξη αναγκαστικών κανόνων που σας προστατεύουν, εφαρμόζεται το ιταλικό δίκαιο. Το λογισμικό δεν προορίζεται για ανηλίκους ούτε για χρήσεις όπου μια δυσλειτουργία θα μπορούσε να προκαλέσει βλάβη σε πρόσωπα ή πράγματα.

Πατώντας «Αποδέχομαι» επιβεβαιώνετε ότι διαβάσατε και αποδεχτήκατε όλα τα παραπάνω σημεία, ότι ευρετηριάζετε με το DocIndexer μόνο αρχεία που έχετε δικαίωμα να επεξεργάζεστε και ότι αναλαμβάνετε την πλήρη ευθύνη για τη χρήση που κάνετε.
"""

_SQ = """\
KUSHTET E PËRDORIMIT DHE PËRJASHTIMI NGA PËRGJEGJËSIA — DocIndexer
Versioni {v} i {d}

Lexoni me kujdes. Duke shtypur "Pranoj" deklaroni se i keni lexuar, kuptuar dhe pranuar plotësisht këto kushte. Nëse nuk i pranoni, shtypni "Refuzoj": programi mbyllet dhe nuk mund ta përdorni.

1. ÇFARË ËSHTË DOCINDEXER
DocIndexer është një program për Windows që lexon skedarët e dosjeve që zgjidhni (dokumente, fletë llogaritëse, prezantime, PDF, imazhe, postë elektronike, arkiva, baza të dhënash dhe të tjera), nxjerr tekstin e tyre, edhe me njohjen optike të karaktereve (OCR), dhe e ruan në një bazë të dhënash lokale që ta kërkoni. Mund të niset bashkë me Windows dhe të punojë në sfond, duke përdorur kohën kur kompjuteri është joaktiv brenda kufijve të CPU-së dhe të temperaturës që vendosni. Skedarët mbeten aty ku janë: programi nuk i ndryshon, nuk i zhvendos dhe nuk i fshin.

2. PËRDORIMI I LEJUAR DHE PËRGJEGJËSIA E PËRDORUESIT
Mund të indeksoni vetëm skedarë dhe dosje që ju përkasin ose që keni të drejtë t'i shikoni dhe t'i përpunoni. Ju jeni i vetmi përgjegjës për: (a) të verifikuar që përdorimi juaj është i ligjshëm, veçanërisht kur skedarët përmbajnë të dhëna personale të të tjerëve, dokumente pune ose informacione të mbuluara nga sekreti ose konfidencialiteti; (b) të marrë çdo pëlqim ose autorizim që kërkon ligji, përfshirë rregullat për mbrojtjen e të dhënave personale; (c) të ruajtur bazën e të dhënave, kopjet rezervë, eksportet dhe pamjet paraprake, që përmbajnë tekstin e dokumenteve tuaja dhe për rrjedhojë mund të përmbajnë të dhëna personale, kredenciale ose informacione konfidenciale. Ndalohet përdorimi i softuerit për të mbledhur ose për të parë të dhëna të të tjerëve pa autorizim ose për çdo qëllim të paligjshëm. Autori nuk e kontrollon dhe nuk mund ta kontrollojë përdorimin që bëni.

3. ASNJË GARANCI ("SIÇ ËSHTË")
NË MASËN MAKSIMALE TË LEJUAR NGA LIGJI I ZBATUESHËM, SOFTUERI OFROHET "SIÇ ËSHTË" DHE "SIÇ ËSHTË I DISPONUESHËM", PA ASNJË LLOJ GARANCIE, TË SHPREHUR OSE TË NËNKUPTUAR, PËRFSHIRË, POR PA U KUFIZUAR NË TO, GARANCITË E NËNKUPTUARA TË TREGTUESHMËRISË, PËRSHTATSHMËRISË PËR NJË QËLLIM TË CAKTUAR, MOSSHKELJES SË TË DREJTAVE TË TË TRETËVE, SAKTËSISË, DISPONUESHMËRISË DHE MUNGESËS SË GABIMEVE. I GJITHË RREZIKU LIDHUR ME CILËSINË DHE PERFORMANCËN E SOFTUERIT ËSHTË I JUAJI. NËSE SOFTUERI REZULTON ME DEFEKT, JU MERRNI PËRSIPËR KOSTON E ÇDO ASISTENCE, RIPARIMI OSE KORRIGJIMI. Në veçanti nuk garantohet që: teksti i nxjerrë dhe rezultatet e OCR-së të jenë të plota ose të sakta; kërkimi të gjejë të gjitha dokumentet që përmbajnë një term; njohja e gjuhës, e dublikatave dhe e meta të dhënave të jetë e saktë; kufijtë e CPU-së dhe të temperaturës të respektohen gjithmonë ose ta mbrojnë pajisjen; programi të mos e ngadalësojë kompjuterin ose të mos ndërhyjë në programe të tjera; softueri të jetë pa dobësi sigurie. Mos e përdorni DocIndexer si mjetin e vetëm për vendime ligjore, hetimore, mjekësore ose ekonomike: kontrolloni gjithmonë dokumentin origjinal.

4. PËRJASHTIMI NGA PËRGJEGJËSIA
NË ASNJË RAST, PËRVEÇ RASTEVE KUR LIGJI I DETYRUESHËM PARASHIKON NDRYSHE, AUTORI, BASHKËPUNËTORËT OSE SHPËRNDARËSIT E SOFTUERIT NUK DO TË MBAJNË PËRGJEGJËSI NDAJ JUSH OSE NDAJ TË TRETËVE PËR ÇDO DËM TË DREJTPËRDREJTË, TË TËRTHORTË, TË RASTËSISHËM, TË VEÇANTË, SHEMBULLOR, NDËSHKUES OSE PASUES (PËRFSHIRË, PA KUFIZIM, HUMBJEN OSE DËMTIMIN E TË DHËNAVE OSE TË BAZËS SË TË DHËNAVE, HUMBJEN E FITIMEVE, TË REPUTACIONIT OSE TË MUNDËSIVE, NDËRPRERJEN E VEPRIMTARISË, DEFEKTIN, MBINXEHJEN OSE MOSFUNKSIONIMIN E KOMPJUTERIT, KOSTOT E SHËRBIMEVE ZËVENDËSUESE, GJOBAT, PRETENDIMET E TË TRETËVE) QË RRJEDHIN NGA PËRDORIMI OSE PAMUNDËSIA E PËRDORIMIT TË SOFTUERIT, NGA VENDIMET E MARRA MBI BAZËN E REZULTATEVE TË TIJ, NGA HAPJA E SKEDARËVE TË DËMTUAR OSE KEQDASHËS GJATË INDEKSIMIT, NGA PËRDORIMI I MJETEVE TË PALËVE TË TRETA TË SHKARKUARA OSE TË NISURA NGA PROGRAMI (modelet OCR, ExifTool, 7-Zip, Microsoft Office) OSE NGA RIKTHIMI I KOPJEVE REZERVË, EDHE NËSE JANË NJOFTUAR PËR MUNDËSINË E DËMEVE TË TILLA DHE CILADO QOFTË BAZA LIGJORE (KONTRATË, PADREJTËSI, PËRGJEGJËSI OBJEKTIVE OSE TJETËR). Në vendet që nuk lejojnë përjashtim të plotë, përgjegjësia kufizohet në masën maksimale të lejuar.

5. TË DHËNAT, PRIVATËSIA DHE FAQET E PALËVE TË TRETA
Softueri punon në nivel lokal dhe nuk i dërgon të dhëna autorit as kujt tjetër: teksti i dokumenteve tuaja, baza e të dhënave dhe kërkimet tuaja mbeten në kompjuterin tuaj. Lidhet me internetin vetëm kur zgjidhni të shkarkoni mjete opsionale (modelet OCR, ExifTool, 7-Zip) nga faqet ose pasqyrat e tyre, të cilat marrin informacionet e zakonshme të një lidhjeje (si adresa IP) dhe u nënshtrohen kushteve të tyre. Autori nuk është përgjegjës për këto faqe, për disponueshmërinë e tyre as për përmbajtjen e skedarëve që shpërndajnë. Baza e të dhënave mund të lexohet nga kushdo që ka qasje në kompjuterin tuaj ose në kopjet tuaja rezervë: mbrojeni ashtu siç do të mbronit dokumentet origjinale.

6. LICENCAT DHE KOMPONENTËT E PALËVE TË TRETA
Softueri shpërndahet me licencën GNU AGPL v3 me kushtet shtesë të skedarit NOTICE (skedarët LICENSE dhe NOTICE); licencat e komponentëve të palëve të treta (PyMuPDF, RapidOCR dhe modelet PaddleOCR, ONNX Runtime, CustomTkinter, Pillow, ExifTool, 7-Zip dhe të tjerë) gjenden në THIRD_PARTY_NOTICES.md dhe në dosjen LICENSES. Jeni të detyruar t'i respektoni. Këto kushte i shtohen AGPL-së dhe nuk i kufizojnë të drejtat e saj për kopjimin, ndryshimin dhe rishpërndarjen e kodit; pikat 3 dhe 4 riprodhojnë dhe plotësojnë seksionet 15 dhe 16 të AGPL v3.

7. NDRYSHIMET, LIGJI I ZBATUESHËM DHE DISPOZITAT PËRFUNDIMTARE
Këto kushte mund të përditësohen në versionet e mëvonshme të softuerit; në hapjen e parë të një versioni me kushte të reja do t'ju kërkohen përsëri. Nëse një pikë është e pavlefshme, të tjerat mbeten në fuqi. Me përjashtim të normave të detyrueshme në mbrojtjen tuaj, zbatohet ligji italian. Softueri nuk është i destinuar për të miturit as për përdorime ku një mosfunksionim mund të shkaktojë dëme ndaj personave ose sendeve.

Duke shtypur "Pranoj" konfirmoni se i keni lexuar dhe pranuar të gjitha pikat e mësipërme, se me DocIndexer indeksoni vetëm skedarë që keni të drejtë t'i përpunoni, dhe se merrni përsipër çdo përgjegjësi për përdorimin që bëni.
"""

TEXTS = {"it": _IT, "en": _EN, "fr": _FR, "de": _DE, "es": _ES, "el": _EL, "sq": _SQ, "pl": _PL}

# etichette nella lingua dei termini (non passano da tr: seguono la lingua scelta nella finestra)
LABELS = {
    "pl": _PL_LABELS,
    "it": ("Termini d'uso", "Accetto", "Rifiuto", "Scegli la lingua",
           "Leggi i termini fino in fondo: con Rifiuto il programma si chiude."),
    "en": ("Terms of use", "I accept", "I decline", "Choose your language",
           "Read the terms to the end: with Decline the program closes."),
    "fr": ("Conditions d'utilisation", "J'accepte", "Je refuse", "Choisissez la langue",
           "Lisez les conditions jusqu'au bout : avec Refuser, le programme se ferme."),
    "de": ("Nutzungsbedingungen", "Ich akzeptiere", "Ich lehne ab", "Sprache wählen",
           "Lesen Sie die Bedingungen bis zum Ende: mit Ablehnen wird das Programm beendet."),
    "es": ("Términos de uso", "Acepto", "Rechazo", "Elija el idioma",
           "Lea los términos hasta el final: con Rechazo el programa se cierra."),
    "el": ("Όροι χρήσης", "Αποδέχομαι", "Απορρίπτω", "Επιλέξτε γλώσσα",
           "Διαβάστε τους όρους μέχρι το τέλος: με Απορρίπτω το πρόγραμμα κλείνει."),
    "sq": ("Kushtet e përdorimit", "Pranoj", "Refuzoj", "Zgjidhni gjuhën",
           "Lexoni kushtet deri në fund: me Refuzoj programi mbyllet."),
}


def text(lang: str) -> str:
    """Il testo completo dei termini nella lingua (italiano se la lingua non c'è)."""
    return TEXTS.get(lang, _IT).format(v=TERMS_VERSION, d=TERMS_DATE)


def labels(lang: str) -> tuple[str, str, str, str, str]:
    """(titolo, Accetto, Rifiuto, Scegli la lingua, nota) nella lingua."""
    return LABELS.get(lang, LABELS["it"])


def markdown() -> str:
    """TERMS.md: tutte le lingue, una sezione per lingua."""
    from .i18n import LANGUAGES
    out = ["# DocIndexer — Terms of use / Termini d'uso", "",
           f"Version {TERMS_VERSION} ({TERMS_DATE}). Generated from `docindexer/terms.py` "
           "(`python -m docindexer.terms > TERMS.md`). The program asks for the language and shows these "
           "terms in that language on first launch, and keeps the acceptance (version and date) in "
           "`config.json`; they are shown again when the version changes. They can be read again from the "
           "*Terms of use* button next to *Manual*.", ""]
    for code in TEXTS:
        out += [f"## {LANGUAGES[code]} ({code})", "", "```text", text(code).rstrip(), "```", ""]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(markdown())
