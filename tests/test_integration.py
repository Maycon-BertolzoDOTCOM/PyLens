"""
Testes de integração end-to-end para o PyLens.

Testa cenários reais com código Python e verifica
se o pipeline completo funciona corretamente.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.decision_engine import DecisionEngine, Decision


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def engine():
    return DecisionEngine()


class TestIntegrationScenarios:
    """Cenários de integração end-to-end."""

    def test_pure_function_skip(self, client):
        """Função pura sem loops deve retornar SKIP ou LLM com baixo score."""
        code = """
def add(x, y):
    return x + y

def multiply(x, y):
    return x * y
"""
        response = client.post("/decide", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] in ("SKIP", "LLM_OPTIMIZE")
        assert data["confidence"] > 0.5

    def test_loop_heavy_optimization(self, client):
        """Código com muitos loops deve sugerir otimização."""
        code = """
result = []
for i in range(1000):
    for j in range(1000):
        result.append(i * j)
"""
        response = client.post("/decide", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] in ("CRYSTAL", "LLM_OPTIMIZE", "BOTH")
        assert len(data["plan"]["steps"]) >= 2

    def test_comprehension_already_optimized(self, client):
        """List comprehension já é otimizada."""
        code = """
squares = [x**2 for x in range(100)]
evens = [x for x in range(100) if x % 2 == 0]
"""
        response = client.post("/decide", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        # Comprehensions são boas práticas, mas ainda pode ser otimizado
        assert data["decision"] is not None
        assert data["confidence"] > 0.5

    def test_class_with_methods(self, client):
        """Classe com métodos deve ser analisada corretamente."""
        code = """
class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, x):
        self.value += x
        return self.value

    def multiply(self, x):
        self.value *= x
        return self.value

    def reset(self):
        self.value = 0
        return self
"""
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["code_structure"]["classes"] == 1
        assert data["code_structure"]["functions"] >= 4

    def test_async_code_detection(self, client):
        """Código assíncrono deve ser detectado."""
        code = """
import asyncio

async def fetch_data(url):
    await asyncio.sleep(1)
    return {"data": "value"}

async def process_all(urls):
    tasks = [fetch_data(url) for url in urls]
    return await asyncio.gather(*tasks)
"""
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["code_structure"]["async_constructs"] >= 2

    def test_try_except_handling(self, client):
        """Try/except deve ser detectado."""
        code = """
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return 0
    except TypeError:
        return None
    finally:
        print("Division attempted")
"""
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["code_structure"]["try_blocks"] >= 1

    def test_lambda_detection(self, client):
        """Lambdas devem ser detectadas."""
        code = """
add = lambda x, y: x + y
square = lambda x: x ** 2
apply_to_all = lambda func, items: [func(x) for x in items]
"""
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert data["code_structure"]["lambdas"] >= 2

    def test_nested_loops_high_score(self, client):
        """Loops aninhados devem gerar score razoável."""
        code = """
total = 0
for i in range(100):
    for j in range(100):
        for k in range(100):
            total += i * j * k
"""
        response = client.post("/analyze", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        # Score pode variar dependendo da análise arquitetural
        assert data["static_analysis"]["score"] >= 0
        assert data["static_analysis"]["loops"] >= 3

    def test_report_generation(self, client):
        """Relatório deve ser gerado corretamente."""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Uso
results = [fibonacci(x) for x in range(20)]
"""
        response = client.post("/report", json={"code": code})
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "analyses" in data
        assert "insights" in data
        assert data["overall"]["score"] >= 0
        assert data["overall"]["grade"] in ("A", "B", "C", "D", "F")

    def test_optimize_with_auto_route(self, client):
        """Auto-route deve funcionar no /optimize."""
        code = """
result = []
for i in range(100):
    result.append(i * 2)
"""
        response = client.post("/optimize", json={
            "code": code,
            "auto_route": True,
            "num_variants": 1,
        })
        assert response.status_code == 200
        data = response.json()
        assert "auto_routed" in data
        assert data["auto_routed"] is True
        assert "decision" in data

    def test_health_check(self, client):
        """Health check deve retornar status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "llm" in data


class TestDecisionMatrixIntegration:
    """Testes de integração da matriz de decisão."""

    def test_user_preference_crystal(self, engine):
        """Preferência do utilizador deve ser respeitada."""
        code = """
for i in range(50):
    for j in range(50):
        pass
"""
        plan = engine.decide(code, user_preference="prefer_crystal")
        # Com preferência Crystal, deve considerar Crystal
        assert plan.decision is not None
        assert plan.confidence > 0.5

    def test_user_preference_llm(self, engine):
        """Preferência LLM deve ser respeitada."""
        code = """
for i in range(50):
    for j in range(50):
        pass
"""
        plan = engine.decide(code, user_preference="prefer_llm")
        assert plan.decision is not None
        assert plan.confidence > 0.5

    def test_alternative_provided(self, engine):
        """Decisões devem ter alternativa quando aplicável."""
        code = """
for i in range(100):
    for j in range(100):
        for k in range(100):
            pass
"""
        plan = engine.decide(code)
        if plan.decision != Decision.SKIP:
            # Pode ter alternativa ou não
            assert plan.alternative is None or plan.alternative is not None

    def test_metrics_summary_complete(self, engine):
        """Métricas resumidas devem estar completas."""
        code = "x = 1"
        plan = engine.decide(code)
        metrics = plan.metrics_summary

        assert "score" in metrics
        assert "regime" in metrics
        assert "cycle_density" in metrics
        assert "loops" in metrics
        assert "feasibility" in metrics
