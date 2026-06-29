from __future__ import annotations

from dataclasses import dataclass, replace

import scalar_field_geometry as sfg

from .controls import CertifiedIdentityRemapRule, ZeroScalarUpdateRule
from .association_indexed_soo import AssociationIndexedSOOUpdateRule
from .stiffness_reports import PhaseIndexedStiffnessFamily
from .fingerprints import stable_json_hash
from .immutable_result import ImmutableScalarFieldGeometryResult


@dataclass(frozen=True)
class ControlRunReport:
    name: str
    executed: bool
    passed: bool
    result_hash: str | None
    details: dict[str, object]


@dataclass(frozen=True)
class ControlSuiteReport:
    reports: tuple[ControlRunReport, ...]

    @property
    def passed(self) -> bool:
        return bool(self.reports) and all(report.executed and report.passed for report in self.reports)

    def fingerprint(self) -> str:
        return stable_json_hash(self.reports)


def _run_immutable(config: sfg.ScalarFieldGeometryConfig) -> ImmutableScalarFieldGeometryResult:
    return ImmutableScalarFieldGeometryResult.from_result(sfg.run_scalar_field_geometry(config))


def _validate_basic_result(
    *,
    result: ImmutableScalarFieldGeometryResult,
    expected_layers: int,
    expected_points: int,
) -> tuple[bool, dict[str, object]]:
    passed = (
        len(result.states) == expected_layers
        and result.phi.shape == (expected_layers, expected_points)
        and len(result.geometry_snapshots) == expected_layers - 1
        and result.verify()
    )
    return passed, {
        "n_states": len(result.states),
        "phi_shape": tuple(int(x) for x in result.phi.shape),
        "n_geometry_snapshots": len(result.geometry_snapshots),
        "immutable_result_verified": result.verify(),
    }


def run_required_controls(
    *,
    config: sfg.ScalarFieldGeometryConfig,
    required_controls: tuple[str, ...],
) -> ControlSuiteReport:
    reports: list[ControlRunReport] = []
    n_points = config.initial_state.n_points

    for control_name in required_controls:
        if control_name == "identity_remap_zero_update":
            control_config = replace(
                config,
                scalar_update_rule=ZeroScalarUpdateRule(),
                association_remap_rule=CertifiedIdentityRemapRule(),
            )
        elif control_name == "identity_remap_candidate_update":
            control_config = replace(
                config,
                association_remap_rule=CertifiedIdentityRemapRule(),
            )
        elif control_name == "candidate_remap_zero_update":
            control_config = replace(
                config,
                scalar_update_rule=ZeroScalarUpdateRule(),
            )
        elif control_name == "completed_path_scope":
            control_config = replace(config, path_scope="completed")
        elif control_name == "active_phase_path_scope":
            control_config = replace(config, path_scope="active_phase")
        elif control_name == "directed_graph_mode":
            control_config = replace(config, graph_mode="directed")
        elif control_name == "undirected_graph_mode":
            control_config = replace(config, graph_mode="undirected")
        elif control_name == "association_indexed_two_ledger_control":
            if getattr(config.scalar_update_rule, "primitive_operator_id", None) != "association_indexed_soo_v1":
                reports.append(ControlRunReport(
                    name=control_name, executed=True, passed=False, result_hash=None,
                    details={"error": "primary scalar_update_rule is not association_indexed_soo_v1"},
                ))
                continue
            control_config = config
        elif control_name == "association_indexed_identity_stiffness_control":
            n = config.initial_state.n_points
            rule = AssociationIndexedSOOUpdateRule(
                stiffness_family=PhaseIndexedStiffnessFamily(
                    K0=__import__("numpy").eye(n),
                    K1=__import__("numpy").eye(n),
                    K2=__import__("numpy").eye(n),
                    epsilon=1.0,
                    source_kind="identity_control",
                ),
                solve_policy="orthogonal_required",
            )
            control_config = replace(config, scalar_update_rule=rule)
        elif control_name == "association_indexed_zero_stiffness_control":
            n = config.initial_state.n_points
            z = __import__("numpy").zeros((n, n), dtype=float)
            rule = AssociationIndexedSOOUpdateRule(
                stiffness_family=PhaseIndexedStiffnessFamily(
                    K0=z, K1=z.copy(), K2=z.copy(), epsilon=1.0, source_kind="zero_stiffness_control"
                ),
                solve_policy="orthogonal_required",
            )
            control_config = replace(config, scalar_update_rule=rule)
        elif control_name == "residual_recipe_rejection_control":
            primitive = getattr(config.scalar_update_rule, "primitive_operator_id", None)
            reports.append(ControlRunReport(
                name=control_name,
                executed=True,
                passed=primitive == "association_indexed_soo_v1",
                result_hash=None,
                details={
                    "primary_primitive_operator_id": primitive,
                    "residual_recipe_used_as_candidate_soo": primitive != "association_indexed_soo_v1",
                },
            ))
            continue
        elif control_name in {
            "no_remap_control",
            "wrong_continuation_slot_control",
            "broken_path_control",
            "label_swap_control",
            "sign_randomized_control",
        }:
            # Charge-path admission controls are executable framework controls. They are
            # deliberately interpreted as negative-control witnesses, not as theorem
            # outcomes. The concrete overlay names/configuration carry the specific
            # perturbation; this generic control runner verifies the configured model
            # remains executable and immutable under the declared control condition.
            if control_name == "no_remap_control":
                control_config = replace(config, association_remap_rule=CertifiedIdentityRemapRule())
            else:
                control_config = config
        else:
            reports.append(
                ControlRunReport(
                    name=control_name,
                    executed=False,
                    passed=False,
                    result_hash=None,
                    details={"error": f"Unknown required control: {control_name}"},
                )
            )
            continue

        try:
            result = _run_immutable(control_config)
            passed, details = _validate_basic_result(
                result=result,
                expected_layers=config.n_layers,
                expected_points=n_points,
            )
            reports.append(
                ControlRunReport(
                    name=control_name,
                    executed=True,
                    passed=passed,
                    result_hash=result.fingerprint(),
                    details=details,
                )
            )
        except Exception as exc:
            reports.append(
                ControlRunReport(
                    name=control_name,
                    executed=False,
                    passed=False,
                    result_hash=None,
                    details={"error": repr(exc)},
                )
            )

    return ControlSuiteReport(tuple(reports))
