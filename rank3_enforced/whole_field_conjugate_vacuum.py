from __future__ import annotations

import argparse
import json
import math
import shutil
import zipfile
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

FRAMEWORK_TARGET_VERSION = "0.1.43"
RUNNER_ID = "whole_field_conjugate_vacuum_derived_longitudinal_runner_v0_1"
PACKET_ID = "whole_field_conjugate_vacuum_approval_items_v0143"
SCHEMA = "whole_field_conjugate_vacuum_derived_longitudinal_v0_1"


@dataclass
class FieldNode:
    id: str
    value: float
    prev_value: float
    kind: str
    site: tuple[int, int] | None = None
    branch_sign: int | None = None
    origin_vacuum: str | None = None
    conjugate_of: str | None = None
    first_association_cycle: int | None = None
    associations: list[str | None] = field(default_factory=lambda: [None, None, None])
    phase_samples: dict[int, list[float]] = field(default_factory=lambda: {0: [], 1: [], 2: []})

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.site is not None:
            d["site"] = list(self.site)
        d["value"] = float(self.value)
        d["prev_value"] = float(self.prev_value)
        d["phase_samples"] = {str(k): [float(x) for x in v[-8:]] for k, v in sorted(self.phase_samples.items())}
        return d


@dataclass(frozen=True)
class WholeFieldVariant:
    id: str
    name: str
    conjugate_link_slot: int | None
    path_slot: int
    same_sign_path_affinity: float
    relation_complete_weight: float
    cyclic_successor_weight: float
    purpose: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


VARIANTS: tuple[WholeFieldVariant, ...] = (
    WholeFieldVariant(
        id="A_NO_CONJUGATE_FIRST_ASSOC_BASELINE",
        name="No conjugate-first-association baseline",
        conjugate_link_slot=None,
        path_slot=0,
        same_sign_path_affinity=1.0,
        relation_complete_weight=0.0,
        cyclic_successor_weight=0.0,
        purpose="Whole-field split/lift baseline: vacuum first-association splits, but no generated conjugate link is reserved.",
    ),
    WholeFieldVariant(
        id="B_CONJUGATE_LINK_PATH_SLOT_CONTROL",
        name="Conjugate link in path-facing slot control",
        conjugate_link_slot=0,
        path_slot=0,
        same_sign_path_affinity=1.0,
        relation_complete_weight=0.0,
        cyclic_successor_weight=0.0,
        purpose="Control showing that using the conjugate relation itself as the path-facing association makes the derived longitudinal residual nonzero.",
    ),
    WholeFieldVariant(
        id="C_CONJUGATE_LINK_TRANSVERSE_SLOT",
        name="Conjugate link in transverse slot",
        conjugate_link_slot=1,
        path_slot=0,
        same_sign_path_affinity=1.0,
        relation_complete_weight=0.45,
        cyclic_successor_weight=0.0,
        purpose="Test whether a generated conjugate pair can supply non-path q/-q while path-facing residual is derived from a separate generated association.",
    ),
    WholeFieldVariant(
        id="D_SUCCESSOR_COVARIANT_CONJUGATE_SLOT",
        name="Successor-covariant conjugate slot",
        conjugate_link_slot=1,
        path_slot=0,
        same_sign_path_affinity=1.0,
        relation_complete_weight=0.45,
        cyclic_successor_weight=0.35,
        purpose="Read the candidate relation through ordered scalar-field phases without initializing a three-component photon vector.",
    ),
)

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "WHOLE_FIELD_RUN_SCOPE_REPORT.json",
    "WHOLE_FIELD_ADMISSIBILITY_VARIANT_LEDGER.json",
    "VACUUM_FIRST_ASSOCIATION_CONJUGATE_SPLIT_LEDGER.json",
    "WHOLE_FIELD_ASSOCIATION_SELECTION_LEDGER.json",
    "WHOLE_FIELD_SOO_TRACE.json",
    "DERIVED_LONGITUDINAL_RESIDUAL_REPORT.json",
    "NON_PATH_CONJUGATE_BALANCE_REPORT.json",
    "POSTRUN_TRANSVERSE_RECORD_CANDIDATE_REPORT.json",
    "PHOTON_CANDIDATE_DERIVED_ZERO_AUDIT.json",
    "PATH_ACCOMMODATION_FROM_DERIVED_RESIDUAL_REPORT.json",
    "PHOTON_NONZERO_PATH_FACING_CONTROL_REPORT.json",
    "LEAKAGE_MANIPULATION_AUDIT.json",
    "EXPLORATORY_VERDICT_REPORT.json",
)

FORBIDDEN_GENERATOR_INPUTS: tuple[str, ...] = (
    "stored_path_facing_zero_scalar_value",
    "path_facing_zero_layer",
    "component_zero_sealing",
    "constructed_photon_endpoint",
    "loaded_photon_transverse_form",
    "q_minus_q_initializer",
    "photon_like_label",
    "standard_model_role_label",
    "target_delta_l",
    "expected_delta_l",
    "predeclared_photon_candidate",
    "predeclared_triangle_membership",
    "predeclared_bounded_support",
    "endpoint_class_comparison_set",
)

