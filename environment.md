# Gestione Environment

Puoi usare un virtual environment `venv` oppure un ambiente Conda dedicato.
Le due strade sono alternative:

- `venv` usa `requirements-export.txt` e `requirements.txt`;
- Conda usa `environment-export.yml` e `environment.yml`.

L'importante e non installare le dipendenze nel `base` environment.

Con `venv` l'ambiente locale del progetto vive in:

```text
env/datasetenv
```

Con Conda useremo invece un ambiente chiamato:

```text
datasetenv
```

In entrambi i casi le dipendenze restano separate dagli altri progetti.

## Opzione 1: Creare L'Environment Minimo Con venv

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

## Opzione 2: Creare L'Environment Minimo Con Conda

Questo crea da zero un ambiente Conda isolato. Uso Python 3.11 per restare su
una versione molto compatibile con lo stack ML/RAG.

```bash
conda env create -f environment-export.yml
conda activate datasetenv
```

Verifica:

```bash
python -c "import dotenv; print('dotenv ok')"
python raindrop.py --help
```

## Usare L'Environment venv

```bash
source env/datasetenv/bin/activate
python raindrop.py export-domain repubblica.it
```

Oppure senza attivarlo:

```bash
env/datasetenv/bin/python raindrop.py export-domain repubblica.it
```

## Usare L'Environment Conda

```bash
conda activate datasetenv
python raindrop.py export-domain repubblica.it
```

## Installare Lo Stack Dataset/RAG/Training

`requirements.txt` contiene pandas, datasets, transformers, accelerate, PEFT,
torch, sentence-transformers e FAISS. Installalo solo quando serve lavorare su
dataset, RAG o training.

Con `venv`:

```bash
source env/datasetenv/bin/activate
python -m pip install -r requirements.txt
```

Con Conda:

```bash
conda env update -f environment.yml --prune
conda activate datasetenv
```

Se invece vuoi creare direttamente l'ambiente Conda completo da zero:

```bash
conda env create -f environment.yml
conda activate datasetenv
```

Verifica:

```bash
python -c "import pandas, datasets, transformers, peft, accelerate; print('ml stack ok')"
```

## Aggiornare Dipendenze Con venv

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

## Aggiornare Dipendenze Con Conda

Minimo export:

```bash
conda env update -f environment-export.yml --prune
```

Stack completo:

```bash
conda env update -f environment.yml --prune
```

Se cambi anche la versione di Python in `environment.yml`, applicala con lo
stesso comando:

```bash
conda env update -f environment.yml --prune
```

In pratica, modifichi `environment*.yml` e poi riesegui `conda env update`.
Questo lascia a Conda il tracciamento e la risoluzione delle dipendenze.

## Salvare E Ripristinare Le Versioni

Per `venv`, funziona purche l'ambiente corretto sia attivo.

Salvare le versioni effettivamente installate:

```bash
python -m pip freeze > requirements.lock.txt
```

Ripristinare esattamente quelle versioni:

```bash
python -m pip install -r requirements.lock.txt
```

Per Conda, il file sorgente resta `environment.yml`. Se vuoi anche salvare una
fotografia esatta dell'ambiente risolto sulla tua macchina:

```bash
conda activate datasetenv
conda env export > environment-conda.lock.yml
```

E ripristinarla su una macchina nuova:

```bash
conda env create -f environment-conda.lock.yml
```

## Cancellare L'Environment venv

Disattiva l'ambiente se e attivo:

```bash
deactivate
```

Poi elimina la directory:

```bash
rm -rf env/datasetenv
```

## Cancellare L'Environment Conda

Disattiva l'ambiente se e attivo:

```bash
conda deactivate
```

Poi elimina l'ambiente:

```bash
conda env remove -n datasetenv
```

Verifica che non compaia piu nella lista:

```bash
conda env list
```

## Ricreare Da Zero Con venv

```bash
rm -rf env/datasetenv
python3 -m venv env/datasetenv
source env/datasetenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-export.txt
```

## Ricreare Da Zero Con Conda

```bash
conda deactivate
conda env remove -n datasetenv
conda env create -f environment-export.yml
conda activate datasetenv
```

## Note GPU

`requirements.txt` e `environment.yml` installano la variante standard di
PyTorch. Per training su GPU, usa il comando adatto alla tua versione CUDA dal
sito ufficiale PyTorch.

Con `venv`, installa prima PyTorch come indicato dal sito ufficiale, poi:

```bash
python -m pip install -r requirements.txt
```

Con Conda, modifica `environment.yml` con i pacchetti/canali PyTorch corretti
per CUDA, poi:

```bash
conda env update -f environment.yml --prune
```
