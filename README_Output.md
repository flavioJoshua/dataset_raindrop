# Output di `raindrop.py`

Questo documento descrive dove viene scritto l'output di `raindrop.py`, la
struttura delle directory e il ruolo dei file prodotti.

`raindrop.py` estrae dall'account Raindrop.io il catalogo degli articoli con
tag e highlight, scarica il contenuto dalla cache di Raindrop o dai siti
originali e costruisce un archivio locale. L'archivio è aggiornabile: tramite
`manifest.json` il programma riconosce gli articoli invariati, nuovi, modificati
o con file mancanti, evitando di riscaricare inutilmente l'intera raccolta.

Il ciclo di aggiornamento consigliato è:

```bash
python3 raindrop.py update-articles  # aggiorna il catalogo da Raindrop
python3 raindrop.py                  # aggiorna l'archivio locale
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

Questo comando aggiorna soltanto il catalogo dei metadati: non scarica HTML o
testo e non modifica il manifest. Il successivo `python3 raindrop.py` legge
`articles.json` e aggiorna incrementalmente `files/`, `text/`, `json/` e
`manifest.json`.

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

Il default dipende dal comando:

| Comando | Directory predefinita |
| --- | --- |
| `python3 raindrop.py` | `raindrop_articles/` |
| `python3 raindrop.py export-tag <tag>` | `raindrop_articles/` |
| `python3 raindrop.py update-articles` | aggiorna il catalogo in `raindrop_articles/` |
| `python3 raindrop.py export-domain <dominio>` | `raindrop_test_export/` |

L'opzione `--output <directory>` sostituisce sempre il default. Per esempio:

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
  --cookies repubblica.it_cookies.txt
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

| File o percorso predefinito | Può cambiare? | Chi lo crea o aggiorna | Quali dati contiene | Come si collega agli altri dati | Funzione principale |
| --- | --- | --- | --- | --- | --- |
| `raindrop_articles/articles.json` | Sì. `--articles-file` cambia nome e percorso. | `python3 raindrop.py update-articles` oppure un export con `--refresh`. | Catalogo completo degli articoli: `_id`, titolo, link, dominio, date, tag, collection, excerpt, note, media e highlight associati. | `_id` è l'ID dell'articolo. Corrisponde alla chiave in `manifest.json` e al campo `id` nei JSON di dettaglio. | Fonte dei metadati usata dagli export e da `extraction.py`. |
| `raindrop_articles/highlights.json` | La directory segue `--articles-file`, ma il nome resta `highlights.json`. | `update-articles` o `--refresh`. | Elenco completo e separato degli highlight restituiti dall'API Raindrop. | `raindropRef` identifica l'articolo; corrisponde a `_id` in `articles.json`. | Conservare la risposta completa degli highlight e permettere elaborazioni specifiche. |
| `<output>/manifest.json` | La directory cambia con `--output`; il nome resta `manifest.json`. | Ogni export eseguito da `raindrop.py`. | Una voce per articolo con titolo, percorsi HTML/TXT/JSON, signature, errore e data di aggiornamento; contiene anche il riepilogo dell'ultimo export. | La chiave di `items`, per esempio `"1738177662"`, è l'ID Raindrop. I campi `html_path`, `text_path` e `json_path` portano direttamente ai file di dettaglio. | Indice operativo, resume, controllo delle modifiche e accesso ai file di ogni articolo. |
| `<output>/files/<nome>.html` | Sì. Directory con `--output`; nome generato dal titolo e, quando necessario, dall'ID. | Export di `raindrop.py`. | Copia HTML scaricata dalla cache Raindrop o dal sito originale. | Il percorso esatto è in `manifest.json → items → <ID> → html_path`. | Conservare la pagina originale per consultazione o nuova estrazione. |
| `<output>/text/<nome>.txt` | Sì. Directory con `--output`; nome generato come quello HTML. | Export di `raindrop.py`. | Titolo, link, data Raindrop, eventuali excerpt e nota, seguiti dal testo estratto dall'articolo. | Il percorso esatto è in `manifest.json → items → <ID> → text_path`. `extraction.py` usa questo collegamento. | Testo pulito per ricerca, dataset JSONL, RAG, embeddings e training. |
| `<output>/json/<nome>.json` | Sì. Directory con `--output`; nome generato come quello HTML. Il file può non esistere. | Export di `raindrop.py`, soltanto se esistono tag o highlight. | `id`, `title`, `link`, `tags` e `highlights`, comprese date, note, colori e tag degli highlight. | `id` corrisponde alla chiave del manifest e a `_id` nel catalogo. Il percorso è in `json_path`; se non serve un JSON, `json_path` è vuoto. | Metadati compatti di dettaglio per un singolo articolo. |
| `raindrop_articles/articles.csv` | È un file storico; il codice attuale non ne gestisce nome o percorso. | Non viene creato né aggiornato dal codice attuale. | Vecchio indice tabellare con ID, titolo, link, dominio, data, tag, collection e vecchi campi di download. | `id` può essere collegato a `_id` del catalogo e alla chiave del manifest, ma i dati possono essere obsoleti. | Compatibilità o analisi storica; non deve essere usato per il resume corrente. |
| `<dataset>/<selezione>_articles.jsonl` | Sì, tramite `extraction.py --output`; il prefisso dipende dalla selezione. | `extraction.py all`, `tag` o `domain`. | Una riga JSON per articolo selezionato, con metadati e testo completo. | Deriva da `articles.json`; il testo viene trovato tramite `manifest.json` e `text_path`. | Dataset finale a livello di articolo. |
| `<dataset>/<selezione>_chunks.jsonl` | Sì, tramite `extraction.py --output`; nome legato alla selezione. | `extraction.py all`, `tag` o `domain`. | Più righe per articolo, ottenute suddividendo il testo in chunk sovrapposti. | Ogni chunk mantiene l'identità dell'articolo sorgente. | Dataset per RAG, indicizzazione, embeddings e training a segmenti. |

### Dal manifest ai dati di un articolo

Il collegamento affidabile tra tutti i file è l'ID Raindrop. Per esempio, per
l'articolo con ID `1738177662`:

```text
manifest.json
└── items
    └── "1738177662"
        ├── html_path ──> files/<nome>.html
        ├── text_path ──> text/<nome>.txt
        └── json_path ──> json/<nome>.json