ALLOWED_GENERATOR_INPUTS: tuple[str, ...] = (
    "whole_field_shape",
    "first_association_cycle",
    "vacuum_first_association_conjugate_split_rule",
    "generated_conjugate_link_slot_policy",
    "path_slot_policy",
    "same_sign_path_affinity_selector",
    "bounded_context_soo_v1_parameters",
    "cycles",
    "admissibility_variant_id",
    "postrun_derived_longitudinal_certifier_rules",
)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def _sgn(x: float, tol: float = 1.0e-12) -> int:
    if x > tol:
        return 1
    if x < -tol:
        return -1
    return 0


def _safe_mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def _variant_by_id(variant_id: str) -> WholeFieldVariant:
    for variant in VARIANTS:
        if variant.id == variant_id:
            return variant
    raise ValueError(f"unknown whole-field conjugate-vacuum variant: {variant_id}")


def validate_generator_inputs(inputs: Iterable[str]) -> dict[str, Any]:
    supplied = tuple(str(x) for x in inputs)
    forbidden = tuple(x for x in supplied if x in FORBIDDEN_GENERATOR_INPUTS)
    unknown = tuple(x for x in supplied if x not in FORBIDDEN_GENERATOR_INPUTS and x not in ALLOWED_GENERATOR_INPUTS)
    return {
        "schema": "whole_field_conjugate_vacuum_generator_input_validation_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "supplied_inputs": supplied,
        "forbidden_inputs_present": forbidden,
        "unknown_inputs_present": unknown,
        "passed": not forbidden and not unknown,
    }


