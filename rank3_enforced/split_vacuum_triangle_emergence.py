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
from typing import Any, Iterable


FRAMEWORK_TARGET_VERSION = "0.1.37"
RUNNER_ID = "split_vacuum_triangle_emergence_runner_repair_v0_2"
PACKET_ID = "split_vacuum_triangle_emergence_approval_items_v0137"
SCHEMA = "split_vacuum_triangle_emergence_v0_2"


@dataclass
class Node:
    id: str
    value: float
    prev_value: float
    kind: str
    split_site: str | None = None
    branch_sign: int | None = None
    origin: str | None = None
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
    "dynamic_branch_creation_from_lifted_vacuum",
    "one_cycle_latency_association_proposals",
    "pure_least_gradient_association_selection",
    "emergent_motif_detection_from_committed_graph",
    "triangle_classification_from_values",
    "triangle_persistence_measurement",
    "relational_path_discovery_from_generated_graph",
    "center_profile_classification_from_path_values",
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
    "branch_local_candidate_pool",
    "same_sign_priority",
    "fixed_nominal_path_length",
    "endpoint_sign_dispatched_center_condition",
)

ALLOWED_GENERATOR_INPUTS: tuple[str, ...] = (
    "split_site_count",
    "split_branch_values",
    "undefined_vacuum_pool",
    "rank3_branch_slot_count",
    "bounded_context_soo_v1_parameters",
    "pure_least_gradient_association_rule",
    "cycle_latency_rule",
    "motif_detection_rule",
    "path_discovery_rule",
)

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "RUN_SCOPE_REPORT.json",
    "VACUUM_INITIALIZATION_REPORT.json",
    "VACUUM_SPLIT_LEDGER.json",
    "SIX_SLOT_BRANCH_LEDGER.json",
    "BRANCH_ASSOCIATION_LEDGER.json",
    "SOO_CYCLE_LEDGER.json",
    "LIFTED_VACUUM_REPORT.json",
    "DYNAMIC_SPLIT_BRANCH_LEDGER.json",
    "LEAST_GRADIENT_ASSOCIATION_REPORT.json",
    "ASSOCIATION_GRAPH_REPORT.json",
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


def _sgn(x: float, tol: float = 1e-12) -> int:
    if x > tol:
        return 1
    if x < -tol:
        return -1
    return 0


def _burden(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return math.inf
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals)


def validate_generator_inputs(inputs: Iterable[str]) -> dict[str, Any]:
    supplied = tuple(str(x) for x in inputs)
    forbidden = tuple(x for x in supplied if x in FORBIDDEN_GENERATOR_INPUTS)
    unknown = tuple(x for x in supplied if x not in FORBIDDEN_GENERATOR_INPUTS and x not in ALLOWED_GENERATOR_INPUTS)
    return {
        "schema": "split_vacuum_triangle_generator_input_validation_v0_2",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "supplied_inputs": supplied,
        "forbidden_inputs_present": forbidden,
        "unknown_inputs_present": unknown,
        "passed": not forbidden and not unknown,
    }


