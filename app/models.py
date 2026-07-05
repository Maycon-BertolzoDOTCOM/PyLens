from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional
from enum import Enum


class Decision(Enum):
    """Tipos de decisão da análise"""
    OPTIMIZE = "optimize"
    CONSIDER = "consider"
    SKIP = "skip"


class Confidence(Enum):
    """Níveis de confiança da decisão"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class User(SQLModel, table=True):
    """Modelo de usuário"""
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    requests_this_month: int = Field(default=0)


class Analysis(SQLModel, table=True):
    """Modelo de análise de código"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    code_hash: str = Field(index=True)
    original_code: str
    code_size: int
    
    # Resultados da análise
    score: int = Field(description="Score de 0-100 (quanto mais CPU-bound, maior)")
    decision: Decision
    confidence: Confidence
    reasons: str = Field(description="Lista de razões separadas por ;")
    imports_detected: str = Field(description="Imports detectados separados por ;")
    loops_count: int
    
    # Resultados do benchmark (opcionais)
    python_time: Optional[float] = Field(default=None, description="Tempo de execução Python em segundos")
    crystal_time: Optional[float] = Field(default=None, description="Tempo de execução Crystal em segundos")
    speedup: Optional[float] = Field(default=None, description="Speedup (python_time / crystal_time)")
    crystal_code: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.now)


# Models para autenticação
class UserCreate(SQLModel):
    """Modelo para criação de usuário"""
    email: str
    password: str


class UserLogin(SQLModel):
    """Modelo para login"""
    email: str
    password: str


class Token(SQLModel):
    """Modelo para token JWT"""
    access_token: str
    token_type: str


# Models para API
class AnalysisRequest(SQLModel):
    """Request para análise de código"""
    code: str


class AnalysisResponse(SQLModel):
    """Response da análise de código"""
    decision: str
    confidence: str
    score: int
    reasons: list[str]
    analysis_id: int


class BenchmarkResponse(SQLModel):
    """Response do benchmark"""
    python_time: float
    crystal_time: float
    speedup: float
    crystal_code: str
    success: bool
    error: Optional[str] = None


# Models para otimização LLM

class VerificationStatus(str, Enum):
    """Status de verificação de uma variante otimizada"""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MEMORY_REGRESSION = "memory_regression"


class Optimization(SQLModel, table=True):
    """Modelo de otimização de código via LLM"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    analysis_id: Optional[int] = Field(default=None, foreign_key="analysis.id")
    original_code: str
    best_variant_code: Optional[str] = Field(default=None)
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    test_output: Optional[str] = Field(default=None)
    memory_peak_original_mb: Optional[float] = Field(default=None)
    memory_peak_variant_mb: Optional[float] = Field(default=None)
    python_original_time: Optional[float] = Field(default=None)
    python_optimized_time: Optional[float] = Field(default=None)
    crystal_time: Optional[float] = Field(default=None)
    speedup_llm: Optional[float] = Field(default=None)
    speedup_crystal: Optional[float] = Field(default=None)
    crystal_code: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)


class OptimizeRequest(SQLModel):
    """Request para otimização de código via LLM"""
    code: str
    tests: Optional[str] = None


class OptimizeResponse(SQLModel):
    """Response da otimização de código via LLM"""
    optimization_id: int
    decision: str  # "optimized" | "skip" | "no_valid_variants"
    best_variant_code: Optional[str] = None
    verification_status: Optional[str] = None
    python_original_time: Optional[float] = None
    python_optimized_time: Optional[float] = None
    crystal_time: Optional[float] = None
    speedup_llm: Optional[float] = None
    speedup_crystal: Optional[float] = None
    crystal_code: Optional[str] = None