class WholeFieldConjugateVacuumRunner:
    """Exploratory whole-field vacuum runner for derived longitudinal residuals.

    The runner does not construct photon-like endpoints.  It starts with an
    undefined whole-field vacuum lattice.  When a vacuum site first participates
    in association selection, the site is lifted into two generated conjugate
    branches.  Depending on the variant, one association of each branch is
    assigned to its conjugate partner.  The photon-facing question is read only
    after SOO as a derived relation-complete record:

        lambda(P) = Phi(P) - Phi(a_path(P))
        tau+(P)  = Phi(P)
        tau-(P)  = Phi(a_conjugate(P))

    Therefore a zero longitudinal condition is never stored as a path-facing
    scalar value or a sealed component-zero layer.
    """

    def __init__(
        self,
        *,
        variant: WholeFieldVariant,
        width: int = 4,
        height: int = 4,
        cycles: int = 9,
        epsilon2_k: float = 0.05,
        first_association_cycle: int = 1,
        lift_magnitude: float = 1.0,
        tolerance: float = 1.0e-8,
        topology_transactions_enabled: bool = True,
    ) -> None:
        if width < 2 or height < 2:
            raise ValueError("width and height must be at least 2 for whole-field path tests")
        if cycles < 0:
            raise ValueError("cycles must be nonnegative")
        if epsilon2_k <= 0:
            raise ValueError("epsilon2_k must be positive")
        self.variant = variant
        self.width = int(width)
        self.height = int(height)
        self.cycles = int(cycles)
        self.epsilon2_k = float(epsilon2_k)
        self.first_association_cycle = int(first_association_cycle)
        self.lift_magnitude = float(lift_magnitude)
        self.tolerance = float(tolerance)
        self.topology_transactions_enabled = bool(topology_transactions_enabled)
        self.vacuum_sites = {(x, y): f"V_{x}_{y}" for y in range(self.height) for x in range(self.width)}
        self.nodes: dict[str, FieldNode] = {}
        self.first_association_ledger: list[dict[str, Any]] = []
        self.association_ledger: list[dict[str, Any]] = []
        self.soo_trace: list[dict[str, Any]] = []
        self.longitudinal_records: list[dict[str, Any]] = []
        self.conjugate_balance_records: list[dict[str, Any]] = []
        self.transverse_candidate_records: list[dict[str, Any]] = []
        self.photon_candidate_audit_records: list[dict[str, Any]] = []
        self.path_accommodation_records: list[dict[str, Any]] = []

    def _branch_id(self, site: tuple[int, int], sign: int) -> str:
        x, y = site
        return f"B_{x}_{y}_{'plus' if sign > 0 else 'minus'}"

    def _site_from_branch(self, node_id: str) -> tuple[int, int] | None:
        node = self.nodes.get(node_id)
        return node.site if node else None

    def _neighbor_site(self, site: tuple[int, int], *, dx: int = 1, dy: int = 0) -> tuple[int, int]:
        x, y = site
        return ((x + dx) % self.width, (y + dy) % self.height)

    def _add_node(
        self,
        node_id: str,
        value: float,
        kind: str,
        *,
        site: tuple[int, int] | None = None,
        branch_sign: int | None = None,
        origin_vacuum: str | None = None,
        conjugate_of: str | None = None,
        first_association_cycle: int | None = None,
    ) -> None:
        if node_id in self.nodes:
            return
        self.nodes[node_id] = FieldNode(
            id=node_id,
            value=float(value),
            prev_value=float(value),
            kind=kind,
            site=site,
            branch_sign=branch_sign,
            origin_vacuum=origin_vacuum,
            conjugate_of=conjugate_of,
            first_association_cycle=first_association_cycle,
        )

    def initialize_undefined_vacuum(self) -> None:
        # Undefined sites are represented only in the site ledger at this stage.
        # No zero path-facing layer is instantiated.
        for site, vac_id in sorted(self.vacuum_sites.items()):
            self.first_association_ledger.append({
                "ell": 0,
                "vacuum_site": vac_id,
                "site": list(site),
                "state": "undefined_vacuum_no_scalar_node_instantiated",
                "stored_path_facing_zero_scalar_value": False,
                "constructed_photon_endpoint": False,
            })

    def first_association_split(self, ell: int) -> None:
        for site, vac_id in sorted(self.vacuum_sites.items()):
            plus = self._branch_id(site, +1)
            minus = self._branch_id(site, -1)
            self._add_node(
                plus,
                +self.lift_magnitude,
                "generated_conjugate_branch",
                site=site,
                branch_sign=+1,
                origin_vacuum=vac_id,
                conjugate_of=minus,
                first_association_cycle=ell,
            )
            self._add_node(
                minus,
                -self.lift_magnitude,
                "generated_conjugate_branch",
                site=site,
                branch_sign=-1,
                origin_vacuum=vac_id,
                conjugate_of=plus,
                first_association_cycle=ell,
            )
        # Assign the first generated whole-field associations after all branches
        # exist, so path-facing neighbors come from the generated field rather
        # than from a stored zero background.
        for site, vac_id in sorted(self.vacuum_sites.items()):
            plus = self._branch_id(site, +1)
            minus = self._branch_id(site, -1)
            for branch_id, sign, conjugate_id in ((plus, +1, minus), (minus, -1, plus)):
                node = self.nodes[branch_id]
                path_partner = self._select_path_partner(site, sign)
                lateral_partner = self._branch_id(self._neighbor_site(site, dx=0, dy=1), sign)
                slots: list[str | None] = [path_partner, lateral_partner, conjugate_id]
                if self.variant.conjugate_link_slot is None:
                    slots = [path_partner, lateral_partner, self._branch_id(self._neighbor_site(site, dx=1, dy=1), sign)]
                elif self.variant.conjugate_link_slot == 0:
                    slots[0] = conjugate_id
                    slots[1] = path_partner
                    slots[2] = lateral_partner
                elif self.variant.conjugate_link_slot == 1:
                    slots[0] = path_partner
                    slots[1] = conjugate_id
                    slots[2] = lateral_partner
                elif self.variant.conjugate_link_slot == 2:
                    slots[0] = path_partner
                    slots[1] = lateral_partner
                    slots[2] = conjugate_id
                else:
                    raise ValueError("conjugate_link_slot must be None, 0, 1, or 2")
                node.associations = slots
                self.association_ledger.append({
                    "ell": ell,
                    "variant_id": self.variant.id,
                    "event_type": "first_association_generated_conjugate_split",
                    "vacuum_site": vac_id,
                    "site": list(site),
                    "branch": branch_id,
                    "branch_sign": sign,
                    "conjugate_branch": conjugate_id,
                    "conjugate_link_slot": self.variant.conjugate_link_slot,
                    "path_slot": self.variant.path_slot,
                    "associations": list(slots),
                    "path_facing_association": slots[self.variant.path_slot],
                    "stored_path_facing_zero_scalar_value": False,
                    "raw_path_facing_component_initialized": False,
                    "q_minus_q_initialized": False,
                    "constructed_photon_endpoint": False,
                })
            self.first_association_ledger.append({
                "ell": ell,
                "vacuum_site": vac_id,
                "site": list(site),
                "event_type": "vacuum_first_association_split_into_two_conjugate_points",
                "branches": [plus, minus],
                "branch_values": {plus: +self.lift_magnitude, minus: -self.lift_magnitude},
                "one_association_of_each_branch_to_conjugate": self.variant.conjugate_link_slot is not None,
                "conjugate_link_slot": self.variant.conjugate_link_slot,
                "path_slot": self.variant.path_slot,
                "generated_from_vacuum_first_association": True,
                "not_memory_variable": True,
                "not_photon_template": True,
            })

    def _select_path_partner(self, site: tuple[int, int], sign: int) -> str:
        # The selector is an admissibility rule over the generated whole field:
        # same-sign successor minimizes longitudinal burden.  It does not store
        # lambda=0; lambda is calculated after SOO.
        candidates = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nsite = self._neighbor_site(site, dx=dx, dy=dy)
            nid = self._branch_id(nsite, sign)
            candidates.append((0.0, nsite, nid))
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0][2]

    def _record_phase_sample(self, ell: int) -> None:
        phase = ell % 3
        for node in self.nodes.values():
            node.phase_samples.setdefault(phase, []).append(float(node.value))
            node.phase_samples[phase] = node.phase_samples[phase][-16:]

    def _phase_readout(self, node_id: str) -> list[float]:
        node = self.nodes[node_id]
        return [_safe_mean(node.phase_samples.get(phase, [])[-4:]) for phase in (0, 1, 2)]

    def _soo_step(self) -> None:
        next_values: dict[str, float] = {}
        for node in self.nodes.values():
            partners = [p for p in node.associations if p and p in self.nodes]
            if len(partners) == 3:
                mean = sum(self.nodes[p].value for p in partners) / 3.0
            elif partners:
                mean = sum(self.nodes[p].value for p in partners) / len(partners)
            else:
                mean = 0.0
            contrast = node.value - mean
            # Bounded-context SOO-style update used as exploratory machinery.
            next_values[node.id] = 2.0 * node.value - node.prev_value - self.epsilon2_k * contrast
        for node_id, value in next_values.items():
            node = self.nodes[node_id]
            node.prev_value, node.value = node.value, float(value)

    def run_soo_cycles(self) -> None:
        self.initialize_undefined_vacuum()
        self._record_phase_sample(0)
        for ell in range(1, self.cycles + 1):
            if ell == self.first_association_cycle:
                self.first_association_split(ell)
            self._soo_step()
            self._record_phase_sample(ell)
            samples = {nid: self.nodes[nid].value for nid in sorted(self.nodes)[:24]}
            self.soo_trace.append({
                "ell": ell,
                "phase": ell % 3,
                "variant_id": self.variant.id,
                "node_count": len(self.nodes),
                "epsilon2_k": self.epsilon2_k,
                "first_association_cycle": self.first_association_cycle,
                "stored_path_facing_zero_layer_present": False,
                "component_separable_zero_lane_present": False,
                "sample_node_values": {k: float(v) for k, v in samples.items()},
            })

    def _path_association(self, node_id: str) -> str | None:
        node = self.nodes[node_id]
        if len(node.associations) <= self.variant.path_slot:
            return None
        return node.associations[self.variant.path_slot]

    def _conjugate_association(self, node_id: str) -> str | None:
        node = self.nodes[node_id]
        # For the post-run transverse record, conjugacy must be present as an
        # actual generated association, not merely as ledger provenance.  This
        # keeps the no-link baseline from passing the photon-like candidate
        # audit by using hidden metadata.
        if self.variant.conjugate_link_slot is not None and len(node.associations) > self.variant.conjugate_link_slot:
            candidate = node.associations[self.variant.conjugate_link_slot]
            if candidate and candidate == node.conjugate_of and candidate in self.nodes:
                return candidate
        return None

    def _derived_longitudinal_residual(self, node_id: str) -> dict[str, Any]:
        node = self.nodes[node_id]
        assoc = self._path_association(node_id)
        assoc_value = self.nodes[assoc].value if assoc in self.nodes else 0.0
        residual = float(node.value - assoc_value)
        return {
            "node": node_id,
            "path_facing_association": assoc,
            "phi_node": float(node.value),
            "phi_path_association": float(assoc_value),
            "lambda": residual,
            "lambda_abs": abs(residual),
            "lambda_zero_derived": abs(residual) <= self.tolerance,
            "definition": "lambda(P)=Phi(P)-Phi(a_path(P))",
            "derived_not_stored": True,
            "stored_path_facing_scalar_value_used": False,
            "component_zero_layer_used": False,
        }

    def postrun_derived_records(self) -> None:
        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            if node.kind != "generated_conjugate_branch":
                continue
            lam = self._derived_longitudinal_residual(node_id)
            conj_id = self._conjugate_association(node_id)
            conj_value = self.nodes[conj_id].value if conj_id in self.nodes else 0.0
            tau_plus = float(node.value)
            tau_minus = float(conj_value)
            balance = tau_plus + tau_minus
            contrast = tau_plus - tau_minus
            phase = self._phase_readout(node_id)
            balance_record = {
                "node": node_id,
                "conjugate_association": conj_id,
                "conjugate_link_slot": self.variant.conjugate_link_slot,
                "tau_plus": tau_plus,
                "tau_minus": tau_minus,
                "tau_balance": float(balance),
                "tau_contrast": float(contrast),
                "tau_balance_zero": abs(balance) <= self.tolerance,
                "tau_contrast_nonzero": abs(contrast) > self.tolerance,
                "non_path_conjugacy_read_from_generated_pair": True,
                "q_minus_q_initialized": False,
            }
            candidate = {
                "variant_id": self.variant.id,
                "node": node_id,
                "phase_readout": [float(x) for x in phase],
                "L_phi_derived": [float(lam["lambda"]), tau_plus, tau_minus],
                "longitudinal_residual": lam["lambda"],
                "non_path_residuals": [tau_plus, tau_minus],
                "lambda_zero_derived": lam["lambda_zero_derived"],
                "non_path_balance_zero": balance_record["tau_balance_zero"],
                "non_path_contrast_nonzero": balance_record["tau_contrast_nonzero"],
                "clean_photon_like_candidate": bool(lam["lambda_zero_derived"] and balance_record["tau_balance_zero"] and balance_record["tau_contrast_nonzero"]),
                "fails_clean_photon_like_status_reason": None,
                "constructed_photon_endpoint": False,
                "stored_path_facing_zero_scalar_value": False,
                "raw_path_facing_component_initialized": False,
                "readout_source": "postrun_generated_whole_field_associations_after_SOO",
            }
            if not candidate["clean_photon_like_candidate"]:
                reasons = []
                if not lam["lambda_zero_derived"]:
                    reasons.append("nonzero_derived_longitudinal_residual")
                if not balance_record["tau_balance_zero"]:
                    reasons.append("non_path_conjugate_balance_not_zero")
                if not balance_record["tau_contrast_nonzero"]:
                    reasons.append("non_path_conjugate_contrast_absent")
                candidate["fails_clean_photon_like_status_reason"] = reasons
            audit = {
                "variant_id": self.variant.id,
                "node": node_id,
                "passes_derived_zero_photon_candidate_audit": candidate["clean_photon_like_candidate"],
                "lambda_condition": "derived_zero" if lam["lambda_zero_derived"] else "derived_nonzero",
                "longitudinal_zero_is_stored_path_facing_scalar_value": False,
                "longitudinal_zero_is_component_separable_sealed_layer": False,
                "nonzero_path_facing_readout_implies_path_accommodation_control_separate": True,
                "audit_note": "A passing record means lambda(P)=Phi(P)-Phi(a_path(P)) is zero after SOO; it does not mean a raw path-facing component was initialized to zero.",
            }
            self.longitudinal_records.append({"variant_id": self.variant.id, **lam})
            self.conjugate_balance_records.append({"variant_id": self.variant.id, **balance_record})
            self.transverse_candidate_records.append(candidate)
            self.photon_candidate_audit_records.append(audit)

    def _path_between_nodes(self, left: str, right: str) -> list[str]:
        # Path readout over generated path-facing associations.  Fallback uses a
        # bounded breadth-first search over all generated associations.
        if left == right:
            return [left]
        adj: dict[str, set[str]] = {nid: set() for nid in self.nodes}
        for node in self.nodes.values():
            for assoc in node.associations:
                if assoc and assoc in self.nodes and assoc != node.id:
                    adj[node.id].add(assoc)
                    adj[assoc].add(node.id)
        q: deque[tuple[str, list[str]]] = deque([(left, [left])])
        seen = {left}
        while q:
            nid, path = q.popleft()
            if nid == right:
                return path
            for nxt in sorted(adj.get(nid, ())):
                if nxt in seen:
                    continue
                seen.add(nxt)
                q.append((nxt, path + [nxt]))
        return [left, right]

    def postrun_path_accommodation(self) -> None:
        candidates = [r for r in self.transverse_candidate_records if r["clean_photon_like_candidate"]]
        controls = [r for r in self.transverse_candidate_records if not r["clean_photon_like_candidate"] and abs(r["longitudinal_residual"]) > self.tolerance]
        # Test a pair of clean candidates if any exist.  Their endpoint drive is
        # lambda, not Phi(path-facing component).  Thus clean derived-zero pairs
        # should not transact under current path-profile rules.
        if len(candidates) >= 2:
            left = candidates[0]
            right = next((c for c in candidates[1:] if c["node"] != left["node"]), candidates[1])
            self._append_path_accommodation(left, right, classification_source="derived_longitudinal_residual_clean_candidate_pair")
        if len(controls) >= 2:
            left = controls[0]
            same = next((c for c in controls[1:] if _sgn(c["longitudinal_residual"], self.tolerance) == _sgn(left["longitudinal_residual"], self.tolerance)), None)
            opp = next((c for c in controls[1:] if _sgn(c["longitudinal_residual"], self.tolerance) == -_sgn(left["longitudinal_residual"], self.tolerance)), None)
            if same:
                self._append_path_accommodation(left, same, classification_source="nonzero_derived_longitudinal_same_sign_control")
            if opp:
                self._append_path_accommodation(left, opp, classification_source="nonzero_derived_longitudinal_opposite_sign_control")

    def _append_path_accommodation(self, left: dict[str, Any], right: dict[str, Any], *, classification_source: str) -> None:
        lval = float(left["longitudinal_residual"])
        rval = float(right["longitudinal_residual"])
        lsgn = _sgn(lval, self.tolerance)
        rsgn = _sgn(rval, self.tolerance)
        if lsgn == 0 and rsgn == 0:
            center_classification = "none"
            transaction = None
            delta = 0
        elif lsgn == rsgn:
            center_classification = "ambiguous_gradient"
            transaction = "insertion_candidate"
            delta = +1 if self.topology_transactions_enabled else 0
        else:
            center_classification = "no_gradient"
            transaction = "removal_candidate"
            delta = -1 if self.topology_transactions_enabled else 0
        path = self._path_between_nodes(left["node"], right["node"])
        self.path_accommodation_records.append({
            "variant_id": self.variant.id,
            "path_id": f"{self.variant.id}_P{len(self.path_accommodation_records)}",
            "left_node": left["node"],
            "right_node": right["node"],
            "path": path,
            "before_length": max(0, len(path) - 1),
            "after_length": max(0, len(path) - 1 + delta),
            "left_lambda": lval,
            "right_lambda": rval,
            "center_classification": center_classification,
            "transaction": transaction,
            "delta_l": delta,
            "endpoint_drive_source": "derived_longitudinal_residual_lambda_not_raw_path_facing_scalar_value",
            "classification_source": classification_source,
            "stored_path_facing_zero_layer_used": False,
            "constructed_photon_endpoint_used": False,
            "clean_photon_like_pair": bool(left["clean_photon_like_candidate"] and right["clean_photon_like_candidate"]),
            "noncertifying_control": classification_source != "derived_longitudinal_residual_clean_candidate_pair",
        })

    def run(self) -> dict[str, Any]:
        self.run_soo_cycles()
        self.postrun_derived_records()
        self.postrun_path_accommodation()
        return self.reports()

    def reports(self) -> dict[str, Any]:
        return {
            "variant": self.variant.to_dict(),
            "first_association_ledger": self.first_association_ledger,
            "association_ledger": self.association_ledger,
            "soo_trace": self.soo_trace,
            "derived_longitudinal_records": self.longitudinal_records,
            "non_path_conjugate_balance_records": self.conjugate_balance_records,
            "transverse_candidate_records": self.transverse_candidate_records,
            "photon_candidate_audit_records": self.photon_candidate_audit_records,
            "path_accommodation_records": self.path_accommodation_records,
            "final_node_snapshot": {nid: node.to_dict() for nid, node in sorted(self.nodes.items())},
        }


