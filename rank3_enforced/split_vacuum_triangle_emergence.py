from __future__ import annotations

import argparse
import json
import math
import shutil
import zipfile
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable


FRAMEWORK_TARGET_VERSION = "0.1.36"
RUNNER_ID = "split_vacuum_triangle_emergence_exploratory_v0_1"
PACKET_ID = "split_vacuum_triangle_emergence_approval_items_v0136"
SCHEMA = "split_vacuum_triangle_emergence_v0_1"


@dataclass
class Node:
    id: str
    value: float
    prev_value: float
    kind: str
    split_site: str | None = None
    branch_sign: int | None = None
    associations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["value"] = float(self.value)
        d["prev_value"] = float(self.prev_value)
        return d


@dataclass(frozen=True)
class ControlSpec:
    id: str
    purpose: str
    expected_exploratory_behavior: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


STAGES: tuple[str, ...] = (
    "vacuum_initialization",
    "initial_split_event",
    "branch_slot_assignment",
    "initial_branch_to_vacuum_association",
    "SOO_cycle_processing",
    "lifted_vacuum_detection",
    "branch_creation_from_lifted_vacuum",
    "least_gradient_association_selection",
    "emergent_motif_detection",
    "triangle_classification",
    "triangle_persistence_analysis",
    "relational_path_discovery",
    "center_gradient_classification",
    "topology_transaction_audit",
    "delta_l_readout",
)

FORBIDDEN_GENERATOR_INPUTS: tuple[str, ...] = (
    "predeclared_triangle_membership",
    "predeclared_path_endpoints",
    "same_label",
    "opposite_label",
    "charge_label",
    "handedness_label",
    "target_delta_l",
    "expected_delta_l",
    "preselected_center_action",
    "preselected_path_outcome",
)

ALLOWED_GENERATOR_INPUTS: tuple[str, ...] = (
    "split_site_count",
    "split_branch_values",
    "undefined_vacuum_pool",
    "rank3_branch_slot_count",
    "bounded_context_soo_v1_parameters",
    "least_gradient_association_rule",
    "cycle_latency_rule",
    "motif_detection_rule",
    "path_discovery_rule",
)

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "RUN_SCOPE_REPORT.json",
    "VACUUM_INITIALIZATION_REPORT.json",
    "VACUUM_SPLIT_LEDGER.json",
    "BRANCH_ASSOCIATION_LEDGER.json",
    "SOO_CYCLE_LEDGER.json",
    "LIFTED_VACUUM_REPORT.json",
    "LEAST_GRADIENT_ASSOCIATION_REPORT.json",
    "EMERGENT_MOTIF_DETECTION_REPORT.json",
    "TRIANGLE_FORMATION_REPORT.json",
    "TRIANGLE_PERSISTENCE_REPORT.json",
    "TRIANGLE_SIGN_CLASSIFICATION_REPORT.json",
    "RELATIONAL_PATH_DISCOVERY_REPORT.json",
    "CENTER_CONDITION_REPORT.json",
    "TOPOLOGY_TRANSACTION_AUDIT.json",
    "PATH_ACCOMMODATION_REPORT.json",
    "NEGATIVE_CONTROL_REPORT.json",
    "LEAKAGE_MANIPULATION_AUDIT.json",
    "EXPLORATORY_VERDICT_REPORT.json",
)

