from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

import numpy as np

import scalar_field_geometry as sfg
from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash
from .rule_metadata import RuleMetadata, RuleStatus

RULE_ID = "path_target_derived_external_remap_v1"


@dataclass(frozen=True)
class PathTargetDerivedRemapReport:
    report_schema: str
    remap_rule_id: str
    path_slot: int
    remap_slots: tuple[int, ...]
    eligible_points: tuple[int, ...]
    fixed_points: tuple[int, ...]
    fixed_slots_by_point: dict[int, tuple[int, ...]]
    cadence: int
    applied: bool
    association_before_hash: str
    association_after_hash: str
    changed_entries: int
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


@dataclass(frozen=True)
class PathTargetDerivedExternalRemapRule:
    """Candidate direction-preserving external-association remap rule.

    This rule implements the conservative association-level interpretation of
    the current EAS remap constraint:

    * the configured ``path_slot`` is the path-facing anchor;
    * bounded/support-owned points are not remapped unless explicitly listed;
    * boundary-facing associations are kept fixed by excluding them from
      ``remap_slots`` or listing them in ``fixed_slots_by_point``;
    * eligible external slots inherit their targets from the current
      path-facing associate of the same point;
    * no scalar values are moved, copied, overwritten, or reset;
    * no global rotation/cycling of external targets is performed.

    For an eligible point x with y = a_path_slot(x), the default update is

        a'_path_slot(x) = a_path_slot(x)
        a'_s(x) = a_s(y) for each configured external slot s

    subject to per-point fixed-slot exclusions. This is candidate framework
    infrastructure, not an admitted EAS remap law.
    """

    eligible_points: tuple[int, ...]
    path_slot: int = 0
    remap_slots: tuple[int, ...] = (1, 2)
    fixed_points: tuple[int, ...] = ()
    fixed_slots_by_point: Mapping[int, tuple[int, ...]] | None = None
    cadence: int = 1
    name: str = RULE_ID
    metadata: RuleMetadata = RuleMetadata(
        name=RULE_ID,
        version="0.1.19",
        status=RuleStatus.CANDIDATE,
        source_hash="locked_candidate_path_target_derived_external_remap_v1",
        allowed_for_certified_runs=False,
        notes=(
            "Candidate direction-preserving remap. A configurable path_slot is path-facing; "
            "eligible external slots inherit same-slot targets from the path-slot associate. "
            "Bounded/support-owned points and boundary-facing slots must be excluded by "
            "configuration. Not admitted."
        ),
    )

    def __post_init__(self) -> None:
        path_slot = int(self.path_slot)
        if path_slot not in (0, 1, 2):
            raise ManifestError(f"{RULE_ID} path_slot must be 0, 1, or 2.")
        remap_slots = tuple(int(s) for s in self.remap_slots)
        if not remap_slots:
            raise ManifestError(f"{RULE_ID} requires at least one remap slot.")
        if any(s not in (0, 1, 2) for s in remap_slots):
            raise ManifestError(f"{RULE_ID} remap_slots must be in {{0,1,2}}.")
        if path_slot in remap_slots:
            raise ManifestError(f"{RULE_ID} keeps path_slot fixed; do not include it in remap_slots.")
        cadence = int(self.cadence)
        if cadence < 1:
            raise ManifestError(f"{RULE_ID} cadence must be >= 1.")
        eligible = tuple(sorted({int(p) for p in self.eligible_points}))
        fixed_points = tuple(sorted({int(p) for p in self.fixed_points}))
        fixed_slots: dict[int, tuple[int, ...]] = {}
        for raw_p, raw_slots in dict(self.fixed_slots_by_point or {}).items():
            p = int(raw_p)
            slots = tuple(sorted({int(s) for s in raw_slots}))
            if any(s not in (0, 1, 2) for s in slots):
                raise ManifestError(f"{RULE_ID} fixed slots must be in {{0,1,2}}.")
            fixed_slots[p] = slots
        object.__setattr__(self, "path_slot", path_slot)
        object.__setattr__(self, "remap_slots", remap_slots)
        object.__setattr__(self, "eligible_points", eligible)
        object.__setattr__(self, "fixed_points", fixed_points)
        object.__setattr__(self, "fixed_slots_by_point", fixed_slots)
        object.__setattr__(self, "cadence", cadence)
        object.__setattr__(self, "_reports", [])

    def reset_trace(self) -> None:
        self._reports.clear()

    def get_directional_remap_reports(self) -> tuple[PathTargetDerivedRemapReport, ...]:
        return tuple(self._reports)

    def __call__(self, context: sfg.RemapContext) -> sfg.IntArray:
        assoc = np.asarray(context.state_current.assoc, dtype=np.int64)
        if assoc.ndim != 2 or assoc.shape[1] != 3:
            raise ManifestError(f"{RULE_ID} requires an (n,3) association table.")
        n = int(assoc.shape[0])
        for p in self.eligible_points:
            if p < 0 or p >= n:
                raise ManifestError(f"{RULE_ID} eligible point out of bounds: {p}")
        for p in self.fixed_points:
            if p < 0 or p >= n:
                raise ManifestError(f"{RULE_ID} fixed point out of bounds: {p}")

        applied = (int(context.ell) + 1) % self.cadence == 0
        out = assoc.copy()
        if applied:
            fixed_point_set = set(self.fixed_points)
            for x in self.eligible_points:
                if x in fixed_point_set:
                    continue
                y = int(assoc[x, self.path_slot])
                if y < 0 or y >= n:
                    raise ManifestError(f"{RULE_ID} path target out of bounds: {y}")
                fixed_slots = set(self.fixed_slots_by_point.get(int(x), ()))
                for slot in self.remap_slots:
                    if slot in fixed_slots:
                        continue
                    out[x, slot] = int(assoc[y, slot])

        changed_entries = int(np.count_nonzero(out != assoc))
        report = PathTargetDerivedRemapReport(
            report_schema="rank3_path_target_derived_external_remap_report_v1",
            remap_rule_id=self.name,
            path_slot=int(self.path_slot),
            remap_slots=tuple(int(s) for s in self.remap_slots),
            eligible_points=tuple(int(p) for p in self.eligible_points),
            fixed_points=tuple(int(p) for p in self.fixed_points),
            fixed_slots_by_point={int(k): tuple(int(s) for s in v) for k, v in self.fixed_slots_by_point.items()},
            cadence=int(self.cadence),
            applied=bool(applied),
            association_before_hash=array_hash(assoc),
            association_after_hash=array_hash(out),
            changed_entries=changed_entries,
            details={
                "path_facing_slot_fixed": True,
                "path_slot_configurable": True,
                "scalar_values_moved": False,
                "global_external_slot_cycle_used": False,
                "overwrite_reset_or_copy_used": False,
                "target_derivation": "for eligible x, y=a_path_slot(x); a_remap_slot(x)=a_same_slot(y)",
                "candidate_not_admitted": True,
            },
        )
        self._reports.append(report)
        return out