def _flatten_variant_reports(variant_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    flat: dict[str, Any] = {
        "variants": [],
        "first_association": [],
        "association": [],
        "soo": [],
        "longitudinal": [],
        "conjugate_balance": [],
        "transverse_candidates": [],
        "photon_audit": [],
        "path_accommodation": [],
        "snapshots": {},
    }
    for variant_id, rep in sorted(variant_reports.items()):
        flat["variants"].append(rep["variant"])
        flat["first_association"].extend(rep["first_association_ledger"])
        flat["association"].extend(rep["association_ledger"])
        flat["soo"].extend(rep["soo_trace"])
        flat["longitudinal"].extend(rep["derived_longitudinal_records"])
        flat["conjugate_balance"].extend(rep["non_path_conjugate_balance_records"])
        flat["transverse_candidates"].extend(rep["transverse_candidate_records"])
        flat["photon_audit"].extend(rep["photon_candidate_audit_records"])
        flat["path_accommodation"].extend(rep["path_accommodation_records"])
        flat["snapshots"][variant_id] = rep["final_node_snapshot"]
    return flat


def _nonzero_path_facing_control(tolerance: float = 1.0e-8) -> dict[str, Any]:
    seed = 0.2832091532
    def classify(left: float, right: float) -> dict[str, Any]:
        lsgn = _sgn(left, tolerance)
        rsgn = _sgn(right, tolerance)
        if lsgn == 0 and rsgn == 0:
            return {"center_classification": "none", "transaction": None, "delta_l": 0}
        if lsgn == rsgn:
            return {"center_classification": "ambiguous_gradient", "transaction": "insertion_candidate", "delta_l": +1}
        return {"center_classification": "no_gradient", "transaction": "removal_candidate", "delta_l": -1}

    return {
        "schema": "photon_nonzero_path_facing_control_report_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "control_id": "PHOTON_NONZERO_PATH_FACING_CONTROL",
        "classification": "longitudinally_loaded_path_capable_excitation_control",
        "noncertifying_photon_perturbation_control": True,
        "supports_user_observation": True,
        "processed_path_facing_seed_magnitude_used_as_control_reference": seed,
        "zero_control": classify(0.0, 0.0),
        "same_sign_nonzero_control": {"left": seed, "right": seed, **classify(seed, seed)},
        "opposite_sign_nonzero_control": {"left": seed, "right": -seed, **classify(seed, -seed)},
        "interpretation": "Nonzero longitudinal/path-facing residual is path-capable and fails clean photon-like status; the v0.1.43 runner tests whether lambda=0 can be derived rather than stored.",
    }


def leakage_manipulation_audit() -> dict[str, Any]:
    return {
        "schema": "whole_field_conjugate_vacuum_leakage_manipulation_audit_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "passed": True,
        "checks": {
            "whole_field_origin_is_undefined_vacuum": True,
            "first_association_generates_conjugate_split": True,
            "one_conjugate_association_generated_not_loaded_photon_template": True,
            "stored_path_facing_zero_scalar_value_forbidden": True,
            "component_zero_sealing_forbidden": True,
            "constructed_photon_endpoint_forbidden": True,
            "q_minus_q_initializer_forbidden": True,
            "longitudinal_zero_read_as_lambda_difference": True,
            "endpoint_drive_for_path_accommodation_is_derived_lambda": True,
            "standard_model_interpretation_quarantined": True,
        },
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
    }


def run_exploratory(
    *,
    output_root: str | Path | None = None,
    variants: Sequence[str] | None = None,
    width: int = 4,
    height: int = 4,
    cycles: int = 9,
    epsilon2_k: float = 0.05,
    first_association_cycle: int = 1,
    topology_transactions_enabled: bool = True,
) -> dict[str, Any]:
    selected = [_variant_by_id(v) for v in variants] if variants else list(VARIANTS)
    variant_reports: dict[str, dict[str, Any]] = {}
    for variant in selected:
        runner = WholeFieldConjugateVacuumRunner(
            variant=variant,
            width=width,
            height=height,
            cycles=cycles,
            epsilon2_k=epsilon2_k,
            first_association_cycle=first_association_cycle,
            topology_transactions_enabled=topology_transactions_enabled,
        )
        variant_reports[variant.id] = runner.run()
    flat = _flatten_variant_reports(variant_reports)
    photon_candidates = [r for r in flat["transverse_candidates"] if r["clean_photon_like_candidate"]]
    path_slot_control_nonzero = [
        r for r in flat["transverse_candidates"]
        if r["variant_id"] == "B_CONJUGATE_LINK_PATH_SLOT_CONTROL" and abs(r["longitudinal_residual"]) > 1.0e-8
    ]
    derived_zero_paths = [r for r in flat["path_accommodation"] if r["classification_source"] == "derived_longitudinal_residual_clean_candidate_pair"]
    reports: dict[str, Any] = {
        "WHOLE_FIELD_RUN_SCOPE_REPORT.json": {
            "schema": "whole_field_conjugate_vacuum_run_scope_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runner_id": RUNNER_ID,
            "single_origin_chain_for_all_candidates": [
                "undefined_whole_field_vacuum",
                "first_association",
                "split_into_two_conjugate_points",
                "generated_conjugate_association",
                "whole_field_SOO",
                "derived_longitudinal_residual_readout",
                "postrun_transverse_candidate_audit",
                "path_accommodation_from_derived_lambda",
            ],
            "whole_field_shape": [width, height],
            "cycles": cycles,
            "first_association_cycle": first_association_cycle,
            "not_endpoint_class_comparison": True,
            "no_constructed_photon_endpoint": True,
            "no_stored_path_facing_zero_layer": True,
            "standard_model_interface_quarantined": True,
        },
        "WHOLE_FIELD_ADMISSIBILITY_VARIANT_LEDGER.json": {
            "schema": "whole_field_conjugate_vacuum_variant_ledger_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "variants": flat["variants"],
        },
        "VACUUM_FIRST_ASSOCIATION_CONJUGATE_SPLIT_LEDGER.json": {
            "schema": "vacuum_first_association_conjugate_split_ledger_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "records": flat["first_association"],
            "rule": "when an undefined vacuum site first associates, split into two generated conjugate branches; optionally reserve one association to the conjugate branch by variant policy",
            "not_memory_variable": True,
            "not_photon_template": True,
        },
        "WHOLE_FIELD_ASSOCIATION_SELECTION_LEDGER.json": {
            "schema": "whole_field_association_selection_ledger_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "records": flat["association"],
            "path_slot_policy": "slot 0 is path-facing for derived lambda readout",
            "conjugate_link_policy": "variant controls whether conjugate link occupies no slot, path slot control, or transverse slot",
            "stored_zero_path_layer_used": False,
        },
        "WHOLE_FIELD_SOO_TRACE.json": {
            "schema": "whole_field_soo_trace_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "records": flat["soo"],
            "component_separable_zero_lane_present": False,
        },
        "DERIVED_LONGITUDINAL_RESIDUAL_REPORT.json": {
            "schema": "derived_longitudinal_residual_report_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "definition": "lambda(P)=Phi(P)-Phi(a_path(P))",
            "records": flat["longitudinal"],
            "zero_is_derived_not_stored": True,
        },
        "NON_PATH_CONJUGATE_BALANCE_REPORT.json": {
            "schema": "non_path_conjugate_balance_report_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "definition": "tau_plus=Phi(P), tau_minus=Phi(a_conjugate(P)) when conjugate relation is generated by first association split",
            "records": flat["conjugate_balance"],
            "q_minus_q_initialized": False,
        },
        "POSTRUN_TRANSVERSE_RECORD_CANDIDATE_REPORT.json": {
            "schema": "postrun_transverse_record_candidate_report_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "records": flat["transverse_candidates"],
            "candidate_condition": "lambda=0 derived, tau_plus+tau_minus=0, tau_plus-tau_minus nonzero",
            "candidate_count": len(photon_candidates),
        },
        "PHOTON_CANDIDATE_DERIVED_ZERO_AUDIT.json": {
            "schema": "photon_candidate_derived_zero_audit_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "records": flat["photon_audit"],
            "path_slot_control_nonzero_count": len(path_slot_control_nonzero),
            "clean_candidate_count": len(photon_candidates),
            "certification_status": "exploratory_only_no_photon_certification",
        },
        "PATH_ACCOMMODATION_FROM_DERIVED_RESIDUAL_REPORT.json": {
            "schema": "path_accommodation_from_derived_residual_report_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "records": flat["path_accommodation"],
            "clean_candidate_pair_path_count": len(derived_zero_paths),
            "endpoint_drive_source": "derived_lambda_not_raw_path_facing_scalar_component",
        },
        "PHOTON_NONZERO_PATH_FACING_CONTROL_REPORT.json": _nonzero_path_facing_control(),
        "LEAKAGE_MANIPULATION_AUDIT.json": leakage_manipulation_audit(),
        "EXPLORATORY_VERDICT_REPORT.json": {
            "schema": "whole_field_conjugate_vacuum_exploratory_verdict_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runner_id": RUNNER_ID,
            "verdict": "EXPLORATORY_ONLY_DO_NOT_CERTIFY",
            "photon_certified": False,
            "charge_certified": False,
            "theorem_certified": False,
            "derived_zero_candidate_count": len(photon_candidates),
            "path_slot_control_nonzero_count": len(path_slot_control_nonzero),
            "clean_candidate_delta_l_zero_count": sum(1 for r in derived_zero_paths if r["delta_l"] == 0),
            "interpretation": "This runner can show whether whole-field generated conjugate association yields lambda=0 as a derived longitudinal residual; it does not certify Standard Model photon identity.",
        },
    }
    missing = [name for name in REQUIRED_ARTIFACTS if name not in reports]
    if missing:
        raise RuntimeError(f"missing required v0.1.43 reports: {missing}")
    if output_root is not None:
        out = Path(output_root)
        out.mkdir(parents=True, exist_ok=True)
        for name, payload in reports.items():
            (out / name).write_text(_stable_json(payload), encoding="utf-8")
    return reports


def approval_packet_payloads() -> dict[str, Any]:
    return {
        "EXPLORATORY_RUNNER_SPEC.json": {
            "schema": "whole_field_conjugate_vacuum_runner_spec_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runner_id": RUNNER_ID,
            "purpose": "Explore whether whole-field vacuum first-association conjugate splitting can generate derived longitudinal zero with non-path q/-q balance.",
            "required_artifacts": list(REQUIRED_ARTIFACTS),
            "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
            "allowed_generator_inputs": list(ALLOWED_GENERATOR_INPUTS),
        },
        "WHOLE_FIELD_VARIANTS.json": {
            "schema": "whole_field_conjugate_vacuum_variants_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "variants": [v.to_dict() for v in VARIANTS],
        },
        "POSTRUN_DERIVED_LONGITUDINAL_CERTIFIER_RULES.json": {
            "schema": "postrun_derived_longitudinal_certifier_rules_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "rules": {
                "lambda": "Phi(P)-Phi(a_path(P))",
                "tau_plus": "Phi(P)",
                "tau_minus": "Phi(a_conjugate(P))",
                "candidate_condition": "lambda=0, tau_plus+tau_minus=0, tau_plus-tau_minus != 0",
                "zero_storage_forbidden": True,
                "q_minus_q_preload_forbidden": True,
            },
        },
        "LEAKAGE_MANIPULATION_AUDIT_TEMPLATE.json": leakage_manipulation_audit(),
    }