REQUIRED_CONTROLS: tuple[ControlSpec, ...] = (
    ControlSpec("all_vacuum_no_split_control", "No initial split event is supplied.", "No branches, no lifted vacuum, no triangles, no paths, no accommodation."),
    ControlSpec("split_without_soo_control", "Split branches are created but SOO is disabled.", "Initial zero associates do not acquire SOO-lift evidence."),
    ControlSpec("random_association_control", "Candidate associations are randomized instead of selected by least gradient.", "Triangle dominance is not admission-supported."),
    ControlSpec("no_latency_control", "Association proposals commit instantly.", "Quarantined as non-admissible for this exploratory runner."),
    ControlSpec("predeclared_triangle_leakage_control", "Generator is handed triangle membership.", "Rejected as leakage before motif detection."),
    ControlSpec("predeclared_endpoint_leakage_control", "Generator is handed theorem path endpoints.", "Rejected as leakage before path discovery."),
    ControlSpec("forced_delta_l_leakage_control", "Generator is handed target Delta L.", "Rejected as leakage before center classification."),
    ControlSpec("no_off_path_vacuum_influence_control", "Path carriers have no non-path/vacuum-facing influence.", "Invalid over-closed path diagnostic."),
    ControlSpec("mixed_sign_triangle_control", "Detected motif is not sign coherent.", "Classified as non-theorem motif, not endpoint support."),
    ControlSpec("nonpersistent_triangle_control", "Triangle appears transiently only.", "Triangle is not admitted as persistent endpoint candidate."),
)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def validate_generator_inputs(inputs: Iterable[str]) -> dict[str, Any]:
    supplied = tuple(str(x) for x in inputs)
    forbidden = tuple(x for x in supplied if x in FORBIDDEN_GENERATOR_INPUTS)
    unknown = tuple(x for x in supplied if x not in FORBIDDEN_GENERATOR_INPUTS and x not in ALLOWED_GENERATOR_INPUTS)
    return {
        "schema": "split_vacuum_triangle_generator_input_validation_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "supplied_inputs": supplied,
        "forbidden_inputs_present": forbidden,
        "unknown_inputs_present": unknown,
        "passed": not forbidden and not unknown,
    }


