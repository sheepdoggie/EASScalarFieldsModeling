from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Sequence

import numpy as np

import scalar_field_geometry as sfg
from .exceptions import ManifestError
from .fingerprints import stable_json_hash


@dataclass(frozen=True)
class ExplicitPathConstructionReport:
    """Locked report for an explicitly constructed support-to-support path.

    path_length is interpreted conservatively as the number of declared path
    positions in path_points. The completed directed graph distance from the
    left support anchor to the right support anchor is separately reported.
    """

    rule: str
    path_length: int
    path_points: tuple[int, ...]
    orientation: str
    left_support: str
    right_support: str
    left_anchor: int
    right_anchor: int
    path_slot: int
    reverse_slot: int
    support_anchor_graph_distance_edges: int
    semantics: str = "path_length_counts_declared_path_positions"

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def _all_support_indices(supports: Sequence[object]) -> set[int]:
    indices: set[int] = set()
    for support in supports:
        for attr in ("support_points", "boundary_points", "dressing_points"):
            for point in getattr(support, attr, ()):
                indices.add(int(point))
        for point in getattr(support, "active_phase_map", {}).values():
            indices.add(int(point))
    return indices


def _support_by_name(supports: Sequence[object], name: str) -> object:
    for support in supports:
        if getattr(support, "name", None) == name:
            return support
    raise ManifestError(f"Unknown support in path_construction: {name!r}")


def _anchor_for_support(support: object) -> int:
    active_map = getattr(support, "active_phase_map", {})
    if active_map:
        # Phase 0 is used as the locked construction anchor. Phase-specific
        # support activation remains governed by the SOO/init layers.
        if 0 in active_map:
            return int(active_map[0])
        return int(active_map[sorted(active_map)[0]])
    for attr in ("dressing_points", "boundary_points", "support_points"):
        values = tuple(getattr(support, attr, ()))
        if values:
            return int(values[0])
    raise ManifestError(f"Support {getattr(support, 'name', '<unnamed>')!r} has no usable anchor point.")


def _default_path_points(*, n_points: int, supports: Sequence[object], path_length: int) -> tuple[int, ...]:
    blocked = _all_support_indices(supports)
    candidates = [point for point in range(n_points) if point not in blocked]
    if len(candidates) < path_length:
        raise ManifestError(
            "Not enough non-support points to construct explicit path: "
            f"need {path_length}, available {len(candidates)}. Provide path_points explicitly or increase n_points."
        )
    return tuple(candidates[:path_length])


def _base_cyclic_assoc(n_points: int) -> np.ndarray:
    assoc = np.zeros((n_points, 3), dtype=np.int64)
    for i in range(n_points):
        assoc[i, 0] = (i + 1) % n_points
        assoc[i, 1] = (i + 2) % n_points
        assoc[i, 2] = (i + 3) % n_points
    return assoc


def _complete_row(*, source: int, preferred: Sequence[int], n_points: int, allow_self_association: bool) -> tuple[int, int, int]:
    row: list[int] = []
    for raw_target in preferred:
        target = int(raw_target)
        if target < 0 or target >= n_points:
            raise ManifestError(f"Path construction target out of range: {target}")
        if not allow_self_association and target == source:
            continue
        if target not in row:
            row.append(target)
        if len(row) == 3:
            return tuple(row)  # type: ignore[return-value]
    for target in range(n_points):
        if not allow_self_association and target == source:
            continue
        if target not in row:
            row.append(target)
        if len(row) == 3:
            return tuple(row)  # type: ignore[return-value]
    raise ManifestError(f"Unable to complete rank-3 association row for source {source}.")


def _validate_path_points(*, path_points: Sequence[int], n_points: int, supports: Sequence[object], allow_support_overlap: bool) -> tuple[int, ...]:
    points = tuple(int(p) for p in path_points)
    if not points:
        raise ManifestError("linear_support_path_v0_1 requires at least one path point.")
    if len(set(points)) != len(points):
        raise ManifestError("path_construction.path_points contains duplicates.")
    for point in points:
        if point < 0 or point >= n_points:
            raise ManifestError(f"path_construction point out of range: {point}")
    if not allow_support_overlap:
        overlap = sorted(set(points) & _all_support_indices(supports))
        if overlap:
            raise ManifestError(
                "path_construction.path_points may not overlap support-owned points unless "
                f"allow_support_overlap=true. overlap={overlap}"
            )
    return points



