"""RAG retrieval module.

Loads FAISS index and metadata from disk. Uses Embedder (raw transformers)
to vettorize queries. Exposes a query() function used by rag_app.py.

Usage (standalone test):
    python3 rag_query.py "intelligenza artificiale e sicurezza"
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import faiss
import numpy as np

from rag_embedder import Embedder

DEFAULT_INDEX_DIR = "rag_index"
FAISS_INDEX_FILE = "index.faiss"
METADATA_FILE = "metadata.json"
MODEL_FILE = "model_name.txt"
POOLING_FILE = "pooling.txt"


@dataclass
class RetrievalResult:
    chunk_id: str
    article_id: int | None
    chunk_index: int
    title: str
    url: str
    tags: list[str]
    label: str
    created: str
    text: str
    score: float


@dataclass
class RAGRetriever:
    index_dir: Path = field(default_factory=lambda: Path(DEFAULT_INDEX_DIR))
    _index: faiss.Index | None = field(default=None, init=False, repr=False)
    _metadata: list[dict] | None = field(default=None, init=False, repr=False)
    _embedder: Embedder | None = field(default=None, init=False, repr=False)

    def load(self) -> None:
        index_path = self.index_dir / FAISS_INDEX_FILE
        metadata_path = self.index_dir / METADATA_FILE
        model_path = self.index_dir / MODEL_FILE
        pooling_path = self.index_dir / POOLING_FILE

        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}\n"
                "Run rag_index.py first to build the index."
            )

        self._index = faiss.read_index(str(index_path))
        self._metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        model_name = model_path.read_text(encoding="utf-8").strip()
        pooling = pooling_path.read_text(encoding="utf-8").strip() if pooling_path.exists() else "mean"

        self._embedder = Embedder(model_name, pooling=pooling)

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    def all_tags(self) -> list[str]:
        tags: set[str] = set()
        for item in (self._metadata or []):
            for tag in item.get("tags") or []:
                if tag:
                    tags.add(str(tag))
        return sorted(tags)

    def all_domains(self) -> list[str]:
        domains: set[str] = set()
        for item in (self._metadata or []):
            url = item.get("url", "")
            if url:
                hostname = urlparse(url).hostname or ""
                hostname = hostname.removeprefix("www.")
                if hostname:
                    domains.add(hostname)
        return sorted(domains)

    def query(
        self,
        text: str,
        *,
        k: int = 5,
        tag_filter: list[str] | None = None,
        domain_filter: list[str] | None = None,
        fetch_k: int = 50,
    ) -> list[RetrievalResult]:
        if not self.is_loaded:
            raise RuntimeError("Call load() before query()")

        query_embedding = self._embedder.encode([text], show_progress=False)
        query_embedding = np.asarray(query_embedding, dtype="float32")

        candidates = max(fetch_k if (tag_filter or domain_filter) else k, k)
        scores, indices = self._index.search(query_embedding, candidates)

        results: list[RetrievalResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = self._metadata[idx]

            if tag_filter:
                item_tags = [str(t).casefold() for t in item.get("tags") or []]
                if not any(t.casefold() in item_tags for t in tag_filter):
                    continue

            if domain_filter:
                hostname = urlparse(item.get("url", "")).hostname or ""
                hostname = hostname.removeprefix("www.").casefold()
                if not any(d.casefold() == hostname for d in domain_filter):
                    continue

            results.append(
                RetrievalResult(
                    chunk_id=item.get("chunk_id", ""),
                    article_id=item.get("article_id"),
                    chunk_index=item.get("chunk_index", 0),
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    tags=item.get("tags") or [],
                    label=item.get("label", ""),
                    created=item.get("created", ""),
                    text=item.get("text", ""),
                    score=float(score),
                )
            )
            if len(results) >= k:
                break

        return results


_retriever: RAGRetriever | None = None


def get_retriever(index_dir: str = DEFAULT_INDEX_DIR) -> RAGRetriever:
    global _retriever
    if _retriever is None or str(_retriever.index_dir) != index_dir:
        _retriever = RAGRetriever(index_dir=Path(index_dir))
        _retriever.load()
    return _retriever


if __name__ == "__main__":
    query_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "sicurezza informatica"
    print(f"Query: {query_text}\n")
    retriever = get_retriever()
    results = retriever.query(query_text, k=5)
    for i, r in enumerate(results, 1):
        print(f"[{i}] score={r.score:.4f} | {r.title}")
        print(f"     {r.url}")
        print(f"     tags: {', '.join(r.tags) or '—'}")
        print(f"     {r.text[:200]}...")
        print()
