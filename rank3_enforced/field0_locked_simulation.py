from __future__ import annotations

import argparse
import json
import math
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .fingerprints import stable_json_hash

FRAMEWORK_TARGET_VERSION = "0.1.44"
RUNNER_ID = "field0_configured_locked_admissibility_simulation_v0_1"
PACKET_ID = "field0_locked_admissibility_approval_items_v0144"
SCHEMA = "field0_configured_locked_admissibility_simulation_v0_1"

FORBIDDEN_GENERATOR_KEYS: tuple[str, ...] = (
    "structure_label",
    "structure_labels",
    "endpoint_class",
    "photon_like",
    "bounded_support",
    "triangle",
    "target_tuple",
    "target_delta_l",
    "expected_delta_l",
    "path_slot_policy",
    "conjugate_link_slot_policy",
    "same_sign_path_affinity",
    "opposite_sign_transverse_affinity",
    "postrun_certifier_rule",
    "standard_model_role_label",
)

LEGACY_NONCOMPLIANT_RUNNERS: tuple[dict[str, Any], ...] = (
    {
        "module": "rank3_enforced.endpoint_class_path_response_separation",
        "status": "historical_diagnostic_quarantined",
        "reason": "constructs endpoint classes and comparison paths instead of accepting only field-0 configuration",
    },
    {
        "module": "rank3_enforced.vacuum_admissibility_variation",
        "status": "historical_diagnostic_quarantined",
        "reason": "encodes runner-local admissibility variants and motif labels rather than a frozen pre-run admissibility specification",
    },
    {
        "module": "rank3_enforced.whole_field_conjugate_vacuum",
        "status": "historical_false_positive_diagnostic_quarantined",
        "reason": "uses slot-role construction policies that can manufacture a formal photon-like tuple",
    },
)

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "FIELD0_INPUT_CONFIGURATION_REPORT.json",
    "FROZEN_ADMISSIBILITY_SPEC_REPORT.json",
    "FIELD_EVOLUTION_TRACE.json",
    "ASSOCIATION_TRANSITION_LEDGER.json",
    "ADMISSIBILITY_BURDEN_LEDGER.json",
    "SOO_TRANSITION_LEDGER.json",
    "OPERATIONAL_CONSTRAINT_COMPLIANCE_REPORT.json",
    "POSTRUN_OBSERVER_READOUT_REPORT.json",
    "LEGACY_RUNNER_QUARANTINE_REPORT.json",
    "EXPLORATORY_VERDICT_REPORT.json",
)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def _normalize_assoc(associations: Sequence[str | None] | None) -> tuple[str | None, str | None, str | None]:
    raw = list(associations or ())
    if len(raw) > 3:
        raise ValueError("a scalar point may have at most three associations")
    raw = raw + [None] * (3 - len(raw))
    return tuple(x if x is None else str(x) for x in raw[:3])


def _scan_forbidden(obj: Any, *, path: str = "$", hits: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    hits = hits if hits is not None else []
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            kstr = str(k)
            if kstr in FORBIDDEN_GENERATOR_KEYS:
                hits.append({"path": f"{path}.{kstr}", "key": kstr})
            _scan_forbidden(v, path=f"{path}.{kstr}", hits=hits)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _scan_forbidden(v, path=f"{path}[{i}]", hits=hits)
    return hits


@dataclass(frozen=True)
class FieldPoint:
    id: str
    value: float
    associations: tuple[str | None, str | None, str | None]
    metadata: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        meta = {k: v for k, v in self.metadata}
        return {
            "id": self.id,
            "value": float(self.value),
            "associations": list(self.associations),
            "metadata": meta,
        }


@dataclass(frozen=True)
class FieldState:
    ell: int
    points: tuple[FieldPoint, ...]
    previous_values: tuple[tuple[str, float], ...]
    admissibility_spec_hash: str

    def point_map(self) -> dict[str, FieldPoint]:
        return {p.id: p for p in self.points}

    def value_map(self) -> dict[str, float]:
        return {p.id: float(p.value) for p in self.points}

    def previous_value_map(self) -> dict[str, float]:
        return {pid: float(v) for pid, v in self.previous_values}

    def to_dict(self) -> dict[str, Any]:
        return {
            "ell": int(self.ell),
            "point_count": len(self.points),
            "admissibility_spec_hash": self.admissibility_spec_hash,
            "points": [p.to_dict() for p in self.points],
        }


@dataclass(frozen=True)
class Field0Configuration:
    points: tuple[FieldPoint, ...]
    description: str = "field-0 imposed scalar values and associations"

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "point_count": len(self.points),
            "points": [p.to_dict() for p in self.points],
        }


