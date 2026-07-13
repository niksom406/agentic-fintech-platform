"""
GraphRAG — multi-hop policy graph reasoning.

Standard RAG: query → find similar documents → done.
GraphRAG: query → find documents → follow relationships → find MORE documents.

Why this matters:
A case with HIGH DTI should retrieve:
  1. The DTI policy itself (direct match)
  2. The escalation policy (DTI triggers escalation)
  3. Compensating factors (what could justify an exception)
  4. Override documentation requirements (what the reviewer must record)

A flat vector search might only return #1. The graph navigates to #2, #3, #4.

Implementation:
- NetworkX directed graph where nodes = policy document categories
- Edges = "this policy concept references/triggers/relates to that one"
- Multi-hop traversal follows edges up to `max_hops` steps
- Returns the set of categories to also retrieve from Chroma
"""
from __future__ import annotations

import logging
from functools import lru_cache

import networkx as nx

logger = logging.getLogger(__name__)


# ── Policy relationship graph ──────────────────────────────────────────────────
# Each node is a policy category (matches 'category' in document metadata).
# Each directed edge means "when this category is relevant, also check that one".

POLICY_GRAPH_EDGES = [
    # Credit risk connects to fair lending (decisions on credit can be discriminatory)
    ("credit_risk", "fairness"),
    # Credit risk connects to model risk (credit scores come from models)
    ("credit_risk", "model_risk"),

    # High DTI triggers escalation procedures
    ("affordability", "escalation"),
    # DTI exceptions require override documentation
    ("affordability", "escalation"),

    # Fairness concerns always require audit documentation
    ("fairness", "audit"),
    # Fairness connects to model risk (AI models can encode bias)
    ("fairness", "model_risk"),

    # Model risk (low confidence) triggers escalation
    ("model_risk", "escalation"),
    # Model decisions require explainability (audit trail)
    ("model_risk", "audit"),

    # Escalation decisions require override docs when reviewer changes outcome
    ("escalation", "audit"),

    # AML findings always need audit documentation
    ("aml", "audit"),
    # AML connects to escalation (suspicious activity must be reviewed)
    ("aml", "escalation"),

    # Audit connects back to fairness (audit trails prove fair treatment)
    ("audit", "fairness"),
]


@lru_cache(maxsize=1)
def _build_graph() -> nx.DiGraph:
    """
    Builds the policy knowledge graph.
    Cached — built once, reused for all queries.
    """
    G = nx.DiGraph()

    categories = {
        "credit_risk", "affordability", "fairness",
        "model_risk", "escalation", "aml", "audit",
    }
    G.add_nodes_from(categories)
    G.add_edges_from(POLICY_GRAPH_EDGES)

    logger.debug("Policy graph built: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    return G


def get_related_categories(seed_categories: list[str], max_hops: int = 2) -> set[str]:
    """
    Multi-hop traversal: starting from seed categories, follow edges to find
    related policy categories that should also be retrieved.

    Example:
        seed = ["affordability"]  (DTI is high)
        hop 1 → follows edges → ["escalation"]
        hop 2 → follows edges → ["audit"]
        returns {"affordability", "escalation", "audit"}

    Args:
        seed_categories: policy categories directly relevant to the case
        max_hops: how many relationship hops to follow (2 is usually enough)

    Returns:
        All categories to include in the Chroma retrieval query
    """
    G = _build_graph()
    visited = set(seed_categories)
    frontier = set(seed_categories)

    for hop in range(max_hops):
        next_frontier: set[str] = set()
        for node in frontier:
            if node in G:
                # Follow outgoing edges (what does this concept connect to?)
                neighbours = set(G.successors(node))
                new = neighbours - visited
                next_frontier.update(new)

        if not next_frontier:
            break  # no new nodes found — graph traversal complete

        visited.update(next_frontier)
        frontier = next_frontier
        logger.debug("Hop %d: discovered categories %s", hop + 1, next_frontier)

    logger.info("Graph reasoning: %s → %s (via %d hops)", seed_categories, visited, max_hops)
    return visited


def infer_seed_categories(case_context: dict) -> list[str]:
    """
    Determines which policy categories are directly relevant to a case
    based on the case data and governance flags.

    This is the entry point: case signals → seed categories → graph traversal.
    """
    seeds: list[str] = []

    risk_score = case_context.get("risk_score", 0) or 0
    risk_level = (case_context.get("risk_level") or "").lower()
    governance_flags = case_context.get("governance_flags", [])
    flag_names = [f.get("flag_name", "").upper() for f in governance_flags]

    # Credit risk signals
    if "CREDIT" in str(flag_names) or risk_score > 60:
        seeds.append("credit_risk")

    # Affordability / DTI signals
    if any("DTI" in f or "DEBT" in f or "INCOME" in f for f in flag_names):
        seeds.append("affordability")

    # Fairness signals
    if any("SENSITIVE" in f or "FAIR" in f or "DISCRIMINAT" in f for f in flag_names):
        seeds.append("fairness")

    # Model risk signals
    if any("MODEL" in f or "CONFIDENCE" in f or "EXPLANATION" in f for f in flag_names):
        seeds.append("model_risk")

    # Escalation signals
    if any("ESCALAT" in f or "CONTRADICT" in f or "HUMAN" in f for f in flag_names):
        seeds.append("escalation")

    # AML / transaction signals
    if any("AML" in f or "TRANSACTION" in f or "SANCTI" in f for f in flag_names):
        seeds.append("aml")

    # Always include audit for any case going through governance review
    seeds.append("audit")

    # Default: if nothing specific triggered, cover the basics
    if len(seeds) <= 1:
        seeds = ["credit_risk", "affordability", "escalation", "audit"]

    return list(set(seeds))
