# Export Cookie Per Articoli Autenticati

Questa procedura serve per scaricare articoli che richiedono login usando una
sessione browser gia autenticata, senza inserire user e password nello script.

I cookie sono credenziali temporanee: trattali come una password.

## 1. Login Nel Browser

1. Apri Firefox.
2. Vai su `https://www.repubblica.it`.
3. Fai login con il tuo account.
4. Apri un articolo che richiede autenticazione e verifica che sia leggibile nel browser.

Firefox e consigliato perche l'esportazione in formato `cookies.txt` tende a
essere piu semplice. Chrome va bene, ma spesso richiede piu attenzione con
profili, permessi ed estensioni.

## 2. Installa Un Exporter Cookies.txt

Installa una estensione che esporta cookie in formato Netscape `cookies.txt`.

Parole chiave da cercare:

```text
Get cookies.txt LOCALLY
cookies.txt
Netscape cookies.txt
```

L'estensione giusta deve permettere di esportare/scaricare un file simile a:

```text
# Netscape HTTP Cookie File
.repubblica.it	TRUE	/	TRUE	1780000000	nome_cookie	valore_cookie
```

Non serve una estensione che abilita/disabilita i cookie: serve proprio una
funzione di export/download.

## 3. Esporta I Cookie

1. Resta su una pagina di `www.repubblica.it`.
2. Apri l'estensione.
3. Esporta i cookie del sito corrente o del dominio `repubblica.it`.
4. Salva il file in questa cartella:

```text
/home/flavio/Documents/code/dataset/
```

Nome consigliato:

```text
repubblica.it_cookies.txt
```

## 4. Verifica Il File

Dal progetto:

```bash
cd /home/flavio/Documents/code/dataset
test -f repubblica.it_cookies.txt
```

Verifica che lo script riesca a caricarlo senza stampare i valori dei cookie:

```bash
python3 -c "import raindrop; raindrop.load_cookie_jar('repubblica.it_cookies.txt')"
```

Output atteso:

```text
Loaded N cookies from repubblica.it_cookies.txt
```

Se vedi un errore sul formato, riesporta il file assicurandoti che sia in
formato Netscape `cookies.txt`.

## 5. Usa I Cookie Con Lo Script

Per esportare tutti gli articoli usando i cookie quando scarica le pagine:

```bash
python3 raindrop.py --cookies repubblica.it_cookies.txt
```

Per forzare il download dal sito originale, invece della cache Raindrop:

```bash
python3 raindrop.py --source original --cookies repubblica.it_cookies.txt
```

Per estrarre un tag in JSONL:

```bash
python3 raindrop.py export-tag ukraine-war \
  --source original \
  --cookies repubblica.it_cookies.txt
```

Test limitato:

```bash
python3 raindrop.py export-tag ukraine-war \
  --limit 1 \
  --source original \
  --cookies repubblica.it_cookies.txt \
  --extract-output estrazione_cookie_test
```

## 6. Quando Rigenerare I Cookie

Rigenera il file cookie quando:

- lo script scarica pagine di login invece degli articoli;
- il testo esportato sembra incompleto;
- hai fatto logout dal browser;
- sono passati molti giorni;
- il sito ha invalidato la sessione.

Procedura: fai di nuovo login nel browser ed esporta un nuovo `cookies.txt`.

## 7. Sicurezza

Non committare mai file cookie.

Il progetto ignora gia questi file:

```gitignore
cookies.txt
*cookies.txt
```

Non inviare il file cookie in chat, email o issue pubbliche. Chi possiede quel
file puo potenzialmente usare la tua sessione finche resta valida.

Per cancellare i cookie esportati:

```bash
rm repubblica.it_cookies.txt
```

## 8. Limiti

I cookie non garantiscono sempre accesso completo:

- alcuni siti caricano contenuto via JavaScript;
- alcuni sistemi anti-bot possono bloccare richieste non fatte dal browser;
- alcuni contenuti possono dipendere da header, geolocalizzazione o stato account;
- sessioni scadute producono pagine login o paywall.

Usa questa procedura rispettando i termini del sito e i diritti d'uso dei
contenuti scaricati.
