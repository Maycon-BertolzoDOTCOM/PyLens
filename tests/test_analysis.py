"""
Testes para o módulo de análise do PyLens.
"""

import pytest
from app.analysis.static_analysis import StaticAnalyzer, AnalysisResult
from app.analysis.architectural import ArchitecturalAnalyzer, ArchitecturalResult
from app.analysis.quality import QualityAnalyzer, QualityAssessment
from app.analysis.report import ReportGenerator, PyLensReport


@pytest.fixture
def static_analyzer():
    return StaticAnalyzer()


@pytest.fixture
def architectural_analyzer():
    return ArchitecturalAnalyzer()


@pytest.fixture
def report_generator():
    return ReportGenerator()


class TestStaticAnalyzer:
    """Testes para o analisador estático."""

    def test_analyze_simple_code(self, static_analyzer):
        code = """
def add(x, y):
    return x + y
"""
        score, imports, loops = static_analyzer.analyze(code)
        assert 0 <= score <= 100
        assert isinstance(imports, list)
        assert isinstance(loops, int)

    def test_analyze_with_loops(self, static_analyzer):
        code = """
for i in range(100):
    for j in range(100):
        pass
"""
        score, imports, loops = static_analyzer.analyze(code)
        assert loops >= 2

    def test_analyze_detailed(self, static_analyzer):
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        result = static_analyzer.analyze_detailed(code)
        assert isinstance(result, AnalysisResult)
        assert result.score >= 0
        assert result.optimization_potential in ["HIGH", "MEDIUM", "LOW"]

    def test_syntax_error(self, static_analyzer):
        code = "def invalid(:"
        score, imports, loops = static_analyzer.analyze(code)
        assert score == 0
        assert imports == []
        assert loops == 0


class TestArchitecturalAnalyzer:
    """Testes para o analisador arquitetural."""

    def test_analyze_simple_code(self, architectural_analyzer):
        code = """
def add(x, y):
    return x + y
"""
        result = architectural_analyzer.analyze(code)
        assert isinstance(result, ArchitecturalResult)
        assert result.regime is not None
        assert result.optimization_feasibility in ["HIGH", "MEDIUM", "LOW"]

    def test_analyze_with_classes(self, architectural_analyzer):
        code = """
class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, x):
        self.value += x
        return self.value
"""
        result = architectural_analyzer.analyze(code)
        assert len(result.code_structure.classes) == 1

    def test_feasibility_assessment(self, architectural_analyzer):
        code = """
def simple():
    return 42
"""
        result = architectural_analyzer.analyze(code)
        assert result.optimization_feasibility == "HIGH"


class TestReportGenerator:
    """Testes para o gerador de relatórios."""

    def test_generate_report(self, report_generator):
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

results = [fibonacci(x) for x in range(10)]
"""
        report = report_generator.generate(code)
        assert isinstance(report, PyLensReport)
        assert report.overall_score >= 0
        assert report.overall_grade in ["A", "B", "C", "D", "F"]
        assert report.optimization_potential in ["HIGH", "MEDIUM", "LOW"]
        assert len(report.key_findings) > 0

    def test_report_to_dict(self, report_generator):
        code = "x = 1"
        report = report_generator.generate(code)
        report_dict = report.to_dict()
        assert "metadata" in report_dict
        assert "overall" in report_dict
        assert "analyses" in report_dict
        assert "insights" in report_dict
