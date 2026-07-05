"""
ArchitecturalGraph — Fonte única de verdade para todas as métricas.

Baseado em NetworkX DiGraph.
Toda análise deve derivar deste grafo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx


@dataclass
class FileNode:
    """Dados de um arquivo Python no grafo."""

    path: str
    module: str
    loc: int = 0
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    imports_count: int = 0
    responsabilities: Set[str] = field(default_factory=set)


@dataclass
class ModuleNode:
    """Dados de um módulo (pacote) no grafo."""

    name: str
    file_count: int = 0
    total_loc: int = 0
    is_domain: bool = False


@dataclass
class ImportEdge:
    """Aresta de importação entre dois nós."""

    import_type: str  # "import", "from", "relative"
    level: int = 0  # nível de importação relativa
    is_cross_module: bool = False
    is_boundary_violation: bool = False


class ArchitecturalGraph:
    """
    Grafo arquitetural central do AGS.

    Wraps nx.DiGraph com métodos específicos para análise arquitetural.
    """

    def __init__(self) -> None:
        self._graph = nx.DiGraph()
        self._files: Dict[str, FileNode] = {}
        self._modules: Dict[str, ModuleNode] = {}

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @property
    def files(self) -> Dict[str, FileNode]:
        return self._files

    @property
    def modules(self) -> Dict[str, ModuleNode]:
        return self._modules

    @property
    def file_count(self) -> int:
        return len(self._files)

    @property
    def module_count(self) -> int:
        return len(self._modules)

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    # --- Construção ---

    def add_file(
        self,
        path: str,
        module: str,
        loc: int = 0,
        classes: Optional[List[Dict[str, Any]]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        responsabilities: Optional[Set[str]] = None,
    ) -> None:
        self._files[path] = FileNode(
            path=path,
            module=module,
            loc=loc,
            classes=classes or [],
            functions=functions or [],
            responsabilities=responsabilities or set(),
        )
        self._graph.add_node(
            path,
            node_type="file",
            module=module,
            loc=loc,
        )

    def add_module(self, name: str, is_domain: bool = False) -> None:
        if name not in self._modules:
            self._modules[name] = ModuleNode(name=name, is_domain=is_domain)
        self._graph.add_node(
            f"module:{name}",
            node_type="module",
            module_name=name,
        )

    def add_import(
        self,
        from_path: str,
        to_path: str,
        import_type: str = "from",
        level: int = 0,
        is_cross_module: bool = False,
        is_boundary_violation: bool = False,
    ) -> None:
        edge_data = ImportEdge(
            import_type=import_type,
            level=level,
            is_cross_module=is_cross_module,
            is_boundary_violation=is_boundary_violation,
        )
        self._graph.add_edge(
            from_path,
            to_path,
            import_type=import_type,
            level=level,
            is_cross_module=is_cross_module,
            is_boundary_violation=is_boundary_violation,
        )
        if from_path in self._files:
            self._files[from_path].imports_count += 1

    def add_cross_module_import(self, from_module: str, to_module: str) -> None:
        self._graph.add_edge(
            f"module:{from_module}",
            f"module:{to_module}",
            import_type="module",
            is_cross_module=True,
        )

    # --- Consultas ---

    def get_file_nodes(self) -> List[str]:
        return [n for n, d in self._graph.nodes(data=True) if d.get("node_type") == "file"]

    def get_module_nodes(self) -> List[str]:
        return [n for n, d in self._graph.nodes(data=True) if d.get("node_type") == "module"]

    def get_imports_from(self, path: str) -> List[str]:
        return list(self._graph.successors(path))

    def get_imported_by(self, path: str) -> List[str]:
        return list(self._graph.predecessors(path))

    def get_files_in_module(self, module: str) -> List[str]:
        return [
            n for n, d in self._graph.nodes(data=True)
            if d.get("node_type") == "file" and d.get("module") == module
        ]

    # --- Métricas derivadas ---

    def detect_cycles(self) -> List[List[str]]:
        """Detectar ciclos de dependência no grafo de módulos."""
        cycles: List[List[str]] = []
        module_graph = self._extract_module_graph()

        try:
            for cycle in nx.simple_cycles(module_graph):
                clean = [c.replace("module:", "") for c in cycle]
                cycles.append(clean)
        except nx.NetworkXError:
            pass

        return cycles

    def detect_all_cycles(self) -> List[List[str]]:
        """Detectar TODOS os ciclos, incluindo intra-módulo (no grafo completo)."""
        cycles: List[List[str]] = []
        try:
            for cycle in nx.simple_cycles(self._graph):
                clean = [c.replace("module:", "") for c in cycle]
                cycles.append(clean)
        except nx.NetworkXError:
            pass
        return cycles

    def context_radius(self, path: str, depth: int = 3) -> int:
        """
        Quantos arquivos são afetados por uma mudança em path.
        BFS limitado por profundidade.

        depth=0 → 0 (nenhum salto)
        depth=1 → apenas dependências imediatas
        depth=N → até N saltos
        """
        if depth < 0:
            return 0
        if path not in self._graph:
            return 0

        if depth == 0:
            return 0

        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(path, 0)]

        while queue:
            current, current_depth = queue.pop(0)
            if current in visited or current_depth > depth:
                continue
            visited.add(current)

            if current_depth < depth:
                successors = set(self._graph.successors(current))
                predecessors = set(self._graph.predecessors(current))
                for neighbor in successors | predecessors:
                    if neighbor not in visited:
                        queue.append((neighbor, current_depth + 1))

        return len(visited) - 1

    def dependency_density(self) -> float:
        """
        Densidade de dependências = edges / max_possible_edges.
        Retorna 0.0–1.0.
        """
        n = self._graph.number_of_nodes()
        if n <= 1:
            return 0.0
        return self._graph.number_of_edges() / (n * (n - 1))

    def layer_purity(self, layer_rules: Optional[Dict[str, Dict[str, List[str]]]] = None) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Mede se imports respeitam hierarquia de camadas.

        Retorna (score_0_100, lista_de_violations).
        """
        if layer_rules is None:
            layer_rules = {
                "domain": {"allowed_above": [], "allowed_below": ["application", "infra", "service"]},
                "application": {"allowed_above": ["domain"], "allowed_below": ["infra", "service"]},
                "service": {"allowed_above": ["domain", "application"], "allowed_below": ["infra"]},
                "infra": {"allowed_above": ["domain", "application", "service"], "allowed_below": []},
                "core": {"allowed_above": [], "allowed_below": ["application", "infra"]},
                "api": {"allowed_above": ["domain", "application"], "allowed_below": ["infra"]},
                "web": {"allowed_above": ["domain", "application"], "allowed_below": ["infra"]},
                "cli": {"allowed_above": ["domain", "application"], "allowed_below": ["infra"]},
            }

        violations: List[Dict[str, Any]] = []
        total_edges = 0
        valid_edges = 0

        for from_node, to_node, data in self._graph.edges(data=True):
            if data.get("import_type") == "module":
                continue

            from_module = self._files.get(from_node, FileNode(path=from_node, module="")).module
            to_module = self._files.get(to_node, FileNode(path=to_node, module="")).module

            if from_module == to_module:
                valid_edges += 1
                total_edges += 1
                continue

            from_layer = self._detect_layer(from_module, layer_rules)
            to_layer = self._detect_layer(to_module, layer_rules)

            total_edges += 1

            if from_layer and to_layer:
                allowed_below = layer_rules.get(from_layer, {}).get("allowed_below", [])
                if to_layer in allowed_below:
                    valid_edges += 1
                else:
                    violations.append({
                        "from": from_node,
                        "to": to_node,
                        "from_layer": from_layer,
                        "to_layer": to_layer,
                        "type": "layer_violation",
                    })
            else:
                valid_edges += 1

        score = (valid_edges / max(total_edges, 1)) * 100
        return round(score, 2), violations

    def _detect_layer(self, module_name: str, layer_rules: Dict[str, Dict[str, List[str]]]) -> Optional[str]:
        module_lower = module_name.lower()
        for layer in layer_rules:
            if layer in module_lower:
                return layer
        return None

    def graph_drift(self, previous: ArchitecturalGraph) -> float:
        """
        Mede divergência entre dois grafos usando Jaccard distance nos edges.
        Retorna 0.0 (idênticos) a 1.0 (completamente diferentes).
        """
        edges_current = set(self._graph.edges())
        edges_previous = set(previous._graph.edges())

        if not edges_current and not edges_previous:
            return 0.0

        intersection = edges_current & edges_previous
        union = edges_current | edges_previous

        return 1.0 - (len(intersection) / max(len(union), 1))

    def most_connected_nodes(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """Nós com mais conexões (in-degree + out-degree)."""
        centrality = {}
        for node in self._graph.nodes():
            degree = self._graph.in_degree(node) + self._graph.out_degree(node)
            centrality[node] = degree

        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_n]

    def _extract_module_graph(self) -> nx.DiGraph:
        """Extrai subgrafo de módulos (ignora nós de arquivo)."""
        module_graph = nx.DiGraph()
        module_nodes = [n for n in self._graph.nodes() if n.startswith("module:")]
        module_graph.add_nodes_from(module_nodes)

        for from_node, to_node, data in self._graph.edges(data=True):
            if data.get("import_type") == "module":
                if from_node in module_nodes and to_node in module_nodes:
                    module_graph.add_edge(from_node, to_node)

        return module_graph

    # --- Serialização ---

    def to_dict(self) -> Dict[str, Any]:
        files_data = {}
        for path, node in self._files.items():
            files_data[path] = {
                "module": node.module,
                "loc": node.loc,
                "classes": node.classes,
                "functions": node.functions,
                "imports_count": node.imports_count,
            }

        modules_data = {}
        for name, node in self._modules.items():
            modules_data[name] = {
                "file_count": node.file_count,
                "total_loc": node.total_loc,
                "is_domain": node.is_domain,
            }

        edges_data = []
        for from_node, to_node, data in self._graph.edges(data=True):
            edges_data.append({
                "from": from_node,
                "to": to_node,
                **data,
            })

        return {
            "files": files_data,
            "modules": modules_data,
            "edges": edges_data,
            "stats": {
                "file_count": self.file_count,
                "module_count": self.module_count,
                "edge_count": self.edge_count,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArchitecturalGraph:
        g = cls()

        for path, fdata in data.get("files", {}).items():
            g.add_file(
                path=path,
                module=fdata.get("module", ""),
                loc=fdata.get("loc", 0),
                classes=fdata.get("classes", []),
                functions=fdata.get("functions", []),
            )

        for name, mdata in data.get("modules", {}).items():
            g.add_module(name=name, is_domain=mdata.get("is_domain", False))

        for edge in data.get("edges", []):
            from_node = edge.pop("from")
            to_node = edge.pop("to")
            g._graph.add_edge(from_node, to_node, **edge)

        return g

    @classmethod
    def from_json(cls, json_str: str) -> ArchitecturalGraph:
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        return (
            f"ArchitecturalGraph(files={self.file_count}, "
            f"modules={self.module_count}, edges={self.edge_count})"
        )
