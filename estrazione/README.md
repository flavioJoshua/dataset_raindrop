# Estrazione JSONL

Questa directory contiene dataset derivati da `raindrop_articles/`.
`extraction.py` non scarica dati da Raindrop.io: legge il catalogo locale,
il manifest e i file `.txt` prodotti da `raindrop.py`.

## File

- `*_articles.jsonl`: una riga JSON per articolo completo.
- `*_chunks.jsonl`: una riga JSON per chunk di testo, piu adatto a RAG ed embedding.

## Pandas

```python
import pandas as pd

df = pd.read_json("2026-05-30_tag_articles.jsonl", lines=True)
print(df[["id", "title", "url", "tags"]].head())
```

## Hugging Face Datasets

```python
from datasets import load_dataset

dataset = load_dataset("json", data_files="2026-05-30_tag_chunks.jsonl", split="train")
print(dataset[0])
```

## RAG Semplice

```python
import faiss
import numpy as np
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

data = load_dataset("json", data_files="2026-05-30_tag_chunks.jsonl", split="train")
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

embeddings = model.encode(data["text"], normalize_embeddings=True, show_progress_bar=True)
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(np.asarray(embeddings, dtype="float32"))

query = "Quali sono i punti principali?"
query_embedding = model.encode([query], normalize_embeddings=True)
scores, ids = index.search(np.asarray(query_embedding, dtype="float32"), k=5)

for score, idx in zip(scores[0], ids[0]):
    row = data[int(idx)]
    print(score, row["title"], row["url"])
    print(row["text"][:500])
```