def _cycle_permutation_from_order(order: Sequence[int]) -> dict[int, int]:
    return {int(order[i]): int(order[(i + 1) % len(order)]) for i in range(len(order))}


def _inverse_permutation(perm: dict[int, int]) -> dict[int, int]:
    return {int(v): int(k) for k, v in perm.items()}


def _third_permutation(*, n_points: int, slot0: dict[int, int], slot1: dict[int, int]) -> dict[int, int]:
    points = list(range(n_points))
    for shift in range(2, n_points):
        candidate = {i: points[(i + shift) % n_points] for i in points}
        if all(candidate[i] != i and candidate[i] not in {slot0[i], slot1[i]} for i in points):
            return candidate
    # Deterministic fallback search. n_points in locked candidate tests is large enough
    # that this should not be reached; fail closed instead of fabricating invalid rank-3 rows.
    raise ManifestError("Unable to construct third permutation slot with distinct non-self targets.")


def _permutation_path_assoc_v0_2(
    *,
    n_points: int,
    left_anchor: int,
    right_anchor: int,
    path_points: Sequence[int],
    path_slot: int,
    reverse_slot: int,
) -> np.ndarray:
    path_set = set(int(p) for p in path_points) | {int(left_anchor), int(right_anchor)}
    rest = [p for p in range(n_points) if p not in path_set]
    forward_order = [int(left_anchor), *[int(p) for p in path_points], int(right_anchor), *rest]
    if len(set(forward_order)) != n_points:
        raise ManifestError("linear_support_path_v0_2 failed to form a full point permutation.")
    perm_path = _cycle_permutation_from_order(forward_order)
    perm_reverse = _inverse_permutation(perm_path)
    perm_third = _third_permutation(n_points=n_points, slot0=perm_path, slot1=perm_reverse)
    slot_maps = [None, None, None]
    slot_maps[path_slot] = perm_path
    slot_maps[reverse_slot] = perm_reverse
    third_slot = ({0, 1, 2} - {path_slot, reverse_slot}).pop()
    slot_maps[third_slot] = perm_third
    assoc = np.zeros((n_points, 3), dtype=np.int64)
    for i in range(n_points):
        assoc[i, 0] = slot_maps[0][i]  # type: ignore[index]
        assoc[i, 1] = slot_maps[1][i]  # type: ignore[index]
        assoc[i, 2] = slot_maps[2][i]  # type: ignore[index]
    sfg.validate_association_array(assoc, allow_self_association=False)
    return assoc


