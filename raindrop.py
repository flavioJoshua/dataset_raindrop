#!/usr/bin/env python3
"""Export Raindrop.io articles as local HTML, TXT, and tag/highlight JSON.

Create a .env file next to this script with:

    RAINDROP_TOKEN=your_token_here

Then run:

    python3 raindrop.py

Output:

    raindrop_articles/files/<article title>.html
    raindrop_articles/text/<article title>.txt
    raindrop_articles/json/<article title>.json  # only when tags/highlights exist
    raindrop_articles/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import date
from html.parser import HTMLParser
from http.cookiejar import CookieJar, MozillaCookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener, urlopen


API_BASE = "https://api.raindrop.io/rest/v1"
DEFAULT_OUTPUT_DIR = "raindrop_articles"
DEFAULT_EXTRACTION_DIR = "estrazione"
DEFAULT_DOMAIN_OUTPUT_DIR = "raindrop_test_export"
DEFAULT_DOMAIN_EXTRACTION_DIR = "estrazione_cookie"
TOKEN_ENV_NAMES = ("RAINDROP_TOKEN", "RAINDROP_ACCESS_TOKEN")
USER_AGENT = "raindrop-article-exporter/2.0"


class RaindropError(RuntimeError):
    pass


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class HTMLTextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        text = html.unescape("".join(self.parts))
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise RaindropError(f"Invalid .env line {line_number}: missing key")

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def get_token() -> str:
    for env_name in TOKEN_ENV_NAMES:
        token = os.getenv(env_name)
        if token:
            return token.strip()

    accepted_names = " or ".join(TOKEN_ENV_NAMES)
    raise RaindropError(f"Missing token. Add {accepted_names} to .env")


def load_cookie_jar(path: str | None) -> CookieJar | None:
    if not path:
        return None

    cookie_path = Path(path)
    if not cookie_path.exists():
        raise RaindropError(f"Cookies file not found: {cookie_path}")

    jar = MozillaCookieJar(str(cookie_path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as exc:
        raise RaindropError(
            f"Could not load cookies from {cookie_path}. "
            "Expected Netscape cookies.txt format."
        ) from exc

    print(f"Loaded {len(jar)} cookies from {cookie_path}", file=sys.stderr)
    return jar


def default_cookie_path_for_domain(domain: str) -> str:
    return f"{domain.removeprefix('www.')}_cookies.txt"


def output_dir_for_args(args: argparse.Namespace) -> Path:
    if args.output:
        return Path(args.output)
    if args.command == "export-domain":
        return Path(DEFAULT_DOMAIN_OUTPUT_DIR)
    return Path(DEFAULT_OUTPUT_DIR)


def extraction_dir_for_args(args: argparse.Namespace) -> Path:
    if args.extract_output:
        return Path(args.extract_output)
    if args.command == "export-domain":
        return Path(DEFAULT_DOMAIN_EXTRACTION_DIR)
    return Path(DEFAULT_EXTRACTION_DIR)


def cookie_path_for_args(args: argparse.Namespace) -> str:
    if args.cookies:
        return args.cookies
    if args.command == "export-domain" and args.selector:
        return default_cookie_path_for_domain(args.selector)
    return ""


def source_for_args(args: argparse.Namespace) -> str:
    if args.source:
        return args.source
    if args.command == "export-domain":
        return "original"
    return "both"


def require_existing_dir(path: Path, *, label: str) -> None:
    if not path.exists():
        raise RaindropError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise RaindropError(f"{label} is not a directory: {path}")


def request_json(
    url: str,
    token: str,
    *,
    params: dict[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    content, _content_type = request_content(url, token=token, params=params, retries=retries)

    try:
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RaindropError(f"Invalid JSON response from {url}: {exc}") from exc

    if data.get("result") is False:
        message = data.get("errorMessage") or data.get("error") or "unknown API error"
        raise RaindropError(f"Raindrop API error: {message}")

    return data


def request_content(
    url: str,
    *,
    token: str | None = None,
    cookie_jar: CookieJar | None = None,
    params: dict[str, Any] | None = None,
    retries: int = 3,
    timeout: int = 90,
) -> tuple[bytes, str | None]:
    if params:
        url = f"{url}?{urlencode(params)}"

    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    opener = build_opener(HTTPCookieProcessor(cookie_jar)) if cookie_jar else None
    last_error: Exception | None = None
    for attempt in range(retries):
        req = Request(url, headers=headers)
        try:
            response = opener.open(req, timeout=timeout) if opener else urlopen(req, timeout=timeout)
            with response:
                return response.read(), response.headers.get("Content-Type")
        except HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                wait_seconds = int(exc.headers.get("Retry-After", "5"))
                time.sleep(wait_seconds)
                continue
            if 500 <= exc.code < 600 and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            body = exc.read().decode("utf-8", errors="replace")
            raise RaindropError(f"HTTP {exc.code} for {url}: {body[:500]}") from exc
        except URLError as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise RaindropError(f"Network error for {url}: {exc}") from exc

    raise RaindropError(f"Request failed for {url}: {last_error}")


def fetch_paginated_items(
    endpoint: str,
    token: str,
    *,
    label: str,
    per_page: int = 50,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    page = 0

    while True:
        params = {
            "page": page,
            "perpage": per_page,
        }
        if extra_params:
            params.update(extra_params)

        data = request_json(f"{API_BASE}{endpoint}", token, params=params)
        items = data.get("items") or []
        if not isinstance(items, list):
            raise RaindropError(f"Unexpected {label} response: 'items' is not a list")

        all_items.extend(items)
        print(f"Fetched {label} page {page}: {len(items)} items", file=sys.stderr)

        if len(items) < per_page:
            break
        page += 1

    return all_items


def fetch_all_raindrops(token: str) -> list[dict[str, Any]]:
    return fetch_paginated_items(
        "/raindrops/0",
        token,
        label="raindrops",
        extra_params={
            "sort": "-created",
            "nested": "true",
        },
    )


def fetch_all_highlights(token: str) -> list[dict[str, Any]]:
    return fetch_paginated_items("/highlights", token, label="highlights")


def article_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item.get("type") == "article"]


def update_articles_cache(args: argparse.Namespace, token: str) -> list[dict[str, Any]]:
    articles_path = Path(args.articles_file)
    highlights_path = articles_path.with_name("highlights.json")
    articles_path.parent.mkdir(parents=True, exist_ok=True)

    all_items = fetch_all_raindrops(token)
    all_highlights = fetch_all_highlights(token)
    highlights_by_article = group_highlights(all_highlights)
    articles = article_rows(all_items)

    for item in articles:
        article_id = item.get("_id")
        if isinstance(article_id, int):
            item["highlights"] = highlights_by_article.get(article_id, item.get("highlights") or [])

    articles_path.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    highlights_path.write_text(json.dumps(all_highlights, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(articles)} articles to {articles_path}")
    print(f"Wrote {len(all_highlights)} highlights to {highlights_path}")
    return articles


def load_articles_catalog(args: argparse.Namespace, token: str) -> list[dict[str, Any]]:
    articles_path = Path(args.articles_file)
    if not args.refresh and articles_path.exists():
        data = json.loads(articles_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise RaindropError(f"Invalid articles catalog: {articles_path} is not a list")
        print(f"Loaded {len(data)} articles from {articles_path}")
        return data

    return update_articles_cache(args, token)


def safe_filename(value: str, *, max_length: int = 180) -> str:
    value = html.unescape(value).strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .")
    return value[:max_length].strip(" .") or "untitled"


def unique_filename(base_name: str, used_names: set[str]) -> str:
    if base_name not in used_names:
        used_names.add(base_name)
        return base_name

    counter = 2
    while True:
        candidate = f"{base_name} ({counter})"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


def manifest_filename_for_article(manifest: dict[str, Any], article_id: int) -> str | None:
    manifest_item = manifest.get("items", {}).get(str(article_id), {})
    text_path = manifest_item.get("text_path")
    if not isinstance(text_path, str) or not text_path:
        return None
    return Path(text_path).stem


def decode_bytes(content: bytes, content_type: str | None) -> str:
    charset = None
    if content_type:
        match = re.search(r"charset=([^;]+)", content_type, flags=re.IGNORECASE)
        if match:
            charset = match.group(1).strip("\"'")

    encodings = [charset, "utf-8", "cp1252", "latin-1"]
    for encoding in encodings:
        if not encoding:
            continue
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue

    return content.decode("utf-8", errors="replace")


def looks_like_html(raw_text: str, content_type: str | None) -> bool:
    return bool(
        (content_type and "html" in content_type.lower())
        or re.search(r"<(html|head|body|article|main|p|div)\b", raw_text[:5000], re.I)
    )


def content_to_text(content: bytes, content_type: str | None) -> str:
    raw_text = decode_bytes(content, content_type)

    if looks_like_html(raw_text, content_type):
        parser = HTMLTextExtractor()
        parser.feed(raw_text)
        parser.close()
        return parser.text()

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ensure_base_href(raw_html: str, source_url: str) -> str:
    if re.search(r"<base\b", raw_html[:5000], flags=re.IGNORECASE):
        return raw_html

    base_tag = f'<base href="{html.escape(source_url, quote=True)}">'
    head_match = re.search(r"<head([^>]*)>", raw_html, flags=re.IGNORECASE)
    if head_match:
        insert_at = head_match.end()
        return raw_html[:insert_at] + base_tag + raw_html[insert_at:]

    return raw_html


def content_to_html(content: bytes, content_type: str | None, *, source_url: str, title: str) -> str:
    raw_text = decode_bytes(content, content_type)

    if looks_like_html(raw_text, content_type):
        return ensure_base_href(raw_text, source_url)

    escaped_title = html.escape(title)
    escaped_source = html.escape(source_url, quote=True)
    escaped_text = html.escape(raw_text.strip())
    return (
        "<!doctype html>\n"
        '<html lang="it">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{escaped_title}</title>\n"
        "</head>\n"
        "<body>\n"
        f'  <p><a href="{escaped_source}">{escaped_source}</a></p>\n'
        f"  <pre>{escaped_text}</pre>\n"
        "</body>\n"
        "</html>\n"
    )


def resolve_cache_url(article_id: int, token: str) -> str:
    opener = build_opener(NoRedirectHandler)
    req = Request(
        f"{API_BASE}/raindrop/{article_id}/cache",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        opener.open(req, timeout=30)
    except HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308}:
            location = exc.headers.get("Location")
            if location:
                return location
        body = exc.read().decode("utf-8", errors="replace")
        raise RaindropError(f"Cache not available for article {article_id}: HTTP {exc.code} {body[:300]}") from exc

    raise RaindropError(f"Cache endpoint did not return a redirect for article {article_id}")


def download_article_content(
    item: dict[str, Any],
    token: str,
    *,
    source: str,
    cookie_jar: CookieJar | None = None,
) -> tuple[str | None, str | None, str | None]:
    article_id = item.get("_id")
    if not isinstance(article_id, int):
        return None, None, "missing numeric _id"

    errors: list[str] = []
    urls_to_try: list[tuple[str, str]] = []

    if source in {"cache", "both"}:
        try:
            urls_to_try.append(("cache", resolve_cache_url(article_id, token)))
        except RaindropError as exc:
            errors.append(str(exc))

    if source in {"original", "both"}:
        link = item.get("link")
        if isinstance(link, str) and link:
            urls_to_try.append(("original", link))
        else:
            errors.append("missing original link")

    for label, url in urls_to_try:
        try:
            content, content_type = request_content(url, cookie_jar=cookie_jar)
            text = content_to_text(content, content_type)
            html_content = content_to_html(
                content,
                content_type,
                source_url=url,
                title=str(item.get("title") or item.get("link") or article_id),
            )
            if text:
                return text, html_content, None
            errors.append(f"{label}: empty text after conversion")
        except Exception as exc:  # noqa: BLE001 - keep per-item downloads resilient.
            errors.append(f"{label}: {exc}")

    return None, None, " | ".join(errors)


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


def group_highlights(highlights: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for highlight in highlights:
        raindrop_ref = highlight.get("raindropRef")
        if isinstance(raindrop_ref, int):
            grouped.setdefault(raindrop_ref, []).append(normalize_highlight(highlight))

    for values in grouped.values():
        values.sort(key=lambda row: str(row.get("created") or ""))

    return grouped


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"items": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RaindropError(f"Invalid manifest JSON at {path}: {exc}") from exc

    if not isinstance(data, dict):
        return {"items": {}}
    if not isinstance(data.get("items"), dict):
        data["items"] = {}
    return data


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def article_text_header(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "Untitled")
    link = str(item.get("link") or "")
    created = str(item.get("created") or "")
    excerpt = str(item.get("excerpt") or "").strip()
    note = str(item.get("note") or "").strip()

    lines = [title]
    if link:
        lines.append(link)
    if created:
        lines.append(f"Created: {created}")
    if excerpt:
        lines.extend(["", excerpt])
    if note:
        lines.extend(["", f"Note: {note}"])
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def metadata_for_article(item: dict[str, Any], highlights: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": item.get("_id"),
        "title": item.get("title", ""),
        "link": item.get("link", ""),
        "tags": item.get("tags") or [],
        "highlights": highlights,
    }


def article_record(item: dict[str, Any], highlights: list[dict[str, Any]], *, tag: str, text: str) -> dict[str, Any]:
    return {
        "id": item.get("_id"),
        "title": item.get("title", ""),
        "url": item.get("link", ""),
        "tag": tag,
        "tags": item.get("tags") or [],
        "created": item.get("created", ""),
        "lastUpdate": item.get("lastUpdate", ""),
        "domain": item.get("domain", ""),
        "excerpt": item.get("excerpt", ""),
        "note": item.get("note", ""),
        "text": text,
        "highlights": highlights,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if overlap >= chunk_size:
        raise RaindropError("--chunk-overlap must be smaller than --chunk-size")

    chunks: list[str] = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks


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


def article_highlights(item: dict[str, Any]) -> list[dict[str, Any]]:
    highlights = item.get("highlights") or []
    if not isinstance(highlights, list):
        return []
    return [normalize_highlight(row) for row in highlights if isinstance(row, dict)]


def extraction_base_name(label: str) -> str:
    return f"{date.today().isoformat()}_{safe_filename(label, max_length=80)}"


def write_extraction_readme(path: Path) -> None:
    readme = """# Estrazione JSONL

