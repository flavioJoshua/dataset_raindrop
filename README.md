# Raindrop Article Export

Programma Python per estrarre gli articoli salvati nell'account Raindrop.io e
costruire un dataset locale aggiornabile. Scarica da Raindrop il catalogo degli
articoli, i tag e gli highlight; recupera il contenuto degli articoli dalla
cache di Raindrop o dal sito originale; infine salva dati e contenuti in formati
utilizzabili anche senza accedere nuovamente a Raindrop.

## Cosa fa il programma

Il progetto gestisce due fasi collegate:

1. `raindrop.py` estrae i dati da Raindrop.io e mantiene l'archivio locale
   `raindrop_articles/`.
2. `extraction.py` legge quell'archivio e genera dataset JSONL selezionabili per
   tutti gli articoli, tag o dominio, pronti per pandas, Hugging Face Datasets,
   RAG, embeddings e training.

## Flusso completo: cosa fanno i tre comandi

I tre comandi non fanno la stessa cosa. Ogni comando legge file diversi e
produce un risultato diverso.

### 1. Aggiornare solo il catalogo JSON, senza scaricare gli articoli

```bash
python3 raindrop.py update-articles
```

**Questo comando non scarica il contenuto degli articoli.** Aggiorna soltanto
la fotografia locale dei metadati presenti nell'account Raindrop.

Questo comando usa `RAINDROP_TOKEN` dal file `.env` per interrogare l'account
Raindrop.io. Scarica tramite API l'elenco aggiornato degli articoli, dei tag e
degli highlight e sostituisce questi due cataloghi locali:

```text
raindrop_articles/
├── articles.json
└── highlights.json
```

Non apre gli URL degli articoli, non scarica le pagine, non crea HTML o TXT e
non modifica `manifest.json`. Al termine sappiamo quali articoli esistono
nell'account e quali metadati possiedono, ma non abbiamo ancora scaricato il
loro contenuto.

### 2. Scaricare il contenuto degli articoli

```bash
python3 raindrop.py
```

Se il catalogo locale esiste, questo comando non lo aggiorna automaticamente
dall'account: legge quello già presente in:

```text
raindrop_articles/articles.json
```

Se `articles.json` non esiste, lo script deve prima recuperarlo da Raindrop e
lo crea insieme a `highlights.json`. Per chiedere esplicitamente un catalogo
aggiornato, senza dipendere dalla presenza del file locale, usare `--refresh`.

Per ogni articolo del catalogo controlla `manifest.json` e i file locali, quindi
crea o aggiorna:

```text
raindrop_articles/
├── files/<articolo>.html
├── text/<articolo>.txt
├── json/<articolo>.json   # solo con tag o highlight
└── manifest.json
```

Con il comportamento attuale:

- un articolo nuovo, che non possiede ancora i file locali, viene scaricato;
- un articolo con HTML o TXT mancante viene riscaricato;
- un JSON mancante provoca il download solo quando l'articolo ha tag o
  highlight e quindi quel JSON è necessario;
- un articolo con file presenti e signature identiche viene saltato;
- un articolo modificato nel catalogo, ma con tutti i file già presenti, può
  essere adottato come esistente senza che HTML, TXT e JSON vengano riscritti.

L'ultimo punto è un limite del codice attuale: non è ancora un aggiornamento
incrementale completo degli articoli modificati. Per forzare il download e la
riscrittura di tutti gli articoli selezionati si usa:

```
python3 raindrop.py --cookies
```

--cookie al singolare produce un errore.

Con --cookies il programma:

carica tutti i cookie da cookie/;
controlla manifest.json;

verifica la presenza di HTML, TXT e dell’eventuale JSON;


salta gli articoli già completi;

scarica solamente articoli nuovi o con file mancanti. metti questi  flussi




```bash
python3 raindrop.py --force
```

Per aggiornare prima il catalogo remoto e poi eseguire l'export con un solo
comando si usa:

```bash
python3 raindrop.py --refresh
```

Per aggiornare il catalogo e forzare anche la riscrittura di tutti i contenuti:

```bash
python3 raindrop.py --refresh --force
```

### 3. Costruire il dataset JSONL derivato

```bash
python3 extraction.py all
```

Questo comando non accede a Raindrop.io e non scarica pagine web. Legge:

```text
raindrop_articles/articles.json
raindrop_articles/manifest.json
raindrop_articles/text/*.txt
```

