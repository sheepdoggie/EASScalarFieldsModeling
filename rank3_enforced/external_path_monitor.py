from __future__ import annotations

"""Exploratory external path-monitor API.

This module intentionally does not define EAS ontology rules.  It exposes
framework-owned path records through auditable snapshots and accepts explicit
external edit requests that add/remove already existing scalar points from an
*active* path record.  The framework validates and logs the transaction; it does
not decide that a path length change must occur.

Certified/publication runs should mark any use of this API as external
exploratory intervention unless a later locked admission system explicitly
promotes a monitor policy.  Scalar values are never moved by these operations.
"""

from dataclasses import asdict, dataclass, replace
from typing import Any, Callable, Literal, Mapping

import numpy as np

from .dynamic_paths import GeometryTransactionReport, RelationalPathRecord
from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash

PathEditOperation = Literal["none", "remove_node", "insert_existing_node"]


@dataclass(frozen=True)
class PathMonitorSnapshot:
    """Read-only snapshot supplied to an exploratory external monitor.

    The snapshot is deliberately plain data.  External code may inspect it and
    return an ExternalPathEditRequest, but external code is not imported by the
    framework for certified runs.
    """

    report_schema: str
    path: RelationalPathRecord
    association_hash: str
    scalar_values_hash: str | None
    cycle: int
    phase: int | None
    center_nodes: tuple[int, ...]
    path_length: int
    active_ordered_nodes: tuple[int, ...]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = asdict(self.path)
        return payload

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class ExternalPathEditRequest:
    """Explicit request from an exploratory monitor to edit an active path.

    This request is not an EAS rule and is not a theorem verdict.  It is a
    user/external-monitor proposal that the framework can validate, transact,
    and audit.
    """

    request_schema: str = "rank3_external_path_edit_request_v0_1"
    operation: PathEditOperation = "none"
    path_id: str = ""
    requested_by: str = "external_monitor"
    reason: str = ""
    monitor_fingerprint: str | None = None
    evidence_hash: str | None = None
    target_node: int | None = None
    target_index: int | None = None
    new_node: int | None = None
    insert_after_index: int | None = None
    external_exploratory: bool = True
    ontology_rule: bool = False

    def validate_basic(self, path: RelationalPathRecord) -> None:
        if self.path_id and self.path_id != path.path_id:
            raise ManifestError(f"External path edit targets {self.path_id!r}, not active path {path.path_id!r}.")
        if self.ontology_rule:
            raise ManifestError("External path edit request cannot declare itself an ontology rule.")
        if not self.external_exploratory:
            raise ManifestError("External path edit request must be marked external_exploratory=True.")
        if self.operation not in ("none", "remove_node", "insert_existing_node"):
            raise ManifestError(f"Unknown external path edit operation: {self.operation!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


@dataclass(frozen=True)
class ExternalPathEditResult:
    """Validated result of applying an external path edit request."""

    result_schema: str
    request: ExternalPathEditRequest
    applied: bool
    path_before: RelationalPathRecord
    path_after: RelationalPathRecord
    association_after: np.ndarray
    transaction_report: GeometryTransactionReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_schema": self.result_schema,
            "request": self.request.to_dict(),
            "applied": self.applied,
            "path_before": asdict(self.path_before),
            "path_after": asdict(self.path_after),
            "transaction_report": asdict(self.transaction_report),
        }

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def make_path_monitor_snapshot(
    *,
    assoc: np.ndarray,
    path: RelationalPathRecord,
    phi: np.ndarray | None = None,
    cycle: int = 0,
    phase: int | None = None,
    details: Mapping[str, Any] | None = None,
) -> PathMonitorSnapshot:
    """Create a read-only path snapshot for external exploratory monitoring."""

    assoc_in = np.asarray(assoc, dtype=np.int64)
    scalar_hash = None if phi is None else array_hash(np.asarray(phi, dtype=float))
    return PathMonitorSnapshot(
        report_schema="rank3_path_monitor_snapshot_v0_1",
        path=path,
        association_hash=array_hash(assoc_in),
        scalar_values_hash=scalar_hash,
        cycle=int(cycle),
        phase=None if phase is None else int(phase) % 3,
        center_nodes=path.center_nodes,
        path_length=path.path_length,
        active_ordered_nodes=path.ordered_nodes,
        details=dict(details or {}),
    )


def _neighbors_for_path_edit(path: RelationalPathRecord, index: int) -> tuple[int, int]:
    before = path.left_endpoint if index == 0 else path.ordered_nodes[index - 1]
    after = path.right_endpoint if index == path.path_length - 1 else path.ordered_nodes[index + 1]
    return before, after