def _parse_fixed_slots_by_point(raw: Any) -> dict[int, tuple[int, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ManifestError("fixed_slots_by_point must be an object mapping point index to slot list.")
    return {int(k): tuple(int(s) for s in v) for k, v in raw.items()}


def build_path_target_derived_external_remap_rule(params: dict[str, Any]) -> PathTargetDerivedExternalRemapRule:
    allowed = {"eligible_points", "path_slot", "remap_slots", "fixed_points", "fixed_slots_by_point", "cadence"}
    unknown = set(params) - allowed
    if unknown:
        raise ManifestError(f"{RULE_ID} unknown params: {sorted(unknown)}")
    eligible = params.get("eligible_points")
    if eligible is None:
        raise ManifestError(f"{RULE_ID} requires explicit eligible_points.")
    return PathTargetDerivedExternalRemapRule(
        eligible_points=tuple(int(p) for p in eligible),
        path_slot=int(params.get("path_slot", 0)),
        remap_slots=tuple(int(s) for s in params.get("remap_slots", (1, 2))),
        fixed_points=tuple(int(p) for p in params.get("fixed_points", ())),
        fixed_slots_by_point=_parse_fixed_slots_by_point(params.get("fixed_slots_by_point")),
        cadence=int(params.get("cadence", 1)),
    )


# Backward-compatible Python aliases only. They are intentionally not the
# registry rule id in v0.1.18. New overlays should use
# path_target_derived_external_remap_v1.
Slot0TargetDerivedRemapReport = PathTargetDerivedRemapReport
Slot0TargetDerivedExternalRemapRule = PathTargetDerivedExternalRemapRule
build_slot0_target_derived_external_remap_rule = build_path_target_derived_external_remap_rule
