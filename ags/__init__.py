"""
AGS — Architectural Graph System for PyLens
============================================

Métricas de acoplamento e coesão calculadas a partir do grafo de imports (AST).
Inspirado pelas métricas estruturais de Briand, L.C., Daly, J.W., Wüst, J.
(1999) "A Unified Framework for Coupling Measurement in Object-Oriented
Systems" — IEEE Trans. Software Eng., e por literatura de análise de
dependências em grafos de software (cyclic_ratio, leakage_ratio).

Esta implementação é uma adaptação própria, otimizada para projetos Python.

A taxonomia de 11 regimes (PERFECT → PATHOLOGICAL) e a matriz de decisão
são contribuições originais do PyLens, não derivadas de fontes externas.
"""

__version__ = "2.0.0"
