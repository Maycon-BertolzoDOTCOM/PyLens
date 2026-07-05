"""
Testes para o módulo LLM do PyLens.
"""

import pytest
from unittest.mock import Mock, patch
from app.llm.router import LLMRouter, LLMResponse, LLMUnavailableError, OllamaBackend, OpenAIBackend
from app.llm.optimizer import LLMOptimizer, OptimizationResult
from app.llm.verifier import OptimizationVerifier, VerificationResult


class TestLLMRouter:
    """Testes para o roteador LLM."""

    def test_create_router_with_no_backends(self):
        router = LLMRouter(backends=[])
        assert router.available_backends == []

    def test_generate_raises_when_no_backends(self):
        router = LLMRouter(backends=[])
        with pytest.raises(LLMUnavailableError):
            router.generate("test prompt")


class TestOllamaBackend:
    """Testes para o backend Ollama."""

    def test_backend_name(self):
        backend = OllamaBackend()
        assert backend.name == "ollama"

    @patch('httpx.get')
    def test_is_available_when_running(self, mock_get):
        mock_get.return_value = Mock(status_code=200)
        backend = OllamaBackend()
        assert backend.is_available() is True

    @patch('httpx.get')
    def test_is_available_when_not_running(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        backend = OllamaBackend()
        assert backend.is_available() is False


class TestOpenAIBackend:
    """Testes para o backend OpenAI."""

    def test_backend_name(self):
        backend = OpenAIBackend(api_key="test-key")
        assert backend.name == "openai"

    def test_is_available_with_key(self):
        backend = OpenAIBackend(api_key="test-key")
        assert backend.is_available() is True

    def test_is_available_without_key(self):
        backend = OpenAIBackend(api_key="")
        assert backend.is_available() is False


class TestLLMOptimizer:
    """Testes para o otimizador LLM."""

    def test_extract_code_block(self):
        optimizer = LLMOptimizer(Mock())
        response = """Aqui está o código otimizado:

```python
def optimized():
    return 42
```

Melhorias:
- Simplificação
"""
        code = optimizer._extract_code(response)
        assert "def optimized():" in code

    def test_extract_explanation(self):
        optimizer = LLMOptimizer(Mock())
        response = """Código otimizado.

Explicação das melhorias:
- Melhoria 1
- Melhoria 2
"""
        explanation = optimizer._extract_explanation(response)
        assert "Melhoria 1" in explanation or "Código otimizado" in explanation

    def test_extract_improvements(self):
        optimizer = LLMOptimizer(Mock())
        response = """Melhorias:
- Primeira melhoria
- Segunda melhoria
- Terceira melhoria
"""
        improvements = optimizer._extract_improvements(response)
        assert len(improvements) == 3

    def test_validate_syntax_valid(self):
        optimizer = LLMOptimizer(Mock())
        is_valid, error = optimizer._validate_syntax("x = 1")
        assert is_valid is True
        assert error is None

    def test_validate_syntax_invalid(self):
        optimizer = LLMOptimizer(Mock())
        is_valid, error = optimizer._validate_syntax("def invalid(:")
        assert is_valid is False
        assert error is not None


class TestOptimizationVerifier:
    """Testes para o verificador de otimização."""

    def test_validate_syntax_valid(self):
        verifier = OptimizationVerifier()
        is_valid, error = verifier._validate_syntax("x = 1")
        assert is_valid is True
        assert error is None

    def test_validate_syntax_invalid(self):
        verifier = OptimizationVerifier()
        is_valid, error = verifier._validate_syntax("def invalid(:")
        assert is_valid is False
        assert "sintaxe" in error.lower() or "syntax" in error.lower()

    def test_verify_simple_code(self):
        verifier = OptimizationVerifier(timeout=5)
        code = "x = 1\ny = 2\nz = x + y"
        result = verifier.verify(code, check_memory=False)
        assert result.is_valid is True
