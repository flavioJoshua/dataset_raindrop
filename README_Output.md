# Output di `raindrop.py`

Questo documento descrive dove viene scritto l'output di `raindrop.py`, la
struttura delle directory e il ruolo dei file prodotti.

`raindrop.py` estrae dall'account Raindrop.io il catalogo degli articoli con
tag e highlight, scarica il contenuto dalla cache di Raindrop o dai siti
originali e costruisce un archivio locale. Tramite `manifest.json` il programma
riconosce gli articoli nuovi, quelli invariati e quelli con file mancanti. Il
codice attuale, però, non garantisce la riscrittura di un articolo modificato
quando tutti i suoi file locali esistono già; per riscrivere tutto occorre
usare `--force`.

Il ciclo di aggiornamento consigliato è:

```bash
python3 raindrop.py update-articles  # aggiorna solo i cataloghi JSON, non le pagine
python3 raindrop.py                  # scarica nuovi articoli e file mancanti
python3 extraction.py all            # rigenera il dataset JSONL derivato
```

In alternativa, `python3 raindrop.py --refresh` aggiorna il catalogo remoto
prima di eseguire l'export. `extraction.py` non interroga Raindrop: ricostruisce
i file JSONL usando l'ultima versione dell'archivio locale.

Più precisamente, `update-articles` usa `RAINDROP_TOKEN` (o
`RAINDROP_ACCESS_TOKEN`) letto dal file `.env` per accedere all'account
Raindrop.io. Recupera via API tutti i raindrop e gli highlight, seleziona gli
elementi di tipo `article`, associa gli highlight ai rispettivi articoli e
sostituisce due file JSON:

```text
raindrop_articles/articles.json
raindrop_articles/highlights.json
```

Non apre né scarica gli URL contenuti nel campo `link`: quindi non produce
HTML, TXT, JSON di dettaglio o manifest. Questi vengono creati dal successivo
comando di export, `python3 raindrop.py`.

Questo comando aggiorna soltanto il catalogo dei metadati: non scarica HTML o
testo e non modifica il manifest. Il successivo `python3 raindrop.py` legge
`articles.json`, scarica gli articoli nuovi o con file mancanti e aggiorna
`files/`, `text/`, `json/` e `manifest.json`.

Le directory di output sono escluse da Git: vengono create localmente quando
si esegue lo script e quindi normalmente non compaiono nel repository GitHub.

Quando si esegue un comando, per esempio:

```bash
python3 raindrop.py export-domain repubblica.it \
  --limit 1 \
  --output raindrop_domain_test
```

lo script crea o aggiorna i file richiesti, ma non salva da nessuna parte il
testo completo del comando eseguito. Il `manifest.json` registra gli articoli,
i percorsi dei file, le signature, gli errori e la data dell'aggiornamento; non
registra invece opzioni come `--limit`, `--output`, `--source` o `--cookies`.

Per questo motivo, osservando oggi una directory locale, possiamo capire quali
articoli e quali file contiene, ma non possiamo sapere con assoluta certezza
quale comando sia stato digitato originariamente. Inoltre, la stessa directory
può essere stata aggiornata più volte usando comandi e opzioni differenti.

I comandi mostrati nelle sezioni successive sono quindi esempi semplici e
corretti per creare nuovamente lo stesso tipo di directory. Non rappresentano
necessariamente la cronologia esatta dei comandi eseguiti in passato.

## Qual è l'output predefinito

Il default dipende dal comando. `--refresh` non è un comando separato: è
un'opzione che aggiorna prima il catalogo Raindrop e poi continua con l'export
richiesto.

