from __future__ import annotations

from dataclasses import replace
import os
import time
import numpy as np

import scalar_field_geometry as sfg
from .active_association import build_A_theta, operator_hash
from .association_indexed_soo import build_association_indexed_soo_update_rule
from .exceptions import ManifestError
from .fingerprints import array_hash, stable_json_hash
from .initialization_settling import (
    analyze_settling_scan,
    build_influenced_witness_points,
    disabled_settling_report,
    parse_settling_spec,
    InitializationSettlingReport,
)
from .initialization_sources import build_initialization_source_array
from .initialization_trace import InitializationEpochReport, InitializationResult
from .two_ledger_initialization import InitialTwoLedgerReport, build_support_seeded_two_ledger_pair
from .overlay_schema import InitializationSpec, SupportSpec
from .soo_compiler import build_declarative_soo_update_rule
from .soo_schema import SOORecipe


def recipe_uses_support_initialization_source(recipe: SOORecipe) -> bool:
    return any(term.operator_id == "support_initialization_source" for term in recipe.residual_terms)


def strip_support_initialization_terms(recipe: SOORecipe) -> SOORecipe:
    """Remove initialization-only source terms from the measurement recipe."""

    residual_terms = tuple(
        term for term in recipe.residual_terms if term.operator_id != "support_initialization_source"
    )
    if not residual_terms:
        raise ManifestError(
            "SOO measurement recipe would be empty after removing support_initialization_source. "
            "Add at least one measurement residual term."
        )
    return replace(recipe, residual_terms=residual_terms)


def _build_settled_two_ledger_report(
    *,
    initial_state: sfg.FrozenAssociationState,
    phi_previous: np.ndarray,
    phi_current: np.ndarray,
    source_trace,
    settling_report: InitializationSettlingReport,
    theta_current: int = 0,
) -> InitialTwoLedgerReport:
    theta = int(theta_current) % 3
    A_theta = build_A_theta(initial_state, theta)
    pi_A = np.asarray(phi_current, dtype=np.float64) - A_theta @ np.asarray(phi_previous, dtype=np.float64)
    return InitialTwoLedgerReport(
        report_schema="rank3_initial_two_ledger_report_v1",
        initializer_id="support_seeded_two_ledger_after_soo_settling_v0_1",
        phi_previous_hash=array_hash(phi_previous),
        phi_current_hash=array_hash(phi_current),
        theta_current=theta,
        A_theta_current_hash=operator_hash(A_theta),
        pi_A_current_hash=array_hash(pi_A),
        source_trace_hash=source_trace.fingerprint(),
        support_seeded=True,
        path_seeded=False,
        passed=bool(settling_report.steady_state_reached),
        details={
            "measurement_two_ledger_selected_after_soo_initialization_settling": True,
            "settling_report_hash": settling_report.fingerprint(),
            "forbidden_interpretations": [
                "two-ledger settling does not seed path-carrier scalar values",
                "witness points do not alter SOO update rules",
            ],
        },
    )



def _initialization_progress_enabled() -> bool:
    return os.environ.get("RANK3_INIT_PROGRESS", "").strip().lower() in {"1", "true", "yes", "on"}


def _initialization_progress(message: str) -> None:
    if _initialization_progress_enabled():
        print(message, flush=True)


def _latest_cycle_summary(per_cycle: tuple[dict[str, object], ...], cycle: int) -> dict[str, float | int | None]:
    """Compact progress summary for one completed rank-3 cycle."""
    rows = [r for r in per_cycle if int(r.get("cycle", -1)) == int(cycle)]
    best_phi_max = None
    best_pi_max = None
    best_sign = None
    passed = 0
    for row in rows:
        if row.get("cycle_passed"):
            passed += 1
        for phase in row.get("phase_records", []):
            phi = phase.get("phi", {})
            pi = phase.get("pi_A", {})
            vals = [
                ("phi", float(phi.get("max_abs_delta", 0.0))),
                ("pi", float(pi.get("max_abs_delta", 0.0))),
            ]
            for label, val in vals:
                if label == "phi":
                    best_phi_max = val if best_phi_max is None else min(best_phi_max, val)
                else:
                    best_pi_max = val if best_pi_max is None else min(best_pi_max, val)
            sign_val = max(float(phi.get("sign_change_fraction", 0.0)), float(pi.get("sign_change_fraction", 0.0)))
            best_sign = sign_val if best_sign is None else min(best_sign, sign_val)
    return {
        "cycle": int(cycle),
        "periods_passing": int(passed),
        "best_phi_max_abs_delta": best_phi_max,
        "best_pi_A_max_abs_delta": best_pi_max,
        "best_sign_change_fraction": best_sign,
    }

