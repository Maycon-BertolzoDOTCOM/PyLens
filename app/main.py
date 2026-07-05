"""
PyLens API — Plataforma de análise e otimização inteligente de código Python.

Endpoints principais:
- POST /analyze — Análise completa (AGS + AST + sugestões)
- POST /decide — Pipeline inteligente "observar → classificar → agir"
- POST /optimize — Otimização com LLM + verificação
- POST /report — Relatório inteligente consolidado
"""

import os

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import text
from sqlmodel import Session

from . import db
from . import models
from . import auth
from .analysis.static_analysis import StaticAnalyzer
from .analysis.architectural import ArchitecturalAnalyzer
from .analysis.quality import QualityAnalyzer
from .analysis.report import ReportGenerator
from .llm.router import LLMRouter, LLMUnavailableError
from .llm.optimizer import LLMOptimizer
from .llm.verifier import OptimizationVerifier
from .decision_engine import DecisionEngine, DecisionPlan

# Criar aplicação FastAPI
app = FastAPI(
    title="PyLens API",
    description="Plataforma de análise e otimização inteligente de código Python",
    version="1.0.0"
)

# Configurar CORS
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
if _allowed_origins_env == "*":
    if os.getenv("ENVIRONMENT") == "production":
        raise RuntimeError(
            "ALLOWED_ORIGINS cannot be '*' in production. "
            "Set ALLOWED_ORIGINS to a comma-separated list of allowed origins."
        )
    _origins = ["*"]
else:
    _origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar componentes
static_analyzer = StaticAnalyzer()
architectural_analyzer = ArchitecturalAnalyzer()
quality_analyzer = QualityAnalyzer()
report_generator = ReportGenerator()
decision_engine = DecisionEngine()
security = HTTPBearer()

# Inicializar componentes LLM
try:
    llm_router = LLMRouter.from_env()
    llm_optimizer = LLMOptimizer(llm_router)
except RuntimeError:
    llm_router = None
    llm_optimizer = None

verifier = OptimizationVerifier()


# Modelos de request/response
class AnalyzeRequest(BaseModel):
    code: str
    context: Optional[str] = None


class OptimizeRequest(BaseModel):
    code: str
    context: Optional[str] = None
    optimization_focus: str = "performance"
    num_variants: int = 1
    run_tests: bool = False
    tests: Optional[str] = None
    auto_route: bool = False  # Se True, usa decision engine para escolher rota
    user_preference: Optional[str] = None  # "prefer_crystal", "prefer_llm", None


class ReportRequest(BaseModel):
    code: str


class DecideRequest(BaseModel):
    code: str
    user_preference: Optional[str] = None  # "prefer_crystal", "prefer_llm", None


# Endpoints
@app.get("/")
async def root():
    """Informações básicas da API."""
    return {
        "name": "PyLens API",
        "version": "1.0.0",
        "description": "Plataforma de análise e otimização inteligente de código Python",
        "endpoints": {
            "/analyze": "Análise completa do código",
            "/decide": "Pipeline inteligente de decisão",
            "/optimize": "Otimização com LLM",
            "/report": "Relatório inteligente consolidado",
            "/health": "Verificação de saúde",
        }
    }


@app.get("/health")
async def health_check():
    """Verificação de saúde do sistema."""
    with Session(db.engine) as session:
        try:
            session.execute(text("SELECT 1"))
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

    llm_status = "available" if llm_router and llm_router.available_backends else "unavailable"

    return {
        "status": "healthy",
        "database": db_status,
        "llm": llm_status,
        "available_llm_backends": llm_router.available_backends if llm_router else [],
    }