e rigenera nella directory predefinita `estrazione/` due file il cui nome
contiene la data di esecuzione:

```text
estrazione/
├── AAAA-MM-GG_all_articles.jsonl
└── AAAA-MM-GG_all_chunks.jsonl
```

Il primo contiene una riga JSON per articolo completo. Il secondo divide il
testo degli stessi articoli in più chunk, utili per RAG ed embeddings. Gli
articoli senza un file TXT locale vengono saltati e segnalati nel terminale.

Quindi il flusso completo normale è:

```bash
# 1. Aggiorna solo i cataloghi JSON; non scarica il contenuto degli articoli
python3 raindrop.py update-articles

# 2. Scarica i nuovi articoli e recupera i file locali mancanti
python3 raindrop.py

# 3. Rigenera i JSONL usando catalogo, manifest e TXT locali
python3 extraction.py all
```

### Cosa fa `update-articles`

```bash
python3 raindrop.py update-articles
```

Il termine `articles` nel nome del comando indica le **schede degli articoli
restituite dall'API**, non le pagine HTML. Il comando aggiorna il catalogo
locale dei metadati; il download del contenuto viene eseguito soltanto dal
successivo `python3 raindrop.py`.

Il comando legge dalla root del progetto il token configurato in `.env`:

```bash
RAINDROP_TOKEN=il_tuo_token_raindrop
```

Il token identifica e autorizza l'accesso all'account Raindrop.io. Lo script
interroga le API dell'account, recupera tutte le pagine dei raindrop e tutti gli
highlight, conserva nel catalogo soltanto gli elementi con `type: "article"` e
associa ogni highlight al relativo articolo tramite il suo ID Raindrop.

Scrive, in formato JSON UTF-8 indentato:

```text
raindrop_articles/
├── articles.json     # array di tutti gli articoli con tag e highlight associati
└── highlights.json   # array completo degli highlight restituiti da Raindrop
```

`articles.json` contiene per ogni articolo i dati restituiti da Raindrop, tra
cui `_id`, `title`, `link`, `domain`, `created`, `lastUpdate`, `tags`,
`collection`, `excerpt`, `note` e `highlights`. `highlights.json` conserva anche
la risposta separata e completa dell'API degli highlight.

Il comando sostituisce integralmente questi due cataloghi con la situazione
corrente dell'account. Non scarica le pagine HTML, non crea i file `.txt` e non
aggiorna `manifest.json`: queste operazioni vengono eseguite dal successivo
`python3 raindrop.py`.

Il percorso del catalogo principale può essere cambiato con `--articles-file`;
`highlights.json` viene scritto nella stessa directory:

```bash
python3 raindrop.py update-articles --articles-file output/catalogo.json
# scrive output/catalogo.json e output/highlights.json
```

`python3 raindrop.py --refresh` combina l'aggiornamento del catalogo remoto con
l'export locale. È possibile anche estrarre o aggiornare soltanto gli articoli
di uno specifico tag o dominio con `export-tag` ed `export-domain`.

Per ogni articolo `raindrop.py` esporta:

- una copia HTML locale in `raindrop_articles/files/`
- una versione testo in `raindrop_articles/text/`
- un file JSON in `raindrop_articles/json/` solo se l'articolo ha tag o highlight
- un manifest incrementale in `raindrop_articles/manifest.json`

## Setup

Copia il template e poi inserisci il token:

```bash
cp .env.example .env
```

Crea/aggiorna il file `.env` nella stessa directory di `raindrop.py`:

```bash
RAINDROP_TOKEN=il_tuo_token_raindrop
RAINDROP_LOG_DIR=logs
RAINDROP_LOG_MAX_LINES=3000
RAINDROP_DOWNLOAD_DELAY_MS=0
RAINDROP_DOWNLOAD_JITTER_MS=0
RAINDROP_REQUEST_TIMEOUT_SECONDS=25
RAINDROP_REQUEST_RETRIES=2
RAINDROP_USER_AGENT=Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0
```

Lo script carica sempre il file `.env` dalla root del progetto, cioe dalla
directory dove si trova `raindrop.py`.

`RAINDROP_USER_AGENT` e consigliato: il valore Firefox riportato sopra e gia
stato verificato e permette di scaricare correttamente anche da siti che
limitano o bloccano lo User-Agent predefinito dello script.