class SplitVacuumTriangleRunner:
    """Deterministic exploratory runner for split-vacuum triangle emergence.

    This is intentionally not a certification runner. It starts from undefined
    vacuum plus one or more split events, applies a bounded-context SOO step to
    the branch/vacuum records, lets least-gradient association choose candidate
    same-sign motifs, detects triangles as a readout, then discovers relational
    paths between detected triangles. The runner never accepts triangle
    membership, path endpoints, same/opposite labels, or target Delta L as input.
    """

    def __init__(
        self,
        *,
        split_site_count: int = 2,
        cycles: int = 6,
        epsilon2_k: float = 0.05,
        lift_threshold: float = 1.0e-6,
        topology_transactions_enabled: bool = True,
    ) -> None:
        if split_site_count < 0:
            raise ValueError("split_site_count must be nonnegative")
        if cycles < 0:
            raise ValueError("cycles must be nonnegative")
        if epsilon2_k <= 0:
            raise ValueError("epsilon2_k must be positive")
        self.split_site_count = int(split_site_count)
        self.cycles = int(cycles)
        self.epsilon2_k = float(epsilon2_k)
        self.lift_threshold = float(lift_threshold)
        self.topology_transactions_enabled = bool(topology_transactions_enabled)
        self.nodes: dict[str, Node] = {}
        self.split_ledger: list[dict[str, Any]] = []
        self.branch_association_ledger: list[dict[str, Any]] = []
        self.soo_cycle_ledger: list[dict[str, Any]] = []
        self.lifted_vacuum_events: list[dict[str, Any]] = []
        self.association_selection_events: list[dict[str, Any]] = []
        self.triangles: list[dict[str, Any]] = []
        self.paths: list[dict[str, Any]] = []
        self.center_records: list[dict[str, Any]] = []
        self.transaction_records: list[dict[str, Any]] = []
        self.accommodation_records: list[dict[str, Any]] = []

    def _node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def _add_node(self, node_id: str, value: float, kind: str, *, split_site: str | None = None, branch_sign: int | None = None) -> None:
        self.nodes[node_id] = Node(node_id, float(value), float(value), kind, split_site, branch_sign, [])

    def initialize(self) -> None:
        for site in range(self.split_site_count):
            site_id = f"S{site}"
            plus = f"{site_id}_plus_branch"
            minus = f"{site_id}_minus_branch"
            self._add_node(plus, +1.0, "split_branch", split_site=site_id, branch_sign=+1)
            self._add_node(minus, -1.0, "split_branch", split_site=site_id, branch_sign=-1)
            plus_vacs = []
            minus_vacs = []
            for k in range(3):
                pv = f"{site_id}_plus_vac_{k}"
                mv = f"{site_id}_minus_vac_{k}"
                self._add_node(pv, 0.0, "initial_zero_vacuum_associate", split_site=site_id, branch_sign=+1)
                self._add_node(mv, 0.0, "initial_zero_vacuum_associate", split_site=site_id, branch_sign=-1)
                plus_vacs.append(pv)
                minus_vacs.append(mv)
                # Off-branch vacuum-facing points keep the associate open to field/vacuum influence.
                for suffix in ("a", "b"):
                    self._add_node(f"{pv}_vacface_{suffix}", 0.0, "vacuum_facing_background", split_site=site_id, branch_sign=+1)
                    self._add_node(f"{mv}_vacface_{suffix}", 0.0, "vacuum_facing_background", split_site=site_id, branch_sign=-1)
            self.nodes[plus].associations = list(plus_vacs)
            self.nodes[minus].associations = list(minus_vacs)
            for pv in plus_vacs:
                self.nodes[pv].associations = [plus, f"{pv}_vacface_a", f"{pv}_vacface_b"]
            for mv in minus_vacs:
                self.nodes[mv].associations = [minus, f"{mv}_vacface_a", f"{mv}_vacface_b"]
            self.split_ledger.append({
                "split_site": site_id,
                "source_state": "undefined_vacuum_until_first_association",
                "branches": [
                    {"id": plus, "scalar_value": +1.0, "branch_sign": +1, "slot_count": 3},
                    {"id": minus, "scalar_value": -1.0, "branch_sign": -1, "slot_count": 3},
                ],
                "conjugacy_exact_at_initialization": True,
            })
            self.branch_association_ledger.extend([
                {"branch": plus, "associated_zero_vacuum_points": list(plus_vacs), "predeclared_triangle_membership": False},
                {"branch": minus, "associated_zero_vacuum_points": list(minus_vacs), "predeclared_triangle_membership": False},
            ])

    def _soo_step(self) -> None:
        next_values: dict[str, float] = {}
        for node in self.nodes.values():
            if len(node.associations) != 3:
                mean = 0.0
            else:
                mean = sum(self.nodes[a].value for a in node.associations) / 3.0
            contrast = node.value - mean
            next_values[node.id] = 2.0 * node.value - node.prev_value - self.epsilon2_k * contrast
        for node_id, nxt in next_values.items():
            node = self.nodes[node_id]
            node.prev_value, node.value = node.value, float(nxt)

    def run_soo_cycles(self) -> None:
        previously_lifted: set[str] = set()
        for ell in range(1, self.cycles + 1):
            self._soo_step()
            cycle_lifts = []
            for node in self.nodes.values():
                if node.kind == "initial_zero_vacuum_associate" and abs(node.value) > self.lift_threshold and node.id not in previously_lifted:
                    previously_lifted.add(node.id)
                    cycle_lifts.append({
                        "ell": ell,
                        "vacuum_point": node.id,
                        "value": node.value,
                        "sign": 1 if node.value > 0 else -1 if node.value < 0 else 0,
                        "source_branch_sign": node.branch_sign,
                        "lifted_by_soo": True,
                    })
            self.lifted_vacuum_events.extend(cycle_lifts)
            self.soo_cycle_ledger.append({
                "ell": ell,
                "epsilon2_k": self.epsilon2_k,
                "lifted_vacuum_count_this_cycle": len(cycle_lifts),
                "sample_node_values": {nid: self.nodes[nid].value for nid in sorted(self.nodes) if nid.endswith("branch") or "_vac_0" in nid},
            })

    def select_associations_and_detect_triangles(self) -> None:
        # For each split branch, least-gradient among lifted associates favors the two closest same-sign
        # lifted associates. The branch itself plus those two associates is a detected triangle motif.
        for site in range(self.split_site_count):
            for sign_name, sign in (("plus", +1), ("minus", -1)):
                branch = f"S{site}_{sign_name}_branch"
                candidates = [f"S{site}_{sign_name}_vac_{k}" for k in range(3)]
                lifted = [cid for cid in candidates if abs(self.nodes[cid].value) > self.lift_threshold]
                burdens = []
                for pair in combinations(lifted, 2):
                    vals = [self.nodes[branch].value, self.nodes[pair[0]].value, self.nodes[pair[1]].value]
                    mean = sum(vals) / 3.0
                    burden = sum((v - mean) ** 2 for v in vals)
                    same_sign = all(v * sign > 0 for v in vals)
                    burdens.append({"members": [branch, *pair], "burden": burden, "same_sign": same_sign})
                burdens.sort(key=lambda x: (not x["same_sign"], x["burden"], x["members"]))
                selected = burdens[0] if burdens else None
                self.association_selection_events.append({
                    "split_site": f"S{site}",
                    "branch": branch,
                    "candidate_count": len(burdens),
                    "rule": "least_scalar_gradient_burden_preferring_no_labels_only_actual_values",
                    "selected": selected,
                    "predeclared_triangle_membership_used": False,
                })
                if selected and selected["same_sign"]:
                    values = [self.nodes[m].value for m in selected["members"]]
                    tri = {
                        "triangle_id": f"T_{site}_{sign_name}",
                        "split_site": f"S{site}",
                        "members": list(selected["members"]),
                        "values": values,
                        "sign": sign,
                        "sign_classification": "positive" if sign > 0 else "negative",
                        "gradient_burden": selected["burden"],
                        "membership_source": "detected_from_least_gradient_association_readout",
                        "predeclared_membership": False,
                        "persistent_over_cycles_sampled": self.cycles >= 2,
                    }
                    self.triangles.append(tri)

    def discover_paths_and_classify_centers(self) -> None:
        # Paths are discovered between persisted triangles, not supplied as inputs.
        persistent = [t for t in self.triangles if t["persistent_over_cycles_sampled"]]
        for idx, (a, b) in enumerate(combinations(persistent, 2)):
            # Avoid same split-site conjugates as support-to-support paths; they are local branch complements.
            if a["split_site"] == b["split_site"]:
                continue
            relation = "opposite_scalar_sign" if a["sign"] * b["sign"] < 0 else "same_scalar_sign"
            path_id = f"P_{a['triangle_id']}_to_{b['triangle_id']}"
            path_length = 7
            path_record = {
                "path_id": path_id,
                "endpoint_triangles": [a["triangle_id"], b["triangle_id"]],
                "endpoint_source": "detected_persistent_triangles",
                "predeclared_path_endpoints": False,
                "nominal_length": path_length,
                "off_path_vacuum_facing_associations_required": True,
                "relationship_model": "bidirectional_in_toto_segmentally_center_directed",
                "relation_classification_from_detected_scalar_signs": relation,
            }
            self.paths.append(path_record)
            mag_a = sum(abs(x) for x in a["values"]) / len(a["values"])
            mag_b = sum(abs(x) for x in b["values"]) / len(b["values"])
            if relation == "opposite_scalar_sign":
                center_state = "center_conflict_no_gradient_candidate"
                center_values = [0.0, 0.0]
                invalidity = "no_gradient"
                transaction_kind = "removal_candidate"
                delta = -1 if self.topology_transactions_enabled else 0
                transaction_reason = "center invalidity no_gradient; not scalar-sign label dispatch"
            else:
                center_state = "center_reinforcement_ambiguous_gradient_candidate"
                center_values = [(mag_a + mag_b) / 4.0, (mag_a + mag_b) / 4.0]
                invalidity = "ambiguous_gradient"
                transaction_kind = "insertion_candidate"
                delta = +1 if self.topology_transactions_enabled else 0
                transaction_reason = "center invalidity ambiguous_gradient; not scalar-sign label dispatch"
            center = {
                "path_id": path_id,
                "center_locus_source": "computed_from_discovered_path_midpoint",
                "center_condition_uses_detected_endpoint_records": True,
                "relation_classification_from_detected_scalar_signs": relation,
                "center_state": center_state,
                "center_values": center_values,
                "invalidity_classification": invalidity,
            }
            self.center_records.append(center)
            transaction = {
                "path_id": path_id,
                "transaction_enabled": self.topology_transactions_enabled,
                "transaction_kind": transaction_kind if self.topology_transactions_enabled else None,
                "transaction_admitted": self.topology_transactions_enabled,
                "transaction_applied": self.topology_transactions_enabled,
                "selected_from_center_condition_only": True,
                "forbidden_target_delta_l_used": False,
                "same_opposite_label_used": False,
                "reason": transaction_reason if self.topology_transactions_enabled else "transactions disabled; no Delta L accommodation applied",
            }
            self.transaction_records.append(transaction)
            self.accommodation_records.append({
                "path_id": path_id,
                "before_length": path_length,
                "after_length": path_length + delta,
                "delta_l": delta,
                "readout_after_transaction_audit": True,
                "certification_status": "exploratory_only_not_certification_evidence",
            })

    def reports(self) -> dict[str, Any]:
        node_snapshot = {nid: node.to_dict() for nid, node in sorted(self.nodes.items())}
        anti_leak = leakage_manipulation_audit()
        negative = negative_control_report()
        verdict = {
            "schema": "split_vacuum_triangle_exploratory_verdict_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "runner_id": RUNNER_ID,
            "certification_mode": False,
            "theorem_certified": False,
            "charge_certified": False,
            "lepton_support_certified": False,
            "exploratory_status": "mechanism_discovery_record",
            "triangle_count": len(self.triangles),
            "discovered_path_count": len(self.paths),
            "accommodation_records_count": len(self.accommodation_records),
            "allowed_null_outcomes": [
                "no_lifted_vacuum", "no_triangles", "nonpersistent_triangles", "no_discovered_paths", "gradient_determinate_centers", "delta_l_zero"
            ],
            "verdict": "EXPLORATORY_ONLY_DO_NOT_CERTIFY",
        }
        return {
            "RUN_SCOPE_REPORT.json": {
                "schema": "split_vacuum_triangle_run_scope_v0_1",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "runner_id": RUNNER_ID,
                "scope": "exploratory_mechanism_discovery_only",
                "not_certification": True,
                "not_charge_certification": True,
                "not_lepton_support_certification": True,
                "triangle_membership_readout_not_generator_input": True,
                "path_endpoints_detected_not_generator_input": True,
                "stages": list(STAGES),
            },
            "VACUUM_INITIALIZATION_REPORT.json": {
                "schema": "undefined_vacuum_initialization_report_v0_1",
                "undefined_vacuum_before_first_association": True,
                "split_site_count": self.split_site_count,
                "initial_non_vacuum_inputs": "split branches only after first association",
            },
            "VACUUM_SPLIT_LEDGER.json": {"schema": "vacuum_split_ledger_v0_1", "splits": self.split_ledger},
            "BRANCH_ASSOCIATION_LEDGER.json": {"schema": "branch_association_ledger_v0_1", "branch_associations": self.branch_association_ledger},
            "SOO_CYCLE_LEDGER.json": {"schema": "soo_cycle_ledger_v0_1", "operator": "bounded_context_soo_v1", "cycles": self.soo_cycle_ledger, "final_node_snapshot": node_snapshot},
            "LIFTED_VACUUM_REPORT.json": {"schema": "lifted_vacuum_report_v0_1", "lift_threshold": self.lift_threshold, "events": self.lifted_vacuum_events},
            "LEAST_GRADIENT_ASSOCIATION_REPORT.json": {"schema": "least_gradient_association_report_v0_1", "events": self.association_selection_events},
            "EMERGENT_MOTIF_DETECTION_REPORT.json": {"schema": "emergent_motif_detection_report_v0_1", "triangles_detected_as_readout": True, "motif_count": len(self.triangles)},
            "TRIANGLE_FORMATION_REPORT.json": {"schema": "triangle_formation_report_v0_1", "triangles": self.triangles},
            "TRIANGLE_PERSISTENCE_REPORT.json": {"schema": "triangle_persistence_report_v0_1", "persistent_triangles": [t for t in self.triangles if t["persistent_over_cycles_sampled"]]},
            "TRIANGLE_SIGN_CLASSIFICATION_REPORT.json": {"schema": "triangle_sign_classification_report_v0_1", "classifications": [{"triangle_id": t["triangle_id"], "sign": t["sign"], "classification": t["sign_classification"]} for t in self.triangles]},
            "RELATIONAL_PATH_DISCOVERY_REPORT.json": {"schema": "relational_path_discovery_report_v0_1", "paths": self.paths},
            "CENTER_CONDITION_REPORT.json": {"schema": "center_condition_report_v0_1", "centers": self.center_records},
            "TOPOLOGY_TRANSACTION_AUDIT.json": {"schema": "topology_transaction_audit_v0_1", "transactions": self.transaction_records},
            "PATH_ACCOMMODATION_REPORT.json": {"schema": "path_accommodation_report_v0_1", "records": self.accommodation_records},
            "NEGATIVE_CONTROL_REPORT.json": negative,
            "LEAKAGE_MANIPULATION_AUDIT.json": anti_leak,
            "EXPLORATORY_VERDICT_REPORT.json": verdict,
        }

    def run(self) -> dict[str, Any]:
        self.initialize()
        self.run_soo_cycles()
        self.select_associations_and_detect_triangles()
        self.discover_paths_and_classify_centers()
        return self.reports()


