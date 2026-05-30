# Gestione Environment

Usiamo un virtual environment dedicato al progetto in:

```text
env/datasetenv
```

In questo modo le dipendenze restano separate da `base`, Conda e dagli altri
progetti.

## Creare L'Environment Minimo

Questo basta per usare `raindrop.py` e scaricare/esportare articoli.

```bash
python3 -m venv env/datasetenv
source env/datasetenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-export.txt
```

Verifica:

```bash
python -c "import dotenv; print('dotenv ok')"
python raindrop.py --help
```

## Usare L'Environment

```bash
source env/datasetenv/bin/activate
python raindrop.py export-domain repubblica.it
```

Oppure senza attivarlo:

```bash
env/datasetenv/bin/python raindrop.py export-domain repubblica.it
```

## Installare Lo Stack Dataset/RAG/Training

`requirements.txt` contiene pandas, datasets, transformers, accelerate, PEFT,
torch, sentence-transformers e FAISS. Installalo solo quando serve lavorare su
dataset, RAG o training.

```bash
source env/datasetenv/bin/activate
python -m pip install -r requirements.txt
```

Verifica:

```bash
python -c "import pandas, datasets, transformers, peft, accelerate; print('ml stack ok')"
```

## Aggiornare Dipendenze

Minimo export:

```bash
source env/datasetenv/bin/activate
python -m pip install --upgrade -r requirements-export.txt
```

Stack completo:

```bash
source env/datasetenv/bin/activate
python -m pip install --upgrade -r requirements.txt
```

Salvare le versioni effettivamente installate:

```bash
python -m pip freeze > requirements.lock.txt
```

Ripristinare esattamente quelle versioni:

```bash
python -m pip install -r requirements.lock.txt
```

## Cancellare L'Environment

Disattiva l'ambiente se e attivo:

```bash
deactivate
```

Poi elimina la directory:

```bash
rm -rf env/datasetenv
```

## Ricreare Da Zero

```bash
rm -rf env/datasetenv
python3 -m venv env/datasetenv
source env/datasetenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-export.txt
```

## Note GPU

`requirements.txt` installa la variante standard di `torch`. Per training su GPU,
installa PyTorch seguendo il comando adatto alla tua versione CUDA dal sito
ufficiale PyTorch, poi installa il resto:

```bash
python -m pip install -r requirements.txt
```
