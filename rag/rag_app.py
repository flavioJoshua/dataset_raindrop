"""Streamlit RAG interface.

Features:
- Free text query
- Tag filter (sidebar multiselect)
- Domain/source filter (sidebar multiselect)
- Retrieved chunks preview (expandable)
- LLM response via Ollama with citations

Requirements:
    pip install streamlit ollama

Run:
    streamlit run rag_app.py
"""

from __future__ import annotations

import textwrap
from urllib.parse import urlparse

import ollama
import streamlit as st

from rag_query import get_retriever, RetrievalResult

# ── Configuration ────────────────────────────────────────────────────────────

INDEX_DIR = "rag_index"
DEFAULT_OLLAMA_MODEL = "llama3.2"   # change to any model you have pulled
TOP_K = 5
FETCH_K = 50  # candidates before post-filtering

SYSTEM_PROMPT = """Sei un assistente di ricerca. Rispondi in italiano in modo preciso e conciso.
Usa SOLO le informazioni nei DOCUMENTI RECUPERATI per rispondere.
Alla fine della risposta, cita le fonti nel formato: [Titolo](URL).
Se le informazioni non sono sufficienti, dillo esplicitamente."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def domain_from_url(url: str) -> str:
    hostname = urlparse(url).hostname or url
    return hostname.removeprefix("www.")


def build_context(results: list[RetrievalResult]) -> str:
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[DOCUMENTO {i}]\n"
            f"Titolo: {r.title}\n"
            f"Fonte: {r.url}\n"
            f"Testo: {r.text}"
        )
    return "\n\n---\n\n".join(parts)


def call_ollama(model: str, context: str, query: str) -> str:
    user_message = (
        f"DOCUMENTI RECUPERATI:\n\n{context}\n\n"
        f"DOMANDA: {query}"
    )
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return response["message"]["content"]


def score_bar(score: float) -> str:
    """Visual indicator for cosine similarity score (0-1)."""
    filled = int(score * 10)
    return "█" * filled + "░" * (10 - filled) + f"  {score:.3f}"


# ── Streamlit app ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="RAG – Archivio Articoli",
    page_icon="🔍",
    layout="wide",
)

# Load retriever once per session
@st.cache_resource
def load_retriever(index_dir: str):
    retriever = get_retriever(index_dir)
    return retriever


try:
    retriever = load_retriever(INDEX_DIR)
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

all_tags = retriever.all_tags()
all_domains = retriever.all_domains()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Impostazioni")

    ollama_model = st.text_input(
        "Modello Ollama",
        value=DEFAULT_OLLAMA_MODEL,  #  sarebbe llama 3.2 3B
        help="Nome del modello Ollama da usare (es. llama3.2, mistral, qwen2.5)",
    )

    top_k = st.slider("Chunk da recuperare (k)", min_value=1, max_value=20, value=TOP_K)

    st.divider()
    st.subheader("🏷️ Filtro Tag")
    selected_tags = st.multiselect(
        "Filtra per tag (opzionale)",
        options=all_tags,
        default=[],
        help="Lascia vuoto per cercare su tutti gli articoli",
    )

    st.subheader("🌐 Filtro Dominio")
    selected_domains = st.multiselect(
        "Filtra per fonte (opzionale)",
        options=all_domains,
        default=[],
    )

    st.divider()
    show_chunks = st.toggle("Mostra chunk recuperati", value=True)
    st.caption(f"Indice: `{INDEX_DIR}`  \n{retriever._index.ntotal} vettori indicizzati")

# ── Main ──────────────────────────────────────────────────────────────────────

st.title("🔍 RAG – Archivio Articoli")

query = st.text_area(
    "Domanda",
    placeholder="Cosa vuoi sapere?",
    height=100,
)

col1, col2 = st.columns([1, 5])
with col1:
    search_clicked = st.button("🔍 Cerca", type="primary", use_container_width=True)
with col2:
    if selected_tags:
        st.caption(f"Tag attivi: {', '.join(selected_tags)}")
    if selected_domains:
        st.caption(f"Fonti attive: {', '.join(selected_domains)}")

if search_clicked and query.strip():
    with st.spinner("Retrieval in corso..."):
        results = retriever.query(
            query.strip(),
            k=top_k,
            tag_filter=selected_tags or None,
            domain_filter=selected_domains or None,
            fetch_k=FETCH_K,
        )

    if not results:
        st.warning("Nessun chunk trovato con i filtri selezionati. Prova a rimuovere i filtri.")
        st.stop()

    # ── Chunk preview ──────────────────────────────────────────────────────
    if show_chunks:
        st.subheader(f"📄 Chunk recuperati ({len(results)})")
        for i, r in enumerate(results, 1):
            with st.expander(f"[{i}] {r.title or 'Senza titolo'}  —  {score_bar(r.score)}"):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**Fonte:** [{domain_from_url(r.url)}]({r.url})")
                    if r.tags:
                        st.markdown(f"**Tag:** {', '.join(r.tags)}")
                    if r.created:
                        st.caption(f"Creato: {r.created[:10]}")
                with col_b:
                    st.metric("Score", f"{r.score:.4f}")
                st.markdown("---")
                st.markdown(textwrap.fill(r.text, width=120))

        st.divider()

    # ── LLM response ───────────────────────────────────────────────────────
    st.subheader("🤖 Risposta")
    context = build_context(results)

    with st.spinner(f"Generazione risposta con {ollama_model}..."):
        try:
            answer = call_ollama(ollama_model, context, query.strip())
        except Exception as exc:
            st.error(f"Errore Ollama: {exc}")
            st.caption("Assicurati che Ollama sia avviato (`ollama serve`) e che il modello sia scaricato (`ollama pull llama3.2`).")
            st.stop()

    st.markdown(answer)

    # ── Citations ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📚 Fonti utilizzate")
    seen_urls: set[str] = set()
    for r in results:
        if r.url and r.url not in seen_urls:
            seen_urls.add(r.url)
            tags_str = f" — {', '.join(r.tags)}" if r.tags else ""
            st.markdown(f"- [{r.title or r.url}]({r.url}){tags_str}")

elif search_clicked and not query.strip():
    st.warning("Inserisci una domanda.")
