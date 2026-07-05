# PyLens — Arquitetura e Capacidades do Sistema

> Documento técnico para desenvolvedores. Descreve o sistema **como ele existe hoje**, baseado no código-fonte real.

---

## 1. Visão Geral

PyLens é uma plataforma de análise e otimização inteligente de código Python. Combina análise estática (AST + métricas arquiteturais), análise via AGS (Architectural Graph System) e otimização com LLM para fornecer insights profundos e sugestões acionáveis.

O fluxo principal é:

```
Código Python
     │
     ▼
┌─────────────────────────────────────────────────┐
│              PYLENS PIPELINE                    │
│                                                 │
│  ┌──────────────┐    ┌──────────────┐           │
│  │   Analyzer   │───▶│   Decide     │           │
│  │  (AGS +      │    │   Engine     │           │
│  │   AST)       │    │              │           │
│  └──────────────┘    └──────┬───────┘           │
│                             │                   │
│              ┌──────────────┼──────────────┐    │
│              ▼              ▼              ▼    │
│        ┌──────────┐  ┌──────────┐  ┌──────────┐│
│        │LLM Optim │  │ Crystal  │  │  Manual  ││
│        │          │  │Transpiler│  │ Refactor ││
│        └────┬─────┘  └────┬─────┘  └────┬─────┘│
│             └──────────────┼──────────────┘     │
│                            ▼                    │
│                   ┌──────────────┐              │
│                   │   Verifier   │              │
│                   └──────┬───────┘              │
│                          ▼                      │
│                   ┌──────────────┐              │
│                   │    Report    │              │
│                   └──────────────┘              │
└─────────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Runtime | Python 3.9+ |
| Framework web | FastAPI 0.104 |
| ORM / banco | SQLModel + SQLite/PostgreSQL |
| Autenticação | JWT via `python-jose` + bcrypt via `passlib` |
| Análise estática | Módulo `ast` nativo do Python |
| Análise arquitetural | AGS - Architectural Graph System (NetworkX) |
| LLM | Ollama (local) / OpenAI API |
| HTTP async | httpx |
| Testes | pytest + Hypothesis (property-based testing) |

---

## 3. Arquitetura de Módulos

### `app/analysis/` — Módulo de Análise Unificado

#### `analysis/static_analysis.py` — `StaticAnalyzer`

Análise estática de código Python via AST. Responsável por quantificar o quanto um trecho de código é CPU-bound.

**Método principal:** `analyze(code: str) -> Tuple[int, List[str], int]`
- Retorna `(score, imports_detectados, contagem_de_loops)`

**Como o score é calculado:**
- Loops contam com peso por aninhamento: um `_LoopCounter` (`NodeVisitor`) incrementa `depth` ao entrar em `For`/`While` e soma `depth` ao contador — loops aninhados valem mais.
- Score de loops: `min(loops * 3, 40)` — máximo 40 pontos.
- Score de operações matemáticas (`BinOp` com `+/-/*/÷` e chamadas a `sum/min/max/abs/pow`): `min(math_ops, 30)` se `math_ops > 10` — máximo 30 pontos.
- Score de chamadas de função: `min(function_calls, 20)` se `function_calls > 5` — máximo 20 pontos.
- Score final: `min(total, 100)`.

**Análise detalhada:** `analyze_detailed(code: str) -> AnalysisResult`
- Retorna objeto com todas as métricas arquiteturais (cyclic_ratio, dependency_density)
- Classificação de regime arquitetural
- Potencial de otimização

#### `analysis/architectural.py` — `ArchitecturalAnalyzer`

Análise arquitetural usando AGS. Fornece insights sobre a estrutura do código Python.

**Método principal:** `analyze(code: str) -> ArchitecturalResult`

**Retorna:**
- `code_structure`: Classes, funções, imports, loops, comprehensions, decorators, etc.
- `regime`: Classificação arquitetural (MODULAR, ENTANGLED, COUPLED, etc.)
- `cycle_density`: Densidade de ciclos (0.0 - 1.0)
- `dependency_density`: Densidade de dependências (0.0 - 1.0)
- `optimization_feasibility`: HIGH, MEDIUM, LOW
- `warnings`: Avisos sobre problemas potenciais
- `suggestions`: Sugestões de melhoria

#### `analysis/quality.py` — `QualityAnalyzer`

Métricas arquiteturais para avaliação de qualidade do código.

**Métricas calculadas:**
- **coupling_index**: Concentração do acoplamento entre pacotes (0.0 = uniforme, 1.0 = concentrado)
- **cohesion_index**: Proporção de edges cross-module (0.0 = todos intra, 1.0 = todos inter)
- **cyclic_ratio**: Fração de edges que participam de ciclos
- **leakage_ratio**: Fração de imports que violam fronteiras de domínio
- **quality_score**: Score composto ponderado (0-100)

#### `analysis/report.py` — `ReportGenerator`

Gera relatórios inteligentes consolidando todas as análises.

**Método principal:** `generate(code: str) -> PyLensReport`

**Conteúdo do relatório:**
- Score geral e grade (A-F)
- Potencial de otimização
- Descobertas principais (key_findings)
- Sugestões de otimização (OptimizationSuggestion)
- Quick wins
- Métricas consolidadas

---

### `app/llm/` — Módulo LLM

#### `llm/router.py` — `LLMRouter`

Roteador multi-backend com fallback.

**Backends suportados:**
- **OllamaBackend**: Backend local via Ollama
- **OpenAIBackend**: Backend OpenAI (ou compatível)

**Método principal:** `generate(prompt: str, system: Optional[str] = None) -> LLMResponse`

**Comportamento:**
- Tenta backends em ordem de prioridade
- Fallback automático se um backend falhar
- Raises `LLMUnavailableError` se nenhum backend estiver disponível

#### `llm/optimizer.py` — `LLMOptimizer`

Otimizador de código Python usando LLM.

**Método principal:** `optimize(code: str, context: Optional[str] = None, optimization_focus: str = "performance") -> OptimizationResult`

**Retorna:**
- `original_code`: Código original
- `optimized_code`: Código otimizado
- `explanation`: Explicação das melhorias
- `improvements`: Lista de melhorias específicas
- `is_valid`: Se o código é válido
- `validation_error`: Erro de validação (se houver)

**Geração de variantes:** `generate_variants(code: str, num_variants: int = 3) -> List[OptimizationResult]`

#### `llm/verifier.py` — `OptimizationVerifier`

Verificação de código otimizado em sandbox seguro.

**Método principal:** `verify(code: str, tests: Optional[str] = None, check_memory: bool = True) -> VerificationResult`

**Verificações:**
- Validação de sintaxe AST
- Execução de testes pytest
- Verificação de uso de memória
- Medição de tempo de execução

---

### `app/targets/` — Plugins de Saída (Opcionais)

#### `targets/crystal/transpiler.py` — `Transpiler`

Plugin de transpilação Python → Crystal. **Opcional** — não é necessário para o funcionamento principal do PyLens.

**Construções suportadas:**
- Loops (for, while)
- Funções e métodos
- Classes
- List comprehensions
- Decorators
- f-strings
- Try/except
- With statements
- Lambda
- Type hints
- Async/await
- Yield

---

### `app/decision_engine.py` — `DecisionEngine`

Motor de decisão puro, sem dependências FastAPI.

**Método principal:** `decide(code: str, user_preference: Optional[str] = None) -> DecisionPlan`

**Matriz de decisão:**

| Regime | Loops ≥ 3 | Cycles ≥ 0.2 | Decisão |
|--------|-----------|--------------|---------|
| MODULAR | sim | não | CRYSTAL |
| MODULAR | não | não | SKIP |
| ENTANGLED | sim | não | LLM_OPTIMIZE |
| ENTANGLED | sim | sim | MANUAL_REFACTOR |
| PATHOLOGICAL | * | * | MANUAL_REFACTOR |
| PERFECT | * | * | SKIP |
| COUPLED | sim | não | LLM_OPTIMIZE ou CRYSTAL |
| LEAKY | * | * | LLM_OPTIMIZE |
| MIXED | * | * | LLM_OPTIMIZE |

**Decisões possíveis:**
- `LLM_OPTIMIZE`: Usar LLM para gerar variantes otimizadas
- `CRYSTAL`: Transpilar para Crystal
- `BOTH`: Aplicar LLM + Crystal
- `MANUAL_REFACTOR`: Sugerir refatoração manual
- `SKIP`: Código já está bom

---

## 4. Endpoints da API

### `POST /analyze`

Análise completa do código Python.

**Request:**
```json
{
  "code": "def add(x, y): return x + y",
  "context": "optional context"
}
```

**Response:**
```json
{
  "static_analysis": {
    "score": 0,
    "optimization_potential": "LOW",
    "loops": 0,
    "imports": [],
    "cycle_density": 0.0,
    "dependency_density": 0.0
  },
  "architectural": {
    "regime": "MODULAR_SMALL",
    "feasibility": "HIGH",
    "cycle_density": 0.0,
    "dependency_density": 0.0,
    "warnings": [],
    "suggestions": []
  },
  "code_structure": {
    "classes": 0,
    "functions": 1,
    "loops": 0,
    "comprehensions": 0,
    "decorators": 0,
    "async_constructs": 0,
    "try_blocks": 0,
    "lambdas": 0
  }
}
```

### `POST /decide`

Pipeline inteligente "observar → classificar → agir".

**Request:**
```json
{
  "code": "for i in range(100): for j in range(100): pass",
  "user_preference": "prefer_crystal"
}
```

**Response:**
```json
{
  "decision": "CRYSTAL",
  "confidence": 0.8,
  "risk": "low",
  "reasoning": "Regime MODULAR_SMALL com 6 loops...",
  "plan": {
    "steps": [
      {"action": "analyze", "params": {...}, "status": "done"},
      {"action": "transpile_to_crystal", "params": {...}, "status": "pending"},
      {"action": "benchmark", "params": {...}, "status": "pending"}
    ],
    "alternative": "LLM_OPTIMIZE"
  },
  "metrics_summary": {
    "score": 26,
    "regime": "MODULAR_SMALL",
    "cycle_density": 0.0,
    "loops": 6,
    "feasibility": "HIGH"
  }
}
```

### `POST /optimize`

Otimizar código Python usando LLM.

**Request:**
```json
{
  "code": "for i in range(1000): result.append(i * 2)",
  "context": "List comprehension would be better",
  "optimization_focus": "performance",
  "num_variants": 3,
  "run_tests": true,
  "tests": "def test_optimized(): assert optimized_code() == expected()"
}
```

### `POST /report`

Gerar relatório inteligente consolidado.

**Request:**
```json
{
  "code": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
}
```

---

## 5. Modelos de Dados

### `AnalysisResult`

```python
@dataclass
class AnalysisResult:
    score: int
    imports: List[str]
    loops_count: int
    cycle_density: float
    dependency_density: float
    regime: Optional[RegimeName]
    regime_classification: Optional[RegimeClassification]
    observation: Optional[ObservationSnapshot]
    optimization_potential: str  # "HIGH", "MEDIUM", "LOW"
    details: Dict[str, Any]
```

### `ArchitecturalResult`

```python
@dataclass
class ArchitecturalResult:
    code_structure: CodeStructure
    regime: RegimeName
    regime_classification: RegimeClassification
    observation: ObservationSnapshot
    cycle_density: float
    dependency_density: float
    optimization_feasibility: str
    warnings: List[str]
    suggestions: List[str]
```

### `DecisionPlan`

```python
@dataclass
class DecisionPlan:
    decision: Decision
    confidence: float
    risk: Risk
    reasoning: str
    steps: List[ActionStep]
    alternative: Optional[Decision]
    metrics_summary: Dict[str, Any]
```

---

## 6. Fluxo de Decisão

```
Código Python
     │
     ▼
┌─────────────────────────────────────┐
│         StaticAnalyzer              │
│  - Score (0-100)                    │
│  - Loops, imports, math ops         │
│  - Métricas arquiteturais            │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│       ArchitecturalAnalyzer         │
│  - Regime (MODULAR, ENTANGLED, etc) │
│  - Cycle density                    │
│  - Dependency density               │
│  - Warnings e suggestions           │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         DecisionEngine              │
│                                     │
│  if regime == PATHOLOGICAL:         │
│      return MANUAL_REFACTOR         │
│                                     │
│  if regime == PERFECT:              │
│      return SKIP                    │
│                                     │
│  if regime == MODULAR and loops:    │
│      return CRYSTAL                 │
│                                     │
│  if regime == ENTANGLED and cycles: │
│      return MANUAL_REFACTOR         │
│                                     │
│  default:                           │
│      return LLM_OPTIMIZE            │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         Ação Selecionada            │
│                                     │
│  LLM_OPTIMIZE → LLMOptimizer       │
│  CRYSTAL → Transpiler              │
│  BOTH → LLM + Crystal              │
│  MANUAL_REFACTOR → Sugestões       │
│  SKIP → Log                        │
└─────────────────────────────────────┘
```

---

## 7. Segurança

- **Sandbox para execução**: Código executado em ambiente isolado
- **Limites de tempo**: Timeout de 10 segundos para execução
- **Limites de memória**: Monitoramento de pico de memória
- **Validação de entrada**: AST parsing antes de executar
- **Autenticação JWT**: Endpoints protegidos

---

## 8. Testes

| Suite | Testes | O que valida |
|---|---|---|
| `test_analysis.py` | 9 | StaticAnalyzer, ArchitecturalAnalyzer, ReportGenerator |
| `test_llm.py` | 16 | LLMRouter, LLMOptimizer, OptimizationVerifier |
| `test_api.py` | 5 | Endpoints da API |
| `test_decision_engine.py` | 11 | DecisionEngine, matriz de decisão |

**Total: 41 testes passando**
