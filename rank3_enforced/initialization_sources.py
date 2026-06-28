from __future__ import annotations

from dataclasses import asdict
import math
import numpy as np

from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash
from .initialization_trace import InitializationSourceTrace
from .overlay_schema import InitializationSpec, SupportSpec


INITIALIZATION_SOURCE_RULES = {
    "zero_vacuum",
    "explicit_phi",
    "balanced_boundary_dressing_lift_v0_1",
    "balanced_boundary_dressing_two_ledger_lift_v0_1",
    "neutral_boundary_dressing_two_ledger_lift_v0_1",
    "phase_active_dressing_lift_v0_1",
    "phase_active_boundary_lift_v0_1",
}


def _support_declared_sites(supports: tuple[SupportSpec, ...]) -> set[int]:
    points: set[int] = set()
    for support in supports:
        points.update(int(i) for i in support.support_points)
        points.update(int(i) for i in support.boundary_points)
        points.update(int(i) for i in support.dressing_points)
        points.update(int(i) for i in support.active_phase_map.values())
    return points


def _handedness_sign(handedness: str | None) -> float:
    if handedness is None:
        return 1.0
    lowered = handedness.lower().strip()
    if lowered == "right":
        return 1.0
    if lowered == "left":
        return -1.0
    raise ManifestError(f"Unsupported support handedness: {handedness!r}")


def _validate_indices(indices: tuple[int, ...], *, n_points: int, label: str) -> None:
    for index in indices:
        if index < 0 or index >= n_points:
            raise ManifestError(f"{label} contains out-of-range point {index}.")