Questa directory contiene esportazioni pronte per analisi dati, RAG e preparazione dataset.

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
"""
    path.write_text(readme, encoding="utf-8")


def should_skip(
    manifest_item: dict[str, Any],
    *,
    html_path: Path,
    text_path: Path,
    json_path: Path,
    article_signature: str,
    metadata_signature: str,
    needs_json: bool,
    force: bool,
) -> bool:
    if force:
        return False
    if not html_path.exists():
        return False
    if not text_path.exists():
        return False
    if needs_json and not json_path.exists():
        return False

    return (
        manifest_item.get("article_signature") == article_signature
        and manifest_item.get("metadata_signature") == metadata_signature
    )


def export_article(
    item: dict[str, Any],
    highlights: list[dict[str, Any]],
    token: str,
    *,
    html_dir: Path,
    text_dir: Path,
    json_dir: Path,
    filename: str,
    source: str,
    cookie_jar: CookieJar | None,
    manifest: dict[str, Any],
    force: bool,
) -> str:
    article_id = item.get("_id")
    if not isinstance(article_id, int):
        return "skipped: missing numeric _id"

    html_path = html_dir / f"{filename}.html"
    text_path = text_dir / f"{filename}.txt"
    json_path = json_dir / f"{filename}.json"
    metadata = metadata_for_article(item, highlights)
    needs_json = bool(metadata["tags"] or metadata["highlights"])

    article_signature = stable_hash(
        {
            "id": article_id,
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "excerpt": item.get("excerpt", ""),
            "note": item.get("note", ""),
            "created": item.get("created", ""),
            "lastUpdate": item.get("lastUpdate", ""),
            "cache": item.get("cache", {}),
        }
    )
    metadata_signature = stable_hash(metadata)

    manifest_items = manifest.setdefault("items", {})
    manifest_item = manifest_items.get(str(article_id), {})
    if should_skip(
        manifest_item,
        html_path=html_path,
        text_path=text_path,
        json_path=json_path,
        article_signature=article_signature,
        metadata_signature=metadata_signature,
        needs_json=needs_json,
        force=force,
    ):
        return "unchanged"

    text, html_content, error = download_article_content(
        item,
        token,
        source=source,
        cookie_jar=cookie_jar,
    )
    if text is None or html_content is None:
        manifest_items[str(article_id)] = {
            "title": item.get("title", ""),
            "html_path": str(html_path),
            "text_path": str(text_path),
            "json_path": str(json_path) if needs_json else "",
            "article_signature": article_signature,
            "metadata_signature": metadata_signature,
            "download_error": error,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return f"download failed: {error}"

    html_path.write_text(html_content, encoding="utf-8")
    text_path.write_text(article_text_header(item) + text + "\n", encoding="utf-8")

    if needs_json:
        json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    elif json_path.exists():
        json_path.unlink()

    manifest_items[str(article_id)] = {
        "title": item.get("title", ""),
        "html_path": str(html_path),
        "text_path": str(text_path),
        "json_path": str(json_path) if needs_json else "",
        "article_signature": article_signature,
        "metadata_signature": metadata_signature,
        "download_error": "",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return "written"


def build_filenames(articles: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[int, str]:
    used_names: set[str] = set()
    filenames: dict[int, str] = {}
    for item in articles:
        article_id = item.get("_id")
        if not isinstance(article_id, int):
            continue
        existing_filename = manifest_filename_for_article(manifest, article_id)
        if existing_filename:
            filenames[article_id] = existing_filename
            used_names.add(existing_filename)
            continue

        title = str(item.get("title") or item.get("link") or article_id)
        filenames[article_id] = unique_filename(safe_filename(title), used_names)
    return filenames


def export_local_articles(
    articles: list[dict[str, Any]],
    args: argparse.Namespace,
    token: str,
    cookie_jar: CookieJar | None,
) -> tuple[dict[int, Path], dict[str, int]]:
    output_dir = output_dir_for_args(args)
    html_dir = output_dir / "files"
    text_dir = output_dir / "text"
    json_dir = output_dir / "json"
    html_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "manifest.json"
    manifest = load_manifest(manifest_path)
    filenames = build_filenames(articles, manifest)

    counts = {
        "written": 0,
        "unchanged": 0,
        "failed": 0,
    }
    text_paths: dict[int, Path] = {}

    for index, item in enumerate(articles, 1):
        article_id = item.get("_id")
        if not isinstance(article_id, int):
            counts["failed"] += 1
            continue

        title = item.get("title") or item.get("link") or article_id
        print(f"[{index}/{len(articles)}] {title}")
        filename = filenames[article_id]
        status = export_article(
            item,
            article_highlights(item),
            token,
            html_dir=html_dir,
            text_dir=text_dir,
            json_dir=json_dir,
            filename=filename,
            source=source_for_args(args),
            cookie_jar=cookie_jar,
            manifest=manifest,
            force=args.force,
        )
        print(f"  {status}")

        if status == "written":
            counts["written"] += 1
        elif status == "unchanged":
            counts["unchanged"] += 1
        else:
            counts["failed"] += 1

        text_path = text_dir / f"{filename}.txt"
        if text_path.exists():
            text_paths[article_id] = text_path

        save_manifest(manifest_path, manifest)

    manifest["summary"] = {
        "articles": len(articles),
        "written": counts["written"],
        "unchanged": counts["unchanged"],
        "failed": counts["failed"],
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save_manifest(manifest_path, manifest)

    print(f"Wrote HTML files in {html_dir}")
    print(f"Wrote TXT files in {text_dir}")
    print(f"Wrote JSON files in {json_dir}")
    print(f"Wrote manifest in {manifest_path}")
    print(
        f"Summary: {counts['written']} written, "
        f"{counts['unchanged']} unchanged, {counts['failed']} failed"
    )
    return text_paths, counts


def write_dataset_from_text_paths(
    articles: list[dict[str, Any]],
    text_paths: dict[int, Path],
    args: argparse.Namespace,
    *,
    label: str,
) -> None:
    extraction_dir = extraction_dir_for_args(args)
    extraction_dir.mkdir(parents=True, exist_ok=True)
    write_extraction_readme(extraction_dir / "README.md")

    article_records: list[dict[str, Any]] = []
    for item in articles:
        article_id = item.get("_id")
        if not isinstance(article_id, int) or article_id not in text_paths:
            continue
        text = text_paths[article_id].read_text(encoding="utf-8")
        article_records.append(
            article_record(
                item,
                article_highlights(item),
                tag=label,
                text=text,
            )
        )

    base_name = extraction_base_name(label)
    articles_path = extraction_dir / f"{base_name}_articles.jsonl"
    chunks_path = extraction_dir / f"{base_name}_chunks.jsonl"
    chunks = [
        chunk
        for article in article_records
        for chunk in chunk_records(article, chunk_size=args.chunk_size, overlap=args.chunk_overlap)
    ]

    write_jsonl(articles_path, article_records)
    write_jsonl(chunks_path, chunks)

    print(f"Wrote {len(article_records)} article rows to {articles_path}")
    print(f"Wrote {len(chunks)} chunk rows to {chunks_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Raindrop.io articles to local HTML, TXT, and tag/highlight JSON files."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("export-tag", "export-domain", "update-articles"),
        help=(
            "Optional command. Use 'update-articles', 'export-tag <tag>', "
            "or 'export-domain <domain>'."
        ),
    )
    parser.add_argument(
        "selector",
        nargs="?",
        help="Tag name for export-tag or domain name for export-domain.",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to .env file containing RAINDROP_TOKEN. Default: .env",
    )
    parser.add_argument(
        "--output",
        default="",
        help=(
            f"Output directory. Default: {DEFAULT_OUTPUT_DIR}; "
            f"for export-domain: {DEFAULT_DOMAIN_OUTPUT_DIR}"
        ),
    )
    parser.add_argument(
        "--articles-file",
        default=f"{DEFAULT_OUTPUT_DIR}/articles.json",
        help="Local Raindrop articles catalog JSON. Default: raindrop_articles/articles.json",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh articles catalog from Raindrop before exporting.",
    )
    parser.add_argument(
        "--source",
        choices=("both", "cache", "original"),
        default="",
        help=(
            "Download source. Default: both; for export-domain: original. "
            "'both' tries Raindrop permanent copy first, then original URL."
        ),
    )
    parser.add_argument(
        "--cookies",
        default="",
        help=(
            "Optional Netscape cookies.txt file for authenticated article downloads. "
            "For export-domain, default is <domain>_cookies.txt."
        ),
    )
    parser.add_argument(
        "--extract-output",
        default="",
        help=(
            f"Output directory for JSONL files. Default: {DEFAULT_EXTRACTION_DIR}; "
            f"for export-domain: {DEFAULT_DOMAIN_EXTRACTION_DIR}"
        ),
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=700,
        help="Approximate chunk size in words for export-tag chunks JSONL. Default: 700",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=100,
        help="Chunk overlap in words for export-tag chunks JSONL. Default: 100",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N articles. Useful for testing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite files even when manifest says they are unchanged.",
    )
    return parser.parse_args()


def export_all(args: argparse.Namespace, token: str, cookie_jar: CookieJar | None) -> int:
    articles = load_articles_catalog(args, token)

    if args.limit and args.limit > 0:
        articles = articles[: args.limit]

    print(f"Found {len(articles)} articles")
    export_local_articles(articles, args, token, cookie_jar)
    return 0


def export_tag_dataset(args: argparse.Namespace, token: str, cookie_jar: CookieJar | None) -> int:
    if not args.selector:
        raise RaindropError("Missing tag. Usage: python3 raindrop.py export-tag <tag>")

    tag = args.selector
    extraction_dir = extraction_dir_for_args(args)
    extraction_dir.mkdir(parents=True, exist_ok=True)
    write_extraction_readme(extraction_dir / "README.md")

    all_articles = load_articles_catalog(args, token)
    articles = [item for item in all_articles if tag_matches(item, tag)]

    if args.limit and args.limit > 0:
        articles = articles[: args.limit]

    article_records: list[dict[str, Any]] = []
    failed = 0
    print(f"Found {len(articles)} articles for tag '{tag}'")

    for index, item in enumerate(articles, 1):
        article_id = item.get("_id")
        title = item.get("title") or item.get("link") or article_id
        print(f"[{index}/{len(articles)}] {title}")
        text, _html_content, error = download_article_content(
            item,
            token,
            source=source_for_args(args),
            cookie_jar=cookie_jar,
        )
        if text is None:
            failed += 1
            print(f"  skipped: {error}", file=sys.stderr)
            continue
        article_records.append(
            article_record(
                item,
                article_highlights(item),
                tag=tag,
                text=text,
            )
        )

    base_name = extraction_base_name(tag)
    articles_path = extraction_dir / f"{base_name}_articles.jsonl"
    chunks_path = extraction_dir / f"{base_name}_chunks.jsonl"
    chunks = [
        chunk
        for article in article_records
        for chunk in chunk_records(article, chunk_size=args.chunk_size, overlap=args.chunk_overlap)
    ]

    write_jsonl(articles_path, article_records)
    write_jsonl(chunks_path, chunks)

    print(f"Wrote {len(article_records)} article rows to {articles_path}")
    print(f"Wrote {len(chunks)} chunk rows to {chunks_path}")
    print(f"Wrote extraction README to {extraction_dir / 'README.md'}")
    if failed:
        print(f"Skipped {failed} articles due to download errors", file=sys.stderr)

    return 0


def export_domain(args: argparse.Namespace, token: str, cookie_jar: CookieJar | None) -> int:
    if not args.selector:
        raise RaindropError("Missing domain. Usage: python3 raindrop.py export-domain <domain>")

    domain = args.selector
    output_dir = output_dir_for_args(args)
    extraction_dir = extraction_dir_for_args(args)
    require_existing_dir(output_dir, label="Local export directory")
    require_existing_dir(extraction_dir, label="Extraction directory")
    print(f"Local export directory: {output_dir}")
    print(f"Extraction directory: {extraction_dir}")

    all_articles = load_articles_catalog(args, token)
    articles = [item for item in all_articles if domain_matches(item, domain)]

    if args.limit and args.limit > 0:
        articles = articles[: args.limit]

    print(f"Found {len(articles)} articles for domain '{domain}'")
    text_paths, _counts = export_local_articles(articles, args, token, cookie_jar)
    write_dataset_from_text_paths(articles, text_paths, args, label=domain)
    return 0


def main() -> int:
    args = parse_args()
    load_dotenv(Path(args.env))
    token = get_token()
    cookie_path = cookie_path_for_args(args)
    if cookie_path:
        print(f"Cookies file: {cookie_path}")
    cookie_jar = load_cookie_jar(cookie_path)

    if args.command == "update-articles":
        update_articles_cache(args, token)
        return 0

    if args.command == "export-tag":
        return export_tag_dataset(args, token, cookie_jar)

    if args.command == "export-domain":
        return export_domain(args, token, cookie_jar)

    return export_all(args, token, cookie_jar)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RaindropError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