def _run_association_indexed_settling(
    *,
    initialization: InitializationSpec,
    initial_state: sfg.FrozenAssociationState,
    phi_previous_seed: np.ndarray,
    phi_current_seed: np.ndarray,
    supports: tuple[SupportSpec, ...],
    graph_mode: str,
    path_scope: str,
    phase_rule,
    pair_weight_rule,
    triplet_lift_rule,
    scalar_update_params: dict[str, object],
    source_trace,
    path_construction_report: object | None = None,
) -> tuple[np.ndarray, np.ndarray, InitializationSettlingReport, tuple[object, ...]]:
    spec = parse_settling_spec(getattr(initialization, "settling", {}))
    witness_points, excluded_support_points, witness_rule = build_influenced_witness_points(
        initial_state=initial_state,
        supports=supports,
        path_report=path_construction_report,
        spec=spec,
    )
    if not spec.enabled:
        return (
            np.asarray(phi_previous_seed, dtype=np.float64).copy(),
            np.asarray(phi_current_seed, dtype=np.float64).copy(),
            disabled_settling_report(
                spec=spec,
                phi_current=phi_current_seed,
                phi_previous=phi_previous_seed,
                witness_points=witness_points,
                excluded_support_points=excluded_support_points,
                witness_rule=witness_rule,
            ),
            (),
        )

    if spec.max_cycles < 1:
        raise ManifestError("initialization.settling.max_cycles must be positive when settling is enabled.")
    if spec.max_cycles < spec.min_cycles:
        raise ManifestError("initialization.settling.max_cycles must be >= min_cycles.")
    if not witness_points:
        raise ManifestError("Initialization settling witness set is empty.")

    diagnostic_points = tuple((int(p), f"settling_witness_{i}") for i, p in enumerate(witness_points[:32]))
    init_rule = build_association_indexed_soo_update_rule(
        scalar_update_params,
        n_points=initial_state.n_points,
        diagnostic_points=diagnostic_points,
    )
    init_rule.reset_trace()
    scan_layers_requested = int(spec.max_cycles) * 3 + 1
    max_steps = int(spec.max_cycles) * 3

    # Run initialization SOO incrementally so the scan can stop as soon as a
    # fixed/recurrent witness condition is accepted. This is intentionally a
    # manual equivalent of scalar_field_geometry.run_scalar_field_geometry; SOO
    # is still whole-field and the witness set is never passed to the update rule.
    phi_layers: list[np.ndarray] = [np.asarray(phi_current_seed, dtype=np.float64).copy()]
    init_states: list[sfg.FrozenAssociationState] = [initial_state]
    accepted_layer: int | None = None
    accepted_period: int | None = None
    steady_type = "not_reached"
    stable_run = 0
    per_cycle: tuple[dict[str, object], ...] = ()
    t0 = time.perf_counter()
    progress_interval = max(1, int(spec.progress_interval_cycles))
    _initialization_progress(
        f"[init-settling] start max_cycles={spec.max_cycles} min_cycles={spec.min_cycles} "
        f"periods={spec.recurrence_period_min}-{spec.recurrence_period_max} witness_points={len(witness_points)}"
    )

    for ell in range(max_steps):
        current_state = init_states[-1]
        geometry = sfg.build_geometry_snapshot(
            state=current_state,
            ell=ell,
            phase_rule=phase_rule,
            graph_mode=graph_mode,  # type: ignore[arg-type]
            path_scope=path_scope,  # type: ignore[arg-type]
            pair_weight_rule=pair_weight_rule,
            triplet_lift_rule=triplet_lift_rule,
        )
        phi_previous_for_step = (
            np.asarray(phi_previous_seed, dtype=np.float64).copy()
            if ell == 0
            else phi_layers[ell - 1].copy()
        )
        update_context = sfg.ScalarUpdateContext(
            ell=ell,
            phase=geometry.phase,
            phi_current=phi_layers[ell].copy(),
            phi_previous=phi_previous_for_step,
            geometry=geometry,
        )
        next_phi = np.asarray(init_rule(update_context), dtype=np.float64)
        phi_layers.append(next_phi.copy())
        remap_context = sfg.RemapContext(
            ell=ell,
            phase=geometry.phase,
            state_current=current_state,
            phi_current=phi_layers[ell].copy(),
            phi_next=next_phi.copy(),
            geometry=geometry,
        )
        next_state = sfg.apply_association_remap(
            context=remap_context,
            remap_rule=sfg.IdentityRemapRule(),
            allow_self_association=initial_state.allow_self_association,
        )
        init_states.append(next_state)

        if (ell + 1) % 3 == 0:
            completed_cycle = (ell + 1) // 3
            phi_scan = np.asarray(phi_layers, dtype=np.float64)
            accepted_layer, accepted_period, steady_type, stable_run, per_cycle = analyze_settling_scan(
                phi=phi_scan,
                states=init_states,
                witness_points=witness_points,
                spec=spec,
            )
            if completed_cycle == 1 or completed_cycle % progress_interval == 0 or accepted_layer is not None or completed_cycle == int(spec.max_cycles):
                summary = _latest_cycle_summary(per_cycle, completed_cycle)
                _initialization_progress(
                    "[init-settling] "
                    f"cycle={completed_cycle}/{spec.max_cycles} "
                    f"accepted={accepted_layer is not None} "
                    f"period={accepted_period} type={steady_type} "
                    f"best_phi_max={summary['best_phi_max_abs_delta']} "
                    f"best_pi_A_max={summary['best_pi_A_max_abs_delta']} "
                    f"best_sign={summary['best_sign_change_fraction']} "
                    f"elapsed={time.perf_counter()-t0:.2f}s"
                )
            if accepted_layer is not None:
                break

    reached = accepted_layer is not None
    scan_layers_actual = len(phi_layers)
    scan_cycles_actual = (scan_layers_actual - 1) // 3
    if reached:
        assert accepted_layer is not None
        phi_current = np.asarray(phi_layers[accepted_layer], dtype=np.float64).copy()
        phi_previous = np.asarray(phi_layers[accepted_layer - 1], dtype=np.float64).copy()
        accepted_steps = int(accepted_layer)
        accepted_cycles = int(accepted_layer // 3)
    else:
        phi_current = np.asarray(phi_layers[-1], dtype=np.float64).copy()
        phi_previous = np.asarray(phi_layers[-2], dtype=np.float64).copy()
        accepted_steps = 0
        accepted_cycles = 0

    report = InitializationSettlingReport(
        report_schema="rank3_initialization_settling_report_v1",
        status="passed" if reached else "failed_not_settled",
        enabled=True,
        witness_scope=spec.witness_scope,
        witness_rule=witness_rule,
        witness_neighborhood_depth=int(spec.witness_neighborhood_depth),
        witness_points=tuple(int(x) for x in witness_points),
        excluded_support_points=tuple(int(x) for x in excluded_support_points),
        initialization_scan_steps=int(scan_layers_actual - 1),
        initialization_scan_rank3_cycles=int(scan_cycles_actual),
        accepted_initialization_steps=accepted_steps,
        accepted_initialization_rank3_cycles=accepted_cycles,
        measurement_starts_after_initialization=True,
        steady_state_reached=bool(reached),
        steady_state_type=steady_type,
        accepted_recurrence_period_cycles=(None if accepted_period is None else int(accepted_period)),
        consecutive_stable_cycles=int(stable_run),
        tolerance_profile={
            "min_cycles": spec.min_cycles,
            "max_cycles": spec.max_cycles,
            "consecutive_stable_cycles_required": spec.consecutive_stable_cycles_required,
            "recurrence_period_min": spec.recurrence_period_min,
            "recurrence_period_max": spec.recurrence_period_max,
            "tol_rms": spec.tol_rms,
            "tol_q95": spec.tol_q95,
            "tol_max": spec.tol_max,
            "tol_sign": spec.tol_sign,
            "zero_epsilon": spec.zero_epsilon,
        },
        per_cycle_witness_statistics=per_cycle,
        phi_after_settling_hash=(array_hash(phi_current) if reached else None),
        phi_previous_for_measurement_hash=(array_hash(phi_previous) if reached else None),
        measurement_initial_state_hash=(
            stable_json_hash({
                "phi_current_hash": array_hash(phi_current),
                "phi_previous_hash": array_hash(phi_previous),
                "accepted_layer": accepted_layer,
            })
            if reached
            else None
        ),
        forbidden_interpretations=(
            "settling witness set does not alter SOO",
            "relational path witness does not make path points scalar-special",
            "steady state is judged only for support-influenced exterior witness records",
            "support-owned oscillation need not be globally quiet",
        ),
        details={
            "source_trace_hash": source_trace.fingerprint(),
            "initial_phi_previous_seed_hash": array_hash(phi_previous_seed),
            "initial_phi_current_seed_hash": array_hash(phi_current_seed),
            "initialization_soo_operator": "association_indexed_soo_v1",
            "initialization_scan_layers_requested": scan_layers_requested,
            "initialization_scan_layers_actual": scan_layers_actual,
            "initialization_stopped_early_on_steady": bool(reached),
            "initialization_progress_enabled": _initialization_progress_enabled(),
            "whole_field_soo_during_initialization": True,
            "measurement_started_after_accepted_settling_layer": bool(reached),
            "witness_points_are_for_convergence_reporting_only": True,
        },
    )
    if spec.fail_if_not_steady and not report.steady_state_reached:
        # Do not raise here. Return a failing report so the mandatory gate can
        # block measurement with evidence of why it failed.
        pass
    return phi_previous, phi_current, report, tuple(init_rule.get_traces())


def run_initialization_epoch(
    *,
    initialization: InitializationSpec,
    initial_state: sfg.FrozenAssociationState,
    initial_phi: sfg.FloatArray,
    supports: tuple[SupportSpec, ...],
    graph_mode: str,
    path_scope: str,
    phase_rule,
    pair_weight_rule,
    triplet_lift_rule,
    soo_recipe: SOORecipe | None,
    path_construction_report: object | None = None,
    scalar_update_rule_name: str | None = None,
    scalar_update_params: dict[str, object] | None = None,
) -> InitializationResult:
    """Execute the locked initialization epoch and return measurement phi_0.

    For association-indexed charge/path runs, this includes an optional SOO
    settling scan over support-influenced exterior witness records. The witness
    set never changes SOO execution; SOO still acts whole-field.
    """

    phi = np.asarray(initial_phi, dtype=np.float64).copy()
    if phi.shape != (initial_state.n_points,):
        raise ManifestError(
            f"initial_phi shape {phi.shape} does not match n_points={initial_state.n_points}."
        )

    source_array, source_trace = build_initialization_source_array(
        initialization=initialization,
        supports=supports,
        n_points=initial_state.n_points,
    )

    if not source_trace.passed:
        raise ManifestError(f"Initialization source validation failed: {source_trace.details}")

    phi_previous_for_measurement = None
    initial_two_ledger_report = None
    settling_report: InitializationSettlingReport | None = None

    if initialization.mode == "support_seeded_two_ledger":
        phi_previous_for_measurement, phi, seed_two_ledger_report = build_support_seeded_two_ledger_pair(
            initial_state=initial_state,
            declared_initial_phi=phi,
            source_array=source_array,
            source_trace=source_trace,
            theta_current=0,
            path_report=path_construction_report,
        )
        if scalar_update_rule_name == "association_indexed_soo_v1":
            phi_previous_for_measurement, phi, settling_report, init_traces_assoc = _run_association_indexed_settling(
                initialization=initialization,
                initial_state=initial_state,
                phi_previous_seed=np.asarray(phi_previous_for_measurement, dtype=np.float64),
                phi_current_seed=np.asarray(phi, dtype=np.float64),
                supports=supports,
                graph_mode=graph_mode,
                path_scope=path_scope,
                phase_rule=phase_rule,
                pair_weight_rule=pair_weight_rule,
                triplet_lift_rule=triplet_lift_rule,
                scalar_update_params=dict(scalar_update_params or {}),
                source_trace=source_trace,
                path_construction_report=path_construction_report,
            )
            initial_two_ledger_report = (
                _build_settled_two_ledger_report(
                    initial_state=initial_state,
                    phi_previous=np.asarray(phi_previous_for_measurement, dtype=np.float64),
                    phi_current=np.asarray(phi, dtype=np.float64),
                    source_trace=source_trace,
                    settling_report=settling_report,
                    theta_current=0,
                )
                if settling_report.enabled
                else seed_two_ledger_report
            )
            init_traces = init_traces_assoc
        else:
            if initialization.initialization_cycles != 0:
                raise ManifestError("support_seeded_two_ledger initialization cycles require association_indexed_soo_v1 settling.")
            settling_spec = parse_settling_spec(getattr(initialization, "settling", {}))
            settling_report = disabled_settling_report(
                spec=settling_spec,
                phi_current=phi,
                phi_previous=phi_previous_for_measurement,
            )
            initial_two_ledger_report = seed_two_ledger_report
            init_traces = ()
    elif initialization.mode == "support_seeded":
        if soo_recipe is None:
            raise ManifestError("support_seeded initialization requires soo_declarative_v0_1 recipe.")
        # The sealed support source provides the non-vacuum starting record.
        phi = phi + source_array
        init_traces = ()
    elif initialization.mode == "vacuum_zero":
        init_traces = ()
    elif initialization.mode == "explicit_phi":
        init_traces = ()
    else:
        raise ManifestError(f"Unsupported initialization.mode: {initialization.mode}")

    states = [initial_state]

    # Legacy residual initialization path retained for old overlays only.
    if initialization.initialization_cycles > 0 and initialization.mode != "support_seeded_two_ledger":
        if soo_recipe is None:
            raise ManifestError("initialization_cycles > 0 requires soo_declarative_v0_1 recipe.")
        init_rule = build_declarative_soo_update_rule(
            soo_recipe,
            boundary_source_array=source_array if recipe_uses_support_initialization_source(soo_recipe) else None,
            boundary_source_hash=source_trace.source_hash if recipe_uses_support_initialization_source(soo_recipe) else None,
            epoch_label="initialization",
            supports=supports,
            path_construction_report=path_construction_report,
        )
        init_config = sfg.ScalarFieldGeometryConfig(
            initial_state=initial_state,
            initial_phi=phi,
            n_layers=initialization.initialization_cycles + 1,
            graph_mode=graph_mode,  # type: ignore[arg-type]
            path_scope=path_scope,  # type: ignore[arg-type]
            phase_rule=phase_rule,
            pair_weight_rule=pair_weight_rule,
            triplet_lift_rule=triplet_lift_rule,
            scalar_update_rule=init_rule,
            association_remap_rule=sfg.IdentityRemapRule(),
            allow_self_association=initial_state.allow_self_association,
        )
        init_rule.reset_trace()
        init_result = sfg.run_scalar_field_geometry(init_config)
        phi = np.asarray(init_result.phi[-1], dtype=np.float64).copy()
        states = init_result.states
        init_traces = init_rule.get_traces()

    soo_trace_hashes = tuple(trace.fingerprint() for trace in init_traces)
    report_passed = bool(source_trace.passed)
    if initialization.mode in ("support_seeded", "support_seeded_two_ledger") and initialization.require_nonzero_support_activation:
        report_passed = report_passed and source_trace.support_nonzero_count > 0
    if initialization.initialization_cycles > 0 and initialization.mode != "support_seeded_two_ledger":
        report_passed = report_passed and len(init_traces) == initialization.initialization_cycles
        report_passed = report_passed and all(trace.invariants.passed for trace in init_traces)
    if settling_report is not None and settling_report.enabled:
        report_passed = report_passed and settling_report.steady_state_reached

    report = InitializationEpochReport(
        mode=initialization.mode,
        initialization_cycles=int(initialization.initialization_cycles),
        measurement_starts_after_initialization=bool(initialization.measurement_starts_after_initialization),
        initial_phi_hash=array_hash(initial_phi),
        source_trace=source_trace,
        phi_after_initialization_hash=array_hash(phi),
        phi_previous_for_measurement_hash=(array_hash(phi_previous_for_measurement) if phi_previous_for_measurement is not None else None),
        initial_two_ledger_hash=(initial_two_ledger_report.fingerprint() if initial_two_ledger_report is not None else None),
        settling_report_hash=(settling_report.fingerprint() if settling_report is not None else None),
        soo_trace_hashes=soo_trace_hashes,
        passed=report_passed,
        details={
            "state_lineage_hash": stable_json_hash([state.fingerprint for state in states]),
            "source_added_to_initial_phi": initialization.mode in ("support_seeded", "support_seeded_two_ledger"),
            "two_ledger_initialization": initialization.mode == "support_seeded_two_ledger",
            "measurement_readouts_start_after_initialization": initialization.measurement_starts_after_initialization,
            "trace_epochs": [getattr(trace, "epoch", "association_indexed_initialization") for trace in init_traces],
            "initialization_settling_enabled": bool(settling_report.enabled) if settling_report is not None else False,
            "initialization_settling_report_hash": settling_report.fingerprint() if settling_report is not None else None,
            "initialization_cycles_field_semantics": "legacy declared residual steps; association-indexed settling cycles are reported in INITIALIZATION_SETTLING_REPORT.json",
        },
    )

    if initialization.mode in ("support_seeded", "support_seeded_two_ledger") and not initialization.measurement_starts_after_initialization:
        raise ManifestError(f"{initialization.mode} initialization requires measurement_starts_after_initialization=true.")

    return InitializationResult(
        phi_after_initialization=phi,
        report=report,
        soo_traces=init_traces,
        phi_previous_for_measurement=phi_previous_for_measurement,
        initial_two_ledger_report=initial_two_ledger_report,
        settling_report=settling_report,
    )