def build_initialization_source_array(
    *,
    initialization: InitializationSpec,
    supports: tuple[SupportSpec, ...],
    n_points: int,
) -> tuple[np.ndarray, InitializationSourceTrace]:
    """Build a sealed initialization source vector from declarative support records.

    This is data-only and registry-driven. It does not inspect model outputs and
    does not create primitive association geometry.
    """

    source = np.zeros(n_points, dtype=np.float64)
    mode = initialization.mode
    source_rule = initialization.source_rule or "zero_vacuum"
    amplitude = float(initialization.amplitude)

    if not math.isfinite(amplitude) or amplitude < 0.0:
        raise ManifestError("initialization.amplitude must be a finite non-negative number.")

    if source_rule not in INITIALIZATION_SOURCE_RULES:
        raise ManifestError(f"Unknown locked initialization source_rule: {source_rule}")

    if mode == "vacuum_zero":
        if source_rule not in ("zero_vacuum", None):
            raise ManifestError("vacuum_zero initialization must use source_rule='zero_vacuum'.")
    elif mode == "explicit_phi":
        if source_rule not in ("explicit_phi", "zero_vacuum", None):
            raise ManifestError("explicit_phi initialization may not use a support source rule.")
    elif mode in ("support_seeded", "support_seeded_two_ledger"):
        if not supports:
            raise ManifestError("support_seeded initialization requires declared supports.")
        if source_rule in ("zero_vacuum", "explicit_phi", None):
            raise ManifestError("support_seeded initialization requires a locked support source_rule.")
    else:
        raise ManifestError(f"Unsupported initialization.mode: {mode}")

    if mode in ("support_seeded", "support_seeded_two_ledger"):
        for support in supports:
            _validate_indices(support.support_points, n_points=n_points, label=f"support {support.name} support_points")
            _validate_indices(support.boundary_points, n_points=n_points, label=f"support {support.name} boundary_points")
            _validate_indices(support.dressing_points, n_points=n_points, label=f"support {support.name} dressing_points")
            sign = _handedness_sign(support.handedness)

            if source_rule in ("balanced_boundary_dressing_lift_v0_1", "balanced_boundary_dressing_two_ledger_lift_v0_1", "neutral_boundary_dressing_two_ledger_lift_v0_1"):
                if not support.boundary_points or not support.dressing_points:
                    raise ManifestError(
                        f"Support {support.name!r} requires boundary_points and dressing_points "
                        "for balanced_boundary_dressing_lift_v0_1/two_ledger variants."
                    )
                if len(support.boundary_points) != len(support.dressing_points):
                    raise ManifestError(
                        f"Support {support.name!r} must have equal boundary/dressing counts "
                        "for balanced_boundary_dressing_lift_v0_1/two_ledger variants."
                    )
                if initialization.start_sites not in ("boundary_and_dressing_points",):
                    raise ManifestError(
                        "balanced_boundary_dressing_lift_v0_1 requires "
                        "start_sites='boundary_and_dressing_points'."
                    )
                for boundary, dressing in zip(support.boundary_points, support.dressing_points):
                    if source_rule == "neutral_boundary_dressing_two_ledger_lift_v0_1":
                        # Neutral support seed: balanced internal boundary/dressing lift
                        # with no handed charge-facing reversal. This is a role seed,
                        # not a gravity claim.
                        source[int(boundary)] += amplitude
                        source[int(dressing)] += -amplitude
                    else:
                        source[int(boundary)] += sign * amplitude
                        source[int(dressing)] += -sign * amplitude

            elif source_rule == "phase_active_dressing_lift_v0_1":
                if initialization.start_sites != "dressing_points":
                    raise ManifestError(
                        "phase_active_dressing_lift_v0_1 requires start_sites='dressing_points'."
                    )
                if set(support.active_phase_map.keys()) != {0, 1, 2}:
                    raise ManifestError(
                        f"Support {support.name!r} needs active_phase_map for phases 0,1,2."
                    )
                for point in support.active_phase_map.values():
                    source[int(point)] += sign * amplitude

            elif source_rule == "phase_active_boundary_lift_v0_1":
                if initialization.start_sites != "boundary_points":
                    raise ManifestError(
                        "phase_active_boundary_lift_v0_1 requires start_sites='boundary_points'."
                    )
                if len(support.boundary_points) < 3:
                    raise ManifestError(
                        f"Support {support.name!r} needs at least 3 boundary_points for phase-active boundary lift."
                    )
                for point in support.boundary_points[:3]:
                    source[int(point)] += sign * amplitude

            else:
                raise ManifestError(f"Unsupported support source_rule: {source_rule}")

    support_sites = _support_declared_sites(supports)
    support_nonzero_count = sum(1 for i in support_sites if abs(float(source[i])) > 0.0)
    vacuum_nonzero_count = sum(
        1 for i, value in enumerate(source) if i not in support_sites and abs(float(value)) > 0.0
    )
    nonzero_count = int(np.count_nonzero(source))

    nonzero_passed = True
    if initialization.require_nonzero_support_activation:
        nonzero_passed = support_nonzero_count > 0 and nonzero_count > 0

    vacuum_passed = True
    if initialization.require_vacuum_zero_elsewhere:
        vacuum_passed = vacuum_nonzero_count == 0

    passed = bool(nonzero_passed and vacuum_passed)
    support_hash = stable_json_hash([asdict(support) for support in supports])
    source_hash = array_hash(source)

    trace = InitializationSourceTrace(
        mode=mode,
        start_sites=initialization.start_sites,
        source_rule=source_rule,
        source_hash=source_hash,
        support_hash=support_hash,
        source_l1=float(np.sum(np.abs(source))),
        source_l2=float(np.linalg.norm(source)),
        nonzero_count=nonzero_count,
        support_nonzero_count=int(support_nonzero_count),
        vacuum_nonzero_count=int(vacuum_nonzero_count),
        require_nonzero_support_activation=bool(initialization.require_nonzero_support_activation),
        require_vacuum_zero_elsewhere=bool(initialization.require_vacuum_zero_elsewhere),
        passed=passed,
        details={
            "source_rule": source_rule,
            "amplitude": amplitude,
            "support_sites": sorted(int(i) for i in support_sites),
            "nonzero_passed": nonzero_passed,
            "vacuum_passed": vacuum_passed,
        },
    )
    return source, trace
