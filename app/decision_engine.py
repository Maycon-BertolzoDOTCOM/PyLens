"""
Decision Engine — Pipeline "observar → classificar → agir".

Módulo puro, sem dependências FastAPI.
Responsável por decidir a melhor ação para otimizar código Python.

Baseado em métricas arquiteturais (cyclic_ratio, coupling_index,
cohesion_index) e classificação de regime do AGS.

Decisões possíveis:
- LLM_OPTIMIZE: Usar LLM para gerar variantes otimizadas
- CRYSTAL: Transpilar para Crystal (se plugin disponível)
- BOTH: Aplicar LLM + Crystal (benchmark comparativo)
- MANUAL_REFACTOR: Sugerir refatoração manual (código muito acoplado)
- SKIP: Código já está bom, não precisa de otimização
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .analysis.static_analysis import StaticAnalyzer, AnalysisResult
from .analysis.architectural import ArchitecturalAnalyzer, ArchitecturalResult
from ags.synthetic.regimes import RegimeName


class Decision(str, Enum):
    """Decisões possíveis."""
    LLM_OPTIMIZE = "LLM_OPTIMIZE"
    CRYSTAL = "CRYSTAL"
    BOTH = "BOTH"
    MANUAL_REFACTOR = "MANUAL_REFACTOR"
    SKIP = "SKIP"


class Risk(str, Enum):
    """Nível de risco da decisão."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ActionStep:
    """Passo de ação no plano."""
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


