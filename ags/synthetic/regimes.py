"""
Regime Taxonomy — 11 canonical regimes (attractor-collapse classes).

Analysis:
- Ontology: Architecture, Boundary, Dependency
- Theory: Axiom 1 (Architecture is graphable)
- Phenomenon: All structural phenomena
- Causal Factors: Construction parameter ranges
- State Vector: All dimensions
- Invariants: Regimes are parameter ranges, not point configs
- Applicability: Controlled experimental conditions

Key design constraint: regimes are defined as parameter ranges,
not fixed configurations. This prevents hidden arbitrariness and
enables falsifiability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


class RegimeName(str, Enum):
    """Canonical regime names (attractor classes)."""

    PERFECT = "PERFECT"
    COUPLED = "COUPLED"
    LEAKY = "LEAKY"
    COLLAPSED = "COLLAPSED"
    MODULAR_SMALL = "MODULAR_SMALL"
    MODULAR_LARGE = "MODULAR_LARGE"
    ENTANGLED_SMALL = "ENTANGLED_SMALL"
    ENTANGLED_LARGE = "ENTANGLED_LARGE"
    MIXED = "MIXED"
    PATHOLOGICAL = "PATHOLOGICAL"
    ACYCLIC_DOMINANT = "ACYCLIC_DOMINANT"


@dataclass(frozen=True)
class RegimeRange:
    """
    A regime defined as a parameter range (attractor basin).

    Each regime is a set of construction parameter ranges:
        R = { x in X | theta_min <= theta(x) < theta_max }
    """

    name: RegimeName
    description: str
    cross_domain_ratio: Tuple[float, float]
    intra_domain_ratio: Tuple[float, float]
    file_level_leakage: Tuple[float, float]
    cycle_density: Tuple[float, float]
    size_class: str  # "SMALL", "MEDIUM", "LARGE"


REGIME_TAXONOMY: Dict[RegimeName, RegimeRange] = {
    RegimeName.PERFECT: RegimeRange(
        name=RegimeName.PERFECT,
        description="No cross-domain edges, no leakage",
        cross_domain_ratio=(0.0, 0.05),
        intra_domain_ratio=(0.8, 1.0),
        file_level_leakage=(0.0, 0.02),
        cycle_density=(0.0, 0.05),
        size_class="MEDIUM",
    ),
    RegimeName.COUPLED: RegimeRange(
        name=RegimeName.COUPLED,
        description="Controlled cross-domain coupling",
        cross_domain_ratio=(0.2, 0.4),
        intra_domain_ratio=(0.6, 0.9),
        file_level_leakage=(0.0, 0.1),
        cycle_density=(0.05, 0.15),
        size_class="MEDIUM",
    ),
    RegimeName.LEAKY: RegimeRange(
        name=RegimeName.LEAKY,
        description="File-level violations of domain boundaries",
        cross_domain_ratio=(0.0, 0.1),
        intra_domain_ratio=(0.4, 0.7),
        file_level_leakage=(0.6, 0.9),
        cycle_density=(0.1, 0.3),
        size_class="MEDIUM",
    ),
    RegimeName.COLLAPSED: RegimeRange(
        name=RegimeName.COLLAPSED,
        description="Full graph connectivity, all domains merged",
        cross_domain_ratio=(0.9, 1.0),
        intra_domain_ratio=(0.9, 1.0),
        file_level_leakage=(0.4, 0.6),
        cycle_density=(0.15, 0.25),
        size_class="MEDIUM",
    ),
    RegimeName.MODULAR_SMALL: RegimeRange(
        name=RegimeName.MODULAR_SMALL,
        description="Small clean modules, minimal coupling",
        cross_domain_ratio=(0.0, 0.15),
        intra_domain_ratio=(0.5, 0.8),
        file_level_leakage=(0.0, 0.1),
        cycle_density=(0.0, 0.1),
        size_class="SMALL",
    ),
    RegimeName.MODULAR_LARGE: RegimeRange(
        name=RegimeName.MODULAR_LARGE,
        description="Large clean modules, minimal coupling",
        cross_domain_ratio=(0.0, 0.15),
        intra_domain_ratio=(0.5, 0.8),
        file_level_leakage=(0.0, 0.1),
        cycle_density=(0.0, 0.1),
        size_class="LARGE",
    ),
    RegimeName.ENTANGLED_SMALL: RegimeRange(
        name=RegimeName.ENTANGLED_SMALL,
        description="Small with high coupling",
        cross_domain_ratio=(0.5, 0.8),
        intra_domain_ratio=(0.7, 1.0),
        file_level_leakage=(0.2, 0.5),
        cycle_density=(0.1, 0.3),
        size_class="SMALL",
    ),
    RegimeName.ENTANGLED_LARGE: RegimeRange(
        name=RegimeName.ENTANGLED_LARGE,
        description="Large with high coupling",
        cross_domain_ratio=(0.5, 0.8),
        intra_domain_ratio=(0.7, 1.0),
        file_level_leakage=(0.2, 0.5),
        cycle_density=(0.1, 0.3),
        size_class="LARGE",
    ),
    RegimeName.MIXED: RegimeRange(
        name=RegimeName.MIXED,
        description="Typical real project (mixed signals)",
        cross_domain_ratio=(0.2, 0.5),
        intra_domain_ratio=(0.5, 0.8),
        file_level_leakage=(0.1, 0.4),
        cycle_density=(0.1, 0.3),
        size_class="MEDIUM",
    ),
    RegimeName.PATHOLOGICAL: RegimeRange(
        name=RegimeName.PATHOLOGICAL,
        description="Anti-patterns: god modules, deep cycles",
        cross_domain_ratio=(0.7, 0.9),
        intra_domain_ratio=(0.8, 1.0),
        file_level_leakage=(0.6, 0.9),
        cycle_density=(0.3, 0.5),
        size_class="MEDIUM",
    ),
    RegimeName.ACYCLIC_DOMINANT: RegimeRange(
        name=RegimeName.ACYCLIC_DOMINANT,
        description="Pure hierarchy, no cycles",
        cross_domain_ratio=(0.1, 0.3),
        intra_domain_ratio=(0.5, 0.8),
        file_level_leakage=(0.0, 0.1),
        cycle_density=(0.0, 0.1),
        size_class="MEDIUM",
    ),
}


def size_to_params(size_class: str) -> Tuple[int, int, int]:
    """
    Map size class to (domains, modules_per_domain, files_per_module).
    """
    if size_class == "SMALL":
        return (2, 1, 2)
    elif size_class == "MEDIUM":
        return (3, 2, 3)
    elif size_class == "LARGE":
        return (4, 3, 4)
    else:
        return (3, 2, 3)


def classify_observed_regime(
    cross_domain_ratio: float,
    intra_domain_ratio: float,
    file_level_leakage: float,
    cycle_density: float,
    graph_size: int,
) -> RegimeName:
    """
    Classify a measured graph into a regime (observational truth).

    Uses 4 structural metrics PLUS graph_size to disambiguate
    MODULAR_SMALL/MODULAR_LARGE and ENTANGLED_SMALL/ENTANGLED_LARGE.
    """
    best_match = None
    best_distance = float("inf")

    for name, rng in REGIME_TAXONOMY.items():
        d = _distance_to_range(
            cross_domain_ratio, intra_domain_ratio,
            file_level_leakage, cycle_density,
            graph_size, rng,
        )
        if d < best_distance:
            best_distance = d
            best_match = name

    return best_match


def _size_distance(graph_size: int, size_class: str) -> float:
    """
    Penalize mismatch between observed size and size_class.

    For SMALL: graph_size <= 8 (2 domains * 1 module * 2 files + overhead)
    For MEDIUM: 8 < graph_size <= 30
    For LARGE: graph_size > 30
    """
    if size_class == "SMALL":
        target = 6
    elif size_class == "MEDIUM":
        target = 20
    else:  # LARGE
        target = 50
    return abs(graph_size - target) / 20.0


def _distance_to_range(
    cross: float, intra: float, leakage: float, cycles: float,
    graph_size: int, rng: RegimeRange,
) -> float:
    """Euclidean distance from point to range midpoint, normalized."""
    def _d(val: float, bounds: Tuple[float, float]) -> float:
        mid = (bounds[0] + bounds[1]) / 2
        width = bounds[1] - bounds[0]
        return abs(val - mid) / max(width, 0.01)

    metric_dist = (
        _d(cross, rng.cross_domain_ratio) ** 2
        + _d(intra, rng.intra_domain_ratio) ** 2
        + _d(leakage, rng.file_level_leakage) ** 2
        + _d(cycles, rng.cycle_density) ** 2
    )
    size_dist = _size_distance(graph_size, rng.size_class) ** 2

    return (metric_dist + size_dist) ** 0.5


CIR1_DOC = """
CIR-1: Structural Causality

For any regime R:
    P(R_obs | R_spec) must be sharply peaked

Otherwise regime definition is invalid.

This is the Causal Integrity Rule -- the core invariant
of the C0.0 experimental system.
"""
