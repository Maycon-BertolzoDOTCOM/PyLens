"""
Métricas derivadas do ArchitecturalGraph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import networkx as nx


def cycle_density(graph: nx.DiGraph) -> float:
    """
    Densidade de ciclos = ciclos / nós.
    Retorna 0.0 se não houver ciclos.
    """
    try:
        cycles = list(nx.simple_cycles(graph))
        n = graph.number_of_nodes()
        return len(cycles) / max(n, 1)
    except nx.NetworkXError:
        return 0.0


def dependency_density(graph: nx.DiGraph) -> float:
    """
    Densidade de dependências = edges / max_possible_edges.
    Retorna 0.0–1.0.
    """
    n = graph.number_of_nodes()
    if n <= 1:
        return 0.0
    return graph.number_of_edges() / (n * (n - 1))


def graph_drift(g1: nx.DiGraph, g2: nx.DiGraph) -> float:
    """
    Divergência entre dois grafos usando Jaccard distance nos edges.
    0.0 = idênticos, 1.0 = completamente diferentes.
    """
    edges1 = set(g1.edges())
    edges2 = set(g2.edges())

    if not edges1 and not edges2:
        return 0.0

    intersection = edges1 & edges2
    union = edges1 | edges2

    return 1.0 - (len(intersection) / max(len(union), 1))


def most_connected_nodes(graph: nx.DiGraph, top_n: int = 10) -> List[Tuple[str, int]]:
    """Nós com mais conexões (in-degree + out-degree)."""
    centrality = {}
    for node in graph.nodes():
        degree = graph.in_degree(node) + graph.out_degree(node)
        centrality[node] = degree

    sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
    return sorted_nodes[:top_n]


def isolated_modules(graph: nx.DiGraph) -> List[str]:
    """Módulos sem nenhuma conexão."""
    return [
        n for n in graph.nodes()
        if graph.in_degree(n) == 0 and graph.out_degree(n) == 0
    ]


def fan_out(graph: nx.DiGraph, node: str) -> int:
    """Quantas dependências um nó tem (out-degree)."""
    return graph.out_degree(node)


def fan_in(graph: nx.DiGraph, node: str) -> int:
    """Quantos dependentes um nó tem (in-degree)."""
    return graph.in_degree(node)


def highest_fan_out(graph: nx.DiGraph, top_n: int = 10) -> List[Tuple[str, int]]:
    """Nós com maior fan-out (mais dependências)."""
    fo = [(n, graph.out_degree(n)) for n in graph.nodes()]
    return sorted(fo, key=lambda x: x[1], reverse=True)[:top_n]


def highest_fan_in(graph: nx.DiGraph, top_n: int = 10) -> List[Tuple[str, int]]:
    """Nós com maior fan-in (mais dependências externas)."""
    fi = [(n, graph.in_degree(n)) for n in graph.nodes()]
    return sorted(fi, key=lambda x: x[1], reverse=True)[:top_n]
