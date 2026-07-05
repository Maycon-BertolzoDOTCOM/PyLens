"""
Architectural Analysis — Análise arquitetural via AGS (Architectural Graph System).

Fornece:
- Classificação de regime (MODULAR, ENTANGLED, COUPLED, etc.)
- Métricas de dependência
- Avaliação de viabilidade de otimização
"""

from __future__ import annotations

import ast
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ags.core.graph.builders import GraphBuilder
from ags.core.graph.metrics import cycle_density, dependency_density
from ags.core.observation.primitives import ObservationSnapshot, compute_observation_snapshot
from ags.core.observation.classification import RegimeClassification, classify_from_snapshot
from ags.synthetic.regimes import RegimeName


@dataclass
class CodeStructure:
    """Estrutura do código Python analisado."""
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    loops: int = 0
    comprehensions: int = 0
    decorators: int = 0
    async_constructs: int = 0
    try_blocks: int = 0
    with_blocks: int = 0
    lambdas: int = 0
    yields: int = 0
    f_strings: int = 0


@dataclass
class ArchitecturalResult:
    """Resultado da análise arquitetural."""
    code_structure: CodeStructure
    regime: RegimeName
    regime_classification: RegimeClassification
    observation: ObservationSnapshot
    cycle_density: float
    dependency_density: float
    optimization_feasibility: str  # "HIGH", "MEDIUM", "LOW"
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ArchitecturalAnalyzer:
    """
    Analisador arquitetural usando AGS.

    Fornece insights sobre a estrutura do código Python
    para guiar decisões de otimização.
    """

    def __init__(self):
        self._structure_analyzer = _StructureAnalyzer()

    def analyze(self, python_code: str) -> ArchitecturalResult:
        """
        Realizar análise arquitetural completa.

        Args:
            python_code: Código Python para analisar

        Returns:
            ArchitecturalResult com estrutura, regime e métricas
        """
        # 1. Analisar estrutura do código
        code_structure = self._structure_analyzer.analyze(python_code)

        # 2. Criar projeto temporário para o GraphBuilder
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "main.py"
            code_file.write_text(python_code, encoding="utf-8")

            builder = GraphBuilder(tmpdir)
            graph = builder.build()

            # 3. Calcular métricas
            cycle_density_value = cycle_density(graph.graph)
            dep_density = dependency_density(graph.graph)

            # 4. Computar observation snapshot
            observation = compute_observation_snapshot(
                graph,
                total_imports_attempted=builder.total_imports_attempted
            )

            # 5. Classificar regime
            regime_class = classify_from_snapshot(observation, graph_size=graph.file_count)

        # 6. Avaliar viabilidade de otimização
        feasibility = self._assess_feasibility(
            code_structure,
            regime_class.regime,
            cycle_density_value
        )

        # 7. Gerar warnings e sugestões
        warnings, suggestions = self._generate_feedback(
            code_structure,
            regime_class.regime,
            cycle_density_value,
            dep_density
        )

        return ArchitecturalResult(
            code_structure=code_structure,
            regime=regime_class.regime,
            regime_classification=regime_class,
            observation=observation,
            cycle_density=cycle_density_value,
            dependency_density=dep_density,
            optimization_feasibility=feasibility,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _assess_feasibility(
        self,
        structure: CodeStructure,
        regime: RegimeName,
        cycles: float
    ) -> str:
        """Avaliar viabilidade de otimização."""
        score = 100

        # Penalizar por construções complexas (difíceis de otimizar com LLM)
        complexity = (
            len(structure.classes) * 5 +
            structure.decorators * 3 +
            structure.async_constructs * 5 +
            structure.try_blocks * 3 +
            structure.with_blocks * 2
        )
        score -= min(complexity, 40)

        # Bonus por código mais otimizável
        optimization_targets = (
            structure.loops * 8 +
            structure.comprehensions * 5 +
            structure.lambdas * 3
        )
        score += min(optimization_targets, 30)

        # Penalizar por regime problemático
        regime_penalties = {
            RegimeName.PATHOLOGICAL: 20,
            RegimeName.COLLAPSED: 15,
            RegimeName.LEAKY: 10,
        }
        score -= regime_penalties.get(regime, 0)

        # Bonus por regime bom
        regime_bonuses = {
            RegimeName.PERFECT: 15,
            RegimeName.MODULAR_SMALL: 10,
            RegimeName.MODULAR_LARGE: 10,
        }
        score += regime_bonuses.get(regime, 0)

        if score >= 70:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_feedback(
        self,
        structure: CodeStructure,
        regime: RegimeName,
        cycles: float,
        dep_density: float
    ) -> tuple[List[str], List[str]]:
        """Gerar warnings e sugestões."""
        warnings = []
        suggestions = []

        # Warnings
        if len(structure.classes) > 3:
            warnings.append(
                f"{len(structure.classes)} classes detectadas. "
                "Classes complexas podem dificultar otimização automática."
            )

        if cycles > 0.3:
            warnings.append(
                f"Alta densidade de ciclos ({cycles:.2f}). "
                "Considere refatorar antes de otimizar."
            )

        if regime in (RegimeName.PATHOLOGICAL, RegimeName.COLLAPSED):
            warnings.append(
                f"Regime arquitetônico {regime.value}. "
                "Estrutura pode precisar de refatoração antes da otimização."
            )

        # Sugestões de otimização
        if structure.loops > 0:
            suggestions.append(
                f"{structure.loops} loops detectados. "
                "Considere usar comprehensions ou map/select para otimizar."
            )

        if structure.comprehensions > 0:
            suggestions.append(
                f"{structure.comprehensions} comprehensions detectadas. "
                "Já são uma forma otimizada de iteração."
            )

        if structure.lambdas > 0:
            suggestions.append(
                f"{structure.lambdas} lambdas detectadas. "
                "Funções anônimas são eficientes para operações simples."
            )

        if structure.async_constructs > 0:
            suggestions.append(
                "Código assíncrono detectado. "
                "Otimização de I/O-bound é mais eficaz que CPU-bound."
            )

        if len(structure.imports) > 5:
            suggestions.append(
                "Múltiplos imports. "
                "Considere importar apenas funções específicas."
            )

        return warnings, suggestions


class _StructureAnalyzer:
    """Analisador de estrutura Python."""

    def analyze(self, python_code: str) -> CodeStructure:
        """Analisar estrutura do código Python."""
        try:
            tree = ast.parse(python_code)
        except SyntaxError:
            return CodeStructure()

        structure = CodeStructure()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                structure.classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "decorators": len(node.decorator_list),
                })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_async = isinstance(node, ast.AsyncFunctionDef)
                structure.functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "is_async": is_async,
                    "args": len(node.args.args),
                })
                if is_async:
                    structure.async_constructs += 1
                structure.decorators += len(node.decorator_list)

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        structure.imports.append({
                            "module": alias.name,
                            "type": "import",
                        })
                else:
                    module = node.module or ""
                    for alias in node.names:
                        structure.imports.append({
                            "module": module,
                            "name": alias.name,
                            "type": "from",
                        })

            elif isinstance(node, (ast.For, ast.While)):
                structure.loops += 1

            elif isinstance(node, ast.ListComp):
                structure.comprehensions += 1

            elif isinstance(node, ast.SetComp):
                structure.comprehensions += 1

            elif isinstance(node, ast.DictComp):
                structure.comprehensions += 1

            elif isinstance(node, ast.GeneratorExp):
                structure.comprehensions += 1

            elif isinstance(node, ast.Try):
                structure.try_blocks += 1

            elif isinstance(node, (ast.With, ast.AsyncWith)):
                structure.with_blocks += 1

            elif isinstance(node, ast.Lambda):
                structure.lambdas += 1

            elif isinstance(node, (ast.Yield, ast.YieldFrom)):
                structure.yields += 1

            elif isinstance(node, ast.JoinedStr):
                structure.f_strings += 1

        return structure