@app.post("/analyze")
async def analyze_code(request: AnalyzeRequest):
    """
    Análise completa do código Python.

    Retorna:
    - Score de otimização (0-100)
    - Métricas arquiteturais (cyclic_ratio, coupling_index, cohesion_index)
    - Regime arquitetural (11 regimes quantitativos)
    - Sugestões de otimização
    """
    try:
        # Análise estática
        static_result = static_analyzer.analyze_detailed(request.code)

        # Análise arquitetural
        arch_result = architectural_analyzer.analyze(request.code)

        return {
            "static_analysis": {
                "score": static_result.score,
                "optimization_potential": static_result.optimization_potential,
                "loops": static_result.loops_count,
                "imports": static_result.imports,
                "cycle_density": static_result.cycle_density,
                "dependency_density": static_result.dependency_density,
            },
            "architectural": {
                "regime": arch_result.regime.value,
                "feasibility": arch_result.optimization_feasibility,
                "cycle_density": arch_result.cycle_density,
                "dependency_density": arch_result.dependency_density,
                "warnings": arch_result.warnings,
                "suggestions": arch_result.suggestions,
            },
            "code_structure": {
                "classes": len(arch_result.code_structure.classes),
                "functions": len(arch_result.code_structure.functions),
                "loops": arch_result.code_structure.loops,
                "comprehensions": arch_result.code_structure.comprehensions,
                "decorators": arch_result.code_structure.decorators,
                "async_constructs": arch_result.code_structure.async_constructs,
                "try_blocks": arch_result.code_structure.try_blocks,
                "lambdas": arch_result.code_structure.lambdas,
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decide")
async def decide_action(request: DecideRequest):
    """
    Pipeline inteligente "observar → classificar → agir".

    Retorna:
    - Decisão (LLM_OPTIMIZE, CRYSTAL, BOTH, MANUAL_REFACTOR, SKIP)
    - Confiança (0.0 - 1.0)
    - Risco (low, medium, high)
    - Reasoning (explicação da decisão)
    - Plano de ação (passos a executar)
    - Alternativa (segunda melhor opção)
    - Métricas resumidas
    """
    try:
        plan = decision_engine.decide(
            python_code=request.code,
            user_preference=request.user_preference,
        )
        return plan.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/optimize")
async def optimize_code(request: OptimizeRequest):
    """
    Otimizar código Python usando LLM.

    Retorna:
    - Código otimizado
    - Explicação das melhorias
    - Resultado da verificação (se tests fornecidos)
    - Decisão e reasoning (se auto_route=True)
    """
    try:
        # Auto-route: usar decision engine para escolher rota
        if request.auto_route:
            plan = decision_engine.decide(
                python_code=request.code,
                user_preference=request.user_preference,
            )

            # Se decisão for SKIP ou MANUAL_REFACTOR, retornar plano
            if plan.decision.value in ("SKIP", "MANUAL_REFACTOR"):
                return {
                    "auto_routed": True,
                    "decision": plan.to_dict(),
                    "variants": [],
                    "message": f"Decisão: {plan.decision.value}. {plan.reasoning}",
                }

            # Se decisão for CRYSTAL, tentar transpilar
            if plan.decision.value == "CRYSTAL":
                try:
                    from .targets.crystal.transpiler import Transpiler
                    crystal_transpiler = Transpiler()
                    crystal_code = crystal_transpiler.transpile(request.code)
                    return {
                        "auto_routed": True,
                        "decision": plan.to_dict(),
                        "variants": [{
                            "optimized_code": crystal_code,
                            "explanation": "Código transpilado para Crystal",
                            "improvements": ["Código compilado de alta performance"],
                            "backend_used": "crystal",
                            "model_used": "transpiler",
                            "is_valid": True,
                            "validation_error": None,
                        }],
                        "verification": None,
                    }
                except Exception as e:
                    # Fallback para LLM se Crystal falhar
                    pass

            # Para LLM_OPTIMIZE ou BOTH, continuar com LLM
            if not llm_optimizer:
                raise HTTPException(
                    status_code=503,
                    detail="LLM não disponível. Configure OLLAMA_BASE_URL ou OPENAI_API_KEY."
                )

            results = llm_optimizer.generate_variants(
                request.code,
                num_variants=request.num_variants,
                optimization_focus=request.optimization_focus,
            )

            verification_result = None
            if request.run_tests and request.tests:
                best_result = max(results, key=lambda r: len(r.improvements))
                verification_result = verifier.verify(
                    best_result.optimized_code,
                    tests=request.tests,
                )

            return {
                "auto_routed": True,
                "decision": plan.to_dict(),
                "variants": [
                    {
                        "optimized_code": r.optimized_code,
                        "explanation": r.explanation,
                        "improvements": r.improvements,
                        "backend_used": r.backend_used,
                        "model_used": r.model_used,
                        "is_valid": r.is_valid,
                        "validation_error": r.validation_error,
                    }
                    for r in results
                ],
                "verification": {
                    "is_valid": verification_result.is_valid if verification_result else None,
                    "tests_passed": verification_result.tests_passed if verification_result else None,
                    "memory_usage": verification_result.memory_usage if verification_result else None,
                    "execution_time": verification_result.execution_time if verification_result else None,
                    "errors": verification_result.errors if verification_result else [],
                } if verification_result else None,
            }

        # Modo manual (comportamento original)
        if not llm_optimizer:
            raise HTTPException(
                status_code=503,
                detail="LLM não disponível. Configure OLLAMA_BASE_URL ou OPENAI_API_KEY."
            )

        # Otimizar código
        if request.num_variants > 1:
            results = llm_optimizer.generate_variants(
                request.code,
                num_variants=request.num_variants,
                optimization_focus=request.optimization_focus,
            )
        else:
            result = llm_optimizer.optimize(
                request.code,
                context=request.context,
                optimization_focus=request.optimization_focus,
            )
            results = [result]

        # Verificar se executou testes
        verification_result = None
        if request.run_tests and request.tests:
            best_result = max(results, key=lambda r: len(r.improvements))
            verification_result = verifier.verify(
                best_result.optimized_code,
                tests=request.tests,
            )

        return {
            "auto_routed": False,
            "variants": [
                {
                    "optimized_code": r.optimized_code,
                    "explanation": r.explanation,
                    "improvements": r.improvements,
                    "backend_used": r.backend_used,
                    "model_used": r.model_used,
                    "is_valid": r.is_valid,
                    "validation_error": r.validation_error,
                }
                for r in results
            ],
            "verification": {
                "is_valid": verification_result.is_valid if verification_result else None,
                "tests_passed": verification_result.tests_passed if verification_result else None,
                "memory_usage": verification_result.memory_usage if verification_result else None,
                "execution_time": verification_result.execution_time if verification_result else None,
                "errors": verification_result.errors if verification_result else [],
            } if verification_result else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report")
async def generate_report(request: ReportRequest):
    """
    Gerar relatório inteligente consolidado.

    Combina análise estática, arquitetural e LLM em um relatório coeso.
    """
    try:
        report = report_generator.generate(request.code)
        return report.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoints de autenticação (mantidos do Crystalize)
@app.post("/signup")
async def signup(user: models.UserCreate):
    """Criar nova conta."""
    with Session(db.engine) as session:
        # Verificar se usuário já existe
        existing = session.query(models.User).filter(models.User.email == user.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )

        # Criar usuário
        hashed_password = auth.get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            name=user.name,
            hashed_password=hashed_password
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        # Gerar token
        access_token = auth.create_access_token(data={"sub": db_user.email})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "name": db_user.name,
            }
        }


@app.post("/login")
async def login(user: models.UserLogin):
    """Autenticar usuário."""
    with Session(db.engine) as session:
        db_user = session.query(models.User).filter(models.User.email == user.email).first()
        if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = auth.create_access_token(data={"sub": db_user.email})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "name": db_user.name,
            }
        }


@app.get("/profile")
async def get_profile(current_user: models.User = Depends(auth.get_current_user)):
    """Obter perfil do usuário autenticado."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
    }
