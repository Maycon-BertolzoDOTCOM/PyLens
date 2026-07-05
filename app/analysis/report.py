"""
Report Generator — Relatório inteligente consolidado.

Combina:
- Análise estática (AST + métricas PyArch)
- Análise arquitetural (AGS + regime)
- Sugestões de otimização
- Recomendações de melhoria
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .architectural import ArchitecturalAnalyzer, ArchitecturalResult
from .quality import QualityAnalyzer, QualityAssessment
from .static_analysis import StaticAnalyzer, AnalysisResult


@dataclass
class OptimizationSuggestion:
    """Sugestão de otimização."""
    category: str  # "performance", "structure", "style"
    priority: str  # "high", "medium", "low"
    description: str
    code_example: Optional[str] = None
    impact: str = "unknown"  # "high", "medium", "low"


@dataclass
class PyLensReport:
    """Relatório completo do PyLens."""
    # Metadados
    code_length: int = 0
    language: str = "python"

    # Análises
    static_analysis: Optional[AnalysisResult] = None
    architectural: Optional[ArchitecturalResult] = None
    quality: Optional[QualityAssessment] = None

    # Resumo
    overall_score: float = 0.0
    overall_grade: str = "F"
    optimization_potential: str = "LOW"

    # Insights
    key_findings: List[str] = field(default_factory=list)
    suggestions: List[OptimizationSuggestion] = field(default_factory=list)
    quick_wins: List[str] = field(default_factory=list)

    # Métricas consolidadas
    metrics_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário serializável."""
        return {
            "metadata": {
                "code_length": self.code_length,
                "language": self.language,
            },
            "overall": {
                "score": self.overall_score,
                "grade": self.overall_grade,
                "optimization_potential": self.optimization_potential,
            },
            "analyses": {
                "static": self.static_analysis.to_dict() if self.static_analysis else None,
                "architectural": {
                    "regime": self.architectural.regime.value if self.architectural else None,
                    "cycle_density": self.architectural.cycle_density if self.architectural else 0,
                    "dependency_density": self.architectural.dependency_density if self.architectural else 0,
                } if self.architectural else None,
                "quality": {
                    "grade": self.quality.grade if self.quality else "F",
                    "score": self.quality.metrics.quality_score if self.quality else 0,
                } if self.quality else None,
            },
            "insights": {
                "key_findings": self.key_findings,
                "quick_wins": self.quick_wins,
                "suggestions_count": len(self.suggestions),
            },
            "metrics_summary": self.metrics_summary,
        }


