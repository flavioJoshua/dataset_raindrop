from __future__ import annotations

import hashlib
import html
import json
import os
import random
import re
import sys
import time
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar, MozillaCookieJar
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_MAX_LINES = 3000
DEFAULT_DOWNLOAD_DELAY_MS = 0
DEFAULT_DOWNLOAD_JITTER_MS = 0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 25
DEFAULT_REQUEST_RETRIES = 2


class RaindropError(RuntimeError):
    pass


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


def env_int(name: str, default: int, *, minimum: int = 1) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RaindropError(f"{name} must be an integer, got: {value}") from exc
    if parsed < minimum:
        raise RaindropError(f"{name} must be >= {minimum}, got: {value}")
    return parsed


def log_dir() -> Path:
    log_directory = Path(os.getenv("RAINDROP_LOG_DIR", DEFAULT_LOG_DIR))
    if not log_directory.is_absolute():
        log_directory = PROJECT_ROOT / log_directory
    log_directory.mkdir(parents=True, exist_ok=True)
    return log_directory


def log_line_count(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _line in handle)


def log_path(max_lines: int) -> Path:
    directory = log_dir()
    stem = f"{date.today().isoformat()}-log"
    base_path = directory / f"{stem}.log"
    sequence_pattern = re.compile(rf"^{re.escape(stem)}-(\d+)\.log$")

    numbered_paths: list[tuple[int, Path]] = []
    for path in directory.glob(f"{stem}-*.log"):
        match = sequence_pattern.fullmatch(path.name)
        if match:
            numbered_paths.append((int(match.group(1)), path))

    candidates = [(1, base_path), *numbered_paths]
    existing_candidates = [(number, path) for number, path in candidates if path.exists()]
    if not existing_candidates:
        return base_path

    current_number, current_path = max(existing_candidates, key=lambda item: item[0])
    if log_line_count(current_path) < max_lines:
        return current_path

    next_number = current_number + 1
    return directory / f"{stem}-{next_number:04d}.log"


def write_log_event(event: dict[str, Any]) -> None:
    max_lines = env_int("RAINDROP_LOG_MAX_LINES", DEFAULT_LOG_MAX_LINES, minimum=1)
    path = log_path(max_lines)
    event = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def elapsed_ms_since(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def bytes_to_kb(size: int) -> int:
    return int(round(size / 1024))


def download_delay_seconds() -> float:
    delay_ms = env_int("RAINDROP_DOWNLOAD_DELAY_MS", DEFAULT_DOWNLOAD_DELAY_MS, minimum=0)
    jitter_ms = env_int("RAINDROP_DOWNLOAD_JITTER_MS", DEFAULT_DOWNLOAD_JITTER_MS, minimum=0)
    if jitter_ms:
        delay_ms += random.randint(0, jitter_ms)
    return delay_ms / 1000


def request_timeout_seconds() -> int:
    return env_int("RAINDROP_REQUEST_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS, minimum=1)


def request_retries() -> int:
    return env_int("RAINDROP_REQUEST_RETRIES", DEFAULT_REQUEST_RETRIES, minimum=1)


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


def load_cookie_directory(path: Path) -> CookieJar:
    if not path.exists():
        raise RaindropError(
            f"Cookie directory not found: {path}. "
            "Create it and add Netscape *.txt cookie files."
        )
    if not path.is_dir():
        raise RaindropError(f"Cookie path is not a directory: {path}")

    cookie_files = sorted(candidate for candidate in path.glob("*.txt") if candidate.is_file())
    if not cookie_files:
        raise RaindropError(
            f"No cookie files found in {path}. "
            "Expected one or more Netscape *.txt files."
        )

    combined_jar = CookieJar()
    for cookie_file in cookie_files:
        file_jar = load_cookie_jar(str(cookie_file))
        if file_jar is None:
            continue
        for cookie in file_jar:
            combined_jar.set_cookie(cookie)

    print(
        f"Loaded {len(combined_jar)} cookies from {len(cookie_files)} files in {path}",
        file=sys.stderr,
    )
    return combined_jar


def require_existing_dir(path: Path, *, label: str) -> None:
    if not path.exists():
        raise RaindropError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise RaindropError(f"{label} is not a directory: {path}")


def safe_filename(value: str, *, max_length: int = 120, max_bytes: int = 180) -> str:
    value = html.unescape(value).strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .")
    value = value[:max_length].strip(" .") or "untitled"

    while len(value.encode("utf-8")) > max_bytes and len(value) > 1:
        value = value[:-1].strip(" .")

    return value or "untitled"


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
