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
```

Lo script carica sempre il file `.env` dalla root del progetto, cioe dalla
directory dove si trova `raindrop.py`.

Lo script legge anche `RAINDROP_ACCESS_TOKEN`, se preferisci usare quel nome.

Installa le dipendenze:

```bash
python3 -m pip install -r requirements.txt
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

Oppure per estrazione JSONL per tag:

```bash
python3 raindrop.py export-tag ukraine-war --cookies repubblica.it_cookies.txt
```

I cookie sono credenziali temporanee: non committarli e rigenerali quando la sessione scade.

## Estrazione Per Tag In JSONL

Per creare file pronti per pandas, Hugging Face Datasets, RAG o training:

```bash
python3 raindrop.py export-tag ukraine-war
```

Output:

```text
estrazione/
  README.md
  2026-05-30_ukraine-war_articles.jsonl
  2026-05-30_ukraine-war_chunks.jsonl
```

`*_articles.jsonl` contiene una riga per articolo completo.

`*_chunks.jsonl` contiene una riga per chunk di testo, piu utile per embedding e RAG.

Esempi:

```bash
# Solo primi 10 articoli del tag
python3 raindrop.py export-tag ukraine-war --limit 10

# Directory diversa
python3 raindrop.py export-tag ukraine-war --extract-output estrazione_ukraine

# Chunk piu piccoli
python3 raindrop.py export-tag ukraine-war --chunk-size 400 --chunk-overlap 50

# Con cookie browser per siti autenticati
python3 raindrop.py export-tag ukraine-war --cookies repubblica.it_cookies.txt
```

Il README dentro `estrazione/` contiene esempi per leggere i dati con pandas,
Hugging Face Datasets, un RAG minimale e un training di esempio con PEFT.

## Estrazione Per Dominio

Per esportare tutti gli articoli di un dominio, leggendo dal catalogo locale
`raindrop_articles/articles.json`:

```bash
python3 raindrop.py export-domain repubblica.it
```

Con questo comando breve lo script usa le convenzioni:

```text
Local export directory: raindrop_test_export
Extraction directory: estrazione_cookie
Cookies file: repubblica.it_cookies.txt
```

Le directory base devono gia esistere. Se `raindrop_test_export` o
`estrazione_cookie` non esistono, lo script va in errore invece di crearle
implicitamente.

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
  --extract-output estrazione_cookie \
  --source original \
  --cookies repubblica.it_cookies.txt
```

Questo crea contemporaneamente:

```text
raindrop_test_export/
  files/
  text/
  json/
  manifest.json

estrazione_cookie/
  README.md
  2026-05-30_repubblica.it_articles.jsonl
  2026-05-30_repubblica.it_chunks.jsonl
```

Test limitato:

```bash
python3 raindrop.py export-domain repubblica.it \
  --limit 1 \
  --output raindrop_test_export \
  --extract-output estrazione_cookie \
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