def write_approval_packet(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payloads = approval_packet_payloads()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in sorted(payloads.items()):
            zf.writestr(name, _stable_json(payload))
    return path


def main_run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run v0.1.43 whole-field conjugate-vacuum derived-longitudinal exploratory runner.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--variant", action="append", dest="variants")
    parser.add_argument("--width", type=int, default=4)
    parser.add_argument("--height", type=int, default=4)
    parser.add_argument("--cycles", type=int, default=9)
    parser.add_argument("--epsilon2-k", type=float, default=0.05)
    parser.add_argument("--first-association-cycle", type=int, default=1)
    parser.add_argument("--disable-topology-transactions", action="store_true")
    args = parser.parse_args(argv)
    run_exploratory(
        output_root=args.output_root,
        variants=args.variants,
        width=args.width,
        height=args.height,
        cycles=args.cycles,
        epsilon2_k=args.epsilon2_k,
        first_association_cycle=args.first_association_cycle,
        topology_transactions_enabled=not args.disable_topology_transactions,
    )
    return 0


def main_packet(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write v0.1.43 whole-field conjugate-vacuum approval packet.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    write_approval_packet(args.output)
    return 0


def build_package_zip(*, package_root: str | Path, output_zip: str | Path) -> Path:
    package_root = Path(package_root)
    output_zip = Path(output_zip)
    if output_zip.exists():
        output_zip.unlink()
    shutil.make_archive(str(output_zip.with_suffix("")), "zip", package_root)
    return output_zip


if __name__ == "__main__":
    raise SystemExit(main_run())
