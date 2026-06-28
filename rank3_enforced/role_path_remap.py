from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

import scalar_field_geometry as sfg
from .dynamic_paths import (
    DressingRoleMap,
    RelationalPathRecord,
    parse_dressing_role_maps,
    parse_relational_paths,
    validate_role_paths,
)
from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash
from .rule_metadata import RuleMetadata, RuleStatus

RULE_ID = "path_continuation_role_remap_v1"


@dataclass(frozen=True)
class PathContinuationRoleRemapReport:
    report_schema: str
    remap_rule_id: str
    cadence: int
    applied: bool
    association_before_hash: str
    association_after_hash: str
    changed_entries: int
    path_records_hash: str
    role_maps_hash: str
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class PathContinuationRoleRemapRule:
    """Role/path-preserving dressing remap rule.

    This rule is the framework replacement for hard-coded slot remap tests.
    It preserves the boundary-facing dressing slot, identifies the path-facing
    association by role, and advances that role along the registered relational
    path according to endpoint side:

    * left endpoint: path-facing role advances toward the right endpoint;
    * right endpoint: path-facing role advances toward the left endpoint.

    The vacuum-facing role is preserved as a role. If role exchange is enabled
    for a dressing point, the path/vacuum roles exchange numeric slots after the
    remap while the path role still receives the path-continuation target.
    No scalar values are moved, copied, reset, or overwritten.
    """

    paths: tuple[RelationalPathRecord, ...]
    dressing_roles: tuple[DressingRoleMap, ...]
    cadence: int = 1
    name: str = RULE_ID
    metadata: RuleMetadata = RuleMetadata(
        name=RULE_ID,
        version="0.1.21",
        status=RuleStatus.CANDIDATE,
        source_hash="locked_candidate_path_continuation_role_remap_v1",
        allowed_for_certified_runs=False,
        notes=(
            "Candidate role/path-preserving remap. Boundary-facing dressing slot is fixed; "
            "path-facing and vacuum-facing roles are declarative and may exchange only if enabled. "
            "No scalar values are moved. Not admitted as EAS law."
        ),
    )

    def __post_init__(self) -> None:
        cadence = int(self.cadence)
        if cadence < 1:
            raise ManifestError(f"{RULE_ID} cadence must be >= 1.")
        if not self.paths:
            raise ManifestError(f"{RULE_ID} requires at least one path record.")
        if not self.dressing_roles:
            raise ManifestError(f"{RULE_ID} requires at least one dressing role map.")
        object.__setattr__(self, "cadence", cadence)
        object.__setattr__(self, "_reports", [])
        object.__setattr__(self, "_role_state", {int(r.point): r for r in self.dressing_roles})

    def reset_trace(self) -> None:
        self._reports.clear()
        object.__setattr__(self, "_role_state", {int(r.point): r for r in self.dressing_roles})

    def get_role_path_remap_reports(self) -> tuple[PathContinuationRoleRemapReport, ...]:
        return tuple(self._reports)

    def _path_by_id(self) -> dict[str, RelationalPathRecord]:
        return {path.path_id: path for path in self.paths}

    def __call__(self, context: sfg.RemapContext) -> sfg.IntArray:
        assoc = np.asarray(context.state_current.assoc, dtype=np.int64)
        if assoc.ndim != 2 or assoc.shape[1] != 3:
            raise ManifestError(f"{RULE_ID} requires an (n,3) association table.")
        validate_role_paths(assoc=assoc, paths=self.paths, roles=tuple(self._role_state.values()))
        applied = (int(context.ell) + 1) % self.cadence == 0
        out = assoc.copy()
        changes: list[dict[str, Any]] = []
        if applied:
            path_by_id = self._path_by_id()
            new_roles: dict[int, DressingRoleMap] = {}
            for point, role in sorted(self._role_state.items()):
                path = path_by_id[role.path_id]
                old_path_target = int(assoc[role.point, role.path_slot])
                if role.endpoint_side == "left":
                    new_path_target = path.neighbor_toward_right(old_path_target)
                else:
                    new_path_target = path.neighbor_toward_left(old_path_target)

                next_role = role.exchanged()
                # boundary-facing slot is fixed.
                out[role.point, role.boundary_slot] = assoc[role.point, role.boundary_slot]
                # path role receives path-continuation target in its current or exchanged slot.
                out[role.point, next_role.path_slot] = new_path_target
                # vacuum role carries the previous vacuum target by role; this avoids creating a second path edge.
                out[role.point, next_role.vacuum_slot] = assoc[role.point, role.vacuum_slot]
                new_roles[point] = next_role
                changes.append({
                    "point": int(role.point),
                    "path_id": role.path_id,
                    "endpoint_side": role.endpoint_side,
                    "boundary_slot_fixed": int(role.boundary_slot),
                    "old_path_slot": int(role.path_slot),
                    "old_vacuum_slot": int(role.vacuum_slot),
                    "new_path_slot": int(next_role.path_slot),
                    "new_vacuum_slot": int(next_role.vacuum_slot),
                    "old_path_target": old_path_target,
                    "new_path_target": int(new_path_target),
                    "path_vacuum_role_exchange": bool(next_role.path_slot != role.path_slot),
                })
            object.__setattr__(self, "_role_state", new_roles)

        changed_entries = int(np.count_nonzero(out != assoc))
        report = PathContinuationRoleRemapReport(
            report_schema="rank3_path_continuation_role_remap_report_v1",
            remap_rule_id=RULE_ID,
            cadence=int(self.cadence),
            applied=bool(applied),
            association_before_hash=array_hash(assoc),
            association_after_hash=array_hash(out),
            changed_entries=changed_entries,
            path_records_hash=stable_json_hash([asdict(p) for p in self.paths]),
            role_maps_hash=stable_json_hash([asdict(r) for r in self._role_state.values()]),
            details={
                "scalar_values_moved": False,
                "boundary_slots_fixed": True,
                "role_based_not_slot_index_based": True,
                "orientation_aware_continuation": True,
                "changes": changes,
                "candidate_not_admitted": True,
            },
        )
        self._reports.append(report)
        return out


def build_path_continuation_role_remap_rule(params: dict[str, Any]) -> PathContinuationRoleRemapRule:
    allowed = {"path_records", "dressing_roles", "cadence"}
    unknown = set(params) - allowed
    if unknown:
        raise ManifestError(f"{RULE_ID} unknown params: {sorted(unknown)}")
    return PathContinuationRoleRemapRule(
        paths=parse_relational_paths(params.get("path_records")),
        dressing_roles=parse_dressing_role_maps(params.get("dressing_roles")),
        cadence=int(params.get("cadence", 1)),
    )
