"""
PyLens Analysis — Análise estática e arquitetural de código Python.

Módulos:
- architectural: Análise via AGS (Architectural Graph System)
- quality: Métricas arquiteturais (coupling_index, cohesion_index, cyclic_ratio, leakage_ratio)
- static_analysis: Análise estática com AST + scoring
- report: Relatório inteligente consolidado
"""

from .architectural import ArchitecturalAnalyzer, ArchitecturalResult
from .quality import QualityAnalyzer, QualityMetrics, QualityAssessment
from .static_analysis import StaticAnalyzer, AnalysisResult
from .report import ReportGenerator, PyLensReport

__all__ = [
    "ArchitecturalAnalyzer",
    "ArchitecturalResult",
    "QualityAnalyzer",
    "QualityMetrics",
    "QualityAssessment",
    "StaticAnalyzer",
    "AnalysisResult",
    "ReportGenerator",
    "PyLensReport",
]