Lo script legge anche `RAINDROP_ACCESS_TOKEN`, se preferisci usare quel nome.

Installa l'ambiente minimo dedicato:

```bash
python3 -m venv env/datasetenv
source env/datasetenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-export.txt
```

Poi esegui lo script con:

```bash
python raindrop.py --help
```

Per pandas, Hugging Face Datasets, RAG e training installa anche lo stack
completo:

```bash
python -m pip install -r requirements.txt
```

Vedi [environment.md](environment.md) per creare, aggiornare o cancellare
l'environment.

## Log Download

Ogni richiesta HTTP e ogni download articolo vengono registrati in JSONL:

```text
logs/YYYY-MM-DD-log.log
logs/YYYY-MM-DD-log-0002.log
logs/YYYY-MM-DD-log-0003.log
```

Il numero massimo di righe per ogni file si configura in `.env`:

```bash
RAINDROP_LOG_MAX_LINES=3000
```

Quando il file giornaliero raggiunge questo limite, lo script continua su un
nuovo file con suffisso progressivo. I log precedenti non vengono troncati.

La directory dei log si configura nel file `.env` che si trova nella root del
progetto, cioè nella stessa directory di `raindrop.py`:

```bash
RAINDROP_LOG_DIR=logs
```

Con questo valore, se il progetto si trova in
`/home/flavio/Documents/code/dataset`, i log vengono scritti in:

```text
/home/flavio/Documents/code/dataset/logs/
```

Il valore può essere sostituito con un altro percorso, per esempio:

```bash
RAINDROP_LOG_DIR=output/logs_raindrop
```

Esempio di evento:

```json
{"event":"http_request","url":"https://example.com","status":200,"ok":true,"elapsed_ms":421,"kb":139}
```

Esempio per leggere il log con pandas:

```python
import pandas as pd

df = pd.read_json("logs/2026-05-30-log.log", lines=True)
errors = df[df["ok"] == False]
print(errors[["ts", "event", "url", "status", "error"]].tail())
```

Il log non salva header, token o cookie. Salva URL, tempi, status HTTP, KB
scaricati e messaggi di errore utili a distinguere problemi di rete, paywall,
redirect/cache e parsing del contenuto.

## Resume E Download Lenti

Il download e incrementale. Se il processo si ferma a meta, rilancia lo stesso
comando:

```bash
python3 raindrop.py export-domain repubblica.it
```

Lo script:

- legge `manifest.json`
- salta gli articoli gia completati
- se trova file `.html`, `.txt` e l'eventuale `.json` gia presenti ma non ancora
  registrati nel manifest, li adotta e li marca come completati
- riprende dai successivi

Per riscrivere tutto:

```bash
python3 raindrop.py export-domain repubblica.it --force
```

Se il sito rallenta dopo molti download, puo essere throttling lato server.
Lo script crea gia una nuova richiesta HTTP per ogni articolo. Puoi ridurre la
pressione aggiungendo una pausa tra articoli in `.env`:

```bash
RAINDROP_DOWNLOAD_DELAY_MS=1500
RAINDROP_DOWNLOAD_JITTER_MS=1000
```

Con questi valori aspetta circa 1.5-2.5 secondi tra un articolo e il successivo.

Se invece un singolo dominio si blocca su handshake, TLS o server lento, regola
timeout e retry:

```bash
RAINDROP_REQUEST_TIMEOUT_SECONDS=25
RAINDROP_REQUEST_RETRIES=2
```

Così un articolo problematico non blocca il processo per molti minuti. Se cache
e originale puntano allo stesso URL, lo script ora prova quell'URL una sola
volta.

Se un sito si apre nel browser ma blocca lo script, prova con lo User-Agent del
browser:

```bash
python3 raindrop.py export-domain medium.com \
  --output raindrop_articles \
  --user-agent "Mozilla/5.0 ..."
```

In alternativa metti lo stesso valore in `.env` con `RAINDROP_USER_AGENT`.

Esempio che ha funzionato con Medium da Firefox su Linux:

```bash
python3 raindrop.py export-domain medium.com \
  --output raindrop_articles \
  --user-agent "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"
```

## Uso Base

Esporta tutti gli articoli:

```bash
python3 raindrop.py
```

Aggiorna prima il catalogo locale da Raindrop:

```bash
python3 raindrop.py update-articles
```

