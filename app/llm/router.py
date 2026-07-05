"""
LLM Router — Roteador multi-backend para LLMs.

Suporta:
- Ollama (local)
- OpenAI API
- Qualquer endpoint compatível com OpenAI
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class LLMResponse:
    """Resposta do LLM."""
    content: str
    model: str
    backend: str
    usage: Optional[Dict[str, int]] = None


class LLMBackend(ABC):
    """Interface para backends LLM."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do backend."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Gerar resposta."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verificar se o backend está disponível."""
        pass


class OllamaBackend(LLMBackend):
    """Backend Ollama (local)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model

    @property
    def name(self) -> str:
        return "ollama"

    def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Gerar resposta via Ollama."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
            },
            timeout=60.0,
        )
        response.raise_for_status()

        data = response.json()
        return LLMResponse(
            content=data["message"]["content"],
            model=self.model,
            backend=self.name,
        )

    def is_available(self) -> bool:
        """Verificar se Ollama está rodando."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


class OpenAIBackend(LLMBackend):
    """Backend OpenAI (ou compatível)."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @property
    def name(self) -> str:
        return "openai"

    def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """Gerar resposta via OpenAI API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
            },
            timeout=60.0,
        )
        response.raise_for_status()

        data = response.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=self.model,
            backend=self.name,
            usage=data.get("usage"),
        )

    def is_available(self) -> bool:
        """Verificar se a API key é válida."""
        return bool(self.api_key)


class LLMRouter:
    """
    Roteador multi-backend com fallback.

    Tenta backends em ordem de prioridade.
    """

    def __init__(self, backends: Optional[List[LLMBackend]] = None):
        self.backends = backends or []

    @classmethod
    def from_env(cls) -> LLMRouter:
        """Criar roteador a partir de variáveis de ambiente."""
        backends = []

        # Ollama (se disponível)
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        backends.append(OllamaBackend(base_url=ollama_url, model=ollama_model))

        # OpenAI (se API key disponível)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            openai_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
            backends.append(OpenAIBackend(api_key=openai_key, base_url=openai_url, model=openai_model))

        return cls(backends=backends)

    def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        """
        Gerar resposta usando o primeiro backend disponível.

        Raises:
            LLMUnavailableError: Se nenhum backend estiver disponível.
        """
        for backend in self.backends:
            try:
                if backend.is_available():
                    return backend.generate(prompt, system)
            except Exception:
                continue

        raise LLMUnavailableError("Nenhum backend LLM disponível")

    @property
    def available_backends(self) -> List[str]:
        """Listar backends disponíveis."""
        return [b.name for b in self.backends if b.is_available()]


class LLMUnavailableError(Exception):
    """Erro quando nenhum backend LLM está disponível."""
    pass
