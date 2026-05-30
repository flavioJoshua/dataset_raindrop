#!/usr/bin/env python3
"""Create JSONL datasets from local Raindrop exports.

This script does not call Raindrop.io and does not download articles. It reads
the local catalog and manifest written by raindrop.py, then creates JSONL files
for pandas, Hugging Face Datasets, RAG, embeddings, and training workflows.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from utility import RaindropError, chunk_text, load_manifest, safe_filename, write_jsonl


DEFAULT_EXPORT_DIR = "raindrop_articles"
DEFAULT_EXTRACTION_DIR = "estrazione"


def normalize_highlight(highlight: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": highlight.get("_id", ""),
        "text": highlight.get("text", ""),
        "note": highlight.get("note", ""),
        "color": highlight.get("color", ""),
        "created": highlight.get("created", ""),
        "lastUpdate": highlight.get("lastUpdate", ""),
        "tags": highlight.get("tags") or [],
    }


def article_highlights(item: dict[str, Any]) -> list[dict[str, Any]]:
    highlights = item.get("highlights") or []
    if not isinstance(highlights, list):
        return []
    return [normalize_highlight(row) for row in highlights if isinstance(row, dict)]


def article_record(item: dict[str, Any], *, label: str, text: str) -> dict[str, Any]:
    return {
        "id": item.get("_id"),
        "title": item.get("title", ""),
        "url": item.get("link", ""),
        "label": label,
        "tag": label,
        "tags": item.get("tags") or [],
        "created": item.get("created", ""),
        "lastUpdate": item.get("lastUpdate", ""),
        "domain": item.get("domain", ""),
        "excerpt": item.get("excerpt", ""),
        "note": item.get("note", ""),
        "text": text,
        "highlights": article_highlights(item),
    }


def chunk_records(article: dict[str, Any], *, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    chunks = chunk_text(str(article.get("text") or ""), chunk_size=chunk_size, overlap=overlap)
    article_id = article.get("id")
    records: list[dict[str, Any]] = []
    for index, text in enumerate(chunks):
        records.append(
            {
                "article_id": article_id,
                "chunk_id": f"{article_id}-{index:04d}",
                "chunk_index": index,
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "label": article.get("label", ""),
                "tag": article.get("tag", ""),
                "tags": article.get("tags") or [],
                "created": article.get("created", ""),
                "text": text,
                "highlights": article.get("highlights") or [],
            }
        )
    return records


def tag_matches(item: dict[str, Any], tag: str) -> bool:
    target = tag.casefold()
    return any(str(value).casefold() == target for value in item.get("tags") or [])


def domain_matches(item: dict[str, Any], domain: str) -> bool:
    target = domain.removeprefix("www.").casefold()
    item_domain = str(item.get("domain") or "").removeprefix("www.").casefold()
    if item_domain == target or item_domain.endswith(f".{target}"):
        return True

    link = str(item.get("link") or "")
    hostname = urlparse(link).hostname or ""
    hostname = hostname.removeprefix("www.").casefold()
    return hostname == target or hostname.endswith(f".{target}")


def load_articles(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise RaindropError(f"Articles catalog not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RaindropError(f"Invalid articles catalog: {path} is not a list")
    return [row for row in data if isinstance(row, dict)]


def resolve_text_path(raw_path: str, *, export_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if path.exists():
        return path
    candidate = export_dir / path
    if candidate.exists():
        return candidate
    return path


def manifest_text_paths(export_dir: Path) -> dict[int, Path]:
    manifest_path = export_dir / "manifest.json"
    manifest = load_manifest(manifest_path)
    text_paths: dict[int, Path] = {}
    for raw_id, manifest_item in manifest.get("items", {}).items():
        if not isinstance(manifest_item, dict):
            continue
        raw_text_path = manifest_item.get("text_path")
        if not isinstance(raw_text_path, str) or not raw_text_path:
            continue
        try:
            article_id = int(raw_id)
        except ValueError:
            continue
        text_path = resolve_text_path(raw_text_path, export_dir=export_dir)
        if text_path.exists():
            text_paths[article_id] = text_path
    return text_paths


def extraction_base_name(label: str) -> str:
    return f"{date.today().isoformat()}_{safe_filename(label, max_length=80)}"


def write_extraction_readme(path: Path) -> None:
    readme = """# Estrazione JSONL

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
"""
    path.write_text(readme, encoding="utf-8")


def select_articles(articles: list[dict[str, Any]], mode: str, selector: str) -> tuple[str, list[dict[str, Any]]]:
    if mode == "all":
        return "all", articles
    if not selector:
        raise RaindropError(f"Missing selector. Usage: python3 extraction.py {mode} <value>")
    if mode == "tag":
        return selector, [item for item in articles if tag_matches(item, selector)]
    if mode == "domain":
        return selector, [item for item in articles if domain_matches(item, selector)]
    raise RaindropError(f"Unknown extraction mode: {mode}")


def write_dataset(
    articles: list[dict[str, Any]],
    text_paths: dict[int, Path],
    *,
    label: str,
    output_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_extraction_readme(output_dir / "README.md")

    article_records: list[dict[str, Any]] = []
    missing_text = 0
    for item in articles:
        article_id = item.get("_id")
        if not isinstance(article_id, int):
            missing_text += 1
            continue
        text_path = text_paths.get(article_id)
        if text_path is None:
            missing_text += 1
            continue
        text = text_path.read_text(encoding="utf-8")
        article_records.append(article_record(item, label=label, text=text))

    base_name = extraction_base_name(label)
    articles_path = output_dir / f"{base_name}_articles.jsonl"
    chunks_path = output_dir / f"{base_name}_chunks.jsonl"
    chunks = [
        chunk
        for article in article_records
        for chunk in chunk_records(article, chunk_size=chunk_size, overlap=chunk_overlap)
    ]

    write_jsonl(articles_path, article_records)
    write_jsonl(chunks_path, chunks)

    print(f"Wrote {len(article_records)} article rows to {articles_path}")
    print(f"Wrote {len(chunks)} chunk rows to {chunks_path}")
    if missing_text:
        print(f"Skipped {missing_text} articles without local TXT files", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create JSONL datasets from local Raindrop exports without downloading."
    )
    parser.add_argument(
        "mode",
        choices=("all", "tag", "domain"),
        help="Dataset selection mode.",
    )
    parser.add_argument(
        "selector",
        nargs="?",
        help="Tag name for 'tag' mode or domain name for 'domain' mode.",
    )
    parser.add_argument(
        "--articles-file",
        default=f"{DEFAULT_EXPORT_DIR}/articles.json",
        help="Local Raindrop articles catalog JSON.",
    )
    parser.add_argument(
        "--export-dir",
        default=DEFAULT_EXPORT_DIR,
        help="Local export directory containing manifest.json and text files.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_EXTRACTION_DIR,
        help="Output directory for JSONL dataset files.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=700,
        help="Approximate chunk size in words. Default: 700",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=100,
        help="Chunk overlap in words. Default: 100",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N selected articles. Useful for testing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    articles = load_articles(Path(args.articles_file))
    label, selected_articles = select_articles(articles, args.mode, args.selector or "")
    if args.limit and args.limit > 0:
        selected_articles = selected_articles[: args.limit]

    print(f"Found {len(selected_articles)} articles for {args.mode} '{label}'")
    write_dataset(
        selected_articles,
        manifest_text_paths(Path(args.export_dir)),
        label=label,
        output_dir=Path(args.output),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RaindropError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
