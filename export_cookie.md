# Cookie per articoli autenticati

Questa procedura permette a `raindrop.py` di usare le sessioni già aperte in
Firefox per scaricare articoli che richiedono login. I cookie sono credenziali
temporanee: trattarli come password.

## 1. Esportare da Firefox

1. Installare dal sito ufficiale Mozilla
   [Get cookies.txt LOCALLY](https://addons.mozilla.org/firefox/addon/get-cookies-txt-locally/).
2. Accedere al primo sito, per esempio `repubblica.it`, e verificare che un
   articolo riservato sia leggibile nel browser.
3. Aprire l'estensione dalla scheda del sito ed esportare i cookie del dominio
   in formato **Netscape**, non JSON.
4. Ripetere l'operazione per ogni altro sito autenticato, per esempio
   `medium.com`.

Un file Netscape ha una struttura simile:

```text
# Netscape HTTP Cookie File
.repubblica.it	TRUE	/	TRUE	1780000000	nome_cookie	valore_cookie
```

## 2. Directory obbligatoria

Salvare tutti i file esclusivamente nella directory `cookie/` della root del
progetto:

```text
dataset/
├── raindrop.py
├── .env
└── cookie/
    ├── repubblica.it_cookies.txt
    └── medium.com_cookies.txt
```

Il nome può essere scelto liberamente, purché termini in `.txt`. Usare il
dominio nel nome rende chiaro a quale sessione appartiene.

I cookie lasciati nella root o in altre directory non vengono letti.

## 3. Come funziona `--cookies`

`--cookies` è un interruttore e non accetta un percorso:

```bash
python3 raindrop.py --cookies
```

Quando l'opzione è presente, lo script:

1. apre `cookie/`;
2. carica tutti i file `*.txt` in formato Netscape;
3. unisce i cookie in un solo cookie jar;
4. invia a ogni sito soltanto i cookie validi per il suo dominio e percorso.

Nell'esempio, la stessa esecuzione usa i cookie di Repubblica per
`repubblica.it` e quelli di Medium per `medium.com`.

Senza `--cookies`, nessun file della directory viene caricato. Se l'opzione è
presente ma la directory manca, è vuota o contiene un `.txt` non valido, il
programma termina con un errore.

`--cookies` non implica `--force`: abilita i cookie, poi mantiene il normale
controllo del manifest. Per riscaricare tutti gli articoli dal sito originale
usando i cookie:

```bash
python3 raindrop.py --source original --cookies --force
```

## 4. Verificare tutti i file

Dalla root del progetto:

```bash
python3 -c "from utility import PROJECT_ROOT, load_cookie_directory; load_cookie_directory(PROJECT_ROOT / 'cookie')"
```

Output di esempio:

```text
Loaded 12 cookies from cookie/repubblica.it_cookies.txt
Loaded 5 cookies from cookie/medium.com_cookies.txt
Loaded 17 cookies from 2 files in /home/flavio/Documents/code/dataset/cookie
```

Non stampare il contenuto dei file nel terminale o nei log.

## 5. Usare tutti i cookie

Export generale dal sito originale:

```bash
python3 raindrop.py --source original --cookies
```

Export limitato a un tag:

```bash
python3 raindrop.py export-tag ukraine-war \
  --source original \
  --cookies
```

Test di un dominio su un solo articolo:

```bash
python3 raindrop.py export-domain repubblica.it \
  --limit 1 \
  --source original \
  --cookies
```

Anche nell'export di un singolo dominio vengono caricati tutti i file di
`cookie/`; il cookie jar utilizza però soltanto quelli compatibili con gli URL
richiesti.

## 6. Quando rigenerarli

Rieseguire login ed esportazione quando:

- lo script scarica una pagina di login o paywall;
- il testo esportato è incompleto;
- si è fatto logout dal browser;
- il sito ha invalidato la sessione;
- il download restituisce HTTP 401 o 403.

I cookie non superano necessariamente pagine che dipendono da JavaScript,
header speciali, geolocalizzazione o controlli anti-bot.

## 7. Sicurezza

La directory `cookie/` è esclusa da Git tramite `.gitignore`. Controllare
comunque `git status` prima di ogni commit. Non condividere mai questi file in
chat, email, issue o ticket: chi li possiede può utilizzare la sessione finché
rimane valida.
