"""
ChromaDB vector store setup.

ChromaDB stores policy documents as embeddings (numeric vectors).
When the governance agent needs to find relevant policy text,
it queries this store with a natural-language question and gets back
the most semantically similar policy passages.

We use OpenAI's text-embedding-3-small model:
- Same API key, no extra setup
- ~$0.00002 per 1K tokens (almost free)
- 1536-dimensional vectors — high quality

Storage: ./chroma_db/ folder next to the SQLite database.
On first run, documents are embedded and stored. On subsequent runs,
the store is loaded from disk — no re-embedding needed.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from app.core.config import get_settings

logger = logging.getLogger(__name__)

CHROMA_PATH = Path(__file__).parent.parent.parent / "chroma_db"
COLLECTION_NAME = "policy_documents"


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """
    Returns a persistent Chroma client.
    Data is saved to ./chroma_db/ and survives server restarts.
    Cached so the same client is reused across all requests.
    """
    CHROMA_PATH.mkdir(exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


@lru_cache(maxsize=1)
def get_embedding_function() -> OpenAIEmbeddingFunction:
    """
    OpenAI embedding function.
    text-embedding-3-small: fast, cheap, high quality.
    """
    settings = get_settings()
    return OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name="text-embedding-3-small",
    )


def get_policy_collection() -> chromadb.Collection:
    """
    Returns (or creates) the policy documents collection.
    A collection is like a table — one collection holds all policy documents.
    """
    client = get_chroma_client()
    ef = get_embedding_function()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"description": "FinTech governance policy documents"},
    )


def collection_is_populated() -> bool:
    """Returns True if the collection already has documents loaded."""
    try:
        col = get_policy_collection()
        return col.count() > 0
    except Exception:
        return False