def _role_path_two_support_assoc_v0_1(
    *,
    n_points: int,
    left_support: object,
    right_support: object,
    left_anchor: int,
    right_anchor: int,
    path_points: Sequence[int],
    allow_self_association: bool,
) -> np.ndarray:
    """Construct a role/path-preserving two-support path geometry.

    This construction exists so role/path remap tests do not have to misuse the
    older permutation path constructor. Dressing endpoint slot 0 remains
    boundary-facing, slot 1 is path-facing, and slot 2 is vacuum-facing. Path
    nodes use slot 0 toward the left endpoint, slot 1 toward the right endpoint,
    and slot 2 as a non-path/vacuum-facing completion.
    """
    assoc = _base_cyclic_assoc(n_points)
    left_boundaries = tuple(int(x) for x in getattr(left_support, "boundary_points", ()))
    right_boundaries = tuple(int(x) for x in getattr(right_support, "boundary_points", ()))
    left_dressings = tuple(int(x) for x in getattr(left_support, "dressing_points", ()))
    right_dressings = tuple(int(x) for x in getattr(right_support, "dressing_points", ()))
    if not left_boundaries or not right_boundaries:
        raise ManifestError("role_path_two_support_v0_1 requires boundary_points on both supports.")
    if left_anchor not in left_dressings or right_anchor not in right_dressings:
        raise ManifestError("role_path_two_support_v0_1 anchors must be dressing points.")

    support_and_path = set(_all_support_indices((left_support, right_support))) | set(int(x) for x in path_points)
    vacuum_candidates = [p for p in range(n_points) if p not in support_and_path]
    if len(vacuum_candidates) < 3:
        raise ManifestError("role_path_two_support_v0_1 requires at least three non-support/non-path vacuum completion points.")

    def vac(index: int) -> int:
        return int(vacuum_candidates[index % len(vacuum_candidates)])

    # Boundary rows remain bounded/support-facing; deterministic completion only.
    for support in (left_support, right_support):
        boundaries = tuple(int(x) for x in getattr(support, "boundary_points", ()))
        dressings = tuple(int(x) for x in getattr(support, "dressing_points", ()))
        for i, b in enumerate(boundaries[:3]):
            preferred = (boundaries[(i + 1) % len(boundaries)], boundaries[(i - 1) % len(boundaries)], dressings[i % len(dressings)])
            assoc[b, :] = np.asarray(_complete_row(source=b, preferred=preferred, n_points=n_points, allow_self_association=allow_self_association), dtype=np.int64)
        for i, d in enumerate(dressings[:3]):
            # All dressing points have a fixed boundary-facing slot 0. Only the
            # phase-0 anchors get the explicit inter-support path in slot 1.
            boundary = boundaries[i % len(boundaries)]
            path_target = path_points[0] if d == left_anchor else (path_points[-1] if d == right_anchor else vac(i + 5))
            preferred = (boundary, path_target, vac(i))
            row = [int(preferred[0]), int(preferred[1]), int(preferred[2])]
            if len(set(row)) != 3 or (not allow_self_association and d in row):
                row = list(_complete_row(source=d, preferred=preferred, n_points=n_points, allow_self_association=allow_self_association))
                row[0] = int(boundary)
                row[1] = int(path_target)
                if len(set(row)) != 3 or (not allow_self_association and d in row):
                    row = list(_complete_row(source=d, preferred=(boundary, path_target, vac(i)), n_points=n_points, allow_self_association=allow_self_association))
            assoc[d, :] = np.asarray(row, dtype=np.int64)

    # Ordered relational path: slot 0 toward left, slot 1 toward right, slot 2 vacuum.
    for index, point in enumerate(path_points):
        leftward = left_anchor if index == 0 else path_points[index - 1]
        rightward = right_anchor if index == len(path_points) - 1 else path_points[index + 1]
        row = [int(leftward), int(rightward), vac(index + 17)]
        if len(set(row)) != 3 or (not allow_self_association and int(point) in row):
            row = list(_complete_row(source=int(point), preferred=(leftward, rightward, vac(index + 17)), n_points=n_points, allow_self_association=allow_self_association))
            row[0] = int(leftward)
            row[1] = int(rightward)
            if len(set(row)) != 3 or (not allow_self_association and int(point) in row):
                raise ManifestError("role_path_two_support_v0_1 could not complete a path row with distinct targets.")
        assoc[int(point), :] = np.asarray(row, dtype=np.int64)

    return assoc