class ReportGenerator:
    """
    Gerador de relatórios inteligentes.

    Combina todas as análises em um relatório coeso e acionável.
    """

    def __init__(self):
        self.static_analyzer = StaticAnalyzer()
        self.architectural_analyzer = ArchitecturalAnalyzer()
        self.quality_analyzer = QualityAnalyzer()

    def generate(self, python_code: str) -> PyLensReport:
        """
        Gerar relatório completo para código Python.

        Args:
            python_code: Código Python para analisar

        Returns:
            PyLensReport com todas as análises e sugestões
        """
        report = PyLensReport(
            code_length=len(python_code),
            language="python",
        )

        # 1. Análise estática
        report.static_analysis = self.static_analyzer.analyze_detailed(python_code)

        # 2. Análise arquitetural
        report.architectural = self.architectural_analyzer.analyze(python_code)

        # 3. Análise de qualidade (se tiver grafo disponível)
        if (report.architectural and
                hasattr(report.architectural, 'observation') and
                report.architectural.observation):
            try:
                from ags.core.graph.architectural_graph import ArchitecturalGraph
                graph = ArchitecturalGraph()
                # Nota: qualidade requer grafo completo, que pode não estar disponível
                # Neste caso, usamos métricas derivadas
                pass
            except Exception:
                pass

        # 4. Calcular score geral
        report.overall_score = self._calculate_overall_score(report)

        # 5. Determinar grade
        report.overall_grade = self._determine_grade(report.overall_score)

        # 6. Determinar potencial de otimização
        report.optimization_potential = self._determine_optimization_potential(report)

        # 7. Gerar insights
        report.key_findings = self._generate_key_findings(report)

        # 8. Gerar sugestões
        report.suggestions = self._generate_suggestions(report)

        # 9. Gerar quick wins
        report.quick_wins = self._generate_quick_wins(report)

        # 10. Consolidar métricas
        report.metrics_summary = self._consolidate_metrics(report)

        return report

    def _calculate_overall_score(self, report: PyLensReport) -> float:
        """Calcular score geral ponderado."""
        scores = []
        weights = []

        # Score estático (40%)
        if report.static_analysis:
            scores.append(report.static_analysis.score)
            weights.append(0.4)

        # Score arquitetural (30%)
        if report.architectural:
            arch_score = 100
            if report.architectural.optimization_feasibility == "HIGH":
                arch_score = 90
            elif report.architectural.optimization_feasibility == "MEDIUM":
                arch_score = 60
            else:
                arch_score = 30
            scores.append(arch_score)
            weights.append(0.3)

        # Score de qualidade (30%)
        if report.quality:
            scores.append(report.quality.metrics.quality_score)
            weights.append(0.3)

        if not scores:
            return 0.0

        # Média ponderada
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return round(weighted_sum / total_weight, 1)

    def _determine_grade(self, score: float) -> str:
        """Determinar grade baseado no score."""
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

    def _determine_optimization_potential(self, report: PyLensReport) -> str:
        """Determinar potencial de otimização."""
        potentials = []

        if report.static_analysis:
            potentials.append(report.static_analysis.optimization_potential)

        if report.architectural:
            potentials.append(report.architectural.optimization_feasibility)

        # Lógica: se algum é LOW, retorna LOW
        if "LOW" in potentials:
            return "LOW"
        elif all(p == "HIGH" for p in potentials):
            return "HIGH"
        else:
            return "MEDIUM"

    def _generate_key_findings(self, report: PyLensReport) -> List[str]:
        """Gerar descobertas principais."""
        findings = []

        if report.static_analysis:
            findings.append(
                f"Score de otimização: {report.static_analysis.score}/100"
            )
            if report.static_analysis.loops_count > 0:
                findings.append(
                    f"{report.static_analysis.loops_count} loops detectados (oportunidade de otimização)"
                )

        if report.architectural:
            findings.append(
                f"Regime arquitetônico: {report.architectural.regime.value}"
            )
            if report.architectural.cycle_density > 0.2:
                findings.append(
                    "Alta densidade de ciclos - refatoração recomendada"
                )

        if report.quality:
            findings.append(
                f"Qualidade geral: {report.quality.grade} ({report.quality.metrics.quality_score})"
            )

        return findings

    def _generate_suggestions(self, report: PyLensReport) -> List[OptimizationSuggestion]:
        """Gerar sugestões de otimização."""
        suggestions = []

        if report.architectural and report.architectural.suggestions:
            for i, sug in enumerate(report.architectural.suggestions):
                suggestions.append(
                    OptimizationSuggestion(
                        category="structure",
                        priority="medium" if i < 2 else "low",
                        description=sug,
                        impact="medium",
                    )
                )

        if report.static_analysis and report.static_analysis.loops_count > 3:
            suggestions.append(
                OptimizationSuggestion(
                    category="performance",
                    priority="high",
                    description="Múltiplos loops detectados. Considere usar comprehensions ou map/select.",
                    code_example="# Antes\nfor x in items:\n    result.append(x * 2)\n\n# Depois\nresult = [x * 2 for x in items]",
                    impact="high",
                )
            )

        if report.architectural and report.architectural.cycle_density > 0.2:
            suggestions.append(
                OptimizationSuggestion(
                    category="structure",
                    priority="high",
                    description="Alta densidade de ciclos. Refatore para reduzir acoplamento.",
                    impact="high",
                )
            )

        return suggestions

    def _generate_quick_wins(self, report: PyLensReport) -> List[str]:
        """Gerar quick wins (melhorias fáceis com alto impacto)."""
        quick_wins = []

        if report.static_analysis and report.static_analysis.loops_count > 0:
            quick_wins.append(
                "Usar comprehensions em vez de loops simples para melhor legibilidade e performance"
            )

        if report.architectural and report.architectural.code_structure.lambdas > 0:
            quick_wins.append(
                "Lambdas já são eficientes - manter para operações simples"
            )

        if report.architectural and report.architectural.code_structure.comprehensions > 0:
            quick_wins.append(
                "Comprehensions já são otimizadas - ótimo uso de padrões Python"
            )

        return quick_wins

    def _consolidate_metrics(self, report: PyLensReport) -> Dict[str, Any]:
        """Consolidar todas as métricas."""
        metrics = {}

        if report.static_analysis:
            metrics["static_score"] = report.static_analysis.score
            metrics["loops"] = report.static_analysis.loops_count
            metrics["imports"] = len(report.static_analysis.imports)

        if report.architectural:
            metrics["regime"] = report.architectural.regime.value
            metrics["cycle_density"] = report.architectural.cycle_density
            metrics["dependency_density"] = report.architectural.dependency_density
            metrics["classes"] = len(report.architectural.code_structure.classes)
            metrics["functions"] = len(report.architectural.code_structure.functions)
            metrics["decorators"] = report.architectural.code_structure.decorators
            metrics["async_constructs"] = report.architectural.code_structure.async_constructs

        if report.quality:
            metrics["quality_score"] = report.quality.metrics.quality_score
            metrics["quality_grade"] = report.quality.grade
            metrics["coupling_index"] = report.quality.metrics.coupling_index
            metrics["cohesion_index"] = report.quality.metrics.cohesion_index

        return metrics