def apply_external_path_edit_request(
    *,
    assoc: np.ndarray,
    path: RelationalPathRecord,
    request: ExternalPathEditRequest,
    operation_id: str = "external_path_monitor_edit_v0_1",
) -> ExternalPathEditResult:
    """Validate and apply an external path edit request.

    The framework never infers that a length change should occur here.  It only
    applies a request supplied by external exploratory code and records the
    transaction.  No scalar values are accepted or moved.
    """

    request.validate_basic(path)
    assoc_in = np.asarray(assoc, dtype=np.int64)
    out = assoc_in.copy()
    path_after = path
    affected: tuple[int, ...] = ()
    validation: dict[str, Any] = {
        "request_hash": request.fingerprint(),
        "input_path_hash": path.fingerprint(),
        "external_exploratory": True,
        "ontology_rule": False,
        "scalar_values_moved": False,
        "operation": request.operation,
    }
    details: dict[str, Any] = {"reason": request.reason, "requested_by": request.requested_by}
    applied = False

    if request.operation == "none":
        details["no_edit_reason"] = request.reason or "external monitor requested no path edit"
    elif request.operation == "remove_node":
        if request.target_node is None and request.target_index is None:
            raise ManifestError("remove_node requires target_node or target_index.")
        if request.target_index is not None:
            idx = int(request.target_index)
            if idx < 0 or idx >= path.path_length:
                raise ManifestError("remove_node target_index out of bounds.")
            node = path.ordered_nodes[idx]
        else:
            node = int(request.target_node)  # type: ignore[arg-type]
            if node not in path.ordered_nodes:
                raise ManifestError("remove_node target_node is not in the active path.")
            idx = path.ordered_nodes.index(node)
        before, after = _neighbors_for_path_edit(path, idx)
        for slot in range(3):
            if out[before, slot] == node:
                out[before, slot] = after
            if out[after, slot] == node:
                out[after, slot] = before
        new_nodes = path.ordered_nodes[:idx] + path.ordered_nodes[idx + 1:]
        if len(new_nodes) < 1:
            raise ManifestError("remove_node would leave an empty path record.")
        path_after = replace(path, ordered_nodes=new_nodes)
        affected = (before, node, after)
        details.update({"removed_node": node, "reconnected_predecessor": before, "reconnected_successor": after})
        applied = True
    elif request.operation == "insert_existing_node":
        if request.new_node is None:
            raise ManifestError("insert_existing_node requires new_node.")
        new_node = int(request.new_node)
        if new_node < 0 or new_node >= int(out.shape[0]):
            raise ManifestError("insert_existing_node new_node out of bounds.")
        if new_node in path.ordered_nodes or new_node in (path.left_endpoint, path.right_endpoint):
            raise ManifestError("insert_existing_node new_node is already on the active path.")
        insert_after = int(request.insert_after_index if request.insert_after_index is not None else ((path.path_length - 1) // 2))
        if insert_after < 0 or insert_after >= path.path_length:
            raise ManifestError("insert_existing_node insert_after_index out of bounds.")
        before = path.ordered_nodes[insert_after]
        after = path.right_endpoint if insert_after == path.path_length - 1 else path.ordered_nodes[insert_after + 1]
        for slot in range(3):
            if out[before, slot] == after:
                out[before, slot] = new_node
            if out[after, slot] == before:
                out[after, slot] = new_node
        out[new_node, 0] = before
        out[new_node, 1] = after
        if out[new_node, 2] in (new_node, before, after):
            for candidate in range(int(out.shape[0])):
                if candidate not in (new_node, before, after):
                    out[new_node, 2] = candidate
                    break
        new_nodes = path.ordered_nodes[: insert_after + 1] + (new_node,) + path.ordered_nodes[insert_after + 1:]
        path_after = replace(path, ordered_nodes=new_nodes)
        affected = (before, new_node, after)
        details.update({"inserted_node": new_node, "inserted_between": (before, after)})
        applied = True

    validation.update({
        "output_path_hash": path_after.fingerprint(),
        "path_length_before": path.path_length,
        "path_length_after": path_after.path_length,
        "delta_L": path_after.path_length - path.path_length,
        "external_monitor_request_required": True,
    })
    report = GeometryTransactionReport(
        report_schema="rank3_geometry_transaction_report_v1",
        operation_id=operation_id,
        operation_kind="external_path_monitor_edit",
        applied=applied,
        association_before_hash=array_hash(assoc_in),
        association_after_hash=array_hash(out),
        scalar_values_moved=False,
        affected_points=affected,
        validation=validation,
        details=details,
    )
    return ExternalPathEditResult(
        result_schema="rank3_external_path_edit_result_v0_1",
        request=request,
        applied=applied,
        path_before=path,
        path_after=path_after,
        association_after=out,
        transaction_report=report,
    )


def call_external_path_monitor(
    snapshot: PathMonitorSnapshot,
    monitor: Callable[[PathMonitorSnapshot], ExternalPathEditRequest | Mapping[str, Any] | None],
    *,
    allow_external_code: bool = False,
) -> ExternalPathEditRequest:
    """Call an exploratory monitor only when explicitly allowed.

    This guard prevents accidental use of Python callbacks in framework-certified
    runs.  Exploratory code can opt in with allow_external_code=True.
    """

    if not allow_external_code:
        raise ManifestError(
            "External path monitor callbacks are disabled by default. "
            "Set allow_external_code=True only for exploratory, non-certified runs."
        )
    raw = monitor(snapshot)
    if raw is None:
        return ExternalPathEditRequest(operation="none", path_id=snapshot.path.path_id, reason="monitor returned None")
    if isinstance(raw, ExternalPathEditRequest):
        return raw
    if isinstance(raw, Mapping):
        payload = dict(raw)
        payload.setdefault("path_id", snapshot.path.path_id)
        return ExternalPathEditRequest(**payload)
    raise ManifestError("External monitor must return ExternalPathEditRequest, mapping, or None.")