Questo crea/aggiorna:

```text
raindrop_articles/articles.json
raindrop_articles/highlights.json
```

Le estrazioni successive leggono `raindrop_articles/articles.json` senza rifare
la query completa a Raindrop. Per forzare un aggiornamento durante un export:

```bash
python3 raindrop.py --refresh
```

Output predefinito:

```text
raindrop_articles/
  files/
    Titolo articolo.html
  text/
    Titolo articolo.txt
  json/
    Titolo articolo.json
  manifest.json
```

La struttura completa dell'output, il ruolo di `articles.json`,
`articles.csv`, `manifest.json` e il calcolo delle signature sono descritti in
[README_Output.md](README_Output.md).

## Esempi

Esportare solo i primi 5 articoli, utile per test:

```bash
python3 raindrop.py --limit 5
```

Usare una directory di output diversa:

```bash
python3 raindrop.py --output raindrop_test_export --limit 3
```

Forzare la riscrittura anche degli articoli gia esportati:

```bash
python3 raindrop.py --force
```

Usare solo la copia permanente/cache di Raindrop, quando disponibile:

```bash
python3 raindrop.py --source cache
```

Usare solo il link originale dell'articolo:

```bash
python3 raindrop.py --source original
```

Comportamento predefinito:

```bash
python3 raindrop.py --source both
```

Con `both`, lo script prova prima la copia permanente di Raindrop e poi il link originale.

## Articoli Con Login: Cookies

I cookie servono per scaricare dal **sito originale** un articolo visibile solo
dopo il login, per esempio dietro un abbonamento. Non sostituiscono
`RAINDROP_TOKEN`: il token autorizza l'accesso all'account Raindrop, mentre il
file cookie trasferisce allo script la sessione già aperta sul sito
dell'articolo.

Non inserire username e password nel programma. Accedi normalmente con Firefox
e poi esporta soltanto i cookie necessari nel formato Netscape `cookies.txt`.

### 1. Installare l'estensione Firefox