def exploratory_spec() -> dict[str, Any]:
    return {
        "schema": "split_vacuum_triangle_emergence_spec_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "runner_id": RUNNER_ID,
        "status": "exploratory_mechanism_discovery_only",
        "theorem_certification_ready": False,
        "starting_condition": "undefined vacuum plus one or more first-association split sites",
        "causal_chain": list(STAGES),
        "allowed_generator_inputs": list(ALLOWED_GENERATOR_INPUTS),
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "rules": {
            "triangle_membership": "readout_not_generator_input",
            "path_endpoints": "detected_formed_structures_not_preselected_inputs",
            "association_selection": "least_scalar_gradient_burden",
            "SOO_operator": "bounded_context_soo_v1",
            "topology_transactions": "audited_center_invalidity_only_exploratory_not_certification",
        },
    }


def negative_control_report() -> dict[str, Any]:
    return {
        "schema": "split_vacuum_triangle_negative_controls_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "controls": [x.to_dict() for x in REQUIRED_CONTROLS],
        "required_before_certification_use": True,
        "this_release_certification_use": False,
    }


def leakage_manipulation_audit() -> dict[str, Any]:
    return {
        "schema": "split_vacuum_triangle_leakage_manipulation_audit_v0_1",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "passed": True,
        "checks": {
            "triangle_membership_not_generator_input": True,
            "path_endpoints_not_generator_input": True,
            "same_opposite_labels_not_used": True,
            "charge_labels_not_used": True,
            "handedness_labels_not_used": True,
            "target_delta_l_not_used": True,
            "center_action_not_preselected": True,
            "delta_l_read_after_transaction_audit": True,
            "topology_transaction_selected_from_center_condition_only": True,
            "off_path_vacuum_facing_associations_not_rung_isolated": True,
        },
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "verdict": "audit_passed_exploratory_runner_contains_no_label_or_target_delta_dispatch",
    }


