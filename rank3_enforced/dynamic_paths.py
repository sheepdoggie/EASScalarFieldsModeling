from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Literal, Mapping, Sequence

import numpy as np

from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash

PathChangeKind = Literal["none", "shorten", "lengthen"]  # deprecated for intrinsic rules; v0.1.23 uses external monitor requests.


@dataclass(frozen=True)
class RelationalPathRecord:
    """Declarative identity record for one ordered relational path lane.

    The record is a framework data object. It does not by itself claim that a
    path length change has occurred. It gives remap/path-change rules a locked,
    auditable object rather than forcing them to infer path identity from raw
    association rows or from test labels.
    """

    path_id: str
    left_endpoint: int
    right_endpoint: int
    ordered_nodes: tuple[int, ...]
    left_support_id: str = "left"
    right_support_id: str = "right"
    lane_id: str = "0"
    phase_role: int | None = None

    def __post_init__(self) -> None:
        if not self.path_id:
            raise ManifestError("RelationalPathRecord requires path_id.")
        nodes = tuple(int(x) for x in self.ordered_nodes)
        if len(nodes) < 1:
            raise ManifestError(f"Path {self.path_id!r} requires at least one ordered node.")
        all_points = (int(self.left_endpoint), int(self.right_endpoint), *nodes)
        if any(p < 0 for p in all_points):
            raise ManifestError(f"Path {self.path_id!r} contains a negative point index.")
        if len(set(all_points)) != len(all_points):
            raise ManifestError(f"Path {self.path_id!r} contains duplicate endpoint/path points.")
        object.__setattr__(self, "left_endpoint", int(self.left_endpoint))
        object.__setattr__(self, "right_endpoint", int(self.right_endpoint))
        object.__setattr__(self, "ordered_nodes", nodes)
        if self.phase_role is not None:
            object.__setattr__(self, "phase_role", int(self.phase_role) % 3)

    @property
    def path_length(self) -> int:
        return len(self.ordered_nodes)

    @property
    def parity(self) -> str:
        return "odd" if self.path_length % 2 else "even"

    @property
    def center_nodes(self) -> tuple[int, ...]:
        L = self.path_length
        if L % 2:
            return (self.ordered_nodes[L // 2],)
        return (self.ordered_nodes[L // 2 - 1], self.ordered_nodes[L // 2])

    def node_after_left_endpoint(self) -> int:
        return self.ordered_nodes[0]

    def node_before_right_endpoint(self) -> int:
        return self.ordered_nodes[-1]

    def neighbor_toward_right(self, point: int) -> int:
        point = int(point)
        if point == self.right_endpoint:
            return self.right_endpoint
        if point == self.left_endpoint:
            return self.ordered_nodes[0]
        if point in self.ordered_nodes:
            i = self.ordered_nodes.index(point)
            return self.right_endpoint if i == len(self.ordered_nodes) - 1 else self.ordered_nodes[i + 1]
        raise ManifestError(f"Point {point} is not on path {self.path_id!r}.")

    def neighbor_toward_left(self, point: int) -> int:
        point = int(point)
        if point == self.left_endpoint:
            return self.left_endpoint
        if point == self.right_endpoint:
            return self.ordered_nodes[-1]
        if point in self.ordered_nodes:
            i = self.ordered_nodes.index(point)
            return self.left_endpoint if i == 0 else self.ordered_nodes[i - 1]
        raise ManifestError(f"Point {point} is not on path {self.path_id!r}.")

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class DressingRoleMap:
    """Role map for dressing associations.

    Numeric slots are secondary. The ontology-facing constraint is role based:
    boundary-facing association is fixed; the other two slots carry path-facing
    and vacuum-facing roles and may exchange if explicitly enabled.
    """

    point: int
    boundary_slot: int
    path_slot: int
    vacuum_slot: int
    path_id: str
    endpoint_side: Literal["left", "right"]
    allow_path_vacuum_exchange: bool = False

    def __post_init__(self) -> None:
        slots = (int(self.boundary_slot), int(self.path_slot), int(self.vacuum_slot))
        if any(s not in (0, 1, 2) for s in slots):
            raise ManifestError("DressingRoleMap slots must be 0, 1, or 2.")
        if len(set(slots)) != 3:
            raise ManifestError("DressingRoleMap boundary/path/vacuum slots must be distinct.")
        if self.endpoint_side not in ("left", "right"):
            raise ManifestError("DressingRoleMap endpoint_side must be 'left' or 'right'.")
        object.__setattr__(self, "point", int(self.point))
        object.__setattr__(self, "boundary_slot", slots[0])
        object.__setattr__(self, "path_slot", slots[1])
        object.__setattr__(self, "vacuum_slot", slots[2])

    def exchanged(self) -> "DressingRoleMap":
        if not self.allow_path_vacuum_exchange:
            return self
        return replace(self, path_slot=self.vacuum_slot, vacuum_slot=self.path_slot)

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class GeometryTransactionReport:
    report_schema: str
    operation_id: str
    operation_kind: str
    applied: bool
    association_before_hash: str
    association_after_hash: str
    scalar_values_moved: bool
    affected_points: tuple[int, ...]
    validation: dict[str, Any]
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class PathChangeAdmission:
    """Deprecated internal gate record retained for archive compatibility.

    v0.1.23 no longer treats path length changes as framework-intrinsic EAS
    rules. New exploratory path edits should use external_path_monitor.py, where
    an external monitor explicitly requests add/remove operations and the
    framework only validates/logs the transaction.
    """

    admitted: bool
    reason: str
    scalar_condition: str = "not_evaluated"
    phase_complete: bool = False
    negative_controls_passed: bool = False
    label_independence_checked: bool = False

    def require_admitted(self, operation: str) -> None:
        if not self.admitted:
            raise ManifestError(f"Path change {operation!r} rejected: {self.reason}")
        if not self.phase_complete:
            raise ManifestError(f"Path change {operation!r} rejected: phase completeness not established.")
        if not self.negative_controls_passed:
            raise ManifestError(f"Path change {operation!r} rejected: negative controls not established.")
        if not self.label_independence_checked:
            raise ManifestError(f"Path change {operation!r} rejected: label independence not checked.")

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class PathMutationResult:
    path_before: RelationalPathRecord
    path_after: RelationalPathRecord
    association_after: np.ndarray
    transaction_report: GeometryTransactionReport


def _path_map(paths: Sequence[RelationalPathRecord]) -> dict[str, RelationalPathRecord]:
    out: dict[str, RelationalPathRecord] = {}
    for path in paths:
        if path.path_id in out:
            raise ManifestError(f"Duplicate path_id: {path.path_id!r}")
        out[path.path_id] = path
    return out


def parse_relational_paths(raw_paths: Any) -> tuple[RelationalPathRecord, ...]:
    if raw_paths is None:
        return ()
    if not isinstance(raw_paths, list):
        raise ManifestError("path_records must be a list of path record objects.")
    paths: list[RelationalPathRecord] = []
    for raw in raw_paths:
        if not isinstance(raw, dict):
            raise ManifestError("Each path record must be an object.")
        paths.append(RelationalPathRecord(
            path_id=str(raw["path_id"]),
            left_endpoint=int(raw["left_endpoint"]),
            right_endpoint=int(raw["right_endpoint"]),
            ordered_nodes=tuple(int(x) for x in raw["ordered_nodes"]),
            left_support_id=str(raw.get("left_support_id", "left")),
            right_support_id=str(raw.get("right_support_id", "right")),
            lane_id=str(raw.get("lane_id", raw.get("path_id", "0"))),
            phase_role=(None if raw.get("phase_role") is None else int(raw.get("phase_role"))),
        ))
    _path_map(paths)
    return tuple(paths)


def parse_dressing_role_maps(raw_roles: Any) -> tuple[DressingRoleMap, ...]:
    if raw_roles is None:
        return ()
    if not isinstance(raw_roles, list):
        raise ManifestError("dressing_roles must be a list of role-map objects.")
    roles: list[DressingRoleMap] = []
    seen: set[int] = set()
    for raw in raw_roles:
        if not isinstance(raw, dict):
            raise ManifestError("Each dressing role map must be an object.")
        role = DressingRoleMap(
            point=int(raw["point"]),
            boundary_slot=int(raw["boundary_slot"]),
            path_slot=int(raw["path_slot"]),
            vacuum_slot=int(raw["vacuum_slot"]),
            path_id=str(raw["path_id"]),
            endpoint_side=str(raw["endpoint_side"]),  # type: ignore[arg-type]
            allow_path_vacuum_exchange=bool(raw.get("allow_path_vacuum_exchange", False)),
        )
        if role.point in seen:
            raise ManifestError(f"Duplicate dressing role point: {role.point}")
        seen.add(role.point)
        roles.append(role)
    return tuple(roles)


def validate_role_paths(*, assoc: np.ndarray, paths: Sequence[RelationalPathRecord], roles: Sequence[DressingRoleMap]) -> None:
    assoc = np.asarray(assoc, dtype=np.int64)
    if assoc.ndim != 2 or assoc.shape[1] != 3:
        raise ManifestError("Role/path validation requires an (n,3) association table.")
    n = int(assoc.shape[0])
    path_by_id = _path_map(paths)
    for path in paths:
        all_points = (path.left_endpoint, path.right_endpoint, *path.ordered_nodes)
        if any(p < 0 or p >= n for p in all_points):
            raise ManifestError(f"Path {path.path_id!r} contains out-of-bounds points.")
    for role in roles:
        if role.point < 0 or role.point >= n:
            raise ManifestError(f"Dressing role point out of bounds: {role.point}")
        path = path_by_id.get(role.path_id)
        if path is None:
            raise ManifestError(f"Dressing role references unknown path_id: {role.path_id!r}")
        expected_endpoint = path.left_endpoint if role.endpoint_side == "left" else path.right_endpoint
        if role.point != expected_endpoint:
            raise ManifestError(
                f"Role point {role.point} is {role.endpoint_side} endpoint for {role.path_id!r}, "
                f"but path declares endpoint {expected_endpoint}."
            )
        current_path_target = int(assoc[role.point, role.path_slot])
        allowed_targets = set(path.ordered_nodes)
        if role.endpoint_side == "left":
            allowed_targets.add(path.right_endpoint)
        else:
            allowed_targets.add(path.left_endpoint)
        if current_path_target not in allowed_targets:
            raise ManifestError(
                f"Role point {role.point} path slot {role.path_slot} targets {current_path_target}, "
                f"which is not on the declared continuation domain for path {role.path_id!r}."
            )


def shorten_path_record(
    *,
    assoc: np.ndarray,
    path: RelationalPathRecord,
    admission: PathChangeAdmission,
    operation_id: str = "path_shortening_v1_deprecated",
) -> PathMutationResult:
    """Deprecated archive-compatibility helper.

    Do not use as an intrinsic framework rule. v0.1.23 path edits should be
    requested by external monitors through external_path_monitor.py.
    """
    admission.require_admitted(operation_id)
    if path.path_length % 2 == 0:
        raise ManifestError("path_shortening_v1 only handles odd single-center paths; even center pair requires a separate rule.")
    assoc_in = np.asarray(assoc, dtype=np.int64)
    out = assoc_in.copy()
    L = path.path_length
    center_index = L // 2
    center = path.ordered_nodes[center_index]
    before = path.left_endpoint if center_index == 0 else path.ordered_nodes[center_index - 1]
    after = path.right_endpoint if center_index == L - 1 else path.ordered_nodes[center_index + 1]
    # Reconnect predecessor/successor if their rows currently point at center.
    out[out == center] = out[out == center]  # explicit no-op for audit readability
    for slot in range(3):
        if out[before, slot] == center:
            out[before, slot] = after
        if out[after, slot] == center:
            out[after, slot] = before
    nodes_after = path.ordered_nodes[:center_index] + path.ordered_nodes[center_index + 1:]
    path_after = replace(path, ordered_nodes=nodes_after)
    report = GeometryTransactionReport(
        report_schema="rank3_geometry_transaction_report_v1",
        operation_id=operation_id,
        operation_kind="path_shortening",
        applied=True,
        association_before_hash=array_hash(assoc_in),
        association_after_hash=array_hash(out),
        scalar_values_moved=False,
        affected_points=(before, center, after),
        validation={
            "admission_hash": admission.fingerprint(),
            "input_path_hash": path.fingerprint(),
            "output_path_hash": path_after.fingerprint(),
            "path_length_before": path.path_length,
            "path_length_after": path_after.path_length,
            "delta_L": -1,
            "even_path_rejected_by_this_rule": True,
        },
        details={"removed_center_node": center, "reconnected_predecessor": before, "reconnected_successor": after},
    )
    return PathMutationResult(path, path_after, out, report)


def lengthen_path_record(
    *,
    assoc: np.ndarray,
    path: RelationalPathRecord,
    new_node: int,
    admission: PathChangeAdmission,
    operation_id: str = "path_lengthening_v1_deprecated",
) -> PathMutationResult:
    """Deprecated archive-compatibility helper.

    Do not use as an intrinsic framework rule. v0.1.23 path edits should be
    requested by external monitors through external_path_monitor.py.
    """
    admission.require_admitted(operation_id)
    assoc_in = np.asarray(assoc, dtype=np.int64)
    n = int(assoc_in.shape[0])
    new_node = int(new_node)
    if new_node < 0 or new_node >= n:
        raise ManifestError("path_lengthening_v1 new_node out of bounds.")
    if new_node in path.ordered_nodes or new_node in (path.left_endpoint, path.right_endpoint):
        raise ManifestError("path_lengthening_v1 new_node is already on the path.")
    out = assoc_in.copy()
    L = path.path_length
    insert_after_index = (L - 1) // 2
    before = path.ordered_nodes[insert_after_index]
    after = path.right_endpoint if insert_after_index == L - 1 else path.ordered_nodes[insert_after_index + 1]
    for slot in range(3):
        if out[before, slot] == after:
            out[before, slot] = new_node
        if out[after, slot] == before:
            out[after, slot] = new_node
    # New node gets path-neighbor relation in slots 0/1 if possible, preserving rank-3 with existing slot2.
    out[new_node, 0] = before
    out[new_node, 1] = after
    if out[new_node, 2] in (before, after, new_node):
        for candidate in range(n):
            if candidate not in (new_node, before, after):
                out[new_node, 2] = candidate
                break
    nodes_after = path.ordered_nodes[: insert_after_index + 1] + (new_node,) + path.ordered_nodes[insert_after_index + 1:]
    path_after = replace(path, ordered_nodes=nodes_after)
    report = GeometryTransactionReport(
        report_schema="rank3_geometry_transaction_report_v1",
        operation_id=operation_id,
        operation_kind="path_lengthening",
        applied=True,
        association_before_hash=array_hash(assoc_in),
        association_after_hash=array_hash(out),
        scalar_values_moved=False,
        affected_points=(before, new_node, after),
        validation={
            "admission_hash": admission.fingerprint(),
            "input_path_hash": path.fingerprint(),
            "output_path_hash": path_after.fingerprint(),
            "path_length_before": path.path_length,
            "path_length_after": path_after.path_length,
            "delta_L": +1,
        },
        details={"inserted_node": new_node, "inserted_between": (before, after)},
    )
    return PathMutationResult(path, path_after, out, report)