Installare dal sito ufficiale Mozilla l'estensione
[Get cookies.txt LOCALLY](https://addons.mozilla.org/firefox/addon/get-cookies-txt-locally/).
L'estensione supporta sia Netscape sia JSON: per questo programma bisogna
scegliere **Netscape**, non JSON.

Dopo l'installazione, se Firefox lo richiede, concedere all'estensione il
permesso di leggere i cookie del sito corrente. Un'estensione che può leggere i
cookie ha accesso a dati sensibili: installarla soltanto dalla pagina ufficiale
Mozilla e rimuoverla o disabilitarla se non serve più.

### 2. Accedere al sito da Firefox

1. Aprire Firefox con il profilo che si vuole usare.
2. Visitare il sito, per esempio `https://www.repubblica.it`.
3. Eseguire il login.
4. Aprire un articolo riservato e verificare che il testo completo sia
   effettivamente leggibile nel browser.

Se nel browser compare ancora il login o il paywall, anche il cookie esportato
non permetterà allo script di leggere l'articolo.

### 3. Esportare il cookie del dominio

1. Restare su una scheda del dominio interessato.
2. Premere l'icona di **Get cookies.txt LOCALLY** nella barra di Firefox.
3. Selezionare i cookie della scheda o del dominio corrente, evitando di
   esportare inutilmente i cookie di tutti i siti.
4. Selezionare il formato **Netscape**.
5. Usare il pulsante di download/esportazione dell'estensione.

Il file deve iniziare con una riga simile a questa e contenere poi una riga per
cookie, con campi separati da tabulazioni:

```text
# Netscape HTTP Cookie File
.repubblica.it	TRUE	/	TRUE	1780000000	nome_cookie	valore_cookie
```

Non modificare manualmente tabulazioni, valori o date di scadenza.

### 4. Salvare tutti i cookie nella directory `cookie/`

Lo script legge i cookie esclusivamente da questa directory della root del
progetto:

```text
/home/flavio/Documents/code/dataset/cookie/
```

Creare un file separato per ogni sito. Il nome è libero, purché termini in
`.txt`; usare il dominio rende il contenuto riconoscibile:

```text
dataset/
├── raindrop.py
├── .env
└── cookie/
    ├── repubblica.it_cookies.txt
    └── medium.com_cookies.txt
```

Non lasciare i file nella root e non passarne il percorso nel comando. Il nuovo
`--cookies` è un interruttore senza valore:

```bash
python3 raindrop.py --cookies
```

L'opzione corretta è `--cookies`, al plurale. `--cookie` al singolare non è
riconosciuta e produce un errore.

Con `--cookies` il programma:

1. apre `cookie/` nella root del progetto;
2. cerca tutti i file `*.txt`;
3. verifica che ogni file sia in formato Netscape;
4. unisce i cookie in un solo cookie jar;
5. carica automaticamente i cookie corretti per ciascun dominio;
6. controlla `manifest.json`;
7. verifica la presenza dei file HTML, TXT e dell'eventuale JSON richiesto per
   ogni articolo;
8. salta gli articoli che risultano già completi;
9. scarica gli articoli nuovi o quelli a cui manca almeno un file richiesto.

Quindi `--cookies` abilita l'autenticazione, ma non forza un nuovo download
degli articoli già completi.

Nell'esempio precedente una sola esecuzione carica sia Repubblica sia Medium:

```bash
python3 raindrop.py --source original --cookies
```

I cookie di Repubblica vengono usati per `repubblica.it`, quelli di Medium per
`medium.com`; non è più necessario eseguire un comando separato per ogni sito.

Senza `--cookies`, la directory non viene letta e nessun cookie viene caricato.
Se `--cookies` è presente ma `cookie/` non esiste, non contiene `.txt` o include
un file non valido, il programma termina mostrando un errore invece di
continuare senza autenticazione.

Per riscaricare tutti gli articoli selezionati e richiedere le pagine ai siti
originali usando i cookie bisogna aggiungere sia `--source original` sia
`--force`:

```bash
python3 raindrop.py --source original --cookies --force
```

Per forzare soltanto un dominio:

```bash
python3 raindrop.py export-domain medium.com \
  --output raindrop_articles \
  --source original \
  --cookies \
  --force
```

### 5. Verificare formato e caricamento

Dalla root del progetto eseguire:

```bash
python3 -c "from utility import PROJECT_ROOT, load_cookie_directory; load_cookie_directory(PROJECT_ROOT / 'cookie')"
```

Output atteso, dove `N` è il numero di cookie caricati:

```text
Loaded N cookies from 2 files in /home/flavio/Documents/code/dataset/cookie
```

Se compare `Expected Netscape cookies.txt format`, riesportare il file
scegliendo Netscape invece di JSON. Non stampare nel terminale il contenuto
completo del file, perché include i valori della sessione.

### 6. Provare il download di un solo articolo

Per verificare i cookie senza avviare un export grande:

```bash
python3 raindrop.py export-domain repubblica.it \
  --limit 1 \
  --source original \
  --cookies
```

`--source original` è importante per il test: ordina allo script di richiedere
la pagina al sito usando i cookie, invece di usare la copia cache di Raindrop.

La stessa opzione funziona per export generale, tag e dominio:

```bash
python3 raindrop.py --source original --cookies

python3 raindrop.py export-tag ukraine-war \
  --source original \
  --cookies
```

In tutti i casi vengono caricati tutti i `.txt` di `cookie/`; il cookie jar
decide quali cookie inviare a ogni dominio.

### 7. Quando esportare nuovamente i cookie

Ripetere login ed esportazione quando:

- lo script riceve di nuovo la pagina di login o il paywall;
- il file TXT contiene soltanto una pagina di accesso;
- si è fatto logout da Firefox;
- il sito ha invalidato o fatto scadere la sessione;
- il download restituisce HTTP 401 o 403.

I cookie non risolvono tutti i blocchi: alcuni siti richiedono JavaScript,
header aggiuntivi o controlli anti-bot che una semplice richiesta HTTP non può
riprodurre.

### 8. Sicurezza

Un file `cookies.txt` è una credenziale temporanea e deve essere trattato come
una password:

- non inviarlo in chat, email, issue o ticket;
- non copiarne il contenuto nei log;
- non aggiungerlo a Git;
- cancellarlo e riesportarlo se si sospetta che sia stato condiviso.

Il `.gitignore` del progetto esclude l'intera directory `cookie/`, oltre ai
pattern `cookies.txt` e `*cookies.txt`, ma è
comunque opportuno controllare `git status` prima di ogni commit.

La guida separata [export_cookie.md](export_cookie.md) contiene ulteriori
esempi per test limitati e dataset derivati.

## Estrazione Dataset JSONL

La creazione di dataset e file AI/RAG si fa con `extraction.py`.
Questo script non scarica nulla da Raindrop.io: legge solo il catalogo,
il manifest e i `.txt` gia presenti in `raindrop_articles/`.

Prima scarica o aggiorna l'archivio locale:

```bash
python3 raindrop.py export-tag ukraine-war
```

Poi crea i JSONL derivati:

```bash
python3 extraction.py tag ukraine-war
```

Output:

```text
raindrop_articles/
  files/
  text/
  json/
  manifest.json

estrazione/
  README.md
  2026-05-30_ukraine-war_articles.jsonl
  2026-05-30_ukraine-war_chunks.jsonl
```

`raindrop_articles/` conserva HTML, TXT, metadata e manifest per resume e
tracciabilita.

`*_articles.jsonl` contiene una riga per articolo completo.

`*_chunks.jsonl` contiene una riga per chunk di testo, piu utile per embedding e RAG.

Esempi:

```bash
# Dataset su tutti gli articoli locali
python3 extraction.py all

# Dataset su un tag
python3 extraction.py tag ukraine-war

# Dataset su un dominio
python3 extraction.py domain repubblica.it

# Solo primi 10 articoli selezionati
python3 extraction.py tag ukraine-war --limit 10

# Directory dataset diversa
python3 extraction.py tag ukraine-war --output estrazione_ukraine

# Chunk piu piccoli
python3 extraction.py tag ukraine-war --chunk-size 400 --chunk-overlap 50

# Leggere da una export directory diversa
python3 extraction.py domain repubblica.it \
  --export-dir raindrop_test_export \
  --output estrazione_cookie
```

Il README dentro `estrazione/` contiene esempi per leggere i dati con pandas,
Hugging Face Datasets e un RAG minimale.

## Export Per Dominio

Per scaricare/cache tutti gli articoli di un dominio, leggendo dal catalogo
locale `raindrop_articles/articles.json`:

```bash
python3 raindrop.py export-domain repubblica.it
```

Con questo comando breve lo script usa le convenzioni:

```text
Local export directory: raindrop_test_export
```

Senza `--cookies` non viene caricato alcun cookie. Con `--cookies`, lo script
carica tutti i file Netscape `*.txt` presenti in `cookie/`, compresi per esempio
`cookie/repubblica.it_cookies.txt` e `cookie/medium.com_cookies.txt`.

Esempio con autenticazione:

```bash
python3 raindrop.py export-domain repubblica.it \
  --output raindrop_test_export \
  --source original \
  --cookies
```

Questo crea/aggiorna:

```text
raindrop_test_export/
  files/
  text/
  json/
  manifest.json
```

Per creare il dataset JSONL da questa export directory:

```bash
python3 extraction.py domain repubblica.it \
  --export-dir raindrop_test_export \
  --output estrazione_cookie
```

Test limitato:

```bash
python3 raindrop.py export-domain repubblica.it \
  --limit 1 \
  --output raindrop_test_export \
  --source original \
  --cookies
```

## File JSON

Il file JSON viene creato solo quando l'articolo ha almeno un tag o un highlight.

Esempio:

```json
{
  "id": 1738177662,
  "title": "Titolo articolo",
  "link": "https://example.com/articolo",
  "tags": ["tag-1", "tag-2"],
  "highlights": [
    {
      "id": "highlight-id",
      "text": "Testo evidenziato",
      "note": "",
      "color": "yellow",
      "created": "2026-05-30T08:47:00.287Z",
      "lastUpdate": "",
      "tags": ["tag-1"]
    }
  ]
}
```

## Aggiornamenti Incrementali

Lo script salva lo stato in:

```text
raindrop_articles/manifest.json
```

Ai lanci successivi:

- salta gli articoli invariati
- riscrive gli articoli modificati
- crea i file mancanti, per esempio HTML o TXT assenti
- aggiorna JSON se cambiano tag o highlight

Per ignorare il manifest e riscrivere tutto:

```bash
python3 raindrop.py --force
```

## Note

- Il download completo puo richiedere tempo se l'account contiene molti articoli.
- La copia permanente/cache di Raindrop puo richiedere un piano Raindrop Pro.
- `.env` e le directory di output sono escluse da `.gitignore`.