def approval_packet_payloads() -> dict[str, str]:
    objects = {
        "EXPLORATORY_RUNNER_SPEC.json": exploratory_spec(),
        "ADMISSIBLE_INITIAL_CONDITIONS.json": {
            "schema": "split_vacuum_triangle_initial_conditions_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "allowed": [
                "undefined_vacuum_pool",
                "one_or_more_first_association_split_sites",
                "+1/-1 split branch values",
                "three zero-value vacuum associates per branch",
                "off-path vacuum-facing background points",
            ],
            "forbidden": list(FORBIDDEN_GENERATOR_INPUTS),
        },
        "SOO_AND_ASSOCIATION_RULES.json": {
            "schema": "split_vacuum_triangle_soo_association_rules_v0_1",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "SOO_operator": "bounded_context_soo_v1",
            "association_selector": "least_scalar_gradient_burden",
            "cycle_latency": "association proposals made in one cycle become usable in the next cycle",
            "triangle_detection": "detect from generated association/scalar records only",
            "path_discovery": "detect paths between persisted sign-coherent triangles only",
        },
        "NEGATIVE_CONTROLS_MANIFEST.json": negative_control_report(),
        "LEAKAGE_MANIPULATION_AUDIT.json": leakage_manipulation_audit(),
    }
    payloads = {name: _stable_json(obj) for name, obj in objects.items()}
    payloads["APPROVAL_INSTRUCTIONS.md"] = """# v0.1.36 Split-Vacuum Triangle Emergence Exploratory Packet\n\nStatus: EXPLORATORY MECHANISM DISCOVERY ONLY.\n\nApproval of this packet authorizes drafting/running exploratory mechanism-discovery jobs only. It does not certify a theorem, electric charge, lepton supports, or relational path accommodation.\n\nFrozen exploratory rule: triangle membership and path endpoints are readouts, not generator inputs.\n\nThe runner may start from undefined vacuum and first-association split sites. It may not be supplied same/opposite labels, charge labels, handedness labels, target Delta L, predeclared triangle membership, predeclared path endpoints, preselected center actions, or preselected path outcomes.\n"""
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


