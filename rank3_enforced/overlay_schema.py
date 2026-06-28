from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .exceptions import ManifestError

OverlayRunKind = Literal["control", "candidate", "admission"]


@dataclass(frozen=True)
class InitialGeometrySpec:
    n_points: int
    generation_rule: str = "random_distinct_no_self"
    seed: int | None = None
    seed_set: tuple[int, ...] = ()
    allow_self_association: bool = False


@dataclass(frozen=True)
class PathConstructionSpec:
    """Declarative locked explicit path construction request.

    rule="none" preserves existing initial association generation.
    rule="linear_support_path_v0_1" builds a locked support-to-support
    rank-3 association path before initialization. path_length counts the
    declared path positions in path_points; graph-edge distance between support
    anchors is reported separately.
    """

    rule: Literal["none", "linear_support_path_v0_1", "linear_support_path_v0_2"] = "none"
    path_length: int = 0
    path_points: tuple[int, ...] = ()
    orientation: Literal["unspecified", "same", "opposite"] = "unspecified"
    left_support: str | None = None
    right_support: str | None = None
    path_slot: int = 0
    reverse_slot: int = 1
    allow_support_overlap: bool = False


@dataclass(frozen=True)
class InitialPhiSpec:
    kind: Literal["zeros", "explicit"] = "zeros"
    values: tuple[float, ...] = ()




@dataclass(frozen=True)
class InitializationSpec:
    """Declarative initialization epoch before measurement readouts begin.

    support_seeded initialization is the enforced way to let SOO start from
    support-owned boundary/dressing records instead of anonymous all-zero vacuum.
    """

    mode: Literal["vacuum_zero", "explicit_phi", "support_seeded", "support_seeded_two_ledger"] = "vacuum_zero"
    start_sites: Literal[
        "none",
        "boundary_points",
        "dressing_points",
        "boundary_and_dressing_points",
    ] = "none"
    source_rule: str | None = None
    initialization_cycles: int = 0
    amplitude: float = 1.0
    require_nonzero_support_activation: bool = False
    require_vacuum_zero_elsewhere: bool = True
    measurement_starts_after_initialization: bool = True
    settling: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionSpec:
    n_layers: int
    graph_mode: Literal["directed", "undirected"] = "undirected"
    path_scope: Literal["completed", "active_phase"] = "completed"
    phase_rule: str = "cyclic_phase"
    pair_weight_rule: str = "inverse_path_length"
    triplet_lift_rule: str = "product_triplet_lift"


@dataclass(frozen=True)
class RuleSelectionSpec:
    scalar_update_rule: str
    association_remap_rule: str
    scalar_update_params: dict[str, Any] = field(default_factory=dict)
    association_remap_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SupportSpec:
    name: str
    support_points: tuple[int, ...]
    boundary_points: tuple[int, ...] = ()
    dressing_points: tuple[int, ...] = ()
    handedness: str | None = None
    active_phase_map: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ConstraintSpec:
    non_overlap_required: bool = False
    require_three_phase_coherence: bool = False
    forbid_projected_graph_evidence: bool = True




@dataclass(frozen=True)
class OptionalModuleSpec:
    module_id: str
    status: str = "experimental"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeclarativeOverlay:
    """
    Data-only overlay accepted by enforced candidate/admission execution.

    This object carries no executable model logic. The compiler maps names to
    locked registry entries and expands model_type into mandatory diagnostics.
    """

    schema_version: str
    model_type: str
    model_name: str
    model_version: str
    purpose: str
    run_kind: OverlayRunKind
    external_admission_verdict: str
    initial_geometry: InitialGeometrySpec
    path_construction: PathConstructionSpec
    initial_phi: InitialPhiSpec
    initialization: InitializationSpec
    execution: ExecutionSpec
    rules: RuleSelectionSpec
    supports: tuple[SupportSpec, ...] = ()
    constraints: ConstraintSpec = field(default_factory=ConstraintSpec)
    optional_modules: tuple[OptionalModuleSpec, ...] = ()
    requested_readouts: tuple[str, ...] = ()
    requested_controls: tuple[str, ...] = ()
    requested_certification: bool = False
    expected_core_hash: str | None = None
    notes: str = ""


FORBIDDEN_OVERLAY_KEYS = {
    "python",
    "callable",
    "function",
    "lambda",
    "source",
    "source_code",
    "code",
    "exec",
    "eval",
    "module",
    "import",
    "class",
}


