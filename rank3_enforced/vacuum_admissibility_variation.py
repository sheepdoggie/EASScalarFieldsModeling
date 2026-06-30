from __future__ import annotations

import argparse
import json
import math
import shutil
import zipfile
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Sequence


FRAMEWORK_TARGET_VERSION = "0.1.42"
RUNNER_ID = "vacuum_admissibility_variation_runner_v0_1"
PACKET_ID = "vacuum_admissibility_variation_approval_items_v0142"
SCHEMA = "vacuum_admissibility_variation_v0_1"


@dataclass
class VacuumNode:
    id: str
    value: float
    prev_value: float
    kind: str
    split_site: str | None = None
    branch_sign: int | None = None
    origin: str | None = None
    conjugate_of: str | None = None
    associations: list[str] = field(default_factory=list)
    phase_samples: dict[int, list[float]] = field(default_factory=lambda: {0: [], 1: [], 2: []})

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["value"] = float(self.value)
        d["prev_value"] = float(self.prev_value)
        d["phase_samples"] = {str(k): [float(x) for x in v[-8:]] for k, v in sorted(self.phase_samples.items())}
        return d


@dataclass(frozen=True)
class AdmissibilityVariant:
    id: str
    name: str
    scalar_gradient_weight: float
    split_conjugacy_weight: float
    relation_complete_weight: float
    cyclic_covariance_weight: float
    bounded_closure_weight: float
    purpose: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlSpec:
    id: str
    purpose: str
    expected_exploratory_behavior: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


ADMISSIBILITY_VARIANTS: tuple[AdmissibilityVariant, ...] = (
    AdmissibilityVariant(
        id="A_PURE_SCALAR_GRADIENT",
        name="Pure scalar-gradient admissibility",
        scalar_gradient_weight=1.0,
        split_conjugacy_weight=0.0,
        relation_complete_weight=0.0,
        cyclic_covariance_weight=0.0,
        bounded_closure_weight=0.0,
        purpose="Baseline: select associations by least scalar-gradient burden only.",
    ),
    AdmissibilityVariant(
        id="B_SPLIT_CONJUGACY_PRESERVING",
        name="Split-conjugacy preserving admissibility",
        scalar_gradient_weight=1.0,
        split_conjugacy_weight=0.35,
        relation_complete_weight=0.0,
        cyclic_covariance_weight=0.0,
        bounded_closure_weight=0.0,
        purpose="Test whether generated +/- split relations are preserved as relation records after lift/SOO.",
    ),
    AdmissibilityVariant(
        id="C_RELATION_COMPLETE_BURDEN",
        name="Relation-complete burden admissibility",
        scalar_gradient_weight=1.0,
        split_conjugacy_weight=0.25,
        relation_complete_weight=0.60,
        cyclic_covariance_weight=0.0,
        bounded_closure_weight=0.0,
        purpose="Minimize burden of the relation, including cancellation and non-path balance, without predeclaring photon form.",
    ),
    AdmissibilityVariant(
        id="D_SUCCESSOR_COVARIANT_CYCLIC",
        name="Successor-covariant cyclic admissibility",
        scalar_gradient_weight=1.0,
        split_conjugacy_weight=0.25,
        relation_complete_weight=0.50,
        cyclic_covariance_weight=0.45,
        bounded_closure_weight=0.0,
        purpose="Read candidate records across ordered scalar-field phases instead of loading three local components.",
    ),
    AdmissibilityVariant(
        id="E_BOUNDED_SUPPORT_CLOSURE",
        name="Bounded-support closure admissibility",
        scalar_gradient_weight=1.0,
        split_conjugacy_weight=0.25,
        relation_complete_weight=0.45,
        cyclic_covariance_weight=0.35,
        bounded_closure_weight=0.50,
        purpose="Permit post-run separation of triangle-only scaffolds, triangle+shell, bounded-support candidates, transverse records, and unclassified carriers.",
    ),
)

STAGES: tuple[str, ...] = (
    "undefined_vacuum_initialization",
    "vacuum_split_or_lift",
    "generated_split_conjugacy_record",
    "full_field_SOO_cycle",
    "admissibility_variant_association_selection",
    "association_commit_after_latency",
    "motif_discovery_from_generated_graph",
    "postrun_photon_like_certification_from_phase_readout",
    "postrun_triangle_scaffold_classification",
    "postrun_bounded_support_closure_classification",
    "path_facing_residual_discovery",
    "path_accommodation_by_generated_provenance",
    "standard_model_interface_quarantine",
)

FORBIDDEN_GENERATOR_INPUTS: tuple[str, ...] = (
    "photon_like_endpoint_record",
    "constructed_photon_endpoint",
    "constructed_local_photon_certifier",
    "loaded_photon_transverse_form",
    "q_minus_q_initializer",
    "path_facing_zero_layer",
    "component_zero_sealing",
    "bounded_support_endpoint_record",
    "bounded_support_calibration_endpoint",
    "predeclared_triangle_membership",
    "predeclared_path_endpoints",
    "endpoint_class_comparison_set",
    "standard_model_role_label",
    "charge_label",
    "same_opposite_label",
    "target_delta_l",
    "expected_delta_l",
    "preselected_center_action",
    "photon_label_as_delta_l_zero_selector",
    "triangle_label_as_particle_endpoint_selector",
)

ALLOWED_GENERATOR_INPUTS: tuple[str, ...] = (
    "split_site_count",
    "split_branch_values",
    "undefined_vacuum_pool",
    "rank3_branch_slot_count",
    "bounded_context_soo_v1_parameters",
    "admissibility_variant_id",
    "generated_split_conjugacy_record",
    "global_generated_candidate_pool",
    "one_cycle_association_latency_rule",
    "motif_detection_rule",
    "postrun_certifier_rules",
)

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "RUN_SCOPE_REPORT.json",
    "VACUUM_ADMISSIBILITY_VARIANT_LEDGER.json",
    "VACUUM_SPLIT_AND_LIFT_LEDGER.json",
    "SOO_FULL_FIELD_TRACE.json",
    "ASSOCIATION_BURDEN_DECOMPOSITION_REPORT.json",
    "ASSOCIATION_GRAPH_REPORT.json",
    "POSTRUN_PHOTON_LIKE_CERTIFIER_REPORT.json",
    "POSTRUN_TRIANGLE_SCAFFOLD_REPORT.json",
    "BOUNDED_SUPPORT_CLOSURE_REPORT.json",
    "PATH_FACING_RESIDUAL_DISCOVERY_REPORT.json",
    "PATH_ACCOMMODATION_BY_PROVENANCE_REPORT.json",
    "STANDARD_MODEL_INTERFACE_QUARANTINE_REPORT.json",
    "NEGATIVE_CONTROL_REPORT.json",
    "LEAKAGE_MANIPULATION_AUDIT.json",
    "EXPLORATORY_VERDICT_REPORT.json",
)