@dataclass(frozen=True)
class FrozenAdmissibilitySpec:
    id: str
    name: str
    scalar_update_rule: str
    association_update_rule: str
    topology_update_rule: str
    candidate_pool_rule: str
    burden_terms: tuple[str, ...]
    parameters: tuple[tuple[str, Any], ...] = ()
    created_before_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "scalar_update_rule": self.scalar_update_rule,
            "association_update_rule": self.association_update_rule,
            "topology_update_rule": self.topology_update_rule,
            "candidate_pool_rule": self.candidate_pool_rule,
            "burden_terms": list(self.burden_terms),
            "parameters": {k: v for k, v in self.parameters},
            "created_before_run": self.created_before_run,
            "hash": self.hash,
            "single_functional_for_all_slots": True,
            "slot_role_policy_present": False,
            "structure_label_generator_present": False,
        }

    @property
    def parameter_map(self) -> dict[str, Any]:
        return {k: v for k, v in self.parameters}

    @property
    def hash(self) -> str:
        payload = {
            "id": self.id,
            "name": self.name,
            "scalar_update_rule": self.scalar_update_rule,
            "association_update_rule": self.association_update_rule,
            "topology_update_rule": self.topology_update_rule,
            "candidate_pool_rule": self.candidate_pool_rule,
            "burden_terms": list(self.burden_terms),
            "parameters": {k: v for k, v in self.parameters},
            "created_before_run": self.created_before_run,
        }
        return stable_json_hash(payload)


ADMISSIBILITY_REGISTRY: dict[str, FrozenAdmissibilitySpec] = {
    "LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS": FrozenAdmissibilitySpec(
        id="LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS",
        name="Locked pure-gradient SOO with fixed field-0 associations",
        scalar_update_rule="rank3_mean_contrast_soo",
        association_update_rule="frozen_field0_associations",
        topology_update_rule="none",
        candidate_pool_rule="field_state_points_only",
        burden_terms=("scalar_gradient_abs",),
        parameters=(("epsilon2_k", 0.05),),
    ),
    "LOCKED_LEAST_GRADIENT_REASSOCIATION": FrozenAdmissibilitySpec(
        id="LOCKED_LEAST_GRADIENT_REASSOCIATION",
        name="Locked least-gradient reassociation over the generated field state",
        scalar_update_rule="rank3_mean_contrast_soo",
        association_update_rule="least_gradient_all_slots_same_functional",
        topology_update_rule="none",
        candidate_pool_rule="field_state_points_only",
        burden_terms=("scalar_gradient_abs", "stable_id_tiebreak"),
        parameters=(("epsilon2_k", 0.05),),
    ),
    "LOCKED_CONJUGATE_SPLIT_ON_FIRST_ASSOCIATION": FrozenAdmissibilitySpec(
        id="LOCKED_CONJUGATE_SPLIT_ON_FIRST_ASSOCIATION",
        name="Locked pre-run admissibility: first-associated zero-vacuum points split into conjugate branches",
        scalar_update_rule="rank3_mean_contrast_soo",
        association_update_rule="least_gradient_all_slots_same_functional",
        topology_update_rule="split_zero_vacuum_points_on_first_association",
        candidate_pool_rule="field_state_points_after_admissible_topology_update",
        burden_terms=("scalar_gradient_abs", "generated_conjugacy_continuation_penalty", "stable_id_tiebreak"),
        parameters=(("epsilon2_k", 0.05), ("split_magnitude", 1.0), ("conjugacy_penalty_weight", 0.25)),
    ),
}


