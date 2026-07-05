"""
PyLens Targets — Plugins de saída opcionais.

Targets disponíveis:
- crystal: Transpilação Python → Crystal
"""

from .crystal.transpiler import Transpiler

__all__ = ["Transpiler"]