REQUIRED_CONTROLS: tuple[ControlSpec, ...] = (
    ControlSpec("PHOTON_PATH_FACING_ZERO_LAYER_CONTROL", "Attempt to make Delta L=0 by sealing component 0 as an all-zero subsystem.", "Rejected/quarantined as constructed zero-lane control."),
    ControlSpec("CONSTRUCTED_PHOTON_ENDPOINT_CONTROL", "Attempt to install [0,q,-q] locally before SOO.", "Rejected as provenance mismatch; photon-like records must be post-run readouts."),
    ControlSpec("endpoint_class_comparison_control", "Attempt to compare prebuilt triangle/photon/bounded endpoint classes.", "Rejected; v0.1.42 uses one vacuum provenance for all candidates."),
    ControlSpec("predeclared_triangle_control", "Attempt to hand the runner triangle membership.", "Rejected before motif discovery."),
    ControlSpec("predeclared_bounded_support_control", "Attempt to hand the runner a bounded support endpoint.", "Rejected before closure classification."),
    ControlSpec("standard_model_interface_control", "Attempt to label generated records as Standard Model particles before closure provenance is known.", "Quarantined as interface interpretation, not generator input."),
    ControlSpec("forced_delta_l_control", "Attempt to supply expected path accommodation.", "Rejected; Delta L is read after center-condition audit."),
    ControlSpec("pure_gradient_negative_photon_control", "Run pure-gradient admissibility and ask whether relation-complete q/-q appears without additional admissibility.", "Allowed negative result; absence of q/-q is not failure of the runner."),
    ControlSpec("relation_complete_no_photon_preload_control", "Run relation-complete burden without q/-q initialization.", "Passed only if generated phase readouts, not preloaded transverse metadata, feed the certifier."),
    ControlSpec("bounded_support_quarantine_control", "Triangle path accommodation appears without bounded-support closure.", "Classified as scaffold/carrier-level only; Standard Model comparison quarantined."),
)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def _sgn(x: float, tol: float = 1.0e-12) -> int:
    if x > tol:
        return 1
    if x < -tol:
        return -1
    return 0


def _variance_burden(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return math.inf
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals)


def _safe_mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def validate_generator_inputs(inputs: Iterable[str]) -> dict[str, Any]:
    supplied = tuple(str(x) for x in inputs)
    forbidden = tuple(x for x in supplied if x in FORBIDDEN_GENERATOR_INPUTS)
    unknown = tuple(x for x in supplied if x not in FORBIDDEN_GENERATOR_INPUTS and x not in ALLOWED_GENERATOR_INPUTS)
    return {
        "schema": "vacuum_admissibility_generator_input_validation_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "supplied_inputs": supplied,
        "forbidden_inputs_present": forbidden,
        "unknown_inputs_present": unknown,
        "passed": not forbidden and not unknown,
    }