@dataclass(frozen=True)
class PreRunSimulationContract:
    field0: Field0Configuration
    admissibility: FrozenAdmissibilitySpec
    cycles: int
    run_id: str = "field0_locked_exploratory_run"
    observer_readouts: tuple[str, ...] = (
        "lambda_from_association_difference",
        "transverse_balance_from_association_records",
        "motif_discovery_observer_only",
    )

    @property
    def hash(self) -> str:
        return stable_json_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "run_id": self.run_id,
            "cycles": int(self.cycles),
            "field0": self.field0.to_dict(),
            "admissibility": self.admissibility.to_dict(),
            "observer_readouts": list(self.observer_readouts),
            "admissibility_specified_before_run": True,
            "admissibility_changes_allowed_during_run": False,
            "later_field_configuration_supplied": False,
        }
        if include_hash:
            payload["contract_hash"] = self.hash
        return payload


class OperationalConstraintError(ValueError):
    pass


class Field0LockedSimulationRunner:
    """Strict field-0 configured scalar-field simulation runner.

    The runner accepts exactly two kinds of pre-run input:

    1. field-0 scalar point values and associations;
    2. one frozen admissibility specification selected before the run begins.

    It does not accept later-field point values, later-field associations,
    structure labels, endpoint classes, target tuples, or slot-specific sign
    policies.  Every field ell>0 is produced by applying the locked
    admissibility engine and the SOO scalar update to the preceding field state.
    """

    def __init__(self, contract: PreRunSimulationContract) -> None:
        self.contract = contract
        self._locked_admissibility_hash = contract.admissibility.hash
        self._field_states: list[FieldState] = []
        self._association_ledger: list[dict[str, Any]] = []
        self._burden_ledger: list[dict[str, Any]] = []
        self._soo_ledger: list[dict[str, Any]] = []
        self._compliance_errors: list[str] = []
        self.validate_contract()

    def validate_contract(self) -> None:
        if self.contract.cycles < 0:
            raise OperationalConstraintError("cycles must be nonnegative")
        if not self.contract.admissibility.created_before_run:
            raise OperationalConstraintError("admissibility spec must be created before the run")
        if self.contract.admissibility.id not in ADMISSIBILITY_REGISTRY:
            raise OperationalConstraintError("admissibility spec must be registered before the run")
        if ADMISSIBILITY_REGISTRY[self.contract.admissibility.id].hash != self.contract.admissibility.hash:
            raise OperationalConstraintError("admissibility spec differs from locked registry version")
        ids = [p.id for p in self.contract.field0.points]
        if len(ids) != len(set(ids)):
            raise OperationalConstraintError("field-0 point ids must be unique")
        field0_payload = self.contract.field0.to_dict()
        forbidden_hits = _scan_forbidden(field0_payload)
        if forbidden_hits:
            keys = ", ".join(sorted({h["key"] for h in forbidden_hits}))
            raise OperationalConstraintError(f"field-0 generator input contains forbidden structure/target keys: {keys}")
        for point in self.contract.field0.points:
            for assoc in point.associations:
                if assoc is not None and assoc not in ids:
                    raise OperationalConstraintError(f"field-0 association {point.id}->{assoc} does not reference a field-0 point")

    def _initial_state(self) -> FieldState:
        points = tuple(sorted(self.contract.field0.points, key=lambda p: p.id))
        previous = tuple((p.id, float(p.value)) for p in points)
        return FieldState(ell=0, points=points, previous_values=previous, admissibility_spec_hash=self._locked_admissibility_hash)

    def _epsilon2_k(self) -> float:
        return float(self.contract.admissibility.parameter_map.get("epsilon2_k", 0.05))

    def _split_magnitude(self) -> float:
        return float(self.contract.admissibility.parameter_map.get("split_magnitude", 1.0))

    def _conjugacy_penalty_weight(self) -> float:
        return float(self.contract.admissibility.parameter_map.get("conjugacy_penalty_weight", 0.0))

    def _apply_topology_update(self, state: FieldState) -> tuple[tuple[FieldPoint, ...], list[dict[str, Any]]]:
        spec = self.contract.admissibility
        if spec.topology_update_rule == "none":
            return state.points, []
        if spec.topology_update_rule != "split_zero_vacuum_points_on_first_association":
            raise OperationalConstraintError(f"unsupported topology update rule: {spec.topology_update_rule}")
        # This topology transition is not a runner-local construction: it is
        # admitted only because the frozen pre-run admissibility spec contains
        # this topology_update_rule.  It is applied uniformly from the field
        # state, not from a structure label or target readout.
        existing = state.point_map()
        out: list[FieldPoint] = []
        ledger: list[dict[str, Any]] = []
        mag = self._split_magnitude()
        for point in state.points:
            metadata = {k: v for k, v in point.metadata}
            already_split = metadata.get("generated_by") == "split_zero_vacuum_points_on_first_association"
            has_assoc = any(a is not None for a in point.associations)
            if state.ell == 0 and abs(point.value) <= 1.0e-12 and has_assoc and not already_split:
                plus_id = f"{point.id}__plus"
                minus_id = f"{point.id}__minus"
                plus_assoc = _normalize_assoc([minus_id] + [f"{a}__plus" if a in existing and abs(existing[a].value) <= 1.0e-12 else a for a in point.associations if a is not None][:2])
                minus_assoc = _normalize_assoc([plus_id] + [f"{a}__minus" if a in existing and abs(existing[a].value) <= 1.0e-12 else a for a in point.associations if a is not None][:2])
                out.append(FieldPoint(plus_id, +mag, plus_assoc, tuple(sorted({"origin": point.id, "conjugate": minus_id, "generated_by": spec.topology_update_rule}.items()))))
                out.append(FieldPoint(minus_id, -mag, minus_assoc, tuple(sorted({"origin": point.id, "conjugate": plus_id, "generated_by": spec.topology_update_rule}.items()))))
                ledger.append({
                    "ell_from": state.ell,
                    "ell_to": state.ell + 1,
                    "event": "admissible_topology_transition",
                    "rule": spec.topology_update_rule,
                    "source_point": point.id,
                    "generated_points": [plus_id, minus_id],
                    "authorized_by_pre_run_admissibility_hash": self._locked_admissibility_hash,
                    "runner_special_construction": False,
                    "structure_label_used": False,
                })
            else:
                out.append(point)
        valid_ids = {p.id for p in out}
        repaired: list[FieldPoint] = []
        for p in out:
            repaired.append(FieldPoint(p.id, p.value, _normalize_assoc([a if a in valid_ids else None for a in p.associations]), p.metadata))
        return tuple(sorted(repaired, key=lambda p: p.id)), ledger

    def _candidate_pool(self, point: FieldPoint, points: tuple[FieldPoint, ...]) -> list[FieldPoint]:
        return [p for p in points if p.id != point.id]

    def _burden(self, point: FieldPoint, candidate: FieldPoint, slot: int, ell_to: int) -> tuple[float, dict[str, Any]]:
        spec = self.contract.admissibility
        scalar_gradient = abs(float(point.value) - float(candidate.value))
        penalty = 0.0
        meta = {k: v for k, v in point.metadata}
        if "generated_conjugacy_continuation_penalty" in spec.burden_terms:
            # This is not a slot sign policy.  It is the same term for all slots:
            # it prevents the generated conjugate from being selected merely by
            # target-tuple role.  Selection remains a single burden functional.
            if candidate.id == meta.get("conjugate"):
                penalty += self._conjugacy_penalty_weight()
        value = scalar_gradient + penalty
        detail = {
            "ell_to": ell_to,
            "point": point.id,
            "slot": slot,
            "candidate": candidate.id,
            "burden": float(value),
            "terms": {
                "scalar_gradient_abs": float(scalar_gradient),
                "generated_conjugacy_continuation_penalty": float(penalty),
            },
            "single_functional_for_all_slots": True,
            "slot_role_known_to_generator": False,
            "structure_label_used": False,
            "target_tuple_used": False,
            "admissibility_spec_hash": self._locked_admissibility_hash,
        }
        return value, detail

    def _select_associations(self, points: tuple[FieldPoint, ...], ell_to: int) -> tuple[tuple[FieldPoint, ...], list[dict[str, Any]], list[dict[str, Any]]]:
        spec = self.contract.admissibility
        if spec.association_update_rule == "frozen_field0_associations":
            assoc_records = []
            for p in points:
                assoc_records.append({
                    "ell_to": ell_to,
                    "point": p.id,
                    "associations": list(p.associations),
                    "selected_by": spec.association_update_rule,
                    "admissibility_spec_hash": self._locked_admissibility_hash,
                    "later_field_association_imposed_by_test": False,
                    "single_functional_for_all_slots": True,
                })
            return points, assoc_records, []
        if spec.association_update_rule != "least_gradient_all_slots_same_functional":
            raise OperationalConstraintError(f"unsupported association update rule: {spec.association_update_rule}")
        updated: list[FieldPoint] = []
        assoc_records: list[dict[str, Any]] = []
        burden_records: list[dict[str, Any]] = []
        for p in points:
            pool = self._candidate_pool(p, points)
            selected: list[str | None] = []
            used: set[str] = set()
            for slot in range(3):
                details: list[dict[str, Any]] = []
                ranked: list[tuple[float, str, FieldPoint]] = []
                for c in pool:
                    if c.id in used and len(pool) >= 3:
                        continue
                    burden, detail = self._burden(p, c, slot, ell_to)
                    details.append(detail)
                    ranked.append((burden, c.id, c))
                ranked.sort(key=lambda item: (item[0], item[1]))
                if ranked:
                    chosen = ranked[0][2]
                    selected.append(chosen.id)
                    used.add(chosen.id)
                else:
                    selected.append(None)
                burden_records.extend(details)
            updated.append(FieldPoint(p.id, p.value, _normalize_assoc(selected), p.metadata))
            assoc_records.append({
                "ell_to": ell_to,
                "point": p.id,
                "associations": list(_normalize_assoc(selected)),
                "selected_by": spec.association_update_rule,
                "admissibility_spec_hash": self._locked_admissibility_hash,
                "later_field_association_imposed_by_test": False,
                "single_functional_for_all_slots": True,
                "slot_sign_policy_present": False,
            })
        return tuple(sorted(updated, key=lambda p: p.id)), assoc_records, burden_records

    def _soo_update_values(self, points: tuple[FieldPoint, ...], previous_values: Mapping[str, float], ell_to: int) -> tuple[tuple[FieldPoint, ...], tuple[tuple[str, float], ...], list[dict[str, Any]]]:
        values = {p.id: float(p.value) for p in points}
        eps = self._epsilon2_k()
        updated: list[FieldPoint] = []
        ledger: list[dict[str, Any]] = []
        for p in points:
            partner_values = [values[a] for a in p.associations if a is not None and a in values]
            mean = sum(partner_values) / len(partner_values) if partner_values else 0.0
            prev = float(previous_values.get(p.id, p.value))
            next_value = 2.0 * float(p.value) - prev - eps * (float(p.value) - mean)
            updated.append(FieldPoint(p.id, next_value, p.associations, p.metadata))
            ledger.append({
                "ell_to": ell_to,
                "point": p.id,
                "previous_value": prev,
                "current_value": float(p.value),
                "association_mean": float(mean),
                "next_value": float(next_value),
                "scalar_update_rule": self.contract.admissibility.scalar_update_rule,
                "admissibility_spec_hash": self._locked_admissibility_hash,
                "later_field_value_imposed_by_test": False,
            })
        prev_tuple = tuple((p.id, float(p.value)) for p in points)
        return tuple(sorted(updated, key=lambda p: p.id)), prev_tuple, ledger

    def _assert_no_runtime_admissibility_change(self) -> None:
        if self.contract.admissibility.hash != self._locked_admissibility_hash:
            raise OperationalConstraintError("admissibility changed during run")

    def run(self) -> dict[str, Any]:
        state = self._initial_state()
        self._field_states.append(state)
        previous_values = state.previous_value_map()
        for ell_to in range(1, self.contract.cycles + 1):
            self._assert_no_runtime_admissibility_change()
            topology_points, topology_events = self._apply_topology_update(state)
            self._association_ledger.extend(topology_events)
            selected_points, assoc_records, burden_records = self._select_associations(topology_points, ell_to)
            self._association_ledger.extend(assoc_records)
            self._burden_ledger.extend(burden_records)
            updated_points, previous_values_tuple, soo_records = self._soo_update_values(selected_points, previous_values, ell_to)
            self._soo_ledger.extend(soo_records)
            state = FieldState(
                ell=ell_to,
                points=updated_points,
                previous_values=previous_values_tuple,
                admissibility_spec_hash=self._locked_admissibility_hash,
            )
            previous_values = state.previous_value_map()
            self._field_states.append(state)
        return self.reports()

    def _observer_readouts(self) -> dict[str, Any]:
        final = self._field_states[-1]
        values = final.value_map()
        point_map = final.point_map()
        lambda_records: list[dict[str, Any]] = []
        for p in final.points:
            first_assoc = next((a for a in p.associations if a in values), None)
            if first_assoc is None:
                continue
            lam = float(p.value) - float(values[first_assoc])
            lambda_records.append({
                "point": p.id,
                "association": first_assoc,
                "lambda": float(lam),
                "definition": "Phi(P)-Phi(first_generated_association(P))",
                "observer_only": True,
                "feeds_generator": False,
            })
        triangle_like = []
        ids = sorted(point_map)
        # Simple observer-only motif scan: cycles among current associations.
        for pid in ids:
            assocs = [a for a in point_map[pid].associations if a in point_map]
            for a in assocs:
                for b in [x for x in point_map[a].associations if x in point_map]:
                    if pid in point_map[b].associations:
                        tri = tuple(sorted((pid, a, b)))
                        if len(set(tri)) == 3 and tri not in triangle_like:
                            triangle_like.append(tri)
        return {
            "schema": "field0_locked_postrun_observer_readout_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "observer_readouts": list(self.contract.observer_readouts),
            "lambda_records": lambda_records,
            "observer_discovered_three_cycles": [list(x) for x in triangle_like[:64]],
            "observer_output_feeds_generator": False,
            "structure_labels_assigned_during_run": False,
        }

    def _compliance_report(self) -> dict[str, Any]:
        hashes = [s.admissibility_spec_hash for s in self._field_states]
        errors: list[str] = []
        if any(h != self._locked_admissibility_hash for h in hashes):
            errors.append("admissibility hash changed across field states")
        forbidden_hits = _scan_forbidden(self.contract.field0.to_dict())
        if forbidden_hits:
            errors.append("forbidden generator keys present in field-0 config")
        return {
            "schema": "field0_locked_operational_constraint_compliance_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "passed": not errors,
            "errors": errors,
            "constraints": {
                "field0_values_and_associations_may_be_imposed": True,
                "later_field_values_may_be_imposed": False,
                "later_field_associations_may_be_imposed": False,
                "admissibility_variation_allowed_pre_run": True,
                "admissibility_changes_allowed_during_run": False,
                "all_later_fields_generated_by_soo_plus_locked_admissibility": True,
                "special_constructions_allowed_during_run": False,
                "structure_labels_assigned_during_run": False,
                "new_admissibilities_introduced_during_run": False,
                "single_functional_for_all_slots": True,
                "postrun_observer_no_feedback": True,
            },
            "admissibility_hash_by_field": hashes,
            "locked_admissibility_hash": self._locked_admissibility_hash,
            "forbidden_generator_input_hits": forbidden_hits,
        }

    def reports(self) -> dict[str, Any]:
        observer = self._observer_readouts()
        compliance = self._compliance_report()
        return {
            "FIELD0_INPUT_CONFIGURATION_REPORT.json": {
                "schema": "field0_input_configuration_report_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "field0": self.contract.field0.to_dict(),
                "allowed_input_surface": "field0_scalar_values_and_rank3_associations_only",
                "later_field_configuration_supplied": False,
                "structure_labels_supplied": False,
                "target_readouts_supplied": False,
            },
            "FROZEN_ADMISSIBILITY_SPEC_REPORT.json": {
                "schema": "frozen_admissibility_spec_report_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "contract_hash": self.contract.hash,
                "admissibility": self.contract.admissibility.to_dict(),
                "allowed_admissibility_variation": "pre_run_only",
                "runtime_admissibility_change_allowed": False,
                "locked_registry_ids": sorted(ADMISSIBILITY_REGISTRY),
            },
            "FIELD_EVOLUTION_TRACE.json": {
                "schema": "field_evolution_trace_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "states": [s.to_dict() for s in self._field_states],
                "all_states_after_field0_generated": True,
            },
            "ASSOCIATION_TRANSITION_LEDGER.json": {
                "schema": "association_transition_ledger_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "records": self._association_ledger,
                "later_associations_imposed_by_test": False,
            },
            "ADMISSIBILITY_BURDEN_LEDGER.json": {
                "schema": "admissibility_burden_ledger_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "records": self._burden_ledger,
                "single_functional_for_all_slots": True,
            },
            "SOO_TRANSITION_LEDGER.json": {
                "schema": "soo_transition_ledger_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "records": self._soo_ledger,
                "later_values_imposed_by_test": False,
            },
            "OPERATIONAL_CONSTRAINT_COMPLIANCE_REPORT.json": compliance,
            "POSTRUN_OBSERVER_READOUT_REPORT.json": observer,
            "LEGACY_RUNNER_QUARANTINE_REPORT.json": {
                "schema": "legacy_runner_quarantine_report_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "current_compliant_runner": "rank3_enforced.field0_locked_simulation",
                "legacy_runners": list(LEGACY_NONCOMPLIANT_RUNNERS),
                "legacy_runners_available_only_as_historical_diagnostics": True,
            },
            "EXPLORATORY_VERDICT_REPORT.json": {
                "schema": "field0_locked_exploratory_verdict_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "runner_id": RUNNER_ID,
                "passed_operational_constraints": compliance["passed"],
                "scientific_certification": False,
                "certification_note": "This runner certifies operational constraint compliance only; physical motif classification remains post-run observer output.",
            },
        }


