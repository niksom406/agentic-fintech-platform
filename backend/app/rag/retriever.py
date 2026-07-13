"""
Public RAG retrieval interface.

This is the only file governance_agent.py imports from the RAG module.
It combines:
  1. Graph reasoning  → determines which policy categories to retrieve
  2. Chroma retrieval → semantic search within those categories
  3. Result formatting → clean text the LLM can read directly

The result is a structured block of policy passages with their sources,
injected into the governance agent's prompt before the LLM call.
"""
from __future__ import annotations

import logging

from app.rag.chroma_store import collection_is_populated, get_policy_collection
from app.rag.graph_reasoner import get_related_categories, infer_seed_categories

logger = logging.getLogger(__name__)

# How many document chunks to retrieve per query
TOP_K = 3


def retrieve_policy_context(
    case_context: dict,
    query: str | None = None,
    max_hops: int = 2,
) -> str:
    """
    Main entry point for the governance agent.

    Given a case's context dict (risk flags, governance flags, etc.),
    retrieves the most relevant policy passages using GraphRAG.

    Returns a formatted string ready to inject into a prompt.
    If Chroma is not populated or unavailable, returns empty string
    (governance agent still runs, just without RAG context).

    Args:
        case_context: dict with risk_score, governance_flags, etc.
        query:        optional explicit query string (overrides auto-generated)
        max_hops:     graph traversal depth
    """
    if not collection_is_populated():
        logger.warning("Chroma not populated — governance agent running without RAG context.")
        return ""

    try:
        # Step 1: Infer seed categories from case signals
        seeds = infer_seed_categories(case_context)
        logger.info("RAG seed categories: %s", seeds)

        # Step 2: Graph traversal — expand to related categories
        all_categories = get_related_categories(seeds, max_hops=max_hops)
        logger.info("RAG expanded categories (after graph traversal): %s", all_categories)

        # Step 3: Build the semantic query
        if not query:
            flag_names = [f.get("flag_name", "") for f in case_context.get("governance_flags", [])]
            query = (
                f"governance policy for: {', '.join(flag_names) or 'financial case evaluation'}. "
                f"risk level: {case_context.get('risk_level', '')}. "
                f"categories: {', '.join(seeds)}"
            )

        collection = get_policy_collection()

        # Step 4: Chroma semantic search filtered to the graph-expanded categories
        results = collection.query(
            query_texts=[query],
            n_results=TOP_K,
            where={"category": {"$in": list(all_categories)}},
            include=["documents", "metadatas", "distances"],
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        if not documents:
            logger.info("No relevant policy documents found for this case.")
            return ""

        # Step 5: Format for prompt injection
        passages = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            similarity = round(1 - dist, 3)  # convert distance to similarity score
            passages.append(
                f"[Source: {meta.get('category', 'unknown').upper()} | "
                f"Regulation: {meta.get('regulation', 'internal')} | "
                f"Relevance: {similarity}]\n{doc}"
            )

        formatted = "\n\n---\n\n".join(passages)
        logger.info(
            "RAG retrieved %d policy passages for governance agent (seeds=%s, hops=%d)",
            len(passages), seeds, max_hops,
        )
        return formatted

    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        return ""  # graceful degradation — governance agent still runs