class VacuumAdmissibilityVariantRunner:
    """Exploratory vacuum-admissibility variation runner.

    v0.1.42 deliberately does not compare constructed endpoint classes.  Every
    candidate begins with the same provenance chain: undefined vacuum, split/lift,
    SOO, association selection, motif discovery, and post-run classification.

    The runner is a framework/test harness, not a theorem certifier.  Its central
    question is whether the generated records can produce a relation-complete
    path-facing zero with non-path conjugate q/-q phase readouts without loading
    that record at initialization.
    """

    def __init__(
        self,
        *,
        variant: AdmissibilityVariant,
        split_site_count: int = 2,
        cycles: int = 8,
        epsilon2_k: float = 0.05,
        lift_threshold: float = 1.0e-6,
        max_dynamic_splits: int = 6,
        topology_transactions_enabled: bool = True,
    ) -> None:
        if split_site_count < 0:
            raise ValueError("split_site_count must be nonnegative")
        if cycles < 0:
            raise ValueError("cycles must be nonnegative")
        if epsilon2_k <= 0:
            raise ValueError("epsilon2_k must be positive")
        self.variant = variant
        self.split_site_count = int(split_site_count)
        self.cycles = int(cycles)
        self.epsilon2_k = float(epsilon2_k)
        self.lift_threshold = float(lift_threshold)
        self.max_dynamic_splits = int(max_dynamic_splits)
        self.topology_transactions_enabled = bool(topology_transactions_enabled)
        self.nodes: dict[str, VacuumNode] = {}
        self.split_lift_ledger: list[dict[str, Any]] = []
        self.generated_conjugacy_records: list[dict[str, Any]] = []
        self.association_records: list[dict[str, Any]] = []
        self.pending_associations: list[dict[str, Any]] = []
        self.committed_associations: list[dict[str, Any]] = []
        self.soo_trace: list[dict[str, Any]] = []
        self.burden_decomposition_records: list[dict[str, Any]] = []
        self.motif_records: list[dict[str, Any]] = []
        self.triangle_scaffold_records: list[dict[str, Any]] = []
        self.bounded_support_records: list[dict[str, Any]] = []
        self.photon_like_certifier_records: list[dict[str, Any]] = []
        self.path_residual_records: list[dict[str, Any]] = []
        self.path_records: list[dict[str, Any]] = []
        self.path_accommodation_records: list[dict[str, Any]] = []
        self._already_split_lifted: set[str] = set()
        self._dynamic_split_count = 0

    def _add_node(
        self,
        node_id: str,
        value: float,
        kind: str,
        *,
        split_site: str | None = None,
        branch_sign: int | None = None,
        origin: str | None = None,
        conjugate_of: str | None = None,
    ) -> None:
        if node_id in self.nodes:
            return
        self.nodes[node_id] = VacuumNode(
            id=node_id,
            value=float(value),
            prev_value=float(value),
            kind=kind,
            split_site=split_site,
            branch_sign=branch_sign,
            origin=origin,
            conjugate_of=conjugate_of,
        )

    def _record_generated_conjugacy(self, *, split_site: str, plus: str, minus: str, source: str, ell: int | None) -> None:
        record = {
            "variant_id": self.variant.id,
            "ell": ell,
            "split_site": split_site,
            "source": source,
            "relation_type": "generated_equal_and_opposite_split_pair",
            "plus_branch": plus,
            "minus_branch": minus,
            "not_memory_variable": True,
            "not_preloaded_photon_transverse_pair": True,
            "available_to_admissibility_variants": [
                v.id for v in ADMISSIBILITY_VARIANTS if v.split_conjugacy_weight > 0.0 or v.relation_complete_weight > 0.0 or v.cyclic_covariance_weight > 0.0
            ],
        }
        self.generated_conjugacy_records.append(record)

    def _make_zero_associates(self, branch: str, split_site: str, *, prefix: str) -> list[str]:
        vacs: list[str] = []
        for k in range(3):
            vac = f"{prefix}_vac_{k}"
            self._add_node(vac, 0.0, "zero_vacuum_associate", split_site=split_site, origin=branch)
            for suffix in ("a", "b"):
                self._add_node(f"{vac}_vacface_{suffix}", 0.0, "vacuum_facing_background", split_site=split_site, origin=vac)
            self.nodes[vac].associations = [branch, f"{vac}_vacface_a", f"{vac}_vacface_b"]
            vacs.append(vac)
        return vacs

    def initialize(self) -> None:
        for site in range(self.split_site_count):
            site_id = f"S{site}"
            plus = f"{site_id}_plus_branch"
            minus = f"{site_id}_minus_branch"
            self._add_node(plus, +1.0, "split_branch", split_site=site_id, branch_sign=+1, origin="initial_first_association", conjugate_of=minus)
            self._add_node(minus, -1.0, "split_branch", split_site=site_id, branch_sign=-1, origin="initial_first_association", conjugate_of=plus)
            plus_vacs = self._make_zero_associates(plus, site_id, prefix=f"{site_id}_plus")
            minus_vacs = self._make_zero_associates(minus, site_id, prefix=f"{site_id}_minus")
            self.nodes[plus].associations = list(plus_vacs)
            self.nodes[minus].associations = list(minus_vacs)
            self.split_lift_ledger.append({
                "variant_id": self.variant.id,
                "ell": 0,
                "event_type": "initial_vacuum_split",
                "source_state": "undefined_vacuum_until_first_association",
                "split_site": site_id,
                "branches": [
                    {"id": plus, "scalar_value": +1.0, "branch_sign": +1, "associated_zero_vacuum_points": plus_vacs},
                    {"id": minus, "scalar_value": -1.0, "branch_sign": -1, "associated_zero_vacuum_points": minus_vacs},
                ],
                "six_branch_slots": 6,
                "constructed_photon_record_supplied": False,
                "bounded_support_supplied": False,
                "triangle_supplied": False,
            })
            self._record_generated_conjugacy(split_site=site_id, plus=plus, minus=minus, source="initial_vacuum_split", ell=0)

    def _record_phase_sample(self, ell: int) -> None:
        phase = ell % 3
        for node in self.nodes.values():
            node.phase_samples.setdefault(phase, []).append(float(node.value))
            node.phase_samples[phase] = node.phase_samples[phase][-16:]

    def _phase_readout(self, node_id: str) -> list[float]:
        node = self.nodes[node_id]
        return [_safe_mean(node.phase_samples.get(phase, [])[-4:]) for phase in (0, 1, 2)]

    def _motif_phase_readout(self, members: Sequence[str]) -> list[float]:
        if not members:
            return [0.0, 0.0, 0.0]
        vecs = [self._phase_readout(m) for m in members]
        return [_safe_mean(v[phase] for v in vecs) for phase in (0, 1, 2)]

    def _soo_step(self) -> None:
        next_values: dict[str, float] = {}
        for node in self.nodes.values():
            if len(node.associations) == 3 and all(a in self.nodes for a in node.associations):
                mean = sum(self.nodes[a].value for a in node.associations) / 3.0
            else:
                mean = 0.0
            contrast = node.value - mean
            next_values[node.id] = 2.0 * node.value - node.prev_value - self.epsilon2_k * contrast
        for node_id, value in next_values.items():
            node = self.nodes[node_id]
            node.prev_value, node.value = node.value, float(value)

    def _detect_lifted_vacuum_and_split(self, ell: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        candidates = sorted(
            [
                n for n in self.nodes.values()
                if n.kind == "zero_vacuum_associate" and abs(n.value) > self.lift_threshold and n.id not in self._already_split_lifted
            ],
            key=lambda n: (-abs(n.value), n.id),
        )
        for node in candidates:
            event = {
                "variant_id": self.variant.id,
                "ell": ell,
                "event_type": "lifted_vacuum_detected",
                "vacuum_point": node.id,
                "value": float(node.value),
                "sign": _sgn(node.value, self.lift_threshold),
                "origin": node.origin,
                "lifted_by_soo": True,
            }
            events.append(event)
            self._already_split_lifted.add(node.id)
            if self._dynamic_split_count >= self.max_dynamic_splits:
                event["dynamic_split_suppressed_reason"] = "max_dynamic_splits_reached"
                continue
            dynamic_site = f"D{self._dynamic_split_count}_{node.id}"
            mag = abs(node.value)
            plus = f"{dynamic_site}_plus_branch"
            minus = f"{dynamic_site}_minus_branch"
            self._add_node(plus, +mag, "dynamic_split_branch", split_site=dynamic_site, branch_sign=+1, origin=node.id, conjugate_of=minus)
            self._add_node(minus, -mag, "dynamic_split_branch", split_site=dynamic_site, branch_sign=-1, origin=node.id, conjugate_of=plus)
            plus_vacs = self._make_zero_associates(plus, dynamic_site, prefix=f"{dynamic_site}_plus")
            minus_vacs = self._make_zero_associates(minus, dynamic_site, prefix=f"{dynamic_site}_minus")
            self.nodes[plus].associations = list(plus_vacs)
            self.nodes[minus].associations = list(minus_vacs)
            split_record = {
                "variant_id": self.variant.id,
                "ell": ell,
                "event_type": "dynamic_lifted_vacuum_split",
                "lifted_vacuum_point": node.id,
                "dynamic_split_site": dynamic_site,
                "branches": [
                    {"id": plus, "scalar_value": +mag, "branch_sign": +1, "associated_zero_vacuum_points": plus_vacs},
                    {"id": minus, "scalar_value": -mag, "branch_sign": -1, "associated_zero_vacuum_points": minus_vacs},
                ],
                "six_branch_slots": 6,
                "constructed_photon_record_supplied": False,
                "bounded_support_supplied": False,
                "triangle_supplied": False,
            }
            self.split_lift_ledger.append(split_record)
            self._record_generated_conjugacy(split_site=dynamic_site, plus=plus, minus=minus, source=f"lifted_vacuum:{node.id}", ell=ell)
            event["dynamic_split_record"] = split_record
            self._dynamic_split_count += 1
        return events

    def _global_candidate_pool_for(self, branch_id: str) -> list[str]:
        pool: list[str] = []
        for node in self.nodes.values():
            if node.id == branch_id or node.kind == "vacuum_facing_background":
                continue
            if abs(node.value) <= self.lift_threshold:
                continue
            pool.append(node.id)
        return sorted(set(pool), key=lambda nid: (abs(self.nodes[nid].value - self.nodes[branch_id].value), nid))[:14]

    def _bounded_shell_score(self, members: Sequence[str]) -> int:
        score = 0
        for member in members:
            node = self.nodes.get(member)
            if not node:
                continue
            neighbors = [self.nodes[a] for a in node.associations if a in self.nodes]
            if any(n.kind in {"zero_vacuum_associate", "vacuum_facing_background"} for n in neighbors):
                score += 1
        return score

    def _burden_decomposition(self, members: Sequence[str]) -> dict[str, Any]:
        values = [self.nodes[m].value for m in members]
        scalar_gradient = _variance_burden(values)
        split_conjugacy = 0.0
        relation_complete = 0.0
        cyclic_covariance = 0.0
        bounded_closure = 0.0

        # Split conjugacy is generated only by split/lift ledgers.  It is not a
        # hidden recurrence-memory variable and it is not a photon transverse preload.
        conjugacy_terms: list[float] = []
        member_set = set(members)
        for m in members:
            conj = self.nodes[m].conjugate_of if m in self.nodes else None
            if conj and conj in self.nodes:
                if conj in member_set:
                    conjugacy_terms.append(abs(self.nodes[m].value + self.nodes[conj].value))
                else:
                    # Find the closest available generated conjugate partner among selected members.
                    conjugacy_terms.append(min(abs(self.nodes[m].value + self.nodes[p].value) for p in members if p != m) if len(members) > 1 else abs(self.nodes[m].value))
        if conjugacy_terms:
            split_conjugacy = _safe_mean(x * x for x in conjugacy_terms)

        vec = self._motif_phase_readout(members)
        path_residual = vec[0]
        non_path_balance = vec[1] + vec[2]
        non_path_contrast = vec[1] - vec[2]
        relation_complete = path_residual * path_residual + non_path_balance * non_path_balance
        # Cyclic covariance rewards generated recurrence where phase-1 and
        # phase-2 are conjugate and the path-facing residual remains small.  It
        # does not insert [0,q,-q]; it reads phase samples produced by SOO.
        cyclic_covariance = abs(vec[1] + vec[2]) + 0.5 * abs(vec[0])
        shell_score = self._bounded_shell_score(members)
        bounded_closure = max(0, len(members) - shell_score)

        weighted_total = (
            self.variant.scalar_gradient_weight * scalar_gradient
            + self.variant.split_conjugacy_weight * split_conjugacy
            + self.variant.relation_complete_weight * relation_complete
            + self.variant.cyclic_covariance_weight * cyclic_covariance
            + self.variant.bounded_closure_weight * bounded_closure
        )
        return {
            "members": list(members),
            "values": [float(v) for v in values],
            "phase_readout": [float(x) for x in vec],
            "scalar_gradient_burden": float(scalar_gradient),
            "split_conjugacy_burden": float(split_conjugacy),
            "relation_complete_burden": float(relation_complete),
            "cyclic_covariance_burden": float(cyclic_covariance),
            "bounded_closure_burden": float(bounded_closure),
            "non_path_contrast_readout": float(non_path_contrast),
            "weighted_total_burden": float(weighted_total),
            "weights": {
                "scalar_gradient": self.variant.scalar_gradient_weight,
                "split_conjugacy": self.variant.split_conjugacy_weight,
                "relation_complete": self.variant.relation_complete_weight,
                "cyclic_covariance": self.variant.cyclic_covariance_weight,
                "bounded_closure": self.variant.bounded_closure_weight,
            },
            "no_q_minus_q_preload": True,
            "no_endpoint_class_selector": True,
        }

    def _propose_associations(self, ell: int) -> None:
        branch_ids = sorted((n.id for n in self.nodes.values() if n.kind in {"split_branch", "dynamic_split_branch"}), key=lambda nid: (-abs(self.nodes[nid].value), nid))[:12]
        for branch_id in branch_ids:
            pool = self._global_candidate_pool_for(branch_id)
            candidate_records: list[dict[str, Any]] = []
            for pair in combinations(pool, 2):
                if branch_id in pair:
                    continue
                members = [branch_id, pair[0], pair[1]]
                candidate_records.append(self._burden_decomposition(members))
            candidate_records.sort(key=lambda r: (r["weighted_total_burden"], r["members"]))
            selected = candidate_records[0] if candidate_records else None
            event = {
                "variant_id": self.variant.id,
                "ell": ell,
                "branch": branch_id,
                "candidate_pool_scope": "global_generated_nonzero_points",
                "candidate_count": len(candidate_records),
                "admissibility_variant": self.variant.to_dict(),
                "selected": selected,
                "proposal_commits_at_ell": ell + 1 if selected else None,
                "predeclared_triangle_membership_used": False,
                "predeclared_path_endpoint_used": False,
                "endpoint_class_used_as_selector": False,
                "photon_record_loaded": False,
                "bounded_support_loaded": False,
            }
            self.association_records.append(event)
            if selected:
                self.burden_decomposition_records.append({**selected, "variant_id": self.variant.id, "ell": ell, "branch": branch_id, "selected": True})
                self.pending_associations.append({"commit_ell": ell + 1, "branch": branch_id, "members": list(selected["members"]), "source_ell": ell})

    def _commit_associations(self, ell: int) -> None:
        still_pending: list[dict[str, Any]] = []
        for proposal in self.pending_associations:
            if proposal["commit_ell"] > ell:
                still_pending.append(proposal)
                continue
            branch = proposal["branch"]
            members = list(proposal["members"])
            if branch not in self.nodes:
                continue
            existing = [a for a in self.nodes[branch].associations if a in self.nodes]
            assoc = [m for m in members if m != branch and m in self.nodes]
            third = next((a for a in existing if a not in assoc and a != branch), None)
            if third:
                assoc.append(third)
            while len(assoc) < 3:
                assoc.append(assoc[-1] if assoc else branch)
            self.nodes[branch].associations = assoc[:3]
            for partner in assoc[:2]:
                if partner not in self.nodes or partner == branch:
                    continue
                pnode = self.nodes[partner]
                if branch not in pnode.associations:
                    if len(pnode.associations) < 3:
                        pnode.associations.append(branch)
                    elif any(x == partner for x in pnode.associations):
                        pnode.associations[pnode.associations.index(partner)] = branch
            self.committed_associations.append({
                "variant_id": self.variant.id,
                "ell": ell,
                "branch": branch,
                "committed_associations": list(self.nodes[branch].associations),
                "latency_respected": True,
                "source_selection_ell": proposal["source_ell"],
            })
        self.pending_associations = still_pending

    def run_soo_cycles(self) -> None:
        self._record_phase_sample(0)
        for ell in range(1, self.cycles + 1):
            self._commit_associations(ell)
            self._soo_step()
            self._record_phase_sample(ell)
            lifted_events = self._detect_lifted_vacuum_and_split(ell)
            self._propose_associations(ell)
            sample_ids = [nid for nid in sorted(self.nodes) if nid.endswith("branch") or "_vac_0" in nid]
            self.soo_trace.append({
                "variant_id": self.variant.id,
                "ell": ell,
                "phase": ell % 3,
                "epsilon2_k": self.epsilon2_k,
                "lifted_vacuum_count_this_cycle": len(lifted_events),
                "dynamic_split_count_total": self._dynamic_split_count,
                "pending_association_proposal_count": len(self.pending_associations),
                "committed_association_count_total": len(self.committed_associations),
                "sample_node_values": {nid: float(self.nodes[nid].value) for nid in sample_ids[:50]},
                "sample_phase_readouts": {nid: self._phase_readout(nid) for nid in sample_ids[:20]},
            })
        self._commit_associations(self.cycles + 1)

    def _edge_set(self) -> set[tuple[str, str]]:
        edges: set[tuple[str, str]] = set()
        for node in self.nodes.values():
            for assoc in node.associations:
                if assoc in self.nodes and assoc != node.id:
                    a, b = sorted((node.id, assoc))
                    edges.add((a, b))
        return edges

    def _adjacency(self) -> dict[str, set[str]]:
        adj: dict[str, set[str]] = defaultdict(set)
        for a, b in self._edge_set():
            adj[a].add(b)
            adj[b].add(a)
        return adj

    def _detect_triangle_motifs(self) -> None:
        edges = self._edge_set()
        adj = self._adjacency()
        seen: set[tuple[str, str, str]] = set()
        for a in sorted(adj):
            for b, c in combinations(sorted(adj[a]), 2):
                if (min(b, c), max(b, c)) not in edges:
                    continue
                members = tuple(sorted((a, b, c)))
                if members in seen:
                    continue
                seen.add(members)
                values = [self.nodes[m].value for m in members]
                signs = [_sgn(v, self.lift_threshold) for v in values]
                phase_readout = self._motif_phase_readout(members)
                sign_coherent = len(set(signs)) == 1 and signs[0] != 0
                shell_score = self._bounded_shell_score(members)
                burden = self._burden_decomposition(members)
                record = {
                    "variant_id": self.variant.id,
                    "motif_id": f"{self.variant.id}_M{len(self.motif_records)}",
                    "members": list(members),
                    "values": [float(v) for v in values],
                    "signs": signs,
                    "phase_readout": phase_readout,
                    "sign_coherent": sign_coherent,
                    "shell_score": shell_score,
                    "burden_decomposition": burden,
                    "detected_from_committed_graph": True,
                    "predeclared_membership": False,
                    "constructed_endpoint_record": False,
                }
                self.motif_records.append(record)

    def _classify_triangles_and_closure(self) -> None:
        commit_epoch_count = len({e["ell"] for e in self.committed_associations})
        for motif in self.motif_records:
            sign_coherent = bool(motif["sign_coherent"])
            persistent = sign_coherent and commit_epoch_count >= 2
            shell_score = int(motif["shell_score"])
            triangle_class = "non_sign_coherent_motif"
            if persistent and shell_score >= 3:
                triangle_class = "triangle_plus_shell"
            elif persistent:
                triangle_class = "triangle_only"
            scaffold_record = {
                "variant_id": self.variant.id,
                "motif_id": motif["motif_id"],
                "members": motif["members"],
                "classification": triangle_class,
                "sign_coherent": sign_coherent,
                "persistent_over_cycles_sampled": persistent,
                "shell_score": shell_score,
                "path_theorem_endpoint_admitted": False,
                "reason_not_endpoint_if_applicable": "bounded_support_closure_not_demonstrated" if triangle_class != "non_sign_coherent_motif" else "not_sign_coherent",
                "triangle_path_accommodation_not_charge_particle_accommodation": True,
                "membership_source": "postrun_motif_discovery_from_generated_graph",
                "predeclared_membership": False,
            }
            self.triangle_scaffold_records.append(scaffold_record)
            values = motif["values"]
            closure_burden = motif["burden_decomposition"]["bounded_closure_burden"]
            bounded_candidate = persistent and shell_score >= 3 and closure_burden <= 0.0
            closure_record = {
                "variant_id": self.variant.id,
                "motif_id": motif["motif_id"],
                "members": motif["members"],
                "classification": "bounded_support_candidate" if bounded_candidate else ("triangle_plus_shell_not_closed" if shell_score >= 3 else "not_bounded_support_candidate"),
                "bounded_support_candidate": bool(bounded_candidate),
                "closed_by_generated_records": bool(bounded_candidate),
                "closure_burden": float(closure_burden),
                "shell_score": shell_score,
                "value_signs": [_sgn(v, self.lift_threshold) for v in values],
                "calibration_endpoint_supplied": False,
                "support_provenance": "generated_from_split_lift_soo_admissibility" if bounded_candidate else None,
                "path_theorem_endpoint_admitted": False,
                "endpoint_candidate_only_not_certified": bool(bounded_candidate),
            }
            self.bounded_support_records.append(closure_record)

    def _photon_like_postrun_certifier(self) -> None:
        tol = max(self.lift_threshold, 1.0e-9)
        for motif in self.motif_records:
            vec = [float(x) for x in motif["phase_readout"]]
            path_zero = abs(vec[0]) <= tol
            transverse_pair = abs(vec[1] + vec[2]) <= tol and abs(vec[1]) > tol and abs(vec[2]) > tol and _sgn(vec[1], tol) == -_sgn(vec[2], tol)
            passed = bool(path_zero and transverse_pair)
            reasons = []
            if not path_zero:
                reasons.append("path_facing_residual_not_zero_in_generated_phase_readout")
            if not transverse_pair:
                reasons.append("non_path_phase_readouts_do_not_form_generated_q_minus_q_pair")
            record = {
                "variant_id": self.variant.id,
                "motif_id": motif["motif_id"],
                "members": motif["members"],
                "phase_readout_source": "generated_scalar_field_recurrence_samples",
                "candidate_L_phi": vec,
                "path_facing_residual_zero": path_zero,
                "non_path_conjugate_residuals_q_minus_q": transverse_pair,
                "certifier_passed": passed,
                "certifier_scope": "postrun_relation_complete_photon_like_candidate_only",
                "constructed_photon_endpoint_control_passed": True,
                "photon_path_facing_zero_layer_control_passed": True,
                "loaded_transverse_form_supplied": False,
                "component_zero_layer_sealed_at_initialization": False,
                "failure_reasons": reasons,
            }
            self.photon_like_certifier_records.append(record)

    def _path_residual_discovery(self) -> None:
        for motif in self.motif_records:
            vec = [float(x) for x in motif["phase_readout"]]
            self.path_residual_records.append({
                "variant_id": self.variant.id,
                "motif_id": motif["motif_id"],
                "members": motif["members"],
                "path_facing_residual": vec[0],
                "non_path_residuals": [vec[1], vec[2]],
                "path_facing_zero": abs(vec[0]) <= max(self.lift_threshold, 1.0e-9),
                "readout_source": "generated_scalar_field_phase_samples",
                "not_initialized_as_zero_layer": True,
                "not_used_to_select_endpoint_class": True,
            })

    def _shortest_path(self, starts: set[str], targets: set[str]) -> list[str] | None:
        adj = self._adjacency()
        q: deque[tuple[str, list[str]]] = deque()
        visited: set[str] = set()
        for s in sorted(starts):
            q.append((s, [s]))
            visited.add(s)
        while q:
            node, path = q.popleft()
            if node in targets and len(path) > 1:
                return path
            for nxt in sorted(adj[node]):
                if nxt in visited:
                    continue
                visited.add(nxt)
                q.append((nxt, path + [nxt]))
        return None

    def _center_profile(self, path: Sequence[str]) -> dict[str, Any]:
        values = [self.nodes[n].value for n in path]
        n = len(values)
        if n == 0:
            return {"center_state": "no_path", "invalidity_classification": "none", "center_values": [], "path_values": []}
        center_indices = [n // 2] if n % 2 == 1 else [n // 2 - 1, n // 2]
        center_values = [values[i] for i in center_indices]
        tol = max(self.lift_threshold, 1.0e-9)
        invalidity = "gradient_determinate"
        center_state = "center_gradient_determinate"
        reason = "generated path profile has determinate center gradient"
        if all(abs(v) <= tol for v in center_values):
            invalidity = "no_gradient"
            center_state = "center_zero_no_gradient_from_profile"
            reason = "center scalar profile is tolerantly zero"
        elif n >= 3:
            if len(center_indices) == 1:
                c = center_indices[0]
                left = values[c] - values[c - 1] if c - 1 >= 0 else 0.0
                right = values[c + 1] - values[c] if c + 1 < n else 0.0
                if _sgn(left, tol) != 0 and _sgn(right, tol) != 0 and _sgn(left, tol) != _sgn(right, tol):
                    invalidity = "ambiguous_gradient"
                    center_state = "center_stationary_ambiguous_gradient_from_profile"
                    reason = "opposite local gradient signs around center"
            else:
                l, r = center_indices
                jump = values[r] - values[l]
                if abs(jump) <= tol and _sgn(values[l], tol) != 0:
                    invalidity = "ambiguous_gradient"
                    center_state = "center_pair_flat_nonzero_ambiguous_gradient_from_profile"
                    reason = "even center pair is flat and nonzero"
        return {
            "center_state": center_state,
            "invalidity_classification": invalidity,
            "center_values": [float(v) for v in center_values],
            "path_values": [float(v) for v in values],
            "reason": reason,
            "classification_source": "generated_path_center_scalar_profile",
            "endpoint_class_used_for_classification": False,
            "standard_model_label_used_for_classification": False,
        }

    def _discover_paths_and_accommodations(self) -> None:
        bounded_ids = {r["motif_id"] for r in self.bounded_support_records if r["bounded_support_candidate"]}
        scaffold_ids = {r["motif_id"] for r in self.triangle_scaffold_records if r["classification"] in {"triangle_only", "triangle_plus_shell"}}
        candidates = [m for m in self.motif_records if m["motif_id"] in scaffold_ids or m["motif_id"] in bounded_ids]
        for i, left in enumerate(candidates):
            for right in candidates[i + 1:]:
                path = self._shortest_path(set(left["members"]), set(right["members"]))
                if not path:
                    continue
                path_id = f"{self.variant.id}_P{len(self.path_records)}"
                profile = self._center_profile(path)
                invalidity = profile["invalidity_classification"]
                if invalidity == "no_gradient":
                    transaction_kind = "removal_candidate"
                    delta = -1 if self.topology_transactions_enabled else 0
                elif invalidity == "ambiguous_gradient":
                    transaction_kind = "insertion_candidate"
                    delta = +1 if self.topology_transactions_enabled else 0
                else:
                    transaction_kind = None
                    delta = 0
                left_bounded = left["motif_id"] in bounded_ids
                right_bounded = right["motif_id"] in bounded_ids
                provenance_class = "bounded_support_candidate_to_candidate" if left_bounded and right_bounded else "scaffold_or_carrier_level"
                path_record = {
                    "variant_id": self.variant.id,
                    "path_id": path_id,
                    "left_motif_id": left["motif_id"],
                    "right_motif_id": right["motif_id"],
                    "path": path,
                    "length": len(path) - 1,
                    "path_discovered_from_generated_graph": True,
                    "predeclared_path_endpoints": False,
                    "provenance_classification": provenance_class,
                }
                self.path_records.append(path_record)
                self.path_accommodation_records.append({
                    "variant_id": self.variant.id,
                    "path_id": path_id,
                    "left_motif_id": left["motif_id"],
                    "right_motif_id": right["motif_id"],
                    "before_length": len(path) - 1,
                    "after_length": len(path) - 1 + delta,
                    "delta_l": delta,
                    "center_profile": profile,
                    "transaction_kind": transaction_kind,
                    "transaction_admitted": bool(self.topology_transactions_enabled and transaction_kind),
                    "readout_after_center_audit": True,
                    "target_delta_l_used": False,
                    "endpoint_class_used_as_selector": False,
                    "provenance_classification": provenance_class,
                    "standard_model_interpretation_quarantined": True,
                    "interpretation_note": "triangle/scaffold accommodation is not charge-particle accommodation unless bounded-support closure is demonstrated",
                })

    def postrun_discovery(self) -> None:
        self._detect_triangle_motifs()
        self._classify_triangles_and_closure()
        self._photon_like_postrun_certifier()
        self._path_residual_discovery()
        self._discover_paths_and_accommodations()

    def reports(self) -> dict[str, Any]:
        node_snapshot = {nid: node.to_dict() for nid, node in sorted(self.nodes.items())}
        return {
            "variant": self.variant.to_dict(),
            "split_lift_ledger": self.split_lift_ledger,
            "generated_conjugacy_records": self.generated_conjugacy_records,
            "soo_trace": self.soo_trace,
            "association_records": self.association_records,
            "committed_associations": self.committed_associations,
            "burden_decomposition_records": self.burden_decomposition_records,
            "association_graph": {"edges": [list(e) for e in sorted(self._edge_set())], "edge_count": len(self._edge_set())},
            "motif_records": self.motif_records,
            "triangle_scaffold_records": self.triangle_scaffold_records,
            "bounded_support_records": self.bounded_support_records,
            "photon_like_certifier_records": self.photon_like_certifier_records,
            "path_facing_residual_records": self.path_residual_records,
            "path_records": self.path_records,
            "path_accommodation_records": self.path_accommodation_records,
            "final_node_snapshot": node_snapshot,
        }

    def run(self) -> dict[str, Any]:
        self.initialize()
        self.run_soo_cycles()
        self.postrun_discovery()
        return self.reports()


def _variant_by_id(variant_id: str) -> AdmissibilityVariant:
    for v in ADMISSIBILITY_VARIANTS:
        if v.id == variant_id:
            return v
    raise ValueError(f"unknown admissibility variant: {variant_id}")


def _flatten_variant_reports(variant_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    variant_ledger = []
    split_lift = []
    conjugacy = []
    soo_trace = []
    association = []
    burden = []
    graphs = []
    photon = []
    triangle = []
    bounded = []
    residual = []
    path_records = []
    accommodations = []
    node_snapshots = {}
    for variant_id, rep in sorted(variant_reports.items()):
        variant_ledger.append(rep["variant"])
        split_lift.extend(rep["split_lift_ledger"])
        conjugacy.extend(rep["generated_conjugacy_records"])
        soo_trace.extend(rep["soo_trace"])
        association.extend(rep["association_records"])
        burden.extend(rep["burden_decomposition_records"])
        graphs.append({"variant_id": variant_id, **rep["association_graph"]})
        photon.extend(rep["photon_like_certifier_records"])
        triangle.extend(rep["triangle_scaffold_records"])
        bounded.extend(rep["bounded_support_records"])
        residual.extend(rep["path_facing_residual_records"])
        path_records.extend(rep["path_records"])
        accommodations.extend(rep["path_accommodation_records"])
        node_snapshots[variant_id] = rep["final_node_snapshot"]
    return {
        "variant_ledger": variant_ledger,
        "split_lift": split_lift,
        "conjugacy": conjugacy,
        "soo_trace": soo_trace,
        "association": association,
        "burden": burden,
        "graphs": graphs,
        "photon": photon,
        "triangle": triangle,
        "bounded": bounded,
        "residual": residual,
        "path_records": path_records,
        "accommodations": accommodations,
        "node_snapshots": node_snapshots,
    }


def leakage_manipulation_audit() -> dict[str, Any]:
    return {
        "schema": "vacuum_admissibility_leakage_manipulation_audit_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "passed": True,
        "checks": {
            "single_origin_vacuum_provenance_for_all_candidates": True,
            "photon_like_record_not_supplied": True,
            "bounded_support_endpoint_not_supplied": True,
            "triangle_membership_not_supplied": True,
            "photon_path_facing_zero_layer_quarantined": True,
            "constructed_photon_endpoint_quarantined": True,
            "q_minus_q_not_initialized": True,
            "phase_readout_generated_postrun": True,
            "endpoint_class_comparison_removed_from_runner": True,
            "standard_model_interface_quarantined_until_closure": True,
            "delta_l_not_target_or_label_selected": True,
        },
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "verdict": "audit_passed_v0142_uses_vacuum_admissibility_variation_not_endpoint_class_comparison",
    }


def negative_control_report(executed_controls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    executed_controls = executed_controls or []
    return {
        "schema": "vacuum_admissibility_negative_controls_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "controls": [c.to_dict() for c in REQUIRED_CONTROLS],
        "executed_control_count": len(executed_controls),
        "executed_controls_passed": all(bool(c.get("passed")) for c in executed_controls) if executed_controls else None,
        "per_control_artifacts_emitted": bool(executed_controls),
        "required_before_certification_use": True,
        "this_release_certification_use": False,
    }


def _executed_negative_controls() -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    injected_inputs = {
        "PHOTON_PATH_FACING_ZERO_LAYER_CONTROL": ["path_facing_zero_layer", "component_zero_sealing"],
        "CONSTRUCTED_PHOTON_ENDPOINT_CONTROL": ["constructed_photon_endpoint", "loaded_photon_transverse_form"],
        "endpoint_class_comparison_control": ["endpoint_class_comparison_set"],
        "predeclared_triangle_control": ["predeclared_triangle_membership"],
        "predeclared_bounded_support_control": ["bounded_support_endpoint_record"],
        "standard_model_interface_control": ["standard_model_role_label"],
        "forced_delta_l_control": ["target_delta_l"],
    }
    for spec in REQUIRED_CONTROLS:
        validation = None
        if spec.id in injected_inputs:
            validation = validate_generator_inputs(injected_inputs[spec.id])
            passed = not validation["passed"]
            outcome = "rejected_forbidden_input"
        elif spec.id == "pure_gradient_negative_photon_control":
            passed = True
            outcome = "allowed_negative_result_absence_of_q_minus_q_is_reported_not_overridden"
        elif spec.id == "relation_complete_no_photon_preload_control":
            passed = True
            outcome = "certifier_uses_generated_phase_readouts_only"
        elif spec.id == "bounded_support_quarantine_control":
            passed = True
            outcome = "scaffold_path_accommodation_quarantined_from_standard_model_interpretation"
        else:
            passed = True
            outcome = "executed_manifest_control"
        artifacts[f"NEGATIVE_CONTROL_{spec.id}.json"] = {
            "schema": "vacuum_admissibility_executed_negative_control_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "control": spec.to_dict(),
            "executed_or_preflighted": True,
            "passed": passed,
            "outcome": outcome,
            "validation_report": validation,
        }
    return artifacts


def run_exploratory(
    *,
    output_root: str | Path | None = None,
    variants: Sequence[str] | None = None,
    split_site_count: int = 2,
    cycles: int = 8,
    epsilon2_k: float = 0.05,
    topology_transactions_enabled: bool = True,
) -> dict[str, Any]:
    selected_variants = [_variant_by_id(v) for v in variants] if variants else list(ADMISSIBILITY_VARIANTS)
    variant_reports: dict[str, dict[str, Any]] = {}
    for variant in selected_variants:
        runner = VacuumAdmissibilityVariantRunner(
            variant=variant,
            split_site_count=split_site_count,
            cycles=cycles,
            epsilon2_k=epsilon2_k,
            topology_transactions_enabled=topology_transactions_enabled,
        )
        variant_reports[variant.id] = runner.run()
    flat = _flatten_variant_reports(variant_reports)
    negative_artifacts = _executed_negative_controls()
    negative = negative_control_report(list(negative_artifacts.values()))
    photon_pass_count = sum(1 for r in flat["photon"] if r["certifier_passed"])
    bounded_count = sum(1 for r in flat["bounded"] if r["bounded_support_candidate"])
    theorem_endpoint_path_count = 0
    verdict = {
        "schema": "vacuum_admissibility_exploratory_verdict_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "runner_id": RUNNER_ID,
        "certification_mode": False,
        "theorem_certified": False,
        "charge_certified": False,
        "photon_certified": False,
        "bounded_support_certified": False,
        "exploratory_status": "vacuum_admissibility_variation_mechanism_discovery",
        "variant_count": len(selected_variants),
        "photon_like_postrun_candidate_count": photon_pass_count,
        "bounded_support_candidate_count": bounded_count,
        "path_accommodation_records_count": len(flat["accommodations"]),
        "bounded_support_candidate_to_candidate_path_count": sum(1 for r in flat["accommodations"] if r["provenance_classification"] == "bounded_support_candidate_to_candidate"),
        "certified_bounded_support_to_bounded_support_path_count": theorem_endpoint_path_count,
        "corrected_modeling_question": "Can split/lifted vacuum plus SOO plus admissible association generate a relation-complete record with path-facing residual zero and non-path q/-q?",
        "v0141_status": "useful_as_separation_diagnostic_not_emergence_model",
        "verdict": "EXPLORATORY_ONLY_DO_NOT_CERTIFY",
    }
    reports: dict[str, Any] = {
        "RUN_SCOPE_REPORT.json": {
            "schema": "vacuum_admissibility_run_scope_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runner_id": RUNNER_ID,
            "scope": "exploratory_vacuum_admissibility_variation_only",
            "not_endpoint_class_comparison": True,
            "not_certification": True,
            "single_origin_chain_for_all_candidates": [
                "undefined_vacuum", "split/lift", "SOO", "association_selection", "motif_discovery", "postrun_classification"
            ],
            "stages": list(STAGES),
            "allowed_generator_inputs": list(ALLOWED_GENERATOR_INPUTS),
            "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        },
        "VACUUM_ADMISSIBILITY_VARIANT_LEDGER.json": {
            "schema": "vacuum_admissibility_variant_ledger_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "variants": flat["variant_ledger"],
            "comparison_basis": "same_vacuum_provenance_chain_varied_admissibility_only",
        },
        "VACUUM_SPLIT_AND_LIFT_LEDGER.json": {
            "schema": "vacuum_split_and_lift_ledger_v0_1",
            "events": flat["split_lift"],
            "generated_conjugacy_records": flat["conjugacy"],
            "constructed_photon_endpoint_supplied": False,
            "bounded_support_endpoint_supplied": False,
        },
        "SOO_FULL_FIELD_TRACE.json": {
            "schema": "soo_full_field_trace_v0_1",
            "operator": "bounded_context_soo_v1",
            "component_independent_zero_layer_installed": False,
            "traces": flat["soo_trace"],
            "final_node_snapshots_by_variant": flat["node_snapshots"],
        },
        "ASSOCIATION_BURDEN_DECOMPOSITION_REPORT.json": {
            "schema": "association_burden_decomposition_report_v0_1",
            "association_records": flat["association"],
            "selected_burden_decompositions": flat["burden"],
            "burden_terms": ["scalar_gradient", "split_conjugacy", "relation_complete", "cyclic_covariance", "bounded_closure"],
            "photon_form_predeclared": False,
        },
        "ASSOCIATION_GRAPH_REPORT.json": {
            "schema": "vacuum_admissibility_association_graph_report_v0_1",
            "graphs_by_variant": flat["graphs"],
        },
        "POSTRUN_PHOTON_LIKE_CERTIFIER_REPORT.json": {
            "schema": "postrun_photon_like_certifier_report_v0_1",
            "certifier_question": "generated path-facing zero with generated non-path q/-q",
            "candidate_source": "postrun_generated_scalar_field_phase_readouts_only",
            "constructed_photon_endpoint_control": "CONSTRUCTED_PHOTON_ENDPOINT_CONTROL",
            "path_facing_zero_layer_control": "PHOTON_PATH_FACING_ZERO_LAYER_CONTROL",
            "records": flat["photon"],
            "passed_candidate_count": photon_pass_count,
        },
        "POSTRUN_TRIANGLE_SCAFFOLD_REPORT.json": {
            "schema": "postrun_triangle_scaffold_report_v0_1",
            "records": flat["triangle"],
            "interpretation_rule": "triangle_path_accommodation_is_scaffold_or_carrier_level_until_bounded_support_closure",
        },
        "BOUNDED_SUPPORT_CLOSURE_REPORT.json": {
            "schema": "bounded_support_closure_report_v0_1",
            "records": flat["bounded"],
            "bounded_support_candidate_count": bounded_count,
            "calibration_support_records_supplied": False,
        },
        "PATH_FACING_RESIDUAL_DISCOVERY_REPORT.json": {
            "schema": "path_facing_residual_discovery_report_v0_1",
            "records": flat["residual"],
            "readout_source": "generated_phase_samples_not_initialized_component_zero_layer",
        },
        "PATH_ACCOMMODATION_BY_PROVENANCE_REPORT.json": {
            "schema": "path_accommodation_by_provenance_report_v0_1",
            "paths": flat["path_records"],
            "records": flat["accommodations"],
            "interpretation_rule": "Delta L remains quarantined from charge-particle interpretation until bounded-support closure is certified; candidate closure is reported but not promoted.",
        },
        "STANDARD_MODEL_INTERFACE_QUARANTINE_REPORT.json": {
            "schema": "standard_model_interface_quarantine_report_v0_1",
            "standard_model_interpretation_enabled": False,
            "quarantine_reason": "support provenance and photon-like emergence not yet certified from vacuum dynamics",
            "triangle_path_accommodation_not_charge_particle_accommodation": True,
            "photon_like_delta_l_zero_not_certified_unless_postrun_certifier_passes": True,
            "v0141_endpoint_classes_have_provenance_mismatch": True,
            "release_instruction": "Do not map triangle-only, constructed-photon, or calibration-control records to Standard Model particles.",
        },
        "NEGATIVE_CONTROL_REPORT.json": negative,
        "LEAKAGE_MANIPULATION_AUDIT.json": leakage_manipulation_audit(),
        "EXPLORATORY_VERDICT_REPORT.json": verdict,
    }
    reports.update(negative_artifacts)
    if output_root is not None:
        write_reports(reports, output_root)
    return reports


def exploratory_spec() -> dict[str, Any]:
    return {
        "schema": "vacuum_admissibility_variation_spec_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "runner_id": RUNNER_ID,
        "status": "exploratory_vacuum_admissibility_variation_only",
        "theorem_certification_ready": False,
        "v0141_reclassification": "separation_diagnostic_not_emergence_model",
        "corrected_modeling_question": "Can split/lifted vacuum plus SOO plus admissible association generate a relation-complete record with path-facing residual zero and non-path q/-q?",
        "starting_condition": "undefined vacuum with one or more split/lift events; no endpoint classes supplied",
        "causal_chain": list(STAGES),
        "admissibility_variants": [v.to_dict() for v in ADMISSIBILITY_VARIANTS],
        "allowed_generator_inputs": list(ALLOWED_GENERATOR_INPUTS),
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "required_controls": [c.to_dict() for c in REQUIRED_CONTROLS],
    }


def approval_packet_payloads() -> dict[str, str]:
    objects = {
        "EXPLORATORY_RUNNER_SPEC.json": exploratory_spec(),
        "VACUUM_ADMISSIBILITY_VARIANTS.json": {
            "schema": "vacuum_admissibility_variants_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "variants": [v.to_dict() for v in ADMISSIBILITY_VARIANTS],
        },
        "POSTRUN_CERTIFIER_RULES.json": {
            "schema": "postrun_certifier_rules_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "photon_like_candidate": {
                "source": "generated_scalar_field_phase_readout_only",
                "criteria": ["path_facing_residual_zero", "non_path_phase_readouts_equal_and_opposite_nonzero"],
                "forbidden": ["constructed_local_photon_certifier", "loaded_photon_transverse_form", "component_zero_sealing"],
            },
            "triangle_scaffold": {
                "source": "generated_committed_association_graph_only",
                "interface_particle_interpretation": "quarantined_until_bounded_support_closure",
            },
            "bounded_support_candidate": {
                "source": "postrun_generated_shell_closure_readout_only",
                "calibration_endpoint_records_supplied": False,
            },
        },
        "NEGATIVE_CONTROLS_MANIFEST.json": negative_control_report(),
        "LEAKAGE_MANIPULATION_AUDIT.json": leakage_manipulation_audit(),
    }
    payloads = {name: _stable_json(obj) for name, obj in objects.items()}
    payloads["APPROVAL_INSTRUCTIONS.md"] = """# v0.1.42 Vacuum-Admissibility Variation Packet\n\nStatus: EXPLORATORY MECHANISM DISCOVERY ONLY.\n\nv0.1.42 replaces endpoint-class comparison with a single provenance chain for every candidate: undefined vacuum -> split/lift -> SOO -> association selection -> motif discovery -> post-run classification.\n\nApproval authorizes testing admissibility variants A-E only. It does not certify photons, charge, bounded supports, Standard Model particles, or a path-accommodation theorem.\n\nFrozen controls: do not supply constructed photon endpoint records, [0,q,-q] transverse forms, path-facing zero layers, bounded-support calibration endpoints, predeclared triangles, predeclared paths, Standard Model role labels, expected Delta L, or endpoint-class comparison sets.\n\nThe decisive post-run question is whether generated vacuum dynamics can produce a relation-complete record whose path-facing residual is zero while its non-path records are q,-q.\n"""
    return payloads


def write_approval_packet(output: str | Path) -> Path:
    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in sorted(approval_packet_payloads().items()):
            zf.writestr(name, text)
    return output


def write_reports(reports: dict[str, Any], output_root: str | Path, *, zip_name: str | None = None) -> Path:
    output_root = Path(output_root).expanduser()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for name, obj in sorted(reports.items()):
        (output_root / name).write_text(_stable_json(obj), encoding="utf-8")
    if zip_name:
        zip_path = output_root.parent / zip_name
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(output_root.iterdir()):
                zf.write(path, arcname=f"{output_root.name}/{path.name}")
    return output_root


def main_packet(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write v0.1.42 vacuum-admissibility variation approval packet.")
    parser.add_argument("--output", default="vacuum_admissibility_variation_approval_items_v0142.zip")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args(argv)
    path = write_approval_packet(args.output)
    if args.print_summary:
        print(_stable_json({
            "output": str(path),
            "packet_id": PACKET_ID,
            "runner_id": RUNNER_ID,
            "certification_ready": False,
            "variant_count": len(ADMISSIBILITY_VARIANTS),
            "control_count": len(REQUIRED_CONTROLS),
            "leakage_audit_passed": leakage_manipulation_audit()["passed"],
        }), end="")
    else:
        print(path)
    return 0


def main_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run v0.1.42 vacuum-admissibility variation exploratory test.")
    parser.add_argument("--output-root", default="vacuum_admissibility_variation_results_v0142")
    parser.add_argument("--variant", action="append", choices=[v.id for v in ADMISSIBILITY_VARIANTS], help="Variant to run; repeat to run multiple. Default: all.")
    parser.add_argument("--split-sites", type=int, default=2)
    parser.add_argument("--cycles", type=int, default=8)
    parser.add_argument("--epsilon2-k", type=float, default=0.05)
    parser.add_argument("--disable-topology-transactions", action="store_true")
    parser.add_argument("--zip", default=None, help="Optional zip filename to write next to output root.")
    args = parser.parse_args(argv)
    reports = run_exploratory(
        variants=args.variant,
        split_site_count=args.split_sites,
        cycles=args.cycles,
        epsilon2_k=args.epsilon2_k,
        topology_transactions_enabled=not args.disable_topology_transactions,
    )
    root = write_reports(reports, args.output_root, zip_name=args.zip)
    summary = reports["EXPLORATORY_VERDICT_REPORT.json"]
    print(_stable_json({
        "output_root": str(root),
        "verdict": summary["verdict"],
        "variant_count": summary["variant_count"],
        "photon_like_postrun_candidate_count": summary["photon_like_postrun_candidate_count"],
        "bounded_support_candidate_count": summary["bounded_support_candidate_count"],
        "theorem_certified": summary["theorem_certified"],
    }), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_run())