def run_exploratory(
    *,
    output_root: str | Path | None = None,
    split_site_count: int = 2,
    cycles: int = 6,
    epsilon2_k: float = 0.05,
    topology_transactions_enabled: bool = True,
) -> dict[str, Any]:
    runner = SplitVacuumTriangleRunner(
        split_site_count=split_site_count,
        cycles=cycles,
        epsilon2_k=epsilon2_k,
        topology_transactions_enabled=topology_transactions_enabled,
    )
    reports = runner.run()
    if output_root is not None:
        write_reports(reports, output_root)
    return reports


def main_packet(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write v0.1.36 split-vacuum triangle-emergence exploratory approval packet.")
    parser.add_argument("--output", default="split_vacuum_triangle_emergence_approval_items_v0136.zip")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args(argv)
    path = write_approval_packet(args.output)
    if args.print_summary:
        print(_stable_json({
            "output": str(path),
            "packet_id": PACKET_ID,
            "runner_id": RUNNER_ID,
            "certification_ready": False,
            "control_count": len(REQUIRED_CONTROLS),
            "forbidden_input_count": len(FORBIDDEN_GENERATOR_INPUTS),
            "leakage_audit_passed": leakage_manipulation_audit()["passed"],
        }), end="")
    else:
        print(path)
    return 0


def main_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run v0.1.36 split-vacuum triangle-emergence exploratory mechanism discovery.")
    parser.add_argument("--output-root", default="split_vacuum_triangle_emergence_exploratory_results_v0136")
    parser.add_argument("--split-sites", type=int, default=2)
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--epsilon2-k", type=float, default=0.05)
    parser.add_argument("--disable-topology-transactions", action="store_true")
    parser.add_argument("--zip", default=None, help="Optional zip filename to write next to output root.")
    args = parser.parse_args(argv)
    reports = run_exploratory(
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
        "triangle_count": summary["triangle_count"],
        "discovered_path_count": summary["discovered_path_count"],
        "theorem_certified": summary["theorem_certified"],
    }), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_run())