def build_explicit_path_association_state(
    *,
    n_points: int,
    path_spec: object,
    supports: Sequence[object],
    allow_self_association: bool = False,
) -> tuple[sfg.FrozenAssociationState, ExplicitPathConstructionReport]:
    """Build G_0 from a locked explicit linear support-path construction.

    This is a registry construction rule, not overlay Python. It creates a
    full valid rank-3 association table and records the declared path points and
    support anchors for locked center/readout rules.
    """

    rule = str(getattr(path_spec, "rule", "none"))
    if rule not in ("linear_support_path_v0_1", "linear_support_path_v0_2", "role_path_two_support_v0_1"):
        raise ManifestError(f"Unsupported explicit path construction rule: {rule}")
    if len(supports) < 2:
        raise ManifestError("linear_support_path_v0_1 requires at least two supports.")

    left_name = getattr(path_spec, "left_support", None) or getattr(supports[0], "name")
    right_name = getattr(path_spec, "right_support", None) or getattr(supports[1], "name")
    left_support = _support_by_name(supports, str(left_name))
    right_support = _support_by_name(supports, str(right_name))
    left_anchor = _anchor_for_support(left_support)
    right_anchor = _anchor_for_support(right_support)
    if left_anchor == right_anchor:
        raise ManifestError("Explicit path construction requires distinct left/right anchors.")

    path_length = int(getattr(path_spec, "path_length", 0))
    if path_length < 1:
        raise ManifestError("path_construction.path_length must be at least 1.")

    raw_path_points = tuple(getattr(path_spec, "path_points", ()))
    if raw_path_points:
        path_points = _validate_path_points(
            path_points=raw_path_points,
            n_points=n_points,
            supports=supports,
            allow_support_overlap=bool(getattr(path_spec, "allow_support_overlap", False)),
        )
        if len(path_points) != path_length:
            raise ManifestError(
                f"path_construction.path_length={path_length} but len(path_points)={len(path_points)}."
            )
    else:
        path_points = _default_path_points(n_points=n_points, supports=supports, path_length=path_length)

    path_slot = int(getattr(path_spec, "path_slot", 0)) % 3
    reverse_slot = int(getattr(path_spec, "reverse_slot", 1)) % 3
    if path_slot == reverse_slot:
        raise ManifestError("path_slot and reverse_slot must be distinct slots.")

    if rule == "linear_support_path_v0_2":
        if allow_self_association:
            raise ManifestError("linear_support_path_v0_2 does not allow self-association; permutation slots require distinct non-self targets.")
        assoc = _permutation_path_assoc_v0_2(
            n_points=n_points,
            left_anchor=left_anchor,
            right_anchor=right_anchor,
            path_points=path_points,
            path_slot=path_slot,
            reverse_slot=reverse_slot,
        )
    elif rule == "role_path_two_support_v0_1":
        assoc = _role_path_two_support_assoc_v0_1(
            n_points=n_points,
            left_support=left_support,
            right_support=right_support,
            left_anchor=left_anchor,
            right_anchor=right_anchor,
            path_points=path_points,
            allow_self_association=allow_self_association,
        )
    else:
        assoc = _base_cyclic_assoc(n_points)

        # Support anchors connect into the declared path.
        assoc[left_anchor, :] = np.asarray(
            _complete_row(
                source=left_anchor,
                preferred=(path_points[0],),
                n_points=n_points,
                allow_self_association=allow_self_association,
            ),
            dtype=np.int64,
        )
        assoc[right_anchor, :] = np.asarray(
            _complete_row(
                source=right_anchor,
                preferred=(path_points[-1],),
                n_points=n_points,
                allow_self_association=allow_self_association,
            ),
            dtype=np.int64,
        )

        # Linear directed path; completed/undirected reports expose the reverse path.
        for index, point in enumerate(path_points):
            forward = path_points[index + 1] if index + 1 < len(path_points) else right_anchor
            backward = path_points[index - 1] if index > 0 else left_anchor
            row = [None, None, None]
            row[path_slot] = int(forward)
            row[reverse_slot] = int(backward)
            preferred = [x for x in row if x is not None]
            completed = list(
                _complete_row(
                    source=int(point),
                    preferred=preferred,
                    n_points=n_points,
                    allow_self_association=allow_self_association,
                )
            )
            # Preserve requested slots for path/reverse where validation permits.
            completed[path_slot] = int(forward)
            completed[reverse_slot] = int(backward)
            # Re-complete if slot placement introduced duplication.
            if len(set(completed)) != 3 or (not allow_self_association and int(point) in completed):
                completed = list(
                    _complete_row(
                        source=int(point),
                        preferred=(int(forward), int(backward)),
                        n_points=n_points,
                        allow_self_association=allow_self_association,
                    )
                )
            assoc[int(point), :] = np.asarray(completed, dtype=np.int64)

    metadata = {
        "path_construction_rule": rule,
        "path_length": path_length,
        "path_points": path_points,
        "orientation": str(getattr(path_spec, "orientation", "unspecified")),
        "left_support": str(left_name),
        "right_support": str(right_name),
        "left_anchor": left_anchor,
        "right_anchor": right_anchor,
        "path_slot": path_slot,
        "reverse_slot": reverse_slot,
        "semantics": "path_length_counts_declared_path_positions",
    }
    fingerprint = sfg.association_fingerprint(
        assoc=assoc,
        step=0,
        rule_name=f"path_construction::{rule}",
        parent_fingerprint=None,
        metadata=metadata,
    )
    state = sfg.FrozenAssociationState(
        assoc=assoc,
        step=0,
        rule_name=f"path_construction::{rule}",
        fingerprint=fingerprint,
        parent_fingerprint=None,
        metadata=metadata,
        allow_self_association=allow_self_association,
    )
    report = ExplicitPathConstructionReport(
        rule=rule,
        path_length=path_length,
        path_points=path_points,
        orientation=str(getattr(path_spec, "orientation", "unspecified")),
        left_support=str(left_name),
        right_support=str(right_name),
        left_anchor=left_anchor,
        right_anchor=right_anchor,
        path_slot=path_slot,
        reverse_slot=reverse_slot,
        support_anchor_graph_distance_edges=path_length + 1,
    )
    return state, report
