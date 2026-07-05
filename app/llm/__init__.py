"""
PyLens LLM — Módulo de otimização com LLM.

Módulos:
- router: Roteador multi-backend (Ollama, OpenAI, etc.)
- optimizer: Otimizador de código usando LLM
- verifier: Verificação de código otimizado
"""

from .router import LLMRouter, LLMBackend, LLMUnavailableError
from .optimizer import LLMOptimizer, OptimizationResult
from .verifier import OptimizationVerifier, VerificationResult

__all__ = [
    "LLMRouter",
    "LLMBackend",
    "LLMUnavailableError",
    "LLMOptimizer",
    "OptimizationResult",
    "OptimizationVerifier",
    "VerificationResult",
]