| Comando | Cosa seleziona o aggiorna | Directory/file predefiniti |
| --- | --- | --- |
| `python3 raindrop.py` | Esporta tutti gli articoli presenti nel catalogo locale. | `raindrop_articles/files/`, `text/`, `json/` e `manifest.json`. |
| `python3 raindrop.py --refresh` | Prima sostituisce il catalogo con i dati attuali dell'account, poi esporta tutti gli articoli. | Catalogo in `raindrop_articles/articles.json` e `highlights.json`; export in `raindrop_articles/`. |
| `python3 raindrop.py --refresh --force` | Aggiorna il catalogo e riscrive tutti gli articoli selezionati, anche se i file esistono. | Catalogo ed export in `raindrop_articles/`. |
| `python3 raindrop.py export-tag <tag>` | Esporta soltanto gli articoli che possiedono esattamente il tag indicato. | `raindrop_articles/`. |
| `python3 raindrop.py export-tag <tag> --refresh` | Aggiorna il catalogo e poi esporta gli articoli con il tag indicato. | Catalogo ed export in `raindrop_articles/`. |
| `python3 raindrop.py update-articles` | Aggiorna soltanto il catalogo; non scarica HTML/TXT e non aggiorna il manifest. | `raindrop_articles/articles.json` e `raindrop_articles/highlights.json`. |
| `python3 raindrop.py export-domain <dominio>` | Esporta soltanto gli articoli del dominio indicato. | `raindrop_test_export/`; il catalogo letto resta `raindrop_articles/articles.json`. |
| `python3 raindrop.py export-domain <dominio> --refresh` | Aggiorna il catalogo e poi esporta gli articoli del dominio indicato. | Catalogo in `raindrop_articles/`; export in `raindrop_test_export/`. |

### Tutte le opzioni di `raindrop.py`

| Opzione | Valore predefinito | A cosa serve | Esempio |
| --- | --- | --- | --- |
| `-h`, `--help` | — | Mostra nel terminale la sintassi, i comandi e tutte le opzioni disponibili, poi termina senza creare file. | `python3 raindrop.py --help` |
| `--output <directory>` | `raindrop_articles/`; per `export-domain`, `raindrop_test_export/` | Cambia la directory di HTML, TXT, JSON e manifest. Non cambia il catalogo e non ha effetto operativo su `update-articles`. | `--output mio_export` |
| `--articles-file <file>` | `raindrop_articles/articles.json` | Cambia il file del catalogo letto o scritto. Durante l'aggiornamento, `highlights.json` viene scritto nella stessa directory del file indicato. | `--articles-file dati/catalogo.json` |
| `--refresh` | disattivato | Prima dell'export interroga Raindrop e sostituisce `articles.json` e `highlights.json`. Con `update-articles` è superfluo, perché quel comando aggiorna già il catalogo. | `python3 raindrop.py --refresh` |
| `--source both\|cache\|original` | `both`; per `export-domain`, `original` | Sceglie da dove scaricare il contenuto. `both` prova prima la copia permanente Raindrop e poi il sito originale. | `--source original` |
| `--cookies` | disattivato | Carica e unisce tutti i file Netscape `*.txt` presenti esclusivamente nella directory `cookie/` della root del progetto. | `python3 raindrop.py --cookies` |
| `--user-agent <testo>` | valore di `RAINDROP_USER_AGENT` oppure User-Agent interno | Sostituisce lo User-Agent HTTP per la singola esecuzione. | `--user-agent "Mozilla/5.0 ..."` |
| `--limit <numero>` | `0`, cioè nessun limite | Elabora soltanto i primi N articoli dopo la selezione generale, per tag o dominio. | `--limit 5` |
| `--force` | disattivato | Ignora il controllo del manifest e riscrive i file di tutti gli articoli selezionati. | `python3 raindrop.py --force` |

`--output` sostituisce il default della directory di export. Per esempio:

```bash
python3 raindrop.py --limit 3 --output raindrop_test_export
```

## Le tre directory locali presenti nel progetto

### `raindrop_articles/`

È l'output generale predefinito. Il comando riproducibile è:

```bash
python3 raindrop.py
```

Un test limitato nella stessa directory può essere eseguito con:

```bash
python3 raindrop.py --limit 5
```

Contiene il catalogo Raindrop completo e i file scaricati. È anche la directory
letta per default da `extraction.py` quando si costruiscono dataset derivati.

### `raindrop_test_export/`

È il default specifico di `export-domain`. Per esempio:

```bash
python3 raindrop.py export-domain repubblica.it --limit 1
```

Nel README principale è documentato anche questo test esplicito:

```bash
python3 raindrop.py export-domain repubblica.it \
  --limit 1 \
  --output raindrop_test_export \
  --source original \
  --cookies
```

### `raindrop_domain_test/`

Non è un nome predefinito nel codice: è una directory di test scelta tramite
`--output`. Il contenuto locale (un articolo di `repubblica.it`) è compatibile
con un comando come:

```bash
python3 raindrop.py export-domain repubblica.it \
  --limit 1 \
  --output raindrop_domain_test
```

Il comando esatto originariamente eseguito non viene registrato nel manifest,
quindi non è possibile ricostruirne con certezza eventuali opzioni aggiuntive
come `--source` o `--cookies`. Quello sopra è il comando minimo che riproduce lo
stesso tipo di output.

## Struttura interna

Una directory di export ha questa forma:

```text
raindrop_articles/
├── articles.json
├── highlights.json       # dopo update-articles; può non essere presente
├── articles.csv          # file storico, non prodotto dal codice attuale
├── files/
│   └── <titolo-o-nome-univoco>.html
├── text/
│   └── <titolo-o-nome-univoco>.txt
├── json/
│   └── <titolo-o-nome-univoco>.json
└── manifest.json
```

`articles.json`, `highlights.json` e `articles.csv` possono mancare negli output
di test: l'export può leggere il catalogo centrale da
`raindrop_articles/articles.json` e scrivere nella directory scelta soltanto
`files/`, `text/`, `json/` e `manifest.json`.

I nomi dei file derivano dal titolo e vengono resi sicuri per il filesystem. Il
codice può aggiungere l'ID Raindrop per evitare collisioni. Se un articolo è già
nel manifest, il nome esistente viene conservato.

## Tabella dei file e collegamenti tra i dati

Nella tabella, `<output>` indica la directory di export. Il suo valore
predefinito è `raindrop_articles/`, tranne per `export-domain`, che usa
`raindrop_test_export/`. L'opzione `--output` può cambiare questa directory.

I file vengono prodotti in tre processi distinti e consecutivi:

1. **Catalogo Raindrop** — `python3 raindrop.py update-articles` interroga le
   API e scrive i metadati ricevuti dall'account.
2. **Export incrementale** — `python3 raindrop.py` legge il catalogo e crea o
   aggiorna HTML, testo, JSON di dettaglio e manifest.
3. **Dataset derivato** — `python3 extraction.py all` legge catalogo, manifest
   e testi locali e genera i JSONL per l'analisi e l'AI.

`python3 raindrop.py --refresh` esegue il processo 1 e subito dopo il processo
2 con un solo comando.