def make_ring_field0(point_count: int = 6, *, alternating: bool = True) -> Field0Configuration:
    if point_count < 3:
        raise ValueError("point_count must be at least 3")
    points: list[FieldPoint] = []
    for i in range(point_count):
        value = 0.0 if not alternating else (1.0 if i % 2 == 0 else -1.0)
        assocs = _normalize_assoc([
            f"P{(i + 1) % point_count}",
            f"P{(i + 2) % point_count}",
            f"P{(i + 3) % point_count}",
        ])
        points.append(FieldPoint(id=f"P{i}", value=value, associations=assocs))
    return Field0Configuration(points=tuple(points), description="deterministic ring field-0 test configuration")


def make_vacuum_split_field0(point_count: int = 6) -> Field0Configuration:
    if point_count < 3:
        raise ValueError("point_count must be at least 3")
    points: list[FieldPoint] = []
    for i in range(point_count):
        assocs = _normalize_assoc([
            f"V{(i + 1) % point_count}",
            f"V{(i + 2) % point_count}",
            f"V{(i + 3) % point_count}",
        ])
        points.append(FieldPoint(id=f"V{i}", value=0.0, associations=assocs))
    return Field0Configuration(points=tuple(points), description="zero-valued vacuum ring field-0 configuration for split admissibility exploration")


