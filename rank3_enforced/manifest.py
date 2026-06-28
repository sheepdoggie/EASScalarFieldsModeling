from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .rule_metadata import AdmissionVerdict, RuleStatus

RunKind = Literal["control", "candidate", "admission"]


@dataclass(frozen=True)
class DiagnosticManifest:
    """Pre-run diagnostic registration.

    The enforced runner rejects certified runs when required readouts or controls
    are missing. This prevents post-hoc diagnostic selection.
    """

    required_readouts: tuple[str, ...] = (
        "result_shape",
        "state_verification",
        "phi_history_hash",
        "geometry_snapshot_count",
    )
    required_controls: tuple[str, ...] = (
        "identity_remap_zero_update",
        "identity_remap_candidate_update",
        "candidate_remap_zero_update",
    )
    required_path_scopes: tuple[str, ...] = ()
    required_graph_modes: tuple[str, ...] = ()
    required_phases: tuple[int, ...] = (0, 1, 2)
    seed_set: tuple[int, ...] = ()
    tensor_slices: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class ModelManifest:
    model_name: str
    model_version: str
    purpose: str
    run_kind: RunKind
    external_admission_verdict: AdmissionVerdict
    diagnostics: DiagnosticManifest = field(default_factory=DiagnosticManifest)
    requested_certification: bool = False
    expected_core_hash: str | None = None
    forbidden_interpretations: tuple[str, ...] = (
        "visualization_as_physical_space",
        "control_rule_as_admitted_dynamics",
        "candidate_rule_as_admitted_dynamics",
        "post_hoc_diagnostic_selection",
    )
    notes: str = ""

    def required_rule_statuses(self) -> tuple[RuleStatus, ...]:
        if self.run_kind == "admission":
            return (RuleStatus.ADMITTED,)
        if self.run_kind == "candidate":
            return (RuleStatus.CANDIDATE, RuleStatus.ADMITTED)
        if self.run_kind == "control":
            return (RuleStatus.CONTROL, RuleStatus.DEMONSTRATION)
        raise ValueError(f"Unknown run_kind: {self.run_kind}")