def _reject_executable_keys(value: Any, *, path: str = "overlay") -> None:
    if isinstance(value, dict):
        for key, subvalue in value.items():
            lower = str(key).lower()
            if lower in FORBIDDEN_OVERLAY_KEYS or lower.endswith("_code") or lower.endswith("_source"):
                raise ManifestError(
                    f"Executable overlay key rejected at {path}.{key!s}. "
                    "Enforced overlays are data-only."
                )
            _reject_executable_keys(subvalue, path=f"{path}.{key!s}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_executable_keys(item, path=f"{path}[{index}]")


def _tuple_ints(value: Any, *, field_name: str) -> tuple[int, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ManifestError(f"{field_name} must be a list of integers.")
    return tuple(int(x) for x in value)


def _tuple_floats(value: Any, *, field_name: str) -> tuple[float, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ManifestError(f"{field_name} must be a list of numbers.")
    return tuple(float(x) for x in value)


def parse_declarative_overlay(payload: dict[str, Any]) -> DeclarativeOverlay:
    """Parse and validate a JSON-compatible overlay dictionary."""

    _reject_executable_keys(payload)

    try:
        geometry = payload["initial_geometry"]
        path_construction_raw = payload.get("path_construction", {"rule": "none"})
        phi = payload.get("initial_phi", {"kind": "zeros"})
        initialization_raw = payload.get("initialization", {})
        execution = payload["execution"]
        rules = payload["rules"]
    except KeyError as exc:
        raise ManifestError(f"Missing required overlay section: {exc.args[0]}") from exc

    seed_set = _tuple_ints(geometry.get("seed_set", []), field_name="initial_geometry.seed_set")
    seed = geometry.get("seed")
    if seed is None and not seed_set:
        raise ManifestError("initial_geometry requires either seed or seed_set.")
    if seed is not None and seed_set:
        raise ManifestError("Use either initial_geometry.seed or seed_set, not both.")

    supports: list[SupportSpec] = []
    for raw_support in payload.get("supports", []):
        active_phase_map = {
            int(k): int(v)
            for k, v in dict(raw_support.get("active_phase_map", {})).items()
        }
        supports.append(
            SupportSpec(
                name=str(raw_support["name"]),
                support_points=_tuple_ints(raw_support.get("support_points", []), field_name="support_points"),
                boundary_points=_tuple_ints(raw_support.get("boundary_points", []), field_name="boundary_points"),
                dressing_points=_tuple_ints(raw_support.get("dressing_points", []), field_name="dressing_points"),
                handedness=raw_support.get("handedness"),
                active_phase_map=active_phase_map,
            )
        )

    constraints_raw = payload.get("constraints", {})

    optional_modules: list[OptionalModuleSpec] = []
    for raw_module in payload.get("optional_modules", payload.get("modules", [])):
        if not isinstance(raw_module, dict):
            raise ManifestError("optional_modules entries must be objects.")
        optional_modules.append(
            OptionalModuleSpec(
                module_id=str(raw_module["module_id"] if "module_id" in raw_module else raw_module.get("id")),
                status=str(raw_module.get("status", "experimental")),
                params=dict(raw_module.get("params", {})),
            )
        )

    overlay = DeclarativeOverlay(
        schema_version=str(payload.get("schema_version", "1.0")),
        model_type=str(payload["model_type"]),
        model_name=str(payload["model_name"]),
        model_version=str(payload["model_version"]),
        purpose=str(payload["purpose"]),
        run_kind=str(payload["run_kind"]),  # type: ignore[arg-type]
        external_admission_verdict=str(payload["external_admission_verdict"]),
        initial_geometry=InitialGeometrySpec(
            n_points=int(geometry["n_points"]),
            generation_rule=str(geometry.get("generation_rule", "random_distinct_no_self")),
            seed=int(seed) if seed is not None else None,
            seed_set=seed_set,
            allow_self_association=bool(geometry.get("allow_self_association", False)),
        ),
        path_construction=PathConstructionSpec(
            rule=str(path_construction_raw.get("rule", "none")),  # type: ignore[arg-type]
            path_length=int(path_construction_raw.get("path_length", 0)),
            path_points=_tuple_ints(path_construction_raw.get("path_points", []), field_name="path_construction.path_points"),
            orientation=str(path_construction_raw.get("orientation", "unspecified")),  # type: ignore[arg-type]
            left_support=path_construction_raw.get("left_support"),
            right_support=path_construction_raw.get("right_support"),
            path_slot=int(path_construction_raw.get("path_slot", 0)),
            reverse_slot=int(path_construction_raw.get("reverse_slot", 1)),
            allow_support_overlap=bool(path_construction_raw.get("allow_support_overlap", False)),
        ),
        initial_phi=InitialPhiSpec(
            kind=str(phi.get("kind", "zeros")),  # type: ignore[arg-type]
            values=_tuple_floats(phi.get("values", []), field_name="initial_phi.values"),
        ),
        initialization=InitializationSpec(
            mode=str(initialization_raw.get("mode", "vacuum_zero")),  # type: ignore[arg-type]
            start_sites=str(initialization_raw.get("start_sites", "none")),  # type: ignore[arg-type]
            source_rule=initialization_raw.get("source_rule"),
            initialization_cycles=int(initialization_raw.get("initialization_cycles", 0)),
            amplitude=float(initialization_raw.get("amplitude", 1.0)),
            require_nonzero_support_activation=bool(initialization_raw.get("require_nonzero_support_activation", False)),
            require_vacuum_zero_elsewhere=bool(initialization_raw.get("require_vacuum_zero_elsewhere", True)),
            measurement_starts_after_initialization=bool(initialization_raw.get("measurement_starts_after_initialization", True)),
            settling=dict(initialization_raw.get("settling", {})),
        ),
        execution=ExecutionSpec(
            n_layers=int(execution["n_layers"]),
            graph_mode=str(execution.get("graph_mode", "undirected")),  # type: ignore[arg-type]
            path_scope=str(execution.get("path_scope", "completed")),  # type: ignore[arg-type]
            phase_rule=str(execution.get("phase_rule", "cyclic_phase")),
            pair_weight_rule=str(execution.get("pair_weight_rule", "inverse_path_length")),
            triplet_lift_rule=str(execution.get("triplet_lift_rule", "product_triplet_lift")),
        ),
        rules=RuleSelectionSpec(
            scalar_update_rule=str(rules["scalar_update_rule"]),
            association_remap_rule=str(rules["association_remap_rule"]),
            scalar_update_params=dict(rules.get("scalar_update_params", {})),
            association_remap_params=dict(rules.get("association_remap_params", {})),
        ),
        supports=tuple(supports),
        constraints=ConstraintSpec(
            non_overlap_required=bool(constraints_raw.get("non_overlap_required", False)),
            require_three_phase_coherence=bool(constraints_raw.get("require_three_phase_coherence", False)),
            forbid_projected_graph_evidence=bool(constraints_raw.get("forbid_projected_graph_evidence", True)),
        ),
        optional_modules=tuple(optional_modules),
        requested_readouts=tuple(str(x) for x in payload.get("readouts", [])),
        requested_controls=tuple(str(x) for x in payload.get("controls", [])),
        requested_certification=bool(payload.get("requested_certification", False)),
        expected_core_hash=payload.get("expected_core_hash"),
        notes=str(payload.get("notes", "")),
    )

    if overlay.schema_version != "1.0":
        raise ManifestError(f"Unsupported overlay schema_version: {overlay.schema_version}")
    if overlay.run_kind not in ("control", "candidate", "admission"):
        raise ManifestError(f"Invalid run_kind: {overlay.run_kind}")
    if overlay.initial_geometry.n_points < 4:
        raise ManifestError("initial_geometry.n_points must be at least 4.")
    if overlay.execution.n_layers < 1:
        raise ManifestError("execution.n_layers must be at least 1.")
    if overlay.initial_phi.kind == "explicit" and len(overlay.initial_phi.values) != overlay.initial_geometry.n_points:
        raise ManifestError("explicit initial_phi.values length must equal n_points.")
    if overlay.initial_phi.kind not in ("zeros", "explicit"):
        raise ManifestError(f"Unsupported initial_phi.kind: {overlay.initial_phi.kind}")
    if overlay.initialization.mode not in ("vacuum_zero", "explicit_phi", "support_seeded", "support_seeded_two_ledger"):
        raise ManifestError(f"Unsupported initialization.mode: {overlay.initialization.mode}")
    if overlay.initialization.start_sites not in (
        "none",
        "boundary_points",
        "dressing_points",
        "boundary_and_dressing_points",
    ):
        raise ManifestError(f"Unsupported initialization.start_sites: {overlay.initialization.start_sites}")
    if overlay.initialization.initialization_cycles < 0:
        raise ManifestError("initialization.initialization_cycles must be non-negative.")
    if overlay.initialization.mode in ("support_seeded", "support_seeded_two_ledger") and not overlay.supports:
        raise ManifestError(f"{overlay.initialization.mode} initialization requires supports.")

    if overlay.path_construction.rule not in ("none", "linear_support_path_v0_1", "linear_support_path_v0_2", "role_path_two_support_v0_1"):
        raise ManifestError(f"Unsupported path_construction.rule: {overlay.path_construction.rule}")
    if overlay.path_construction.rule == "none" and overlay.path_construction.path_length:
        raise ManifestError("path_construction.path_length requires a non-none path_construction.rule.")
    if overlay.path_construction.rule in ("linear_support_path_v0_1", "linear_support_path_v0_2", "role_path_two_support_v0_1"):
        if overlay.path_construction.path_length < 1:
            raise ManifestError("linear_support_path_v0_1 requires path_length >= 1.")
        if overlay.path_construction.orientation not in ("same", "opposite", "unspecified"):
            raise ManifestError(f"Unsupported path_construction.orientation: {overlay.path_construction.orientation}")
        if overlay.path_construction.path_slot % 3 == overlay.path_construction.reverse_slot % 3:
            raise ManifestError("path_construction.path_slot and reverse_slot must be distinct modulo 3.")

    return overlay