def make_contract(
    *,
    spec_id: str = "LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS",
    cycles: int = 6,
    point_count: int = 6,
    vacuum: bool = False,
) -> PreRunSimulationContract:
    if spec_id not in ADMISSIBILITY_REGISTRY:
        raise ValueError(f"unknown admissibility spec: {spec_id}")
    field0 = make_vacuum_split_field0(point_count) if vacuum else make_ring_field0(point_count)
    return PreRunSimulationContract(
        field0=field0,
        admissibility=ADMISSIBILITY_REGISTRY[spec_id],
        cycles=cycles,
        run_id=f"{spec_id.lower()}_demo",
    )


def run_exploratory(
    *,
    output_root: str | Path | None = None,
    spec_ids: Sequence[str] | None = None,
    cycles: int = 6,
    point_count: int = 6,
) -> dict[str, Any]:
    selected = list(spec_ids or ADMISSIBILITY_REGISTRY.keys())
    runs: dict[str, dict[str, Any]] = {}
    for spec_id in selected:
        contract = make_contract(
            spec_id=spec_id,
            cycles=cycles,
            point_count=point_count,
            vacuum=spec_id == "LOCKED_CONJUGATE_SPLIT_ON_FIRST_ASSOCIATION",
        )
        runs[spec_id] = Field0LockedSimulationRunner(contract).run()
    # Top-level reports collect each required artifact by run id so the packet
    # remains a single experiment set while preserving per-run frozen specs.
    reports: dict[str, Any] = {}
    for artifact in REQUIRED_ARTIFACTS:
        reports[artifact] = {
            "schema": f"field0_locked_multi_run_{artifact.removesuffix('.json').lower()}_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runs": {spec_id: run[artifact] for spec_id, run in runs.items()},
        }
    reports["EXPLORATORY_VERDICT_REPORT.json"]["all_runs_passed_operational_constraints"] = all(
        run["OPERATIONAL_CONSTRAINT_COMPLIANCE_REPORT.json"]["passed"] for run in runs.values()
    )
    if output_root is not None:
        root = Path(output_root)
        root.mkdir(parents=True, exist_ok=True)
        for name, report in reports.items():
            (root / name).write_text(_stable_json(report), encoding="utf-8")
    return reports


