"""
Static Analysis — Análise estática de código Python com métricas PyArch.

Integra:
- Análise AST
- Métricas do AGS (Architectural Graph System)
- Classificação de regime arquitetônico
- Score de otimização
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ags.core.graph.builders import GraphBuilder
from ags.core.graph.metrics import cycle_density, dependency_density
from ags.core.observation.primitives import ObservationSnapshot, compute_observation_snapshot
from ags.core.observation.classification import RegimeClassification, classify_from_snapshot
from ags.synthetic.regimes import RegimeName


class AnalysisResult:
    """Resultado completo da análise estática."""

    def __init__(
        self,
        score: int,
        imports: List[str],
        loops_count: int,
        cycle_density: float = 0.0,
        dependency_density: float = 0.0,
        regime: Optional[RegimeName] = None,
        regime_classification: Optional[RegimeClassification] = None,
        observation: Optional[ObservationSnapshot] = None,
        optimization_potential: str = "UNKNOWN",
        details: Optional[Dict] = None,
    ):
        self.score = score
        self.imports = imports
        self.loops_count = loops_count
        self.cycle_density = cycle_density
        self.dependency_density = dependency_density
        self.regime = regime
        self.regime_classification = regime_classification
        self.observation = observation
        self.optimization_potential = optimization_potential
        self.details = details or {}

    def to_dict(self) -> Dict:
        """Converter para dicionário."""
        return {
            "score": self.score,
            "imports": self.imports,
            "loops_count": self.loops_count,
            "cycle_density": self.cycle_density,
            "dependency_density": self.dependency_density,
            "regime": self.regime.value if self.regime else None,
            "optimization_potential": self.optimization_potential,
            "details": self.details,
        }


class StaticAnalyzer:
    """Analisador estático de código Python com métricas arquiteturais."""

    def __init__(self):
        self.supported_imports = {
            "math",
            "numpy",
            "pandas",
            "scipy",
            "tensorflow",
            "torch",
            "sklearn",
            "time",
            "datetime",
        }

    def analyze(self, code: str, use_pyarch: bool = True) -> Tuple[int, List[str], int]:
        """
        Analisar código e retornar score, imports, contagem de loops.

        Args:
            code: Código Python para analisar
            use_pyarch: Se True, usa métricas arquiteturais na análise

        Returns:
            Tupla (score, imports, loops_count)
        """
        try:
            tree = ast.parse(code)

            imports = self._analyze_imports(tree)
            loops_count = self._count_loops(tree)
            math_ops = self._count_math_operations(tree)
            function_calls = self._count_function_calls(tree)

            base_score = self._calculate_score(loops_count, math_ops, function_calls)

            if use_pyarch:
                pyarch_score = self._calculate_pyarch_score(code)
                final_score = int(base_score * 0.7 + pyarch_score * 0.3)
                return min(final_score, 100), imports, loops_count

            return base_score, imports, loops_count

        except SyntaxError:
            return 0, [], 0

    def analyze_detailed(self, code: str) -> AnalysisResult:
        """
        Análise detalhada com métricas arquiteturais completas.

        Args:
            code: Código Python para analisar

        Returns:
            AnalysisResult com todas as métricas
        """
        try:
            tree = ast.parse(code)

            imports = self._analyze_imports(tree)
            loops_count = self._count_loops(tree)
            math_ops = self._count_math_operations(tree)
            function_calls = self._count_function_calls(tree)

            base_score = self._calculate_score(loops_count, math_ops, function_calls)

            arch_metrics = self._compute_arch_metrics(code)

            regime_class = arch_metrics.get("regime_classification")

            potential = self._calculate_optimization_potential(
                base_score,
                loops_count,
                arch_metrics.get("cycle_density", 0),
                arch_metrics.get("dependency_density", 0),
                regime_class.regime if regime_class else None,
            )

            return AnalysisResult(
                score=base_score,
                imports=imports,
                loops_count=loops_count,
                cycle_density=arch_metrics.get("cycle_density", 0),
                dependency_density=arch_metrics.get("dependency_density", 0),
                regime=regime_class.regime if regime_class else None,
                regime_classification=regime_class,
                observation=arch_metrics.get("observation"),
                optimization_potential=potential,
                details={
                    "math_ops": math_ops,
                    "function_calls": function_calls,
                    "total_score": base_score,
                },
            )

        except SyntaxError:
            return AnalysisResult(score=0, imports=[], loops_count=0)

    def _analyze_imports(self, tree: ast.AST) -> List[str]:
        """Analisar imports do código"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return [imp for imp in imports if any(supported in imp for supported in self.supported_imports)]

    def _count_loops(self, tree: ast.AST) -> int:
        """Contar loops no código, com peso maior para loops aninhados."""

        class _LoopCounter(ast.NodeVisitor):
            def __init__(self):
                self.count = 0
                self._depth = 0

            def visit_For(self, node):
                self._depth += 1
                self.count += self._depth
                self.generic_visit(node)
                self._depth -= 1

            def visit_While(self, node):
                self._depth += 1
                self.count += self._depth
                self.generic_visit(node)
                self._depth -= 1

        counter = _LoopCounter()
        counter.visit(tree)
        return counter.count

    def _count_math_operations(self, tree: ast.AST) -> int:
        """Contar operações matemáticas"""
        math_ops = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(
                node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
            ):
                math_ops += 1
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"sum", "min", "max", "abs", "pow"}:
                    math_ops += 1

        return math_ops

    def _count_function_calls(self, tree: ast.AST) -> int:
        """Contar chamadas de função"""
        calls = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                calls += 1

        return calls

    def _calculate_score(self, loops: int, math_ops: int, function_calls: int) -> int:
        """Calcular score baseado nos indicadores"""
        score = 0

        if loops > 0:
            score += min(loops * 3, 40)

        if math_ops > 10:
            score += min(math_ops, 30)

        if function_calls > 5:
            score += min(function_calls, 20)

        return min(score, 100)

    def _calculate_pyarch_score(self, code: str) -> int:
        """Calcular score usando métricas arquiteturais do AGS."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                code_file = Path(tmpdir) / "main.py"
                code_file.write_text(code, encoding="utf-8")

                builder = GraphBuilder(tmpdir)
                graph = builder.build()

                cd = cycle_density(graph.graph)
                dd = dependency_density(graph.graph)

                score = 0

                cd_score = (1 - min(cd, 1.0)) * 50
                score += cd_score

                if 0.1 <= dd <= 0.3:
                    score += 50
                elif dd < 0.1:
                    score += dd * 500
                else:
                    score += max(0, 50 - (dd - 0.3) * 100)

                return int(score)

        except Exception:
            return 50

    def _compute_arch_metrics(self, code: str) -> Dict:
        """Computar métricas arquiteturais completas."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                code_file = Path(tmpdir) / "main.py"
                code_file.write_text(code, encoding="utf-8")

                builder = GraphBuilder(tmpdir)
                graph = builder.build()

                cd = cycle_density(graph.graph)
                dd = dependency_density(graph.graph)

                observation = compute_observation_snapshot(
                    graph,
                    total_imports_attempted=builder.total_imports_attempted,
                )

                regime_class = classify_from_snapshot(observation, graph_size=graph.file_count)

                return {
                    "cycle_density": cd,
                    "dependency_density": dd,
                    "observation": observation,
                    "regime_classification": regime_class,
                    "graph": graph,
                }

        except Exception:
            return {
                "cycle_density": 0,
                "dependency_density": 0,
                "observation": None,
                "regime_classification": None,
                "graph": None,
            }

    def _calculate_optimization_potential(
        self,
        score: int,
        loops: int,
        cycle_density: float,
        dependency_density: float,
        regime: Optional[RegimeName],
    ) -> str:
        """Calcular potencial de otimização."""
        potential_score = 100

        potential_score -= max(0, 50 - score)

        if cycle_density > 0.3:
            potential_score -= 25
        elif cycle_density > 0.15:
            potential_score -= 10

        if dependency_density > 0.5:
            potential_score -= 20
        elif dependency_density > 0.3:
            potential_score -= 10

        regime_penalties = {
            RegimeName.PATHOLOGICAL: 30,
            RegimeName.COLLAPSED: 25,
            RegimeName.LEAKY: 20,
            RegimeName.ENTANGLED_SMALL: 15,
            RegimeName.ENTANGLED_LARGE: 15,
            RegimeName.MIXED: 10,
        }
        if regime:
            potential_score -= regime_penalties.get(regime, 0)

        regime_bonuses = {
            RegimeName.PERFECT: 15,
            RegimeName.MODULAR_SMALL: 10,
            RegimeName.MODULAR_LARGE: 10,
            RegimeName.ACYCLIC_DOMINANT: 10,
        }
        if regime:
            potential_score += regime_bonuses.get(regime, 0)

        if potential_score >= 70:
            return "HIGH"
        elif potential_score >= 40:
            return "MEDIUM"
        else:
            return "LOW"