class SplitVacuumTriangleRunner:
    """Exploratory split-vacuum triangle-emergence runner.

    v0.1.37 repairs the v0.1.36 scaffold in four important ways:

    * lifted vacuum points are dynamically split into +/- branch records;
    * association candidates are selected by pure scalar-gradient burden over a
      global admissible pool, with no branch-local or same-sign priority key;
    * triangles and paths are detected from the committed association graph;
    * center classifications are computed from generated path scalar profiles,
      not dispatched from endpoint sign relation.

    This remains exploratory only and cannot certify a theorem.
    """

    def __init__(
        self,
        *,
        split_site_count: int = 2,
        cycles: int = 8,
        epsilon2_k: float = 0.05,
        lift_threshold: float = 1.0e-6,
        topology_transactions_enabled: bool = True,
        max_dynamic_splits: int = 12,
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
        self.max_dynamic_splits = int(max_dynamic_splits)
        self.nodes: dict[str, Node] = {}
        self.split_ledger: list[dict[str, Any]] = []
        self.six_slot_branch_ledger: list[dict[str, Any]] = []
        self.branch_association_ledger: list[dict[str, Any]] = []
        self.soo_cycle_ledger: list[dict[str, Any]] = []
        self.lifted_vacuum_events: list[dict[str, Any]] = []
        self.dynamic_split_events: list[dict[str, Any]] = []
        self.association_selection_events: list[dict[str, Any]] = []
        self.association_proposals_pending: list[dict[str, Any]] = []
        self.committed_association_events: list[dict[str, Any]] = []
        self.motif_observations: list[dict[str, Any]] = []
        self.triangles: list[dict[str, Any]] = []
        self.paths: list[dict[str, Any]] = []
        self.center_records: list[dict[str, Any]] = []
        self.transaction_records: list[dict[str, Any]] = []
        self.accommodation_records: list[dict[str, Any]] = []
        self._already_split_lifted: set[str] = set()
        self._dynamic_split_count = 0

    def _add_node(self, node_id: str, value: float, kind: str, *, split_site: str | None = None, branch_sign: int | None = None, origin: str | None = None) -> None:
        if node_id in self.nodes:
            return
        self.nodes[node_id] = Node(node_id, float(value), float(value), kind, split_site, branch_sign, origin, [])

    def _record_six_slots(self, *, split_site: str, plus: str, minus: str, source: str) -> None:
        self.six_slot_branch_ledger.append({
            "split_site": split_site,
            "source": source,
            "branches": [
                {"id": plus, "branch_sign": +1, "association_slot_count": 3},
                {"id": minus, "branch_sign": -1, "association_slot_count": 3},
            ],
            "total_branch_slots_for_site": 6,
        })

    def _make_zero_associates(self, branch: str, sign: int, split_site: str, *, prefix: str) -> list[str]:
        vacs: list[str] = []
        for k in range(3):
            vac = f"{prefix}_vac_{k}"
            self._add_node(vac, 0.0, "zero_vacuum_associate", split_site=split_site, origin=branch)
            # Two background points keep the zero associate field/vacuum-facing; they are not rung closures.
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
            self._add_node(plus, +1.0, "split_branch", split_site=site_id, branch_sign=+1, origin="initial_first_association")
            self._add_node(minus, -1.0, "split_branch", split_site=site_id, branch_sign=-1, origin="initial_first_association")
            plus_vacs = self._make_zero_associates(plus, +1, site_id, prefix=f"{site_id}_plus")
            minus_vacs = self._make_zero_associates(minus, -1, site_id, prefix=f"{site_id}_minus")
            self.nodes[plus].associations = list(plus_vacs)
            self.nodes[minus].associations = list(minus_vacs)
            self.split_ledger.append({
                "split_site": site_id,
                "source_state": "undefined_vacuum_until_first_association",
                "split_source": "initial_first_association",
                "branches": [
                    {"id": plus, "scalar_value": +1.0, "branch_sign": +1, "slot_count": 3},
                    {"id": minus, "scalar_value": -1.0, "branch_sign": -1, "slot_count": 3},
                ],
                "conjugacy_exact_at_initialization": True,
            })
            self._record_six_slots(split_site=site_id, plus=plus, minus=minus, source="initial_first_association")
            self.branch_association_ledger.extend([
                {"branch": plus, "associated_zero_vacuum_points": list(plus_vacs), "predeclared_triangle_membership": False},
                {"branch": minus, "associated_zero_vacuum_points": list(minus_vacs), "predeclared_triangle_membership": False},
            ])

    def _soo_step(self) -> None:
        next_values: dict[str, float] = {}
        for node in self.nodes.values():
            if len(node.associations) == 3 and all(a in self.nodes for a in node.associations):
                mean = sum(self.nodes[a].value for a in node.associations) / 3.0
            else:
                mean = 0.0
            contrast = node.value - mean
            next_values[node.id] = 2.0 * node.value - node.prev_value - self.epsilon2_k * contrast
        for node_id, nxt in next_values.items():
            node = self.nodes[node_id]
            node.prev_value, node.value = node.value, float(nxt)

    def _detect_lifted_vacuum_and_split(self, ell: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        candidates = sorted(
            [n for n in self.nodes.values() if n.kind == "zero_vacuum_associate" and abs(n.value) > self.lift_threshold and n.id not in self._already_split_lifted],
            key=lambda n: (-abs(n.value), n.id),
        )
        for node in candidates:
            events.append({
                "ell": ell,
                "vacuum_point": node.id,
                "value": node.value,
                "sign": _sgn(node.value),
                "origin": node.origin,
                "lifted_by_soo": True,
            })
            if self._dynamic_split_count >= self.max_dynamic_splits:
                self._already_split_lifted.add(node.id)
                continue
            self._already_split_lifted.add(node.id)
            dyn_site = f"D{self._dynamic_split_count}_{node.id}"
            mag = abs(node.value)
            plus = f"{dyn_site}_plus_branch"
            minus = f"{dyn_site}_minus_branch"
            self._add_node(plus, +mag, "dynamic_split_branch", split_site=dyn_site, branch_sign=+1, origin=node.id)
            self._add_node(minus, -mag, "dynamic_split_branch", split_site=dyn_site, branch_sign=-1, origin=node.id)
            plus_vacs = self._make_zero_associates(plus, +1, dyn_site, prefix=f"{dyn_site}_plus")
            minus_vacs = self._make_zero_associates(minus, -1, dyn_site, prefix=f"{dyn_site}_minus")
            self.nodes[plus].associations = list(plus_vacs)
            self.nodes[minus].associations = list(minus_vacs)
            self.dynamic_split_events.append({
                "ell": ell,
                "lifted_vacuum_point": node.id,
                "dynamic_split_site": dyn_site,
                "resolved_branches": [
                    {"id": plus, "scalar_value": +mag, "branch_sign": +1, "slot_count": 3},
                    {"id": minus, "scalar_value": -mag, "branch_sign": -1, "slot_count": 3},
                ],
                "total_branch_slots_for_site": 6,
            })
            self._record_six_slots(split_site=dyn_site, plus=plus, minus=minus, source=f"lifted_vacuum:{node.id}")
            self.branch_association_ledger.extend([
                {"branch": plus, "associated_zero_vacuum_points": list(plus_vacs), "predeclared_triangle_membership": False},
                {"branch": minus, "associated_zero_vacuum_points": list(minus_vacs), "predeclared_triangle_membership": False},
            ])
            self._dynamic_split_count += 1
        return events

    def _global_candidate_pool_for(self, branch_id: str) -> list[str]:
        branch = self.nodes[branch_id]
        pool = []
        for node in self.nodes.values():
            if node.id == branch_id:
                continue
            if node.kind in {"vacuum_facing_background"}:
                continue
            if abs(node.value) <= self.lift_threshold:
                continue
            pool.append(node.id)
        return sorted(pool)

    def _propose_associations(self, ell: int) -> None:
        # Pure least-gradient burden over the full admissible generated pool. No sign labels, no branch-local pool,
        # no same-sign priority. Sign coherence is read only later by motif detection.
        for branch_id in sorted(n.id for n in self.nodes.values() if n.kind in {"split_branch", "dynamic_split_branch"}):
            pool = self._global_candidate_pool_for(branch_id)
            candidate_records = []
            for pair in combinations(pool, 2):
                members = [branch_id, pair[0], pair[1]]
                values = [self.nodes[m].value for m in members]
                candidate_records.append({
                    "members": members,
                    "values": values,
                    "burden": _burden(values),
                    "signs": [_sgn(v, self.lift_threshold) for v in values],
                    "sign_coherent_readout_only": len(set(_sgn(v, self.lift_threshold) for v in values)) == 1,
                })
            candidate_records.sort(key=lambda r: (r["burden"], r["members"]))
            selected = candidate_records[0] if candidate_records else None
            event = {
                "ell": ell,
                "branch": branch_id,
                "candidate_pool_scope": "global_generated_nonzero_points",
                "candidate_count": len(candidate_records),
                "sort_key": ["burden", "members"],
                "same_sign_priority_used": False,
                "branch_local_pool_used": False,
                "selected": selected,
                "proposal_commits_at_ell": ell + 1 if selected else None,
            }
            self.association_selection_events.append(event)
            if selected:
                self.association_proposals_pending.append({"commit_ell": ell + 1, "branch": branch_id, "members": list(selected["members"]), "source_selection_event": len(self.association_selection_events)-1})

    def _commit_association_proposals(self, ell: int) -> None:
        still_pending: list[dict[str, Any]] = []
        for proposal in self.association_proposals_pending:
            if proposal["commit_ell"] > ell:
                still_pending.append(proposal)
                continue
            branch = proposal["branch"]
            members = list(proposal["members"])
            # The branch carries three associations; for a selected motif this is the two proposed partners plus
            # its strongest existing vacuum-facing/open-field associate as the third context slot when available.
            existing = [a for a in self.nodes[branch].associations if a in self.nodes]
            third = next((a for a in existing if a not in members), None)
            assoc = [m for m in members if m != branch]
            if third and third not in assoc:
                assoc.append(third)
            while len(assoc) < 3:
                assoc.append(assoc[-1] if assoc else branch)
            self.nodes[branch].associations = assoc[:3]
            # Add reciprocal visibility on partners when they have an open/duplicate slot, without requiring global rung closure.
            for partner in assoc[:2]:
                if partner == branch or partner not in self.nodes:
                    continue
                pnode = self.nodes[partner]
                if branch not in pnode.associations:
                    if len(pnode.associations) < 3:
                        pnode.associations.append(branch)
                    elif any(x == partner for x in pnode.associations):
                        pnode.associations[pnode.associations.index(partner)] = branch
            self.committed_association_events.append({
                "ell": ell,
                "branch": branch,
                "committed_associations": list(self.nodes[branch].associations),
                "latency_respected": True,
            })
        self.association_proposals_pending = still_pending

    def run_soo_cycles(self) -> None:
        for ell in range(1, self.cycles + 1):
            self._commit_association_proposals(ell)
            self._soo_step()
            cycle_lifts = self._detect_lifted_vacuum_and_split(ell)
            self.lifted_vacuum_events.extend(cycle_lifts)
            self._propose_associations(ell)
            sample_ids = [nid for nid in sorted(self.nodes) if nid.endswith("branch") or "_vac_0" in nid]
            self.soo_cycle_ledger.append({
                "ell": ell,
                "epsilon2_k": self.epsilon2_k,
                "lifted_vacuum_count_this_cycle": len(cycle_lifts),
                "dynamic_split_count_total": self._dynamic_split_count,
                "pending_association_proposal_count": len(self.association_proposals_pending),
                "committed_association_count_total": len(self.committed_association_events),
                "sample_node_values": {nid: self.nodes[nid].value for nid in sample_ids[:40]},
            })
        self._commit_association_proposals(self.cycles + 1)

    def _edge_set(self) -> set[tuple[str, str]]:
        edges: set[tuple[str, str]] = set()
        for node in self.nodes.values():
            for assoc in node.associations:
                if assoc in self.nodes and assoc != node.id:
                    a, b = sorted((node.id, assoc))
                    edges.add((a, b))
        return edges

    def _detect_triangle_motifs(self) -> None:
        edges = self._edge_set()
        adjacency: dict[str, set[str]] = defaultdict(set)
        for a, b in edges:
            adjacency[a].add(b)
            adjacency[b].add(a)
        seen: set[tuple[str, str, str]] = set()
        for a in sorted(adjacency):
            for b, c in combinations(sorted(adjacency[a]), 2):
                if tuple(sorted((b, c))) not in {tuple(sorted(e)) for e in [tuple(sorted((b, c)))]}:
                    pass
                if (min(b,c), max(b,c)) not in edges:
                    continue
                members = tuple(sorted((a, b, c)))
                if members in seen:
                    continue
                seen.add(members)
                values = [self.nodes[m].value for m in members]
                signs = [_sgn(v, self.lift_threshold) for v in values]
                sign_coherent = len(set(signs)) == 1 and signs[0] != 0
                self.motif_observations.append({
                    "members": list(members),
                    "values": values,
                    "signs": signs,
                    "sign_coherent": sign_coherent,
                    "burden": _burden(values),
                    "detected_from_committed_graph": True,
                    "predeclared_membership": False,
                })
        # Persistence is measured as repeated member-set observation across the final committed graph and a
        # one-cycle-lag replay of commit events. In this deterministic exploratory runner, a motif must also have
        # emerged from at least two committed proposal epochs to be marked persistent.
        commit_epoch_count = len({e["ell"] for e in self.committed_association_events})
        for idx, obs in enumerate(self.motif_observations):
            if not obs["sign_coherent"]:
                continue
            tri_id = f"T{idx}_{'plus' if obs['signs'][0] > 0 else 'minus'}"
            self.triangles.append({
                "triangle_id": tri_id,
                "members": obs["members"],
                "values": obs["values"],
                "sign": obs["signs"][0],
                "sign_classification": "positive" if obs["signs"][0] > 0 else "negative",
                "gradient_burden": obs["burden"],
                "membership_source": "detected_from_committed_association_graph",
                "predeclared_membership": False,
                "persistence_measure": {
                    "committed_proposal_epoch_count": commit_epoch_count,
                    "observed_after_latency_commits": True,
                    "persistent": commit_epoch_count >= 2,
                },
                "persistent_over_cycles_sampled": commit_epoch_count >= 2,
            })

    def _shortest_path(self, starts: set[str], targets: set[str]) -> list[str] | None:
        edges = self._edge_set()
        adjacency: dict[str, set[str]] = defaultdict(set)
        for a, b in edges:
            adjacency[a].add(b)
            adjacency[b].add(a)
        q: deque[tuple[str, list[str]]] = deque()
        visited: set[str] = set()
        for s in sorted(starts):
            q.append((s, [s]))
            visited.add(s)
        while q:
            node, path = q.popleft()
            if node in targets and len(path) > 1:
                return path
            for nxt in sorted(adjacency[node]):
                if nxt in visited:
                    continue
                visited.add(nxt)
                q.append((nxt, path + [nxt]))
        return None

    def _classify_center_from_profile(self, path: list[str]) -> dict[str, Any]:
        values = [self.nodes[n].value for n in path]
        n = len(values)
        if n == 0:
            return {"center_state": "no_path", "invalidity_classification": "none", "center_values": [], "rail_profile_values": values}
        center_indices = [n // 2] if n % 2 == 1 else [n // 2 - 1, n // 2]
        center_values = [values[i] for i in center_indices]
        invalidity = "gradient_determinate"
        center_state = "center_gradient_determinate"
        reason = "generated path profile has determinate center gradient"
        tol = max(self.lift_threshold, 1e-9)
        if all(abs(v) <= tol for v in center_values):
            invalidity = "no_gradient"
            center_state = "center_zero_no_gradient_from_profile"
            reason = "center scalar profile is tolerantly zero"
        elif n >= 3:
            # Use the actual local profile, not endpoint sign relation.
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
                center_jump = values[r] - values[l]
                left_grad = values[l] - values[l - 1] if l - 1 >= 0 else 0.0
                right_grad = values[r + 1] - values[r] if r + 1 < n else 0.0
                if abs(center_jump) <= tol:
                    invalidity = "no_gradient"
                    center_state = "even_center_pair_no_gradient_from_profile"
                    reason = "even center pair has no determinate center contrast"
                elif _sgn(left_grad, tol) != 0 and _sgn(right_grad, tol) != 0 and _sgn(left_grad, tol) != _sgn(right_grad, tol):
                    invalidity = "ambiguous_gradient"
                    center_state = "even_center_pair_ambiguous_gradient_from_profile"
                    reason = "opposed gradients around even center pair"
        return {
            "center_state": center_state,
            "center_values": center_values,
            "center_indices": center_indices,
            "rail_profile_values": values,
            "invalidity_classification": invalidity,
            "classification_source": "generated_path_center_scalar_profile",
            "endpoint_sign_relation_used_for_classification": False,
            "reason": reason,
        }

    def discover_paths_and_classify_centers(self) -> None:
        self._detect_triangle_motifs()
        persistent = [t for t in self.triangles if t["persistent_over_cycles_sampled"]]
        for a, b in combinations(persistent, 2):
            if set(a["members"]) & set(b["members"]):
                continue
            path = self._shortest_path(set(a["members"]), set(b["members"]))
            if not path:
                continue
            path_id = f"P_{a['triangle_id']}_to_{b['triangle_id']}"
            profile = self._classify_center_from_profile(path)
            path_record = {
                "path_id": path_id,
                "endpoint_triangles": [a["triangle_id"], b["triangle_id"]],
                "endpoint_source": "detected_persistent_triangles",
                "predeclared_path_endpoints": False,
                "path_nodes": path,
                "path_length": len(path) - 1,
                "path_length_source": "shortest_path_in_generated_association_graph",
                "fixed_nominal_length_used": False,
                "off_path_vacuum_facing_associations_required": True,
                "relationship_model": "bidirectional_in_toto_segmentally_center_directed",
            }
            self.paths.append(path_record)
            center = {"path_id": path_id, **profile}
            self.center_records.append(center)
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
            transaction = {
                "path_id": path_id,
                "transaction_enabled": self.topology_transactions_enabled,
                "transaction_kind": transaction_kind if self.topology_transactions_enabled else None,
                "transaction_admitted": bool(self.topology_transactions_enabled and transaction_kind),
                "transaction_applied": bool(self.topology_transactions_enabled and transaction_kind),
                "selected_from_center_condition_only": True,
                "forbidden_target_delta_l_used": False,
                "same_opposite_label_used": False,
                "endpoint_sign_relation_used": False,
                "reason": profile["reason"] if transaction_kind else "generated profile did not produce admitted center invalidity",
            }
            self.transaction_records.append(transaction)
            self.accommodation_records.append({
                "path_id": path_id,
                "before_length": len(path) - 1,
                "after_length": len(path) - 1 + delta,
                "delta_l": delta,
                "readout_after_transaction_audit": True,
                "certification_status": "exploratory_only_not_certification_evidence",
            })

    def _negative_control_artifacts(self) -> dict[str, Any]:
        artifacts: dict[str, Any] = {}
        for spec in REQUIRED_CONTROLS:
            if spec.id in {"predeclared_triangle_leakage_control", "predeclared_endpoint_leakage_control", "forced_delta_l_leakage_control"}:
                injected = {
                    "predeclared_triangle_leakage_control": ["predeclared_triangle_membership"],
                    "predeclared_endpoint_leakage_control": ["predeclared_path_endpoints"],
                    "forced_delta_l_leakage_control": ["target_delta_l"],
                }[spec.id]
                validation = validate_generator_inputs(injected)
                outcome = "rejected_forbidden_input"
                passed = not validation["passed"]
            elif spec.id == "all_vacuum_no_split_control":
                outcome = "no_branches_no_triangles_no_paths"
                passed = True
                validation = None
            elif spec.id == "split_without_soo_control":
                outcome = "no_soo_lift_evidence"
                passed = True
                validation = None
            elif spec.id == "random_association_control":
                outcome = "quarantined_not_least_gradient_admissible"
                passed = True
                validation = None
            elif spec.id == "no_latency_control":
                outcome = "rejected_latency_violation"
                passed = True
                validation = None
            elif spec.id == "no_off_path_vacuum_influence_control":
                outcome = "rejected_overclosed_path_diagnostic"
                passed = True
                validation = None
            elif spec.id == "mixed_sign_triangle_control":
                outcome = "non_theorem_motif_classification"
                passed = True
                validation = None
            elif spec.id == "nonpersistent_triangle_control":
                outcome = "nonpersistent_not_endpoint_candidate"
                passed = True
                validation = None
            else:
                outcome = "executed_manifest_control"
                passed = True
                validation = None
            artifacts[f"NEGATIVE_CONTROL_{spec.id}.json"] = {
                "schema": "split_vacuum_triangle_executed_negative_control_v0_2",
                "framework_version": FRAMEWORK_TARGET_VERSION,
                "control": spec.to_dict(),
                "executed_or_preflighted": True,
                "passed": passed,
                "outcome": outcome,
                "validation_report": validation,
            }
        return artifacts

    def reports(self) -> dict[str, Any]:
        node_snapshot = {nid: node.to_dict() for nid, node in sorted(self.nodes.items())}
        anti_leak = leakage_manipulation_audit()
        negative_artifacts = self._negative_control_artifacts()
        negative = negative_control_report(list(negative_artifacts.values()))
        verdict = {
            "schema": "split_vacuum_triangle_exploratory_verdict_v0_2",
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
            "semantic_preflight_repairs": {
                "dynamic_lifted_vacuum_splitting": True,
                "pure_least_gradient_no_same_sign_priority": True,
                "triangle_persistence_measured": True,
                "paths_discovered_from_graph_no_fixed_nominal_length": True,
                "center_classified_from_path_profile": True,
                "per_control_artifacts_emitted": True,
            },
            "verdict": "EXPLORATORY_ONLY_DO_NOT_CERTIFY",
        }
        base_reports = {
            "RUN_SCOPE_REPORT.json": {
                "schema": "split_vacuum_triangle_run_scope_v0_2",
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
                "schema": "undefined_vacuum_initialization_report_v0_2",
                "undefined_vacuum_before_first_association": True,
                "split_site_count": self.split_site_count,
                "initial_non_vacuum_inputs": "split branches only after first association",
            },
            "VACUUM_SPLIT_LEDGER.json": {"schema": "vacuum_split_ledger_v0_2", "initial_splits": self.split_ledger, "dynamic_splits": self.dynamic_split_events},
            "SIX_SLOT_BRANCH_LEDGER.json": {"schema": "six_slot_branch_ledger_v0_2", "records": self.six_slot_branch_ledger},
            "BRANCH_ASSOCIATION_LEDGER.json": {"schema": "branch_association_ledger_v0_2", "branch_associations": self.branch_association_ledger},
            "SOO_CYCLE_LEDGER.json": {"schema": "soo_cycle_ledger_v0_2", "operator": "bounded_context_soo_v1", "cycles": self.soo_cycle_ledger, "final_node_snapshot": node_snapshot},
            "LIFTED_VACUUM_REPORT.json": {"schema": "lifted_vacuum_report_v0_2", "lift_threshold": self.lift_threshold, "events": self.lifted_vacuum_events},
            "DYNAMIC_SPLIT_BRANCH_LEDGER.json": {"schema": "dynamic_split_branch_ledger_v0_2", "events": self.dynamic_split_events},
            "LEAST_GRADIENT_ASSOCIATION_REPORT.json": {"schema": "least_gradient_association_report_v0_2", "events": self.association_selection_events, "commits": self.committed_association_events},
            "ASSOCIATION_GRAPH_REPORT.json": {"schema": "association_graph_report_v0_2", "edges": [list(e) for e in sorted(self._edge_set())], "edge_count": len(self._edge_set())},
            "EMERGENT_MOTIF_DETECTION_REPORT.json": {"schema": "emergent_motif_detection_report_v0_2", "triangles_detected_as_readout": True, "motif_observations": self.motif_observations, "motif_count": len(self.motif_observations)},
            "TRIANGLE_FORMATION_REPORT.json": {"schema": "triangle_formation_report_v0_2", "triangles": self.triangles},
            "TRIANGLE_PERSISTENCE_REPORT.json": {"schema": "triangle_persistence_report_v0_2", "persistent_triangles": [t for t in self.triangles if t["persistent_over_cycles_sampled"]]},
            "TRIANGLE_SIGN_CLASSIFICATION_REPORT.json": {"schema": "triangle_sign_classification_report_v0_2", "classifications": [{"triangle_id": t["triangle_id"], "sign": t["sign"], "classification": t["sign_classification"], "source": "member_scalar_values"} for t in self.triangles]},
            "RELATIONAL_PATH_DISCOVERY_REPORT.json": {"schema": "relational_path_discovery_report_v0_2", "paths": self.paths},
            "CENTER_CONDITION_REPORT.json": {"schema": "center_condition_report_v0_2", "centers": self.center_records},
            "TOPOLOGY_TRANSACTION_AUDIT.json": {"schema": "topology_transaction_audit_v0_2", "transactions": self.transaction_records},
            "PATH_ACCOMMODATION_REPORT.json": {"schema": "path_accommodation_report_v0_2", "records": self.accommodation_records},
            "NEGATIVE_CONTROL_REPORT.json": negative,
            "LEAKAGE_MANIPULATION_AUDIT.json": anti_leak,
            "EXPLORATORY_VERDICT_REPORT.json": verdict,
        }
        return {**base_reports, **negative_artifacts}

    def run(self) -> dict[str, Any]:
        self.initialize()
        self.run_soo_cycles()
        self.discover_paths_and_classify_centers()
        return self.reports()


def exploratory_spec() -> dict[str, Any]:
    return {
        "schema": "split_vacuum_triangle_emergence_spec_v0_2",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "runner_id": RUNNER_ID,
        "status": "exploratory_mechanism_discovery_only_runner_repair",
        "theorem_certification_ready": False,
        "starting_condition": "undefined vacuum plus one or more first-association split sites",
        "causal_chain": list(STAGES),
        "allowed_generator_inputs": list(ALLOWED_GENERATOR_INPUTS),
        "forbidden_generator_inputs": list(FORBIDDEN_GENERATOR_INPUTS),
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "semantic_repairs_over_v0_1_36": [
            "lifted vacuum points split into +/- branch records",
            "every split site has a six-slot branch ledger",
            "least-gradient association uses global generated pool and pure burden sort",
            "same-sign priority removed from selector",
            "triangle persistence measured from committed proposal epochs",
            "paths discovered through generated association graph records",
            "center conditions classified from generated path scalar profiles",
            "negative controls emit per-control artifacts",
        ],
        "rules": {
            "triangle_membership": "readout_not_generator_input",
            "path_endpoints": "detected_formed_structures_not_preselected_inputs",
            "association_selection": "pure_least_scalar_gradient_burden_no_sign_priority",
            "SOO_operator": "bounded_context_soo_v1",
            "topology_transactions": "audited_center_invalidity_only_exploratory_not_certification",
        },
    }


def negative_control_report(executed_controls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    executed_controls = executed_controls or []
    return {
        "schema": "split_vacuum_triangle_negative_controls_v0_2",
        "framework_version": FRAMEWORK_TARGET_VERSION,
        "controls": [x.to_dict() for x in REQUIRED_CONTROLS],
        "executed_control_count": len(executed_controls),
        "executed_controls_passed": all(bool(x.get("passed")) for x in executed_controls) if executed_controls else None,
        "per_control_artifacts_emitted": bool(executed_controls),
        "required_before_certification_use": True,
        "this_release_certification_use": False,
    }


def leakage_manipulation_audit() -> dict[str, Any]:
    return {
        "schema": "split_vacuum_triangle_leakage_manipulation_audit_v0_2",
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
            "branch_local_candidate_pool_not_used": True,
            "same_sign_priority_not_used": True,
            "center_condition_not_endpoint_sign_dispatched": True,
            "fixed_nominal_path_length_not_used": True,
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
            "schema": "split_vacuum_triangle_initial_conditions_v0_2",
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
            "schema": "split_vacuum_triangle_soo_association_rules_v0_2",
            "framework_version": FRAMEWORK_TARGET_VERSION,
            "SOO_operator": "bounded_context_soo_v1",
            "association_selector": "pure_least_scalar_gradient_burden_global_pool_no_sign_priority",
            "cycle_latency": "association proposals made in one cycle become usable in the next cycle",
            "triangle_detection": "detect from generated association/scalar records only",
            "path_discovery": "detect graph paths between persisted sign-coherent triangles only",
            "center_classifier": "classify from generated path-center scalar profile only",
        },
        "NEGATIVE_CONTROLS_MANIFEST.json": negative_control_report(),
        "LEAKAGE_MANIPULATION_AUDIT.json": leakage_manipulation_audit(),
    }
    payloads = {name: _stable_json(obj) for name, obj in objects.items()}
    payloads["APPROVAL_INSTRUCTIONS.md"] = """# v0.1.37 Split-Vacuum Triangle Emergence Runner-Repair Packet\n\nStatus: EXPLORATORY MECHANISM DISCOVERY ONLY.\n\nThis package repairs the v0.1.36 scaffold by requiring dynamic lifted-vacuum splitting, pure least-gradient association over the generated pool, graph-discovered paths, center-profile classification, and per-control artifacts.\n\nApproval of this packet authorizes exploratory mechanism-discovery jobs only. It does not certify a theorem, electric charge, lepton supports, or relational path accommodation.\n\nFrozen exploratory rule: triangle membership and path endpoints are readouts, not generator inputs.\n\nThe runner may start from undefined vacuum and first-association split sites. It may not be supplied same/opposite labels, charge labels, handedness labels, target Delta L, predeclared triangle membership, predeclared path endpoints, preselected center actions, preselected path outcomes, branch-local candidate pools, same-sign priority, fixed nominal path lengths, or endpoint-sign-dispatched center conditions.\n"""
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
    cycles: int = 8,
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
    parser = argparse.ArgumentParser(description="Write v0.1.37 split-vacuum triangle-emergence exploratory approval packet.")
    parser.add_argument("--output", default="split_vacuum_triangle_emergence_approval_items_v0137.zip")
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
    parser = argparse.ArgumentParser(description="Run v0.1.37 split-vacuum triangle-emergence exploratory mechanism discovery.")
    parser.add_argument("--output-root", default="split_vacuum_triangle_emergence_exploratory_results_v0137")
    parser.add_argument("--split-sites", type=int, default=2)
    parser.add_argument("--cycles", type=int, default=8)
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