def write_approval_packet(output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    packet_root = out / PACKET_ID
    if packet_root.exists():
        shutil.rmtree(packet_root)
    packet_root.mkdir(parents=True)
    material = {
        "APPROVAL_INSTRUCTIONS.md": """# v0.1.44 Field-0 Locked Simulation Approval Packet\n\nThis packet approves only the operational runner discipline: field-0 values/associations may be supplied, admissibility variants may be selected before the run, and all later fields must be generated by SOO plus the frozen admissibility specification. Structure labels and target readouts are observer-only.\n""",
        "EXPLORATORY_RUNNER_SPEC.json": {
            "schema": "field0_locked_runner_spec_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runner_id": RUNNER_ID,
            "field0_only_input": True,
            "admissibility_variation_pre_run_only": True,
            "runtime_admissibility_changes_allowed": False,
            "structure_labels_generator_forbidden": True,
            "postrun_observer_no_feedback": True,
        },
        "LOCKED_ADMISSIBILITY_REGISTRY.json": {
            "schema": "locked_admissibility_registry_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "specs": {k: v.to_dict() for k, v in sorted(ADMISSIBILITY_REGISTRY.items())},
        },
        "OPERATIONAL_CONSTRAINTS.json": {
            "schema": "field0_locked_operational_constraints_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "constraints": {
                "field0_values_and_associations_allowed": True,
                "later_field_values_and_associations_as_test_input_allowed": False,
                "admissibility_variants_allowed_before_run": True,
                "admissibility_changes_during_run_allowed": False,
                "new_admissibilities_during_run_allowed": False,
                "special_constructions_during_run_allowed": False,
                "structure_labels_generator_allowed": False,
                "postrun_labels_observer_only": True,
            },
        },
        "LEGACY_RUNNER_QUARANTINE.json": {
            "schema": "legacy_runner_quarantine_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "legacy_runners": list(LEGACY_NONCOMPLIANT_RUNNERS),
        },
        "NEGATIVE_CONTROLS_MANIFEST.json": {
            "schema": "field0_locked_negative_controls_manifest_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "negative_controls": [
                "reject_field0_structure_label_key",
                "reject_unregistered_admissibility_spec",
                "reject_mutated_registered_admissibility_spec",
                "reject_association_to_non_field0_point",
                "record_legacy_runner_quarantine",
            ],
        },
    }
    for name, content in material.items():
        path = packet_root / name
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_text(_stable_json(content), encoding="utf-8")
    zip_path = out / f"{PACKET_ID}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(packet_root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(out).as_posix())
    return zip_path


def main_run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the v0.1.44 field-0 locked admissibility simulation.")
    parser.add_argument("--output", default="v0144_field0_locked_run")
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--point-count", type=int, default=6)
    parser.add_argument("--spec", action="append", choices=sorted(ADMISSIBILITY_REGISTRY), help="Pre-run admissibility spec id. May be repeated.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    run_exploratory(output_root=args.output, spec_ids=args.spec, cycles=args.cycles, point_count=args.point_count)
    print(f"wrote v0.1.44 field-0 locked simulation reports to {args.output}")
    return 0


def main_packet(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write v0.1.44 field-0 locked admissibility approval packet.")
    parser.add_argument("--output", default="v0144_field0_locked_approval_packet")
    args = parser.parse_args(list(argv) if argv is not None else None)
    zip_path = write_approval_packet(args.output)
    print(zip_path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main_run())
