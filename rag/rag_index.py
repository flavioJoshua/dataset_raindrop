#!/usr/bin/env python3
"""Build FAISS index from estrazione/*_chunks.jsonl files.

Embeds title + text for each chunk using a transformer encoder via rag_embedder.
Saves the FAISS index and metadata to disk so rag_app.py can load them
without re-indexing on every run.

Usage:
    python3 rag_index.py
    python3 rag_index.py --estrazione estrazione --output rag_index
    python3 rag_index.py --model sentence-transformers/paraphrase-multilingual-mpnet-base-v2
    python3 rag_index.py --pooling cls
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import faiss
import numpy as np

from rag_embedder import Embedder

DEFAULT_ESTRAZIONE_DIR = "estrazione"
DEFAULT_INDEX_DIR = "rag_index"
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FAISS_INDEX_FILE = "index.faiss"
METADATA_FILE = "metadata.json"
MODEL_FILE = "model_name.txt"
POOLING_FILE = "pooling.txt"


def load_chunks(estrazione_dir: Path) -> list[dict]:
    chunks = []
    jsonl_files = sorted(estrazione_dir.glob("*_chunks.jsonl"))
    if not jsonl_files:
        print(f"No *_chunks.jsonl files found in {estrazione_dir}", file=sys.stderr)
        sys.exit(1)

    for path in jsonl_files:
        print(f"Loading {path.name}...")
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        chunks.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        print(f"  Skipping invalid line: {exc}", file=sys.stderr)

    print(f"Loaded {len(chunks)} chunks from {len(jsonl_files)} files")
    return chunks


def build_texts(chunks: list[dict]) -> list[str]:
    """Concatenate title + text. Tags excluded (incomplete coverage)."""
    texts = []
    for chunk in chunks:
        title = str(chunk.get("title") or "").strip()
        text = str(chunk.get("text") or "").strip()
        combined = f"{title}\n{text}" if title else text
        texts.append(combined)
    return texts


def build_metadata(chunks: list[dict]) -> list[dict]:
    metadata = []
    for chunk in chunks:
        metadata.append({
            "chunk_id": chunk.get("chunk_id", ""),
            "article_id": chunk.get("article_id"),
            "chunk_index": chunk.get("chunk_index", 0),
            "title": chunk.get("title", ""),
            "url": chunk.get("url", ""),
            "tags": chunk.get("tags") or [],
            "label": chunk.get("label", ""),
            "created": chunk.get("created", ""),
            "text": chunk.get("text", ""),
        })
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FAISS index from chunk JSONL files.")
    parser.add_argument("--estrazione", default=DEFAULT_ESTRAZIONE_DIR)
    parser.add_argument("--output", default=DEFAULT_INDEX_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--pooling", choices=["mean", "cls"], default="mean")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    estrazione_dir = Path(args.estrazione)
    output_dir = Path(args.output)

    if not estrazione_dir.exists():
        print(f"Estrazione directory not found: {estrazione_dir}", file=sys.stderr)
        return 1

    chunks = load_chunks(estrazione_dir)
    if not chunks:
        print("No chunks to index.", file=sys.stderr)
        return 1

    texts = build_texts(chunks)
    metadata = build_metadata(chunks)

    embedder = Embedder(
        args.model,
        pooling=args.pooling,
        max_length=args.max_length,
    )

    print(f"Embedding {len(texts)} chunks...")
    embeddings = embedder.encode(texts, batch_size=args.batch_size, show_progress=True)
    embeddings = np.asarray(embeddings, dtype="float32")
    print(f"Embeddings shape: {embeddings.shape}")

    # Build flat inner product index (cosine similarity, vectors already normalized)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    output_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(output_dir / FAISS_INDEX_FILE))
    (output_dir / METADATA_FILE).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / MODEL_FILE).write_text(args.model, encoding="utf-8")
    (output_dir / POOLING_FILE).write_text(args.pooling, encoding="utf-8")

    print(f"\nIndex saved: {output_dir / FAISS_INDEX_FILE}")
    print(f"Metadata saved: {output_dir / METADATA_FILE}")
    print(f"Done. {index.ntotal} vectors indexed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
