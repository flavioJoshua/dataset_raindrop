"""Embedding module with full control over the transformer pipeline.

Replaces SentenceTransformer with raw transformers + manual mean pooling.
Used by rag_index.py and rag_query.py.

Supports:
- Mean pooling (default, best for bi-encoder RAG)
- CLS token pooling (optional)
- L2 normalization for cosine similarity via FAISS IndexFlatIP

Usage:
    from rag_embedder import Embedder
    embedder = Embedder("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vectors = embedder.encode(["testo uno", "testo due"])
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

PoolingStrategy = Literal["mean", "cls"]


class Embedder:
    def __init__(
        self,
        model_name: str,
        *,
        pooling: PoolingStrategy = "mean",
        max_length: int = 512,
        device: str | None = None,
    ) -> None:
        """
        Args:
            model_name: HuggingFace model name or local path.
            pooling: "mean" (mean pooling over token embeddings, recommended)
                     or "cls" (use [CLS] token only).
            max_length: Max token length. 512 for most BERT-family models.
            device: "cpu", "cuda", "mps", or None for auto-detect.
        """
        self.model_name = model_name
        self.pooling = pooling
        self.max_length = max_length
        self.device = device or self._auto_device()

        print(f"Loading tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        print(f"Loading model: {model_name} on {self.device}")
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

        self.embedding_dim = self.model.config.hidden_size
        print(f"Embedding dim: {self.embedding_dim} | Pooling: {self.pooling}")

    @staticmethod
    def _auto_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _mean_pool(
        self,
        token_embeddings: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Mean pooling: average token embeddings weighted by attention mask."""
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * mask, dim=1)
        sum_mask = torch.clamp(mask.sum(dim=1), min=1e-9)
        return sum_embeddings / sum_mask

    def _cls_pool(self, token_embeddings: torch.Tensor) -> torch.Tensor:
        """CLS pooling: take the [CLS] token embedding only."""
        return token_embeddings[:, 0, :]

    def _embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed a single batch of texts. Returns normalized float32 numpy array."""
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.no_grad():
            outputs = self.model(**encoded)

        token_embeddings = outputs.last_hidden_state  # (batch, seq_len, hidden)

        if self.pooling == "mean":
            pooled = self._mean_pool(token_embeddings, encoded["attention_mask"])
        else:
            pooled = self._cls_pool(token_embeddings)

        # L2 normalization — required for cosine similarity with FAISS IndexFlatIP
        normalized = F.normalize(pooled, p=2, dim=1)

        return normalized.cpu().numpy().astype("float32")

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int = 64,
        show_progress: bool = True,
    ) -> np.ndarray:
        """Encode a list of texts into normalized float32 embeddings.

        Args:
            texts: List of strings to embed.
            batch_size: Number of texts per forward pass.
            show_progress: Print progress to stdout.

        Returns:
            np.ndarray of shape (len(texts), embedding_dim), float32, L2-normalized.
        """
        all_embeddings: list[np.ndarray] = []
        n_batches = math.ceil(len(texts) / batch_size)

        for batch_idx in range(n_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(texts))
            batch = texts[start:end]

            if show_progress:
                print(
                    f"\rEmbedding batch {batch_idx + 1}/{n_batches} "
                    f"({end}/{len(texts)} texts)...",
                    end="",
                    flush=True,
                )

            all_embeddings.append(self._embed_batch(batch))

        if show_progress:
            print()  # newline after progress

        return np.vstack(all_embeddings)
