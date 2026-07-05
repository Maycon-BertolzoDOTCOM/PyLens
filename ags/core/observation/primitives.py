"""
Observation Primitives — Bridge between Ω_synth and Ω_real.

Computes primitive architectural metrics [0,1] from a real
ArchitecturalGraph, using the same ratio formulas as the C0.0
synthetic system. Enables regime classification of real projects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import networkx as nx

from ags import __version__ as AGS_VERSION

# Human-readable version tag for this bridge layer
GIT_VERSION = "v2.0.0-bridge.1"


@dataclass
class ObservationSnapshot:
    """
    Observação primitiva de um ArchitecturalGraph real.

    Contém métricas [0,1] no mesmo formato do sistema sintético C0.0,
    permitindo classificação de regime via classify_observed_regime().

    A ObservationSnapshot é PRÉ-classificação — não contém regime,
    distância ou confiança. Esses pertencem a RegimeClassification.
    """

    # --- Primitive metrics [0,1] ---
    cross_domain_ratio: float = 0.0
    intra_domain_ratio: float = 0.0
    file_level_leakage: float = 0.0
    cycle_density: float = 0.0

    # --- Edge classification counts ---
    total_nodes: int = 0
    total_edges: int = 0
    cross_domain_edges: int = 0
    intra_domain_edges: int = 0
    unknown_unresolved_edges: int = 0
    unknown_dynamic_edges: int = 0
    total_imports_attempted: int = 0

    # --- Provenance ---
    parser_version: str = AGS_VERSION
    graph_builder_version: str = GIT_VERSION
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def unknown_edges(self) -> int:
        """Total de edges não classificáveis (soma de unresolved + dynamic)."""
        return self.unknown_unresolved_edges + self.unknown_dynamic_edges

    @property
    def observation_quality(self) -> float:
        """
        Qualidade da observação [0,1].

        Mede a fração de imports que puderam ser classificados como edges.
        Quando total_imports_attempted está disponível, usa esse denominador.
        """
        denominator = self.total_imports_attempted if self.total_imports_attempted > 0 else self.total_edges
        if denominator == 0:
            return 0.0
        return max(0.0, 1.0 - self.unknown_edges / denominator)

    @property
    def classification_confidence(self) -> float:
        """
        Confiança experimental [0,1].

        EXPERIMENTAL — heurística provisória. Ainda não sabemos se
        observation_quality e distance_to_regime devem ter o mesmo peso.
        Será calibrada durante C1.0.

        Fórmula atual: observation_quality (sem distance, pois
        distance pertence a RegimeClassification).
        """
        return self.observation_quality

    def to_dict(self) -> dict[str, Any]:
        return {
            "cross_domain_ratio": self.cross_domain_ratio,
            "intra_domain_ratio": self.intra_domain_ratio,
            "file_level_leakage": self.file_level_leakage,
            "cycle_density": self.cycle_density,
            "observation_quality": self.observation_quality,
            "classification_confidence": self.classification_confidence,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "total_imports_attempted": self.total_imports_attempted,
            "cross_domain_edges": self.cross_domain_edges,
            "intra_domain_edges": self.intra_domain_edges,
            "unknown_unresolved_edges": self.unknown_unresolved_edges,
            "unknown_dynamic_edges": self.unknown_dynamic_edges,
            "parser_version": self.parser_version,
            "graph_builder_version": self.graph_builder_version,
            "timestamp": self.timestamp.isoformat(),
        }


def _get_file_module(graph: Any, node: str) -> Optional[str]:
    """Retorna o módulo de um nó do grafo, se for um nó de arquivo."""
    node_data = graph.graph.nodes.get(node)
    if node_data is None:
        return None
    if node_data.get("node_type") != "file":
        return None
    return node_data.get("module") or graph.files.get(node, None)


def _compute_cycle_density_file_edges(graph: Any, total_edges: int) -> float:
    """
    Fração de edges que participam de ciclos.

    Usa nx.simple_cycles() para detectar edges participantes,
    NÃO cyclomatic complexity (que mede fluxo de controle, não
    retroalimentação estrutural).
    """
    if total_edges == 0:
        return 0.0
    try:
        cycles = list(nx.simple_cycles(graph.graph))
    except nx.NetworkXError:
        return 0.0

    edges_in_cycles: set[tuple[str, str]] = set()
    for cycle in cycles:
        for i in range(len(cycle)):
            u = cycle[i]
            v = cycle[(i + 1) % len(cycle)]
            edges_in_cycles.add((u, v))

    return len(edges_in_cycles) / max(total_edges, 1)


def compute_observation_snapshot(
    graph: Any,
    total_imports_attempted: Optional[int] = None,
) -> ObservationSnapshot:
    """
    Compute primitive metrics [0,1] from a real ArchitecturalGraph.

    Uses the same ratio formulas as the C0.0 synthetic system,
    enabling regime classification via classify_observed_regime().

    Parameters
    ----------
    graph : ArchitecturalGraph
        Grafo arquitetural real, construído por GraphBuilder.
    total_imports_attempted : int, optional
        Número total de imports que o parser tentou resolver.
        Usado para estimar unknown_dynamic_edges (imports que não
        puderam ser resolvidos e não geraram arestas).

    Returns
    -------
    ObservationSnapshot
        Métricas primitivas + qualidade observacional.
    """
    total_nodes = graph.file_count
    total_file_edges = 0
    cross_domain = 0
    intra_domain = 0
    unknown_unresolved = 0

    for u, v, data in graph.graph.edges(data=True):
        # Skip module-to-module edges
        if data.get("import_type") == "module":
            continue

        # Only count file-to-file edges
        u_data = graph.graph.nodes.get(u, {})
        v_data = graph.graph.nodes.get(v, {})

        if u_data.get("node_type") != "file" or v_data.get("node_type") != "file":
            continue

        # Skip self-loops
        if u == v:
            continue

        total_file_edges += 1

        # Get module for both endpoints
        module_u = u_data.get("module") or ""
        module_v = v_data.get("module") or ""

        if not module_u or not module_v:
            unknown_unresolved += 1
            continue

        if module_u == module_v:
            intra_domain += 1
        else:
            cross_domain += 1

    # Cycle density via edges_in_cycles
    cycle_density_value = _compute_cycle_density_file_edges(graph, total_file_edges)

    # file_level_leakage: fraction of edges with explicit boundary violation
    boundary_violations = 0
    for u, v, data in graph.graph.edges(data=True):
        if data.get("is_boundary_violation") and data.get("import_type") != "module":
            boundary_violations += 1

    file_level_leakage_value = 0.0
    if total_file_edges > 0:
        file_level_leakage_value = boundary_violations / total_file_edges

    # Estimate unknown_dynamic_edges
    unknown_dynamic = 0
    if total_imports_attempted is not None and total_imports_attempted > total_file_edges:
        unknown_dynamic = total_imports_attempted - total_file_edges - unknown_unresolved

    # Build ratios
    cross_domain_ratio = 0.0
    intra_domain_ratio = 0.0
    if total_file_edges > 0:
        cross_domain_ratio = cross_domain / total_file_edges
        intra_domain_ratio = intra_domain / total_file_edges

    return ObservationSnapshot(
        cross_domain_ratio=cross_domain_ratio,
        intra_domain_ratio=intra_domain_ratio,
        file_level_leakage=file_level_leakage_value,
        cycle_density=cycle_density_value,
        total_nodes=total_nodes,
        total_edges=total_file_edges,
        cross_domain_edges=cross_domain,
        intra_domain_edges=intra_domain,
        unknown_unresolved_edges=unknown_unresolved,
        unknown_dynamic_edges=unknown_dynamic,
        total_imports_attempted=total_imports_attempted or 0,
    )
