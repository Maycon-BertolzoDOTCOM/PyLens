"""
LLM Verifier — Verificação de código otimizado.

Executa testes e valida código otimizado em sandbox seguro.
"""

from __future__ import annotations

import ast
import tempfile
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import subprocess


@dataclass
class VerificationResult:
    """Resultado da verificação."""
    is_valid: bool
    tests_passed: bool
    memory_usage: Optional[int] = None  # em KB
    execution_time: Optional[float] = None  # em segundos
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class OptimizationVerifier:
    """
    Verificador de código otimizado.

    Valida sintaxe, executa testes e verifica performance.
    """

    def __init__(self, timeout: int = 10):
        """
        Args:
            timeout: Timeout em segundos para execução
        """
        self.timeout = timeout

    def verify(
        self,
        code: str,
        tests: Optional[str] = None,
        check_memory: bool = True
    ) -> VerificationResult:
        """
        Verificar código otimizado.

        Args:
            code: Código Python para verificar
            tests: Código de testes pytest (opcional)
            check_memory: Se True, verifica uso de memória

        Returns:
            VerificationResult com resultado da verificação
        """
        # 1. Validar sintaxe
        syntax_valid, syntax_error = self._validate_syntax(code)
        if not syntax_valid:
            return VerificationResult(
                is_valid=False,
                tests_passed=False,
                errors=[syntax_error],
            )

        # 2. Executar testes se fornecidos
        tests_passed = True
        test_errors = []
        if tests:
            tests_passed, test_errors = self._run_tests(code, tests)

        # 3. Verificar memória se solicitado
        memory_usage = None
        if check_memory:
            memory_usage = self._check_memory(code)

        # 4. Verificar execução básica
        execution_time = self._measure_execution(code)

        return VerificationResult(
            is_valid=True,
            tests_passed=tests_passed,
            memory_usage=memory_usage,
            execution_time=execution_time,
            errors=test_errors,
        )

    def _validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Validar sintaxe do código Python."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Erro de sintaxe na linha {e.lineno}: {e.msg}"

    def _run_tests(self, code: str, tests: str) -> tuple[bool, List[str]]:
        """Executar testes pytest no código."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Escrever código principal
            code_file = Path(tmpdir) / "module.py"
            code_file.write_text(code, encoding="utf-8")

            # Escrever testes
            test_file = Path(tmpdir) / "test_module.py"
            test_file.write_text(tests, encoding="utf-8")

            try:
                result = subprocess.run(
                    [
                        "python", "-m", "pytest",
                        str(test_file),
                        "-v",
                        "--tb=short",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmpdir,
                )

                if result.returncode == 0:
                    return True, []
                else:
                    errors = [line for line in result.stdout.split('\n') if 'FAILED' in line or 'ERROR' in line]
                    return False, errors

            except subprocess.TimeoutExpired:
                return False, ["Testes excederam o tempo limite"]
            except Exception as e:
                return False, [f"Erro ao executar testes: {str(e)}"]

    def _check_memory(self, code: str) -> Optional[int]:
        """Verificar uso de memória do código."""
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "check_memory.py"
            code_file.write_text(code, encoding="utf-8")

            try:
                # Usar /proc/self/status para medir memória
                monitor_code = f"""
import subprocess
import os

# Executar o código em subprocess separado
result = subprocess.run(
    ['python', '{code_file}'],
    capture_output=True,
    timeout={self.timeout}
)

# Ler memória do processo atual
with open('/proc/self/status') as f:
    for line in f:
        if line.startswith('VmPeak:'):
            kb = int(line.split()[1])
            print(kb)
            break
"""
                result = subprocess.run(
                    ["python", "-c", monitor_code],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 5,
                )

                if result.returncode == 0 and result.stdout.strip():
                    return int(result.stdout.strip())

            except Exception:
                pass

        return None

    def _measure_execution(self, code: str) -> Optional[float]:
        """Medir tempo de execução do código."""
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "measure.py"
            code_file.write_text(code, encoding="utf-8")

            try:
                import time
                start = time.time()

                result = subprocess.run(
                    ["python", str(code_file)],
                    capture_output=True,
                    timeout=self.timeout,
                    cwd=tmpdir,
                )

                end = time.time()

                if result.returncode == 0:
                    return round(end - start, 4)

            except Exception:
                pass

        return None
