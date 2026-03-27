import json
import logging
import threading
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

_DOCS_PATH = Path(__file__).resolve().parents[2] / "data" / "finance_docs.json"
_MODEL_NAME = "all-MiniLM-L6-v2"

_LOCK = threading.Lock()
_INITIALIZED = False
_MODEL: SentenceTransformer | None = None
_INDEX: faiss.IndexFlatL2 | None = None
_DOCS: list[dict[str, Any]] = []


def _load_docs() -> list[dict[str, Any]]:
    if not _DOCS_PATH.exists():
        logger.warning("RAG docs file not found at %s", _DOCS_PATH)
        return []

    with _DOCS_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        logger.warning("RAG docs file has invalid format; expected list")
        return []

    normalized_docs: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        content = str(item.get("content", "")).strip()
        if not content:
            continue

        normalized_docs.append(item)

    return normalized_docs


def initialize_retriever() -> None:
    global _INITIALIZED, _MODEL, _INDEX, _DOCS

    if _INITIALIZED:
        return

    with _LOCK:
        if _INITIALIZED:
            return

        docs = _load_docs()
        if not docs:
            _DOCS = []
            _MODEL = None
            _INDEX = None
            _INITIALIZED = True
            return

        try:
            model = SentenceTransformer(_MODEL_NAME)
            contents = [str(doc.get("content", "")).strip() for doc in docs]
            embeddings = model.encode(contents, convert_to_numpy=True)
            embedding_matrix = np.asarray(embeddings, dtype=np.float32)

            if embedding_matrix.ndim != 2 or embedding_matrix.shape[0] == 0:
                logger.warning("RAG embeddings were empty; retrieval disabled")
                _DOCS = []
                _MODEL = None
                _INDEX = None
                _INITIALIZED = True
                return

            dimension = int(embedding_matrix.shape[1])
            index = faiss.IndexFlatL2(dimension)
            index.add(embedding_matrix)

            _DOCS = docs
            _MODEL = model
            _INDEX = index
            _INITIALIZED = True
        except Exception:
            logger.exception("Failed to initialize finance retriever")
            _DOCS = []
            _MODEL = None
            _INDEX = None
            _INITIALIZED = True


def retrieve_relevant_docs(query: str, k: int = 3) -> list[dict[str, str]]:
    query_text = (query or "").strip()
    if not query_text:
        return []

    initialize_retriever()

    if _MODEL is None or _INDEX is None or not _DOCS:
        return []

    top_k = min(max(int(k), 1), 3)

    query_embedding = _MODEL.encode([query_text], convert_to_numpy=True)
    query_vector = np.asarray(query_embedding, dtype=np.float32)

    _, index_rows = _INDEX.search(query_vector, top_k)

    hits: list[dict[str, str]] = []
    for idx in index_rows[0].tolist():
        if idx < 0 or idx >= len(_DOCS):
            continue

        doc = _DOCS[idx]
        hits.append(
            {
                "content": str(doc.get("content", "")).strip(),
                "source": str(doc.get("source", "")).strip(),
            }
        )

    return hits
