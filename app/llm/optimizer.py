"""
LLM Optimizer — Otimizador de código usando LLM.

Gera variantes otimizadas de código Python usando LLMs.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .router import LLMRouter, LLMResponse, LLMUnavailableError


@dataclass
class OptimizationResult:
    """Resultado da otimização."""
    original_code: str
    optimized_code: str
    explanation: str
    improvements: List[str] = field(default_factory=list)
    backend_used: str = "unknown"
    model_used: str = "unknown"
    is_valid: bool = True
    validation_error: Optional[str] = None


class LLMOptimizer:
    """
    Otimizador de código Python usando LLM.

    Gera variantes otimizadas e valida sintaxe.
    """

    def __init__(self, router: LLMRouter):
        self.router = router

    def optimize(
        self,
        python_code: str,
        context: Optional[str] = None,
        optimization_focus: str = "performance"
    ) -> OptimizationResult:
        """
        Otimizar código Python usando LLM.

        Args:
            python_code: Código Python para otimizar
            context: Contexto adicional sobre o código
            optimization_focus: Foco da otimização ("performance", "readability", "memory")

        Returns:
            OptimizationResult com código otimizado e explicações
        """
        # Construir prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(python_code, context, optimization_focus)

        try:
            # Chamar LLM
            response = self.router.generate(user_prompt, system=system_prompt)

            # Extrair código otimizado
            optimized_code = self._extract_code(response.content)
            explanation = self._extract_explanation(response.content)
            improvements = self._extract_improvements(response.content)

            # Validar sintaxe
            is_valid, validation_error = self._validate_syntax(optimized_code)

            return OptimizationResult(
                original_code=python_code,
                optimized_code=optimized_code,
                explanation=explanation,
                improvements=improvements,
                backend_used=response.backend,
                model_used=response.model,
                is_valid=is_valid,
                validation_error=validation_error,
            )

        except LLMUnavailableError:
            return OptimizationResult(
                original_code=python_code,
                optimized_code=python_code,
                explanation="Nenhum LLM disponível para otimização.",
                improvements=[],
                is_valid=True,
            )

    def generate_variants(
        self,
        python_code: str,
        num_variants: int = 3,
        optimization_focus: str = "performance"
    ) -> List[OptimizationResult]:
        """
        Gerar múltiplas variantes otimizadas.

        Args:
            python_code: Código Python para otimizar
            num_variants: Número de variantes a gerar
            optimization_focus: Foco da otimização

        Returns:
            Lista de OptimizationResult
        """
        variants = []

        for i in range(num_variants):
            variant = self.optimize(
                python_code,
                context=f"Variante {i+1} de {num_variants}",
                optimization_focus=optimization_focus,
            )
            variants.append(variant)

        return variants

    def _build_system_prompt(self) -> str:
        """Construir prompt do sistema."""
        return """Você é um especialista em otimização de código Python.

Sua tarefa é otimizar código Python para melhor performance, legibilidade ou uso de memória.

Diretrizes:
1. Mantenha a funcionalidade original
2. Use constructs Python idiomáticos
3. Considere performance (loops → comprehensions, map, select)
4. Considere legibilidade (não sacrifique para performance)
5. Valide a sintaxe do código gerado

Formato de resposta:
```python
# Código otimizado aqui
```

Explicação das melhorias:
- Melhoria 1
- Melhoria 2
- etc.
"""

    def _build_user_prompt(
        self,
        python_code: str,
        context: Optional[str],
        optimization_focus: str
    ) -> str:
        """Construir prompt do usuário."""
        prompt = f"Otimize este código Python para {optimization_focus}:\n\n```python\n{python_code}\n```"

        if context:
            prompt += f"\n\nContexto adicional: {context}"

        return prompt

    def _extract_code(self, response: str) -> str:
        """Extrair código da resposta do LLM."""
        # Procurar por bloco de código Python
        code_match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Fallback: tentar extrair qualquer bloco de código
        code_match = re.search(r'```\n(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Se não encontrar blocos, retornar a resposta inteira
        return response

    def _extract_explanation(self, response: str) -> str:
        """Extrair explicação da resposta."""
        # Procurar por seção de explicação
        explanation_match = re.search(
            r'(?:Explicação|Explanation|Melhorias|Improvements)[:\s]*(.*?)(?:```|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if explanation_match:
            return explanation_match.group(1).strip()

        # Fallback: retornar partes não-código
        lines = response.split('\n')
        explanation_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if not in_code and line.strip():
                explanation_lines.append(line)

        return '\n'.join(explanation_lines) if explanation_lines else "Otimização aplicada."

    def _extract_improvements(self, response: str) -> List[str]:
        """Extrair lista de melhorias."""
        improvements = []

        # Procurar por linhas que começam com -
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                improvements.append(line[2:])
            elif line.startswith(('1.', '2.', '3.', '4.', '5.')):
                # Lista numerada
                match = re.match(r'\d+\.\s*(.*)', line)
                if match:
                    improvements.append(match.group(1))

        return improvements

    def _validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Validar sintaxe do código Python."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Erro de sintaxe: {e}"
