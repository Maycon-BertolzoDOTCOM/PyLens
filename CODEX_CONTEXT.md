# PyLens — Contexto do Projeto

> Este documento descreve o PyLens para desenvolvedores e ferramentas de IA que trabalham no código.

---

## Propósito

PyLens é uma plataforma de **análise e otimização inteligente de código Python**. Não é apenas um lintador ou transpilador — é um sistema que **observa, classifica e age** sobre código Python para melhorar sua performance e qualidade.

**Filosofia:** "Observação, não adivinhação. Dados, não opiniões."

---

## Arquitetura

```
pylens/
├── app/
│   ├── main.py                    # API FastAPI (endpoints)
│   ├── auth.py                    # Autenticação JWT
│   ├── db.py                      # Database (SQLite/PostgreSQL)
│   ├── models.py                  # Modelos de dados
│   ├── exceptions.py              # Exceções customizadas
│   ├── decision_engine.py         # Motor de decisão puro
│   ├── analysis/                  # Módulo de análise
│   │   ├── static_analysis.py     # Análise AST + métricas
│   │   ├── architectural.py       # Análise arquitetural (AGS)
│   │   ├── quality.py             # Métricas arquiteturais
│   │   └── report.py              # Relatório inteligente
│   ├── llm/                       # Módulo LLM
│   │   ├── router.py              # Multi-backend (Ollama, OpenAI)
│   │   ├── optimizer.py           # Otimizador de código
│   │   └── verifier.py            # Verificação de código
│   └── targets/                   # Plugins de saída
│       └── crystal/               # Transpilador Python → Crystal
├── tests/                         # Testes
├── ags/                           # AGS (Architectural Graph System)
├── docs/                          # Documentação
└── web/                           # Frontend HTML
```

---

## Dependências Principais

| Dependência | Uso |
|---|---|
| `fastapi` | Framework web |
| `sqlmodel` | ORM |
| `networkx` | Análise de grafos (AGS) |
| `pydantic` | Validação de dados |
| `httpx` | HTTP client assíncrono |
| `python-jose` | JWT |
| `bcrypt` | Hash de senhas |

---

## Regras de Código

1. **Observação primeiro**: Sempre analisar antes de otimizar
2. **Dados, não opiniões**: Usar métricas objetivas (cyclic_ratio, coupling_index, regime)
3. **Decisão transparente**: Sempre explicar por que uma decisão foi tomada
4. **Segurança**: Nunca executar código sem validação
5. **Modularidade**: Manter módulos independentes e testáveis

---

## Convenções

- **Python**: Seguir PEP 8, usar type hints
- **Testes**: pytest, cobertura mínima de 80%
- **Commits**: Mensagens claras em português ou inglês
- **PRs**: Descrever mudanças e impacto

---

## Comandos Úteis

```bash
# Rodar testes
pytest

# Rodar com cobertura
pytest --cov=app

# Lint
ruff check .

# Formatação
ruff format .

# Rodar servidor de desenvolvimento
uvicorn app.main:app --reload
```

---

## Endpoints Principais

| Método | Rota | Descrição |
|---|---|---|
| POST | `/analyze` | Análise completa do código |
| POST | `/decide` | Pipeline inteligente de decisão |
| POST | `/optimize` | Otimização com LLM |
| POST | `/report` | Relatório inteligente consolidado |
| GET | `/health` | Verificação de saúde |

---

## Fluxo de Dados

```
Código Python
     │
     ▼
Analyzer (AGS + AST)
     │
     ▼
Decision Engine
     │
     ├──▶ LLM_OPTIMIZE ──▶ LLMOptimizer ──▶ Verifier
     │
     ├──▶ CRYSTAL ──▶ Transpiler ──▶ Benchmark
     │
     ├──▶ MANUAL_REFACTOR ──▶ Sugestões
     │
     └──▶ SKIP ──▶ Log
```

---

## Matriz de Decisão

| Regime | Loops ≥ 3 | Cycles ≥ 0.2 | Decisão |
|--------|-----------|--------------|---------|
| MODULAR | sim | não | CRYSTAL |
| MODULAR | não | não | SKIP |
| ENTANGLED | sim | não | LLM_OPTIMIZE |
| ENTANGLED | sim | sim | MANUAL_REFACTOR |
| PATHOLOGICAL | * | * | MANUAL_REFACTOR |
| PERFECT | * | * | SKIP |
| COUPLED | sim | não | LLM ou CRYSTAL |
| LEAKY | * | * | LLM_OPTIMIZE |
| MIXED | * | * | LLM_OPTIMIZE |

---

## Métricas Arquiteturais

- **coupling_index**: Concentração do acoplamento entre pacotes
- **cohesion_index**: Proporção de edges cross-module (intra/inter módulo)
- **cyclic_ratio**: Fração de arestas em ciclos
- **leakage_ratio**: Fração de imports que violam fronteiras de domínio
- **quality_score**: Score composto ponderado (0-100)

---

## Regimes Arquiteturais

| Regime | Descrição |
|---|---|
| PERFECT | Sem acoplamento, sem vazamento |
| MODULAR_SMALL | Módulos limpos, poucos arquivos |
| MODULAR_LARGE | Módulos limpos, muitos arquivos |
| COUPLED | Acoplamento controlado |
| ENTANGLED_SMALL | Poucos arquivos, alto acoplamento |
| ENTANGLED_LARGE | Muitos arquivos, alto acoplamento |
| LEAKY | Vazamento de fronteiras |
| COLLAPSED | Tudo conectado |
| MIXED | Sinais mistos |
| PATHOLOGICAL | Anti-padrões |
| ACYCLIC_DOMINANT | Hierarquia pura, sem ciclos |

---

## Contribuição

1. Fork o repositório
2. Crie uma branch para sua feature
3. Escreva testes para suas mudanças
4. Execute `pytest` e `ruff check .`
5. Abra um PR com descrição clara

---

## Licença

MIT
