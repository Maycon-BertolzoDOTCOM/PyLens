"""
Quality Analysis — Métricas PyArch para avaliação de qualidade do código.

Fornece métricas baseadas no AGS (Architectural Graph System):
- coupling_index: acoplamento entre pacotes (inspirado em Briand et al., 1999)
- cohesion_index: coesão interna de dependências
- cyclic_ratio: fração de arestas envolvidas em ciclos
- leakage_ratio: fração de imports que violam fronteiras de domínio
- quality_score: score composto (0-100)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ags.core.graph.metrics import cycle_density, dependency_density, most_connected_nodes


@dataclass
class QualityMetrics:
    """Métricas de qualidade do código."""
    cyclic_ratio: float = 0.0
    dependency_density: float = 0.0
    leakage_ratio: float = 0.0
    coupling_index: float = 0.0
    cohesion_index: float = 0.0
    quality_score: float = 0.0
    fan_out_avg: float = 0.0
    fan_in_avg: float = 0.0
    most_connected: List[Dict[str, Any]] = field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0


@dataclass
class QualityAssessment:
    """Avaliação completa de qualidade."""
    metrics: QualityMetrics
    grade: str  # "A", "B", "C", "D", "F"
    optimization_potential: str  # "HIGH", "MEDIUM", "LOW"
    issues: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


class QualityAnalyzer:
    """
    Analisador de qualidade baseado em métricas arquiteturais.

    Calcula métricas (cyclic_ratio, coupling_index, cohesion_index,
    leakage_ratio) que ajudam a decidir se o código é adequado
    para otimização.
    """

    def assess(self, graph: Any) -> QualityAssessment:
        """
        Avaliar qualidade do código baseado no grafo arquitetural.

        Args:
            graph: ArchitecturalGraph do AGS

        Returns:
            QualityAssessment com métricas e recomendação
        """
        metrics = self._compute_metrics(graph)
        grade = self._compute_grade(metrics)
        potential = self._compute_optimization_potential(metrics, grade)
        issues, strengths = self._analyze_patterns(metrics)

        return QualityAssessment(
            metrics=metrics,
            grade=grade,
            optimization_potential=potential,
            issues=issues,
            strengths=strengths,
        )

    def _compute_metrics(self, graph: Any) -> QualityMetrics:
        """Calcular todas as métricas."""
        nx_graph = graph.graph
        total_nodes = graph.file_count
        total_edges = nx_graph.number_of_edges()

        cd = cycle_density(nx_graph)
        dd = dependency_density(nx_graph)

        boundary_violations = sum(
            1 for _, _, data in nx_graph.edges(data=True)
            if data.get("is_boundary_violation", False)
        )
        bl = boundary_violations / max(total_edges, 1)

        coupling_idx = self._compute_coupling_index(nx_graph, total_nodes)
        cohesion_idx = self._compute_cohesion_index(nx_graph, total_edges)

        fan_out_avg = sum(nx_graph.out_degree(n) for n in nx_graph.nodes()) / max(total_nodes, 1)
        fan_in_avg = sum(nx_graph.in_degree(n) for n in nx_graph.nodes()) / max(total_nodes, 1)

        top_connected = most_connected_nodes(nx_graph, top_n=5)
        most_connected = [
            {"node": n.split("/")[-1] if "/" in n else n, "connections": c}
            for n, c in top_connected
        ]

        quality_score = self._compute_quality_score(cd, dd, bl, coupling_idx, cohesion_idx)

        return QualityMetrics(
            cyclic_ratio=cd,
            dependency_density=dd,
            leakage_ratio=bl,
            coupling_index=coupling_idx,
            cohesion_index=cohesion_idx,
            quality_score=quality_score,
            fan_out_avg=fan_out_avg,
            fan_in_avg=fan_in_avg,
            most_connected=most_connected,
            total_nodes=total_nodes,
            total_edges=total_edges,
        )

    def _compute_coupling_index(self, nx_graph: Any, total_nodes: int) -> float:
        """Coupling index: acoplamento entre pacotes (inspirado em Briand et al., 1999).

        Mede o quão concentrado está o acoplamento entre módulos.
        Valores altos indicam centralização problemática em poucos módulos.
        """
        if total_nodes == 0:
            return 0.0

        centrality = {}
        for node in nx_graph.nodes():
            degree = nx_graph.in_degree(node) + nx_graph.out_degree(node)
            centrality[node] = degree

        if not centrality:
            return 0.0

        max_degree = max(centrality.values())
        if max_degree == 0:
            return 0.0

        normalized = [d / max_degree for d in centrality.values()]
        avg = sum(normalized) / len(normalized)
        variance = sum((x - avg) ** 2 for x in normalized) / len(normalized)
        return min(variance * 4, 1.0)

    def _compute_cohesion_index(self, nx_graph: Any, total_edges: int) -> float:
        """Cohesion index: coesão interna de dependências.

        Mede a fração de arestas que são cross-module.
        Valores altos indicam muitos imports entre módulos diferentes.
        """
        if total_edges == 0:
            return 0.0

        cross_module = sum(
            1 for _, _, data in nx_graph.edges(data=True)
            if data.get("is_cross_module", False)
        )

        return cross_module / total_edges

    def _compute_quality_score(
        self,
        cyclic_ratio: float,
        dep_density: float,
        leakage_ratio: float,
        coupling_idx: float,
        cohesion_idx: float
    ) -> float:
        """Calcular score de qualidade (0-100).

        Composição ponderada:
        - cyclic_ratio (30%): fração de arestas em ciclos
        - dep_density (20%): densidade de dependências
        - leakage_ratio (25%): fração de imports que violam fronteiras
        - coupling_idx (15%): centralização do acoplamento
        - cohesion_idx (10%): fração de cross-module imports
        """
        cd_score = (1 - min(cyclic_ratio, 1.0)) * 100

        if 0.1 <= dep_density <= 0.3:
            dd_score = 100
        elif dep_density < 0.1:
            dd_score = dep_density * 1000
        else:
            dd_score = max(0, 100 - (dep_density - 0.3) * 200)

        bl_score = (1 - min(leakage_ratio, 1.0)) * 100
        coupling_score = (1 - min(coupling_idx, 1.0)) * 100

        if 0.2 <= cohesion_idx <= 0.5:
            cohesion_score = 100
        elif cohesion_idx < 0.2:
            cohesion_score = cohesion_idx * 500
        else:
            cohesion_score = max(0, 100 - (cohesion_idx - 0.5) * 200)

        score = (
            cd_score * 0.30 +
            dd_score * 0.20 +
            bl_score * 0.25 +
            coupling_score * 0.15 +
            cohesion_score * 0.10
        )

        return round(score, 1)

    def _compute_grade(self, metrics: QualityMetrics) -> str:
        """Converter score para grade."""
        score = metrics.quality_score
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _compute_optimization_potential(
        self,
        metrics: QualityMetrics,
        grade: str
    ) -> str:
        """Determinar potencial de otimização."""
        if grade in ("A", "B") and metrics.cyclic_ratio < 0.2:
            return "HIGH"
        elif grade == "C" and metrics.cyclic_ratio < 0.3:
            return "MEDIUM"
        else:
            return "LOW"

    def _analyze_patterns(
        self,
        metrics: QualityMetrics
    ) -> tuple[List[str], List[str]]:
        """Identificar padrões fortes e fracos."""
        issues = []
        strengths = []

        if metrics.cyclic_ratio > 0.3:
            issues.append(
                f"Alta densidade de ciclos ({metrics.cyclic_ratio:.2f}). "
                "Refatore para reduzir acoplamento circular."
            )

        if metrics.leakage_ratio > 0.2:
            issues.append(
                f"Vazamento de fronteiras alto ({metrics.leakage_ratio:.2f}). "
                "Respeite as fronteiras entre módulos."
            )

        if metrics.coupling_index > 0.6:
            issues.append(
                f"Acoplamento muito concentrado ({metrics.coupling_index:.2f}). "
                "Distribua as dependências mais uniformemente."
            )

        if metrics.cyclic_ratio < 0.1:
            strengths.append(
                f"Baixa densidade de ciclos ({metrics.cyclic_ratio:.2f}). "
                "Estrutura bem organizada."
            )

        if metrics.leakage_ratio < 0.05:
            strengths.append(
                f"Pouco vazamento de fronteiras ({metrics.leakage_ratio:.2f}). "
                "Fronteiras bem definidas."
            )

        if 0.1 <= metrics.dependency_density <= 0.3:
            strengths.append(
                f"Densidade de dependências equilibrada ({metrics.dependency_density:.2f})."
            )

        if metrics.quality_score >= 80:
            strengths.append(
                f"Score de qualidade alto ({metrics.quality_score})."
            )

        return issues, strengths
