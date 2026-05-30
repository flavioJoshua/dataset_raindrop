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

## Training PEFT + Transformers

Questo e solo un esempio minimale. Per un training reale serve definire bene il task,
validare la qualita dei testi e creare split train/validation.

```python
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

model_name = "Qwen/Qwen2.5-0.5B"
dataset = load_dataset("json", data_files="2026-05-30_tag_chunks.jsonl", split="train")

tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

def tokenize(batch):
    return tokenizer(batch["text"], truncation=True, max_length=1024)

tokenized = dataset.map(tokenize, batched=True, remove_columns=dataset.column_names)
model = AutoModelForCausalLM.from_pretrained(model_name)

peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, peft_config)

args = TrainingArguments(
    output_dir="runs/raindrop-peft",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    num_train_epochs=1,
    logging_steps=10,
    save_steps=200,
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)
trainer.train()
model.save_pretrained("runs/raindrop-peft/final")
```