@dataclass
class DecisionPlan:
    """Plano de decisão completo."""
    decision: Decision
    confidence: float
    risk: Risk
    reasoning: str
    steps: List[ActionStep] = field(default_factory=list)
    alternative: Optional[Decision] = None
    metrics_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário serializável."""
        return {
            "decision": self.decision.value,
            "confidence": round(self.confidence, 3),
            "risk": self.risk.value,
            "reasoning": self.reasoning,
            "plan": {
                "steps": [
                    {"action": s.action, "params": s.params, "status": s.status}
                    for s in self.steps
                ],
                "alternative": self.alternative.value if self.alternative else None,
            },
            "metrics_summary": self.metrics_summary,
        }


class DecisionEngine:
    """
    Motor de decisão puro.

    Analisa código e recomenda a melhor ação de otimização
    baseada em métricas objetivas.
    """

    def __init__(self):
        self.static_analyzer = StaticAnalyzer()
        self.architectural_analyzer = ArchitecturalAnalyzer()

    def decide(
        self,
        python_code: str,
        user_preference: Optional[str] = None,
    ) -> DecisionPlan:
        """
        Decidir a melhor ação para o código fornecido.

        Args:
            python_code: Código Python para analisar
            user_preference: Preferência do utilizador ("prefer_crystal", "prefer_llm", None)

        Returns:
            DecisionPlan com decisão, confiança e plano de ação
        """
        # 1. Analisar código
        static_result = self.static_analyzer.analyze_detailed(python_code)
        arch_result = self.architectural_analyzer.analyze(python_code)

        # 2. Extrair métricas-chave
        regime = arch_result.regime
        cycle_density = arch_result.cycle_density
        loops = static_result.loops_count
        score = static_result.score
        feasibility = arch_result.optimization_feasibility

        # 3. Aplicar matriz de decisão
        decision, base_confidence, reasoning = self._apply_decision_matrix(
            regime=regime,
            cycle_density=cycle_density,
            loops=loops,
            score=score,
            feasibility=feasibility,
            user_preference=user_preference,
        )

        # 4. Calcular risco
        risk = self._calculate_risk(base_confidence, decision, cycle_density)

        # 5. Gerar plano de ação
        steps = self._build_plan(decision, static_result, arch_result)

        # 6. Determinar alternativa
        alternative = self._determine_alternative(decision, regime, loops)

        # 7. Consolidar métricas
        metrics_summary = {
            "score": score,
            "regime": regime.value if regime else None,
            "cycle_density": round(cycle_density, 3),
            "loops": loops,
            "feasibility": feasibility,
        }

        return DecisionPlan(
            decision=decision,
            confidence=base_confidence,
            risk=risk,
            reasoning=reasoning,
            steps=steps,
            alternative=alternative,
            metrics_summary=metrics_summary,
        )

    def _apply_decision_matrix(
        self,
        regime: RegimeName,
        cycle_density: float,
        loops: int,
        score: int,
        feasibility: str,
        user_preference: Optional[str],
    ) -> tuple[Decision, float, str]:
        """
        Aplicar matriz de decisão.

        Matriz base:
        | Regime | Loops ≥ 3 | Cycles ≥ 0.2 | Decisão |
        |--------|-----------|--------------|---------|
        | MODULAR | sim | não | CRYSTAL |
        | MODULAR | não | não | SKIP |
        | ENTANGLED | sim | não | LLM_OPTIMIZE |
        | ENTANGLED | sim | sim | MANUAL_REFACTOR |
        | PATHOLOGICAL | * | * | MANUAL_REFACTOR |
        | PERFECT | * | * | SKIP |
        | COUPLED | sim | não | LLM_OPTIMIZE ou CRYSTAL |
        """
        has_loops = loops >= 3
        has_cycles = cycle_density >= 0.2

        # Caso especial: PATHOLOGICAL sempre é MANUAL_REFACTOR
        if regime == RegimeName.PATHOLOGICAL:
            return (
                Decision.MANUAL_REFACTOR,
                0.95,
                f"Regime PATHOLOGICAL detectado. Código com estrutura problemática "
                f"(cycle_density={cycle_density:.2f}). Recomenda-se refatoração manual "
                f"antes de qualquer otimização automática."
            )

        # Caso especial: PERFECT sempre é SKIP
        if regime == RegimeName.PERFECT:
            return (
                Decision.SKIP,
                0.90,
                f"Regime PERFECT. Código bem estruturado e otimizado. "
                f"Nenhuma ação necessária."
            )

        # MODULAR com poucos loops → SKIP
        if regime in (RegimeName.MODULAR_SMALL, RegimeName.MODULAR_LARGE) and not has_loops:
            return (
                Decision.SKIP,
                0.85,
                f"Regime {regime.value} com apenas {loops} loops. "
                f"Código já está em boa forma."
            )

        # MODULAR com muitos loops → CRYSTAL
        if regime in (RegimeName.MODULAR_SMALL, RegimeName.MODULAR_LARGE) and has_loops and not has_cycles:
            confidence = 0.80 if feasibility == "HIGH" else 0.70
            return (
                Decision.CRYSTAL,
                confidence,
                f"Regime {regime.value} com {loops} loops (densidade de ciclos={cycle_density:.2f}). "
                f"Código modular e CPU-bound — ideal para Crystal."
            )

        # ENTANGLED sem ciclos → LLM_OPTIMIZE
        if regime in (RegimeName.ENTANGLED_SMALL, RegimeName.ENTANGLED_LARGE) and not has_cycles:
            return (
                Decision.LLM_OPTIMIZE,
                0.75,
                f"Regime {regime.value} com {loops} loops mas sem ciclos significativos. "
                f"LLM pode otimizar sem refatoração estrutural."
            )

        # ENTANGLED com ciclos → MANUAL_REFACTOR
        if regime in (RegimeName.ENTANGLED_SMALL, RegimeName.ENTANGLED_LARGE) and has_cycles:
            return (
                Decision.MANUAL_REFACTOR,
                0.80,
                f"Regime {regime.value} com alta densidade de ciclos ({cycle_density:.2f}). "
                f"Otimização automática pode piorar o acoplamento. Refatoração manual recomendada."
            )

        # COUPLED com loops → LLM ou CRYSTAL (depende da preferência)
        if regime == RegimeName.COUPLED and has_loops and not has_cycles:
            if user_preference == "prefer_crystal":
                return (
                    Decision.CRYSTAL,
                    0.70,
                    f"Regime COUPLED com {loops} loops. Preferência do utilizador: Crystal."
                )
            elif user_preference == "prefer_llm":
                return (
                    Decision.LLM_OPTIMIZE,
                    0.70,
                    f"Regime COUPLED com {loops} loops. Preferência do utilizador: LLM."
                )
            else:
                return (
                    Decision.LLM_OPTIMIZE,
                    0.65,
                    f"Regime COUPLED com {loops} loops. LLM recomendado como opção mais segura."
                )

        # LEAKY → LLM (foco em legibilidade)
        if regime == RegimeName.LEAKY:
            return (
                Decision.LLM_OPTIMIZE,
                0.70,
                f"Regime LEAKY (vazamento de limites={cycle_density:.2f}). "
                f"LLM pode ajudar a melhorar a organização do código."
            )

        # MIXED → LLM (abordagem conservadora)
        if regime == RegimeName.MIXED:
            return (
                Decision.LLM_OPTIMIZE,
                0.65,
                f"Regime MIXED (sinais mistos). "
                f"LLM é a opção mais conservadora e flexível."
            )

        # ACYCLIC_DOMINANT com loops → CRYSTAL
        if regime == RegimeName.ACYCLIC_DOMINANT and has_loops:
            return (
                Decision.CRYSTAL,
                0.75,
                f"Regime ACYCLIC_DOMINANT com {loops} loops. "
                f"Código sem ciclos — bom candidato a Crystal."
            )

        # Fallback: LLM_OPTIMIZE
        return (
            Decision.LLM_OPTIMIZE,
            0.60,
            f"Análise inconclusiva. Score={score}, loops={loops}, "
            f"regime={regime.value}. LLM como opção padrão."
        )

    def _calculate_risk(
        self,
        confidence: float,
        decision: Decision,
        cycle_density: float
    ) -> Risk:
        """Calcular nível de risco da decisão."""
        risk_score = 0

        # Confiança baixa = risco alto
        if confidence < 0.7:
            risk_score += 2
        elif confidence < 0.8:
            risk_score += 1

        # Decisões mais arriscadas
        if decision == Decision.MANUAL_REFACTOR:
            risk_score += 1
        elif decision == Decision.BOTH:
            risk_score += 1

        # Ciclos altos = risco
        if cycle_density > 0.3:
            risk_score += 1

        if risk_score >= 3:
            return Risk.HIGH
        elif risk_score >= 1:
            return Risk.MEDIUM
        else:
            return Risk.LOW

    def _build_plan(
        self,
        decision: Decision,
        static_result: AnalysisResult,
        arch_result: ArchitecturalResult
    ) -> List[ActionStep]:
        """Gerar plano de ação baseado na decisão."""
        steps = []

        # Passo 1: Análise (sempre presente)
        steps.append(ActionStep(
            action="analyze",
            params={"score": static_result.score, "regime": arch_result.regime.value},
            status="done",
        ))

        # Passo 2: Ação baseada na decisão
        if decision == Decision.LLM_OPTIMIZE:
            focus = "performance" if static_result.loops_count > 3 else "readability"
            steps.append(ActionStep(
                action="llm_optimize",
                params={"focus": focus, "num_variants": 3},
            ))
            steps.append(ActionStep(
                action="verify",
                params={"run_tests": True, "check_memory": True},
            ))

        elif decision == Decision.CRYSTAL:
            steps.append(ActionStep(
                action="transpile_to_crystal",
                params={"target": "crystal"},
            ))
            steps.append(ActionStep(
                action="benchmark",
                params={"compare": True},
            ))

        elif decision == Decision.BOTH:
            steps.append(ActionStep(
                action="llm_optimize",
                params={"focus": "performance", "num_variants": 2},
            ))
            steps.append(ActionStep(
                action="transpile_to_crystal",
                params={"target": "crystal"},
            ))
            steps.append(ActionStep(
                action="benchmark_triple",
                params={"original": True, "llm": True, "crystal": True},
            ))

        elif decision == Decision.MANUAL_REFACTOR:
            steps.append(ActionStep(
                action="generate_refactor_suggestions",
                params={
                    "focus": ["cycle_reduction", "boundary_enforcement"],
                    "priority": "high",
                },
            ))

        elif decision == Decision.SKIP:
            steps.append(ActionStep(
                action="log_skip",
                params={"reason": "Código já está otimizado"},
            ))

        return steps

    def _determine_alternative(
        self,
        decision: Decision,
        regime: RegimeName,
        loops: int
    ) -> Optional[Decision]:
        """Determinar ação alternativa."""
        if decision == Decision.SKIP:
            return None

        if decision == Decision.CRYSTAL:
            return Decision.LLM_OPTIMIZE

        if decision == Decision.LLM_OPTIMIZE:
            if loops >= 3:
                return Decision.CRYSTAL
            return Decision.SKIP

        if decision == Decision.MANUAL_REFACTOR:
            return Decision.SKIP

        if decision == Decision.BOTH:
            return Decision.LLM_OPTIMIZE

        return None
