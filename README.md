# Raindrop Article Export

Script Python per esportare gli articoli salvati su Raindrop.io in locale.

Per ogni articolo esporta:

- una copia HTML locale in `raindrop_articles/files/`
- una versione testo in `raindrop_articles/text/`
- un file JSON in `raindrop_articles/json/` solo se l'articolo ha tag o highlight
- un manifest incrementale in `raindrop_articles/manifest.json`

## Setup

Crea un file `.env` nella stessa directory di `raindrop.py`:

```bash
RAINDROP_TOKEN=il_tuo_token_raindrop
RAINDROP_LOG_DIR=logs
RAINDROP_LOG_MAX_LINES=3000
RAINDROP_DOWNLOAD_DELAY_MS=0
RAINDROP_DOWNLOAD_JITTER_MS=0
RAINDROP_REQUEST_TIMEOUT_SECONDS=25
RAINDROP_REQUEST_RETRIES=2
```

Lo script carica sempre il file `.env` dalla root del progetto, cioe dalla
directory dove si trova `raindrop.py`.

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

La directory si configura con:

```bash
RAINDROP_LOG_DIR=logs
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

Per siti che richiedono autenticazione, non mettere user/password nello script.
Esporta invece i cookie dal browser in formato Netscape `cookies.txt`.

Esempio con il file:

```text
repubblica.it_cookies.txt
```

Uso:

```bash
python3 raindrop.py --cookies repubblica.it_cookies.txt
```

Oppure per scaricare/cache gli articoli di un tag che richiedono cookie:

```bash
python3 raindrop.py export-tag ukraine-war --cookies repubblica.it_cookies.txt
```

I cookie sono credenziali temporanee: non committarli e rigenerali quando la sessione scade.

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
Cookies file: repubblica.it_cookies.txt
```

Il nome cookie predefinito e:

```text
<dominio>_cookies.txt
```

Quindi per `repubblica.it`:

```text
repubblica.it_cookies.txt
```

Esempio esplicito, utile se vuoi cambiare percorsi o usare un nome cookie diverso:

```bash
python3 raindrop.py export-domain repubblica.it \
  --output raindrop_test_export \
  --source original \
  --cookies repubblica.it_cookies.txt
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
  --cookies repubblica.it_cookies.txt
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