| File o percorso predefinito | Può cambiare? | Processo di creazione o aggiornamento | Quali dati contiene | Come si collega agli altri dati | Funzione principale |
| --- | --- | --- | --- | --- | --- |
| `raindrop_articles/articles.json` | Sì. `--articles-file` cambia nome e percorso. | **1 — Catalogo.** `update-articles` lo sostituisce con i dati correnti dell'account. Anche `--refresh` lo aggiorna prima dell'export. | Catalogo completo degli articoli: `_id`, titolo, link, dominio, date, tag, collection, excerpt, note, media e highlight associati. | `_id` è l'ID dell'articolo. Corrisponde alla chiave in `manifest.json` e al campo `id` nei JSON di dettaglio. | Fonte dei metadati usata dagli export e da `extraction.py`. |
| `raindrop_articles/highlights.json` | La directory segue `--articles-file`, ma il nome resta `highlights.json`. | **1 — Catalogo.** `update-articles` o `--refresh` scarica tutti gli highlight dall'API `/highlights` e sostituisce il file. | Elenco completo e separato degli highlight restituiti dall'API Raindrop. | `raindropRef` identifica l'articolo; corrisponde a `_id` in `articles.json`. | Conservare la risposta completa degli highlight e permettere elaborazioni specifiche. |
| `<output>/manifest.json` | La directory cambia con `--output`; il nome resta `manifest.json`. | **2 — Export.** `raindrop.py` lo aggiorna dopo ogni articolo e scrive il riepilogo alla fine. Non viene creato da `update-articles`. | Una voce per articolo con titolo, percorsi HTML/TXT/JSON, signature, errore e data di aggiornamento; contiene anche il riepilogo dell'ultimo export. | La chiave di `items`, per esempio `"1738177662"`, è l'ID Raindrop. I campi `html_path`, `text_path` e `json_path` portano direttamente ai file di dettaglio. | Indice operativo, resume, controllo delle modifiche e accesso ai file di ogni articolo. |
| `<output>/files/<nome>.html` | Sì. Directory con `--output`; nome generato dal titolo e, quando necessario, dall'ID. | **2 — Export.** `raindrop.py` scarica la cache Raindrop o la pagina originale; salta il download se articolo, signature e file risultano invariati. | Copia HTML scaricata dalla cache Raindrop o dal sito originale. | Il percorso esatto è in `manifest.json → items → <ID> → html_path`. | Conservare la pagina originale per consultazione o nuova estrazione. |
| `<output>/text/<nome>.txt` | Sì. Directory con `--output`; nome generato come quello HTML. | **2 — Export.** `raindrop.py` estrae il testo dal contenuto scaricato e lo scrive insieme all'intestazione dell'articolo. | Titolo, link, data Raindrop, eventuali excerpt e nota, seguiti dal testo estratto dall'articolo. | Il percorso esatto è in `manifest.json → items → <ID> → text_path`. `extraction.py` usa questo collegamento. | Testo pulito per ricerca, dataset JSONL, RAG, embeddings e training. |
| `<output>/json/<nome>.json` | Sì. Directory con `--output`; nome generato come quello HTML. Il file può non esistere. | **2 — Export.** `raindrop.py` lo crea o aggiorna soltanto se l'articolo possiede almeno un tag o un highlight. | `id`, `title`, `link`, `tags` e `highlights`, comprese date, note, colori e tag degli highlight. | `id` corrisponde alla chiave del manifest e a `_id` nel catalogo. Il percorso è in `json_path`; se non serve un JSON, `json_path` è vuoto. | Metadati compatti di dettaglio per un singolo articolo. |
| `raindrop_articles/articles.csv` | È un file storico; il codice attuale non ne gestisce nome o percorso. | **Fuori dal processo attuale.** Nessuno dei comandi correnti lo crea o lo aggiorna. | Vecchio indice tabellare con ID, titolo, link, dominio, data, tag, collection e vecchi campi di download. | `id` può essere collegato a `_id` del catalogo e alla chiave del manifest, ma i dati possono essere obsoleti. | Compatibilità o analisi storica; non deve essere usato per il resume corrente. |
| `<dataset>/<selezione>_articles.jsonl` | Sì, tramite `extraction.py --output`; il prefisso dipende dalla selezione. | **3 — Dataset derivato.** `extraction.py all`, `tag` o `domain` lo rigenera leggendo catalogo, manifest e TXT; non interroga Raindrop. | Una riga JSON per articolo selezionato, con metadati e testo completo. | Deriva da `articles.json`; il testo viene trovato tramite `manifest.json` e `text_path`. | Dataset finale a livello di articolo. |
| `<dataset>/<selezione>_chunks.jsonl` | Sì, tramite `extraction.py --output`; nome legato alla selezione. | **3 — Dataset derivato.** La stessa esecuzione di `extraction.py` divide ogni testo in chunk e riscrive il file. | Più righe per articolo, ottenute suddividendo il testo in chunk sovrapposti. | Ogni chunk mantiene l'identità dell'articolo sorgente. | Dataset per RAG, indicizzazione, embeddings e training a segmenti. |

### Dal manifest ai dati di un articolo

Il collegamento affidabile tra tutti i file è l'ID Raindrop. Nell'output
predefinito, tutti i percorsi sotto partono dalla directory
`raindrop_articles/`. Per esempio, per l'articolo con ID `1738177662`:

```text
raindrop_articles/
├── manifest.json
│   └── items
│       └── "1738177662"
│           ├── html_path ──> raindrop_articles/files/<nome>.html
│           ├── text_path ──> raindrop_articles/text/<nome>.txt
│           └── json_path ──> raindrop_articles/json/<nome>.json
│
├── articles.json
│   └── articolo con _id = 1738177662
│
├── files/
│   └── <nome>.html
│
├── text/
│   └── <nome>.txt
│
└── json/
    └── <nome>.json
        └── campo id = 1738177662
```

Quindi `manifest.json`, `articles.json`, `files/`, `text/` e `json/` si trovano
tutti dentro `raindrop_articles/` quando si usa il percorso predefinito. Se il
comando contiene, per esempio, `--output mio_export`, soltanto `manifest.json`,
`files/`, `text/` e `json/` vengono creati sotto `mio_export/`. Il catalogo
`articles.json` resta nel percorso indicato da `--articles-file`, che per
default è `raindrop_articles/articles.json`.