articles.json
└── articolo con _id = 1738177662

json/<nome>.json
└── id = 1738177662
```

Una procedura automatica dovrebbe quindi:

1. aprire `manifest.json`;
2. scorrere le coppie `ID → voce` contenute in `items`;
3. usare `text_path`, `html_path` o `json_path` per leggere il dettaglio
   desiderato;
4. cercare lo stesso ID come `_id` in `articles.json` quando servono tutti i
   metadati Raindrop;
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

Se il catalogo esiste, gli export successivi lo riutilizzano. `--refresh` forza
prima il nuovo download del catalogo dall'API.

`highlights.json`, quando presente, conserva separatamente la risposta completa
dell'endpoint Raindrop degli highlight; `articles.json` ne contiene invece la
copia già associata al rispettivo articolo.

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

Importante: nel codice Python attuale non c'è alcun lettore o writer di
`articles.csv`. Quindi oggi questo CSV **non** serve a decidere cosa è già stato
scaricato e non viene aggiornato dagli export. È un residuo/indice di una
versione precedente del flusso. Il tracciamento incrementale corrente avviene
esclusivamente tramite `manifest.json`.

## `manifest.json`: resume e aggiornamenti incrementali

Il manifest è il file operativo più importante dell'export. `items` è una
mappa indicizzata dall'ID Raindrop. Ogni voce contiene:

- `title`: titolo noto al momento dell'export;
- `html_path`, `text_path`, `json_path`: file associati; `json_path` è vuoto se
  l'articolo non ha tag né highlight;
- `article_signature`: impronta dei dati dell'articolo che possono richiedere
  un nuovo download;
- `metadata_signature`: impronta dei metadati scritti nel JSON;
- `download_error`: ultimo errore di download, oppure stringa vuota;
- `resumed_from_existing`: quando presente, indica che file già esistenti sono
  stati adottati nel manifest;
- `updated_at`: istante UTC in cui quella voce è stata scritta o aggiornata.

La sezione `summary` descrive l'ultimo lancio:

- `articles`: articoli selezionati;
- `written`: articoli scritti;
- `unchanged`: articoli saltati perché invariati o adottati perché completi;
- `failed`: articoli falliti;
- `updated_at`: fine dell'ultimo export, in UTC.

### Come vengono calcolate le signature

Entrambe sono hash SHA-256 di un JSON serializzato con chiavi ordinate e UTF-8.

`article_signature` include:

```text
id, title, link, excerpt, note, created, lastUpdate, cache
```

`metadata_signature` include esattamente i metadati del JSON per articolo:

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
