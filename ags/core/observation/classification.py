"""
RegimeClassification — Classify an ObservationSnapshot into the nearest regime(s).

Design:
- Uses REGIME_TAXONOMY from AGS synthetic module as the reference space
- Distance = Euclidean distance to regime midpoint (same formula as synthetic)
- Margin = distance_2 - distance_1 (separation between nearest and second-nearest)
- Confidence = observation_quality * (1 - distance_1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ags.synthetic.regimes import REGIME_TAXONOMY, RegimeName

from .primitives import ObservationSnapshot


@dataclass(frozen=True)
class RegimeClassification:
    """
    Classification of an ObservationSnapshot against the regime taxonomy.

    Fields:
        regime: Nearest regime name
        nearest_regime: Nearest regime name (same as regime)
        second_nearest_regime: Second-nearest regime name
        distance_1: Distance to nearest regime (Euclidean with size penalty)
        distance_2: Distance to second-nearest regime
        structural_distance_1: Distance without size penalty (pure metrics)
        margin: distance_2 - distance_1 (higher = more decisive)
        confidence: observation_quality * (1 - distance_1) [0, 1]
        observation: The original snapshot (reference, not copy)
        all_distances: List of (str, float) for all regimes sorted asc
    """

    regime: RegimeName
    nearest_regime: RegimeName
    second_nearest_regime: RegimeName
    distance_1: float
    distance_2: float
    structural_distance_1: float = 0.0
    margin: float = 0.0
    confidence: float = 0.0
    observation: ObservationSnapshot = field(default_factory=lambda: ObservationSnapshot())  # type: ignore[arg-type]
    all_distances: List[Tuple[str, float]] = field(default_factory=list)

    def is_confident(self, threshold: float = 0.7) -> bool:
        """Confidence meets or exceeds threshold."""
        return self.confidence >= threshold

    def has_margin(self, threshold: float = 0.1) -> bool:
        """Margin meets or exceeds threshold."""
        return self.margin >= threshold


def classify_from_snapshot(
    snapshot: ObservationSnapshot,
    graph_size: Optional[int] = None,
    size_mode: str = "synthetic",
) -> RegimeClassification:
    """
    Classify an ObservationSnapshot into the nearest regime(s).

    Parameters:
        snapshot: ObservationSnapshot to classify
        graph_size: Optional override for graph size (defaults to snapshot.total_nodes)
        size_mode: "synthetic" (targets 6/20/50) or "real" (log-scale targets)

    Returns:
        RegimeClassification with nearest and second-nearest regimes

    Note:
        ``structural_distance_1`` excludes the size penalty entirely,
        measuring only how well the 4 structural metrics fit each
        regime. This is useful for real-world projects where the
        synthetic size targets (6/20/50) are not meaningful.
    """
    if graph_size is None:
        graph_size = snapshot.total_nodes

    cross = snapshot.cross_domain_ratio
    intra = snapshot.intra_domain_ratio
    leakage = snapshot.file_level_leakage
    cycles = snapshot.cycle_density

    distances: List[Tuple[str, float]] = []

    for name, rng in REGIME_TAXONOMY.items():
        d = _distance_to_regime(cross, intra, leakage, cycles, graph_size, rng, size_mode)
        distances.append((name.value, d))

    distances.sort(key=lambda x: x[1])

    nearest_name = distances[0][0]
    second_name = distances[1][0]
    d1 = distances[0][1]
    d2 = distances[1][1]
    margin = d2 - d1

    conf = snapshot.observation_quality * (1.0 / (1.0 + d1))

    # Structural distance: same regime centroids but no size penalty
    struct_distances: List[Tuple[str, float]] = []
    for name, rng in REGIME_TAXONOMY.items():
        sd = _structural_distance_to_regime(cross, intra, leakage, cycles, rng)
        struct_distances.append((name.value, sd))
    struct_distances.sort(key=lambda x: x[1])
    struct_d1 = struct_distances[0][1]

    return RegimeClassification(
        regime=RegimeName(nearest_name),
        nearest_regime=RegimeName(nearest_name),
        second_nearest_regime=RegimeName(second_name),
        distance_1=d1,
        distance_2=d2,
        structural_distance_1=struct_d1,
        margin=margin,
        confidence=conf,
        observation=snapshot,
        all_distances=distances,
    )


def _structural_distance_to_regime(cross: float, intra: float, leakage: float, cycles: float, rng) -> float:
    """Euclidean distance using only structural metrics (no size)."""
    def _d(val: float, bounds: Tuple[float, float]) -> float:
        mid = (bounds[0] + bounds[1]) / 2
        width = bounds[1] - bounds[0]
        return abs(val - mid) / max(width, 0.01)

    return (
        _d(cross, rng.cross_domain_ratio) ** 2
        + _d(intra, rng.intra_domain_ratio) ** 2
        + _d(leakage, rng.file_level_leakage) ** 2
        + _d(cycles, rng.cycle_density) ** 2
    ) ** 0.5


# ---------------------------------------------------------------------------
# Internal helpers (mirror ags/synthetic/regimes.py _distance_to_range)
# ---------------------------------------------------------------------------


def _size_distance(graph_size: int, size_class: str, mode: str = "synthetic") -> float:
    """
    Penalize mismatch between observed size and size_class.

    Modes:
        "synthetic" — targets 6/20/50 for SMALL/MEDIUM/LARGE (C0.0 compatible).
        "real" — log-scale targets for real-world projects (C1.0+).
    """
    if mode == "real":
        import math
        targets = {"SMALL": math.log(15), "MEDIUM": math.log(60), "LARGE": math.log(500)}
        target = targets[size_class]
        return abs(math.log(graph_size + 1) - target) / math.log(2)
    else:
        if size_class == "SMALL":
            target = 6
        elif size_class == "MEDIUM":
            target = 20
        else:  # LARGE
            target = 50
        return abs(graph_size - target) / 20.0


def _distance_to_regime(
    cross: float,
    intra: float,
    leakage: float,
    cycles: float,
    graph_size: int,
    rng,
    size_mode: str = "synthetic",
) -> float:
    """Euclidean distance from point to regime midpoint, normalized."""
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
    size_dist = _size_distance(graph_size, rng.size_class, mode=size_mode) ** 2

    return (metric_dist + size_dist) ** 0.5
