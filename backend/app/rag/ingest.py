"""
Document ingestion pipeline.

Converts policy text documents into embeddings and stores them in ChromaDB.

How embeddings work:
- text-embedding-3-small converts each document into a 1536-dimensional vector
- Similar documents end up close together in that 1536-dimensional space
- Searching = finding the vectors closest to your query vector
- This is why "high DTI" finds "excessive leverage" — semantically similar = close vectors

This only runs once. After the first run, documents are persisted to ./chroma_db/
and loaded from disk on subsequent server starts (no re-embedding needed).
"""
from __future__ import annotations

import logging

from app.rag.chroma_store import collection_is_populated, get_policy_collection
from app.rag.policy_documents import POLICY_DOCUMENTS

logger = logging.getLogger(__name__)


def ingest_policy_documents(force: bool = False) -> int:
    """
    Embeds and stores all policy documents in ChromaDB.

    Returns the number of documents ingested (0 if already populated and not forced).

    Args:
        force: If True, clears existing documents and re-ingests everything.
               Useful after editing policy_documents.py.
    """
    if collection_is_populated() and not force:
        count = get_policy_collection().count()
        logger.info("Chroma collection already populated (%d documents). Skipping ingest.", count)
        return 0

    collection = get_policy_collection()

    if force:
        logger.info("Force re-ingest: clearing existing documents.")
        existing_ids = collection.get()["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)

    # Batch the documents for efficient embedding
    ids = [doc["id"] for doc in POLICY_DOCUMENTS]
    texts = [doc["text"] for doc in POLICY_DOCUMENTS]
    metadatas = [doc["metadata"] for doc in POLICY_DOCUMENTS]

    logger.info("Ingesting %d policy documents into ChromaDB...", len(POLICY_DOCUMENTS))

    # ChromaDB calls the embedding function automatically
    # All texts are embedded in one API call (batched)
    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
    )

    final_count = collection.count()
    logger.info("Ingest complete. ChromaDB now holds %d policy documents.", final_count)
    return len(POLICY_DOCUMENTS)
