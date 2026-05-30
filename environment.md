# Gestione Environment

Procedure consigliate per creare, aggiornare e cancellare ambienti Python per
analisi dati, RAG e training.

## Creare Con venv

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verifica:

```bash
python -c "import pandas, datasets, transformers, peft, accelerate; print('ok')"
```

## Usare L'Environment

```bash
source .venv/bin/activate
python3 raindrop.py export-tag ukraine-war --limit 10
```

## Aggiornare Dipendenze

Aggiorna usando i vincoli in `requirements.txt`:

```bash
source .venv/bin/activate
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
rm -rf .venv
```

## Creare Con Conda

```bash
conda create -n raindrop-dataset python=3.11
conda activate raindrop-dataset
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Aggiornare:

```bash
conda activate raindrop-dataset
python -m pip install --upgrade -r requirements.txt
```

Cancellare:

```bash
conda deactivate
conda env remove -n raindrop-dataset
```

## Note GPU

`requirements.txt` installa la variante standard di `torch`. Per training su GPU,
installa PyTorch seguendo il comando adatto alla tua versione CUDA dal sito
ufficiale PyTorch, poi installa il resto:

```bash
python -m pip install -r requirements.txt
```

Se lavori solo con pandas, dataset JSONL e RAG su CPU, la configurazione base e sufficiente.
