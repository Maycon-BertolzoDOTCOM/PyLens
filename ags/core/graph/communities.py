"""
Community detection for ArchitecturalGraph.

Layer: 0 (Observation)
Phenomenon: Operational Boundary Leakage
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import networkx as nx
import networkx.algorithms.community as nx_comm


def detect_communities(graph: nx.DiGraph) -> Dict[str, int]:
    """
    Detect communities using Louvain algorithm.
    Returns mapping: node_id → community_id.
    """
    if graph.number_of_nodes() == 0:
        return {}

    undirected = graph.to_undirected()

    try:
        communities_list = list(nx_comm.louvain_communities(undirected, seed=42))
    except nx.NetworkXError:
        return {node: 0 for node in graph.nodes()}

    mapping: Dict[str, int] = {}
    for comm_id, community in enumerate(communities_list):
        for node in community:
            mapping[node] = comm_id

    return mapping


def community_contamination(
    graph: nx.DiGraph,
    communities: Dict[str, int],
) -> Tuple[float, List[Tuple[str, str]], Set[int]]:
    """
    L2 — Phenomenon: Measure Operational Boundary Leakage.

    Analysis:
    - Ontology: Dependency, Boundary
    - Theory: Axioma 3 (Boundary Leakage measures operational violations)
    - Phenomenon: Operational Boundary Leakage
    - State Dimension: leakage_ratio
    - Metric: Leakage Ratio (ratio of imports violating domain boundaries)
    - Invariant: 0 <= leakage <= 1
    - Governance: Correct coupling classification
    - Memory: Included in embedding (index 5)

    Important: Community Contamination filters module edges.
    This measures operational violations, not structural coupling.
    """
    if not communities:
        return 0.0, [], set()

    cross_edges: List[Tuple[str, str]] = []
    contaminated: Set[int] = set()

    # Community Contamination filters module edges (operational violations only)
    for from_node, to_node, data in graph.edges(data=True):
        # Filter out module edges — only file edges represent operational violations
        if data.get("import_type") == "module":
            continue

        from_comm = communities.get(from_node)
        to_comm = communities.get(to_node)

        if from_comm is not None and to_comm is not None and from_comm != to_comm:
            cross_edges.append((from_node, to_node))
            contaminated.add(from_comm)
            contaminated.add(to_comm)

    total_edges = graph.number_of_edges()
    ratio = len(cross_edges) / max(total_edges, 1)

    return ratio, cross_edges, contaminated


def community_modularity(graph: nx.DiGraph, communities: Dict[str, int]) -> float:
    """Modularidade do grafo dado o particionamento de comunidades."""
    if not communities or graph.number_of_nodes() == 0:
        return 0.0

    from collections import defaultdict

    comm_nodes: Dict[int, Set[str]] = defaultdict(set)
    for node, comm_id in communities.items():
        comm_nodes[comm_id].add(node)

    community_sets = list(comm_nodes.values())

    try:
        return nx_comm.modularity(graph, community_sets)
    except Exception:
        return 0.0


def inter_community_edges(
    graph: nx.DiGraph,
    communities: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Lista detalhada de arestas entre comunidades."""
    edges = []
    for from_node, to_node, data in graph.edges(data=True):
        from_comm = communities.get(from_node)
        to_comm = communities.get(to_node)

        if from_comm is not None and to_comm is not None and from_comm != to_comm:
            edges.append({
                "from": from_node,
                "to": to_node,
                "from_community": from_comm,
                "to_community": to_comm,
                **data,
            })

    return edges
