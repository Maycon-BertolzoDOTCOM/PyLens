# PyLens

[![CI](https://github.com/Maycon-BertolzoDOTCOM/PyLens/actions/workflows/ci.yml/badge.svg)](https://github.com/Maycon-BertolzoDOTCOM/PyLens/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Plataforma de análise e otimização inteligente de código Python.

## Visão

PyLens combina análise estática (AST), análise arquitetural via AGS (Architectural Graph System) e otimização com LLM para fornecer insights profundos sobre código Python e sugestões acionáveis de melhoria.

**Filosofia:** "Observação, não adivinhação. Dados, não opiniões."

## Funcionalidades

- **Análise Estática** — Score de otimização (0-100), métricas de loops, imports, operações matemáticas
- **Análise Arquitetural** — Classificação de regime (MODULAR, ENTANGLED, COUPLED, etc.), cyclic_ratio, dependency_density
- **Métricas Arquiteturais** — coupling_index, cohesion_index, leakage_ratio
- **Otimização com LLM** — Geração de variantes otimizadas usando múltiplos backends (Ollama, OpenAI)
- **Verificação** — Execução de testes pytest e verificação de memória
- **Relatório Inteligente** — Consolida todas as análises em um relatório acionável

## Arquitetura

```
Python Code → Analysis (AGS + AST) → LLM Optimizer → Verification
         ↘                                              ↙
     Architectural Report                    Multi-target Output
         + insights                              (or suggestions)
```

## Stack

| Camada | Tecnologia |
|---|---|
| Runtime | Python 3.9+ |
| Framework | FastAPI |
| ORM | SQLModel + SQLite/PostgreSQL |
| Análise | AST nativo + AGS (NetworkX) |
| LLM | Ollama (local) / OpenAI API |
| Testes | pytest + Hypothesis |

## Quick Start

```bash
# Instalar dependências
pip install -e .

# Configurar variáveis de ambiente
cp .env.example .env

# Executar
uvicorn app.main:app --reload
```

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/analyze` | Análise completa do código |
| POST | `/decide` | Pipeline inteligente de decisão |
| POST | `/optimize` | Otimização com LLM (suporta auto_route) |
| POST | `/report` | Relatório inteligente consolidado |
| GET | `/health` | Verificação de saúde |
| POST | `/signup` | Criar conta |
| POST | `/login` | Autenticação |

## Exemplo de Uso

### Análise

```python
import requests

response = requests.post("http://localhost:8000/analyze", json={
    "code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

results = [fibonacci(x) for x in range(10)]
"""
})

print(response.json())
# {
#   "static_analysis": {"score": 75, "optimization_potential": "HIGH", ...},
#   "architectural": {"regime": "MODULAR_SMALL", "feasibility": "HIGH", ...},
#   "code_structure": {"classes": 0, "functions": 1, "loops": 1, ...}
# }
```

### Otimização

```python
response = requests.post("http://localhost:8000/optimize", json={
    "code": """
for i in range(1000):
    for j in range(1000):
        result = i * j
""",
    "optimization_focus": "performance",
    "num_variants": 3
})

print(response.json())
# {
#   "variants": [
#     {
#       "optimized_code": "result = [i * j for i in range(1000) for j in range(1000)]",
#       "explanation": "Substituído loop aninhado por list comprehension...",
#       "improvements": ["Melhor legibilidade", "Possível otimização interna"]
#     },
#     ...
#   ]
# }
```

## Desenvolvimento

```bash
# Rodar testes
pytest

# Formatação
ruff format .

# Lint
ruff check .
```

## Licença

MIT