Una procedura automatica dovrebbe quindi:

1. aprire `raindrop_articles/manifest.json`;
2. scorrere le coppie `ID → voce` contenute in `items`;
3. usare `text_path`, `html_path` o `json_path` per leggere il dettaglio
   desiderato;
4. cercare lo stesso ID come `_id` in
   `raindrop_articles/articles.json` quando servono tutti i metadati Raindrop;
5. controllare che il percorso non sia vuoto e che il file esista, perché il
   JSON di dettaglio è facoltativo e un download può essere fallito;
6. controllare `download_error`, `article_signature`, `metadata_signature` e
   `updated_at` per valutare stato, modifiche e ultimo aggiornamento.

Non conviene ricostruire i collegamenti partendo dal titolo o dal nome del
file: i titoli possono cambiare, essere abbreviati o essere uguali. L'ID
Raindrop e i percorsi salvati nel manifest sono i riferimenti stabili.

### `files/`: contenuto HTML

Contiene una copia HTML dell'articolo. A seconda di `--source`, lo script prova
la copia permanente di Raindrop (`cache`), la pagina originale (`original`) o
entrambe (`both`, default dell'export generale). Per `export-domain` il source
predefinito è `original`.

Il file conserva HTML, non soltanto il testo visibile. Se la risposta non è
HTML, lo script la racchiude in una pagina HTML minima. Non è garantito che la
copia includa risorse esterne come immagini, CSS o JavaScript.

Esempio semplificato di `raindrop_articles/files/Titolo articolo.html`:

```html
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Titolo articolo</title>
</head>
<body>
  <h1>Titolo articolo</h1>
  <p>Questo è il contenuto originale della pagina scaricata.</p>
</body>
</html>
```

Il contenuto reale dipende dal sito sorgente e può essere molto più grande.

### `text/`: testo estratto

Contiene il testo leggibile estratto dalla pagina, senza il markup HTML. Prima
del corpo lo script aggiunge un'intestazione con:

- titolo;
- link originale;
- data `created` di Raindrop;
- eventuale `excerpt`;
- eventuale nota dell'articolo.

Questi `.txt` sono l'input principale usato da `extraction.py` per creare i
dataset JSONL.

Esempio di `raindrop_articles/text/Titolo articolo.txt`:

```text
Titolo articolo
https://example.com/articolo
Created: 2026-05-30T08:46:10.105Z

Breve descrizione salvata nel campo excerpt.

Note: Nota personale salvata in Raindrop.

---
Testo leggibile estratto dal corpo dell'articolo.
Questo testo non contiene i tag HTML della pagina originale.
```

Le prime righe sono l'intestazione aggiunta dal programma; dopo `---` comincia
il testo estratto dalla pagina.

### `json/`: metadati selezionati

Un file JSON viene creato soltanto se l'articolo ha almeno un tag o un
highlight. La struttura è:

```json
{
  "id": 1738177662,
  "title": "Titolo dell'articolo",
  "link": "https://example.com/articolo",
  "tags": ["tag-1", "tag-2"],
  "highlights": [
    {
      "id": "highlight-id",
      "text": "Testo evidenziato",
      "note": "Nota facoltativa",
      "color": "yellow",
      "created": "2026-05-30T08:47:00.287Z",
      "lastUpdate": "2026-05-30T08:48:55.380Z",
      "tags": ["tag-highlight"]
    }
  ]
}
```

Campi principali:

- `id`: identificatore univoco dell'articolo in Raindrop;
- `title`: titolo salvato in Raindrop;
- `link`: URL originale dell'articolo, non un highlight;
- `tags`: tag assegnati all'articolo;
- `highlights`: passaggi evidenziati in Raindrop;
- `highlights[].text`: testo del passaggio evidenziato;
- `highlights[].created` e `lastUpdate`: creazione e ultimo aggiornamento
  dell'highlight;
- `highlights[].note`, `color` e `tags`: nota, colore e tag propri
  dell'highlight.

### `articles.json`: catalogo locale completo

Viene creato o aggiornato con:

```bash
python3 raindrop.py update-articles
```

È un array degli oggetti `article` restituiti dall'API di Raindrop, arricchiti
con gli highlight. I campi più utili sono:

- `_id`: ID Raindrop;
- `title`, `link`, `domain`: titolo, URL e dominio;
- `excerpt`, `note`: descrizione breve e nota personale;
- `created`, `lastUpdate`: date Raindrop dell'articolo;
- `tags`: tag dell'articolo;
- `collection` e `collectionId`: raccolta di appartenenza;
- `cover` e `media`: copertina e media associati;
- `highlights`: highlight completi associati all'articolo;
- `type`: deve valere `article` per entrare nel catalogo;
- `downloaded_path`: campo storico eventualmente già presente nei dati locali;
  il codice attuale non lo legge e non lo aggiorna.

Esempio ridotto di `raindrop_articles/articles.json`. Le parentesi quadre
indicano che il file contiene un array, quindi molti oggetti articolo:

```json
[
  {
    "_id": 1738177662,
    "type": "article",
    "title": "Titolo articolo",
    "link": "https://example.com/articolo",
    "domain": "example.com",
    "excerpt": "Breve descrizione dell'articolo",
    "note": "Nota personale",
    "created": "2026-05-30T08:46:10.105Z",
    "lastUpdate": "2026-05-30T08:48:55.380Z",
    "tags": ["intelligenza-artificiale", "ricerca"],
    "collectionId": -1,
    "highlights": [
      {
        "_id": "6a1aa4042a78c8ebadcc2078",
        "text": "Passaggio evidenziato nell'articolo",
        "note": "Perché questo passaggio è importante",
        "color": "yellow",
        "created": "2026-05-30T08:47:00.287Z",
        "lastUpdate": "2026-05-30T08:48:55.380Z"
      }
    ]
  }
]
```

Se il catalogo esiste, gli export successivi lo riutilizzano. `--refresh` forza
prima il nuovo download del catalogo dall'API.

`highlights.json`, quando presente, conserva separatamente la risposta completa
dell'endpoint Raindrop degli highlight; `articles.json` ne contiene invece la
copia già associata al rispettivo articolo.

Esempio ridotto di `raindrop_articles/highlights.json`:

```json
[
  {
    "_id": "6a1aa4042a78c8ebadcc2078",
    "raindropRef": 1738177662,
    "text": "Passaggio evidenziato nell'articolo",
    "note": "Perché questo passaggio è importante",
    "color": "yellow",
    "created": "2026-05-30T08:47:00.287Z",
    "lastUpdate": "2026-05-30T08:48:55.380Z",
    "tags": ["dato-importante"]
  }
]
```

In questo esempio `raindropRef: 1738177662` collega l'highlight all'articolo
che in `articles.json` possiede `_id: 1738177662`.

### `articles.csv`: indice storico

Il file locale osservato ha queste colonne:

| Colonna | Significato |
| --- | --- |
| `id` | ID univoco Raindrop dell'articolo. |
| `title` | Titolo dell'articolo. |
| `link` | URL originale. |
| `domain` | Dominio ricavato o restituito da Raindrop. |
| `created` | Data di creazione/salvataggio in Raindrop, in formato ISO 8601. |
| `tags` | Tag dell'articolo serializzati in una cella. |
| `collection_id` | ID della collection; `-1` indica in genere la raccolta principale/non classificata. |
| `cache_status` | Stato della copia cache nel vecchio flusso; nel file presente risulta vuoto. |
| `downloaded_path` | Percorso HTML scaricato nel vecchio flusso. |
| `download_error` | Eventuale errore di download nel vecchio flusso. |

Esempio di `raindrop_articles/articles.csv` con intestazione e due record:

```csv
id,title,link,domain,created,tags,collection_id,cache_status,downloaded_path,download_error
1738177662,"Titolo articolo",https://example.com/articolo,example.com,2026-05-30T08:46:10.105Z,"intelligenza-artificiale, ricerca",-1,,raindrop_articles/files/Titolo articolo.html,
1737729848,"Articolo non scaricato",https://example.org/notizia,example.org,2026-05-29T21:30:25.367Z,notizie,-1,,,HTTP 403
```

Nel primo record `downloaded_path` contiene il vecchio percorso HTML e
`download_error` è vuoto. Nel secondo record non è stato registrato un file
scaricato e `download_error` contiene `HTTP 403`. Questo è soltanto un esempio
del formato storico: il programma attuale non produce queste righe.

Importante: nel codice Python attuale non c'è alcun lettore o writer di
`articles.csv`. Quindi oggi questo CSV **non** serve a decidere cosa è già stato
scaricato e non viene aggiornato dagli export. È un residuo/indice di una
versione precedente del flusso. Il tracciamento incrementale corrente avviene
esclusivamente tramite `manifest.json`.

## Esempi dei dataset JSONL derivati

`python3 extraction.py all` genera un file `*_articles.jsonl` in cui ogni riga
è un oggetto JSON completo e indipendente. Esempio di una singola riga:

```jsonl
{"id":1738177662,"title":"Titolo articolo","url":"https://example.com/articolo","label":"all","tag":"all","tags":["intelligenza-artificiale","ricerca"],"created":"2026-05-30T08:46:10.105Z","lastUpdate":"2026-05-30T08:48:55.380Z","domain":"example.com","excerpt":"Breve descrizione","note":"Nota personale","text":"Titolo articolo\nhttps://example.com/articolo\nCreated: 2026-05-30T08:46:10.105Z\n\n---\nTesto estratto...","highlights":[]}
```

Il corrispondente `*_chunks.jsonl` contiene più righe per lo stesso articolo.
Ogni riga rappresenta un segmento del testo:

```jsonl
{"article_id":1738177662,"chunk_id":"1738177662-0000","chunk_index":0,"title":"Titolo articolo","url":"https://example.com/articolo","label":"all","tag":"all","tags":["intelligenza-artificiale","ricerca"],"created":"2026-05-30T08:46:10.105Z","text":"Primo segmento del testo dell'articolo...","highlights":[]}
{"article_id":1738177662,"chunk_id":"1738177662-0001","chunk_index":1,"title":"Titolo articolo","url":"https://example.com/articolo","label":"all","tag":"all","tags":["intelligenza-artificiale","ricerca"],"created":"2026-05-30T08:46:10.105Z","text":"Secondo segmento, con una parte sovrapposta al precedente...","highlights":[]}
```

`article_id` collega tutti i chunk all'articolo originale; `chunk_index` indica
l'ordine e `chunk_id` combina ID articolo e numero progressivo del chunk.

## `manifest.json`: resume e aggiornamenti incrementali

Il manifest è il file operativo più importante dell'export. `items` è una
mappa indicizzata dall'ID Raindrop. Ogni voce contiene:

- `title`: titolo noto al momento dell'export;
- `html_path`, `text_path`, `json_path`: file associati; `json_path` è vuoto se
  l'articolo non ha tag né highlight;
- `article_signature`: hash **SHA-256** calcolato sui campi Raindrop `id`,
  `title`, `link`, `excerpt`, `note`, `created`, `lastUpdate` e `cache`. Serve a
  riconoscere una modifica ai dati dell'articolo e decidere se ripetere
  l'export;
- `metadata_signature`: hash **SHA-256** calcolato su `id`, `title`, `link`,
  `tags` e `highlights`, cioè sui dati destinati al file JSON di dettaglio.
  Serve a riconoscere modifiche a tag e highlight;
- `download_error`: ultimo errore di download, oppure stringa vuota;
- `resumed_from_existing`: quando presente, indica che file già esistenti sono
  stati adottati nel manifest;
- `updated_at`: istante UTC in cui quella voce è stata scritta o aggiornata.

### Esempio di `manifest.json`

Questo esempio mostra due articoli selezionati: il primo è stato scaricato e il
secondo è fallito:

```json
{
  "items": {
    "1738177662": {
      "title": "Titolo dell'articolo scaricato",
      "html_path": "raindrop_articles/files/Titolo dell'articolo scaricato.html",
      "text_path": "raindrop_articles/text/Titolo dell'articolo scaricato.txt",
      "json_path": "raindrop_articles/json/Titolo dell'articolo scaricato.json",
      "article_signature": "32e0e25b8fb7dc134866244e962b70b364773f61b11e2b2b6082dcf5e28bc715",
      "metadata_signature": "e1049de6052395565112e90b040566f912ec06b32ce73d2884053fd6b384a99d",
      "download_error": "",
      "resumed_from_existing": false,
      "updated_at": "2026-05-30T10:16:44Z"
    },
    "1737729848": {
      "title": "Titolo dell'articolo non scaricato",
      "html_path": "raindrop_articles/files/Titolo dell'articolo non scaricato.html",
      "text_path": "raindrop_articles/text/Titolo dell'articolo non scaricato.txt",
      "json_path": "",
      "article_signature": "35ff85a0949fb23dec4c8f8b9f6cbcc933791d17c7e0c03283d52b7e8cdffec6",
      "metadata_signature": "4381db73c6b5491631d8456ce59370cbb1808d81e916a221965cf55236b4e8b1",
      "download_error": "HTTP 403 while downloading the original article",
      "resumed_from_existing": false,
      "updated_at": "2026-05-30T10:16:45Z"
    }
  },
  "summary": {
    "articles": 2,
    "written": 1,
    "unchanged": 0,
    "failed": 1,
    "updated_at": "2026-05-30T10:16:45Z"
  }
}
```

La sezione `summary` contiene soltanto i **contatori dell'ultima esecuzione**;
non contiene il testo o la lista degli articoli:

- `articles: 2` significa che l'ultimo comando ha selezionato due articoli da
  elaborare. La selezione dipende dal comando (`tutti`, tag o dominio) e da un
  eventuale `--limit`;
- `written: 1` significa che per un articolo il download è riuscito e lo script
  ha scritto i file HTML e TXT, oltre al JSON quando richiesto. Il numero non
  contiene i dati dell'articolo: questi si trovano nella rispettiva voce di
  `items` e nei percorsi `html_path`, `text_path` e `json_path`;
- `unchanged: 0` significa che nessun articolo è stato lasciato invariato. Un
  articolo entra in questo conteggio quando signature e file coincidono già,
  oppure quando i file completi esistono e vengono adottati dal manifest con
  `resumed_from_existing: true`;
- `failed: 1` significa che un articolo non è stato esportato correttamente,
  per esempio per HTTP 403/404/500, timeout, TLS, contenuto non disponibile o
  ID Raindrop non valido. Il numero dice quanti errori ci sono, mentre il motivo
  si trova nella voce dell'articolo, nel campo `download_error`. In caso di
  fallimento i percorsi possono essere registrati nel manifest anche se i file
  corrispondenti non sono stati creati;
- `updated_at: "2026-05-30T10:16:45Z"` è la data e ora UTC in cui è terminata
  l'ultima esecuzione. La `Z` finale indica UTC.

Il controllo più utile è quindi partire da `summary.failed`. Se è maggiore di
zero, bisogna scorrere `items` e cercare le voci con `download_error` non vuoto.
Fa eccezione un record privo di `_id` numerico: viene contato come fallito, ma
non può essere inserito in `items` perché manca proprio l'ID da usare come
chiave.

Per elencare gli errori registrati nel manifest con `jq`:

```bash
jq '.items | to_entries[] | select(.value.download_error != "") |
    {id: .key, title: .value.title, error: .value.download_error}' \
  raindrop_articles/manifest.json
```

### Come vengono calcolate le signature

Entrambe sono hash crittografici **SHA-256**, rappresentati nel manifest come
64 caratteri esadecimali. Prima del calcolo, il programma costruisce un oggetto
con i soli campi elencati sotto, lo serializza in JSON con le chiavi ordinate,
mantiene i caratteri Unicode originali (`ensure_ascii=False`), converte il
risultato in byte UTF-8 e infine calcola SHA-256:

```python
encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
signature = hashlib.sha256(encoded).hexdigest()
```

`article_signature` include:

```text
id, title, link, excerpt, note, created, lastUpdate, cache
```

`metadata_signature` include esattamente i metadati del JSON per articolo. Gli
highlight comprendono a loro volta `id`, `text`, `note`, `color`, `created`,
`lastUpdate` e `tags`:

```text
id, title, link, tags, highlights
```

Lo script salta un articolo soltanto quando i file richiesti esistono **e** le
due signature coincidono con quelle nel manifest. Di conseguenza:

- una modifica a uno dei campi Raindrop elencati per l'articolo cambia
  `article_signature`;
- una modifica a tag o highlight cambia `metadata_signature`;
- un file mancante viene ricreato anche se le signature non sono cambiate;
- `--force` ignora il controllo e riscrive tutto.

La signature non è un hash del contenuto HTML scaricato: è un'impronta stabile
dei campi Raindrop elencati sopra. `updated_at` non entra nel calcolo.
