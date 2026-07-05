"""
GraphBuilder — Constrói ArchitecturalGraph a partir de um projeto Python.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .architectural_graph import ArchitecturalGraph


class GraphBuilder:
    """
    Constrói ArchitecturalGraph a partir de um diretório de projeto.

    O parser de arquivos decodifica cada alias de importação separadamente
    (por exemplo `import a, b` → `a` e `b`) e resolve submódulos de `from x import y`.
    Como o grafo interno usa `networkx.DiGraph`, arestas duplicadas são implicitamente
    consolidadas e não criam múltiplas entradas para a mesma relação.
    """

    EXCLUDE_DIRS = frozenset({
        "venv", ".venv", "__pycache__", ".git", ".pytest_cache",
        "node_modules", "dist", "build", ".mypy_cache", ".ruff_cache",
        "eggs", "*.egg-info", ".tox", ".nox",
    })

    def __init__(self, project_path: str, config: Optional[Dict[str, Any]] = None) -> None:
        self.project_path = Path(project_path).resolve()
        self.config = config or {}
        self._python_files: List[Path] = []
        self._file_analyses: Dict[str, Dict[str, Any]] = {}
        self._project_modules: List[str] = []
        self._total_imports_attempted: int = 0

    def build(self) -> ArchitecturalGraph:
        """Pipeline completo de construção do grafo."""
        graph = ArchitecturalGraph()

        self._detect_modules()
        self._collect_files()

        # Streaming mode: parse files one-by-one and populate the graph
        # without retaining all analyses in memory. Useful for very large
        # repositories (Django, Airflow) to avoid OOM.
        if self.config.get("streaming", False):
            self._build_streaming(graph)
        else:
            self._parse_files()
            self._populate_graph(graph)

        return graph

    def _detect_modules(self) -> None:
        self._project_modules = []
        for item in self.project_path.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith(".") or item.name.startswith("__"):
                continue
            if (item / "__init__.py").exists() or any(item.rglob("*.py")):
                self._project_modules.append(item.name)

    def _collect_files(self) -> None:
        self._python_files = []
        for f in self.project_path.rglob("*.py"):
            if not any(part in self.EXCLUDE_DIRS for part in f.parts):
                self._python_files.append(f)
        self._python_files.sort()

    def _build_streaming(self, graph: ArchitecturalGraph) -> None:
        """
        Parse files one-by-one and populate `graph` immediately to keep
        memory usage low for very large projects.
        """
        for file_path in self._python_files:
            try:
                self._parse_file_stream(file_path, graph)
            except (SyntaxError, UnicodeDecodeError):
                continue

    def _parse_file_stream(self, file_path: Path, graph: ArchitecturalGraph) -> None:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content)
        lines = content.splitlines()

        classes: List[Dict[str, Any]] = []
        functions: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []
        responsibilities: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                classes.append({
                    "name": node.name,
                    "lines": end - node.lineno + 1,
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                functions.append({
                    "name": node.name,
                    "lines": end - node.lineno + 1,
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(self._parse_import(node))
            elif isinstance(node, ast.Call):
                dyn = self._parse_dynamic_import_call(node)
                if dyn:
                    imports.append(dyn)

        self._total_imports_attempted += len(imports)

        module = self._get_file_module(str(file_path))

        resp_kw = self.config.get("responsibility_keywords", {})
        content_lower = content.lower()
        fn_lower = file_path.stem.lower()
        for resp_name, keywords in resp_kw.items():
            for kw in keywords:
                if kw in fn_lower or kw in content_lower:
                    responsibilities.add(resp_name)
                    break

        # add file to graph immediately
        graph.add_file(
            path=str(file_path),
            module=module,
            loc=len(lines),
            classes=classes,
            functions=functions,
            responsabilities=responsibilities,
        )

        # add resolved imports as edges
        for imp in imports:
            module_name = imp.get("module", "")
            level = imp.get("level", 0)
            name = imp.get("name", "")
            # dynamic imports without literal module are not resolved
            if imp.get("type") == "dynamic" and not module_name:
                continue
            resolved = self._resolve_import(module_name, level, file_path, name)
            if resolved:
                is_cross = module != self._get_file_module(str(resolved))
                graph.add_import(
                    from_path=str(file_path),
                    to_path=str(resolved),
                    import_type=imp.get("type", "from"),
                    level=level,
                    is_cross_module=is_cross,
                )

        # add cross-module imports aggregation
        imported_modules = set()
        for imp in imports:
            module_name = imp.get("module", "")
            imported_module = module_name.split(".")[0] if module_name else ""
            if imported_module and imported_module != module:
                if imported_module in self._project_modules:
                    imported_modules.add(imported_module)

        for imp_mod in imported_modules:
            graph.add_cross_module_import(module, imp_mod)

    def _parse_files(self) -> None:
        for file_path in self._python_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                lines = content.splitlines()

                classes: List[Dict[str, Any]] = []
                functions: List[Dict[str, Any]] = []
                imports: List[Dict[str, Any]] = []
                responsibilities: Set[str] = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        end = getattr(node, "end_lineno", node.lineno) or node.lineno
                        classes.append({
                            "name": node.name,
                            "lines": end - node.lineno + 1,
                        })
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        end = getattr(node, "end_lineno", node.lineno) or node.lineno
                        functions.append({
                            "name": node.name,
                            "lines": end - node.lineno + 1,
                        })
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        imports.extend(self._parse_import(node))
                    elif isinstance(node, ast.Call):
                        # detect dynamic imports: __import__('mod'), importlib.import_module('mod')
                        dyn = self._parse_dynamic_import_call(node)
                        if dyn:
                            imports.append(dyn)

                self._total_imports_attempted += len(imports)

                module = self._get_file_module(str(file_path))

                resp_kw = self.config.get("responsibility_keywords", {})
                content_lower = content.lower()
                fn_lower = file_path.stem.lower()
                for resp_name, keywords in resp_kw.items():
                    for kw in keywords:
                        if kw in fn_lower or kw in content_lower:
                            responsibilities.add(resp_name)
                            break

                self._file_analyses[str(file_path)] = {
                    "path": file_path,
                    "module": module,
                    "loc": len(lines),
                    "classes": classes,
                    "functions": functions,
                    "imports": imports,
                    "responsibilities": responsibilities,
                }

            except (SyntaxError, UnicodeDecodeError):
                continue

    def _parse_import(self, node: Any) -> List[Dict[str, Any]]:
        """
        Parse each import alias separately and preserve `from`/`import` semantics.

        This avoids treating `import a, b` as a single combined import and makes
        `from pkg import sub` resolve to the imported submodule rather than just
        `pkg.__init__` when possible.
        """
        if isinstance(node, ast.Import):
            return [
                {
                    "type": "import",
                    "module": alias.name,
                    "name": "",
                    "level": 0,
                    "line": node.lineno,
                }
                for alias in node.names
            ]

        module_name = node.module or ""
        level = getattr(node, "level", 0)
        imports: List[Dict[str, Any]] = []

        for alias in node.names:
            name = alias.name if alias.name != "*" else "*"
            target_module = module_name or name
            imports.append({
                "type": "from",
                "module": target_module,
                "name": name,
                "level": level,
                "line": node.lineno,
            })

        return imports

    def _parse_dynamic_import_call(self, node: Any) -> Optional[Dict[str, Any]]:
        """
        Detect calls to dynamic import helpers like `__import__` or
        `importlib.import_module('pkg')`. If the module name is a string
        literal, return a parsed import dict; otherwise return a generic
        dynamic import marker so the parser can count attempted imports.
        """
        # node.func can be Name('__import__') or Attribute(Name('importlib'), 'import_module')
        func = node.func
        func_name = ""
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            func_name = f"{func.value.id}.{func.attr}"

        if func_name in ("__import__", "import_module", "importlib.import_module"):
            # attempt to extract module name if it's a string literal
            if node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    return {
                        "type": "dynamic",
                        "module": first.value,
                        "name": "",
                        "level": 0,
                        "line": getattr(node, "lineno", 0),
                    }
            return {
                "type": "dynamic",
                "module": "",
                "name": "",
                "level": 0,
                "line": getattr(node, "lineno", 0),
            }
        return None

    def _get_file_module(self, file_path_str: str) -> str:
        try:
            rel = Path(file_path_str).relative_to(self.project_path)
            return rel.parts[0] if rel.parts else ""
        except ValueError:
            return ""

    def _populate_graph(self, graph: ArchitecturalGraph) -> None:
        for module_name in self._project_modules:
            graph.add_module(module_name)

        for fp, analysis in self._file_analyses.items():
            graph.add_file(
                path=fp,
                module=analysis["module"],
                loc=analysis["loc"],
                classes=analysis["classes"],
                functions=analysis["functions"],
                responsabilities=analysis["responsibilities"],
            )

        for fp, analysis in self._file_analyses.items():
            from_module = analysis["module"]

            for imp in analysis["imports"]:
                module = imp.get("module", "")
                level = imp.get("level", 0)
                name = imp.get("name", "")
                resolved = self._resolve_import(module, level, Path(fp), name)

                if resolved:
                    is_cross = from_module != self._get_file_module(str(resolved))
                    graph.add_import(
                        from_path=fp,
                        to_path=str(resolved),
                        import_type=imp.get("type", "from"),
                        level=level,
                        is_cross_module=is_cross,
                    )

            # dynamic imports are counted as attempted but unresolved
            # (we don't add edges for them)

            imported_modules = set()
            for imp in analysis["imports"]:
                module = imp.get("module", "")
                imported_module = module.split(".")[0] if module else ""
                if imported_module and imported_module != from_module:
                    if imported_module in self._project_modules:
                        imported_modules.add(imported_module)

            for imp_mod in imported_modules:
                graph.add_cross_module_import(from_module, imp_mod)

    def _resolve_import(
        self,
        module: str,
        level: int,
        from_file: Path,
        name: Optional[str] = None,
    ) -> Optional[Path]:
        if level > 0:
            base = from_file.parent
            for _ in range(level - 1):
                base = base.parent
            parts = module.split(".") if module else []
            target = base
            for part in parts:
                target = target / part
            if name and name != "*":
                alt_target = target
                for part in ([name] if not module else [name]):
                    alt_target = alt_target / part
                if (alt_target.with_suffix(".py")).exists():
                    return alt_target.with_suffix(".py")
                if (alt_target / "__init__.py").exists():
                    return alt_target / "__init__.py"

            if (target.with_suffix(".py")).exists():
                return target.with_suffix(".py")
            if (target / "__init__.py").exists():
                return target / "__init__.py"
        else:
            parts = module.split(".") if module else []
            if parts and parts[0] in self._project_modules:
                target = self.project_path
                for part in parts:
                    target = target / part
                if name and name != "*":
                    alt_target = target
                    for part in [name]:
                        alt_target = alt_target / part
                    if (alt_target.with_suffix(".py")).exists():
                        return alt_target.with_suffix(".py")
                    if (alt_target / "__init__.py").exists():
                        return alt_target / "__init__.py"

                if (target.with_suffix(".py")).exists():
                    return target.with_suffix(".py")
                if (target / "__init__.py").exists():
                    return target / "__init__.py"

        # Fallback: try to locate module by searching project files
        parts = module.split(".") if module else []
        found = self._search_project_for_module(parts)
        if found:
            return found
        return None

    def _search_project_for_module(self, parts: List[str]) -> Optional[Path]:
        """
        Heurística de fallback: tenta encontrar um arquivo no projeto cujo caminho
        termine com os `parts` do módulo (por exemplo, package.sub -> .../package/sub.py).
        Se encontrar único candidato, retorna-o; caso múltiplos, escolhe o de menor
        profundidade ou preferencialmente aquele dentro do mesmo top-level module.
        """
        if not parts:
            return None

        candidates: List[Path] = []
        last = parts[-1]
        for f in self._python_files:
            try:
                rel = f.relative_to(self.project_path)
            except Exception:
                continue
            rel_parts = rel.with_suffix("").parts
            # exact tail match
            if len(rel_parts) >= len(parts) and tuple(rel_parts[-len(parts):]) == tuple(parts):
                candidates.append(f)
            # match by filename
            elif rel_parts and rel_parts[-1] == last:
                candidates.append(f)

        if not candidates:
            return None

        # prefer shallowest path (likely top-level module), then arbitrary
        candidates.sort(key=lambda p: len(p.parts))
        return candidates[0]

    @property
    def total_imports_attempted(self) -> int:
        """Total imports que o parser tentou resolver para o projeto."""
        return self._total_imports_attempted
