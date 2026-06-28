from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .fingerprints import stable_json_hash
from .rule_metadata import RuleMetadata
from .soo_schema import SOORecipe


OPERATOR_FUNCTIONAL_NOTES: dict[str, dict[str, Any]] = {
    "active_association_contrast": {
        "channel": "raw_scalar_association_contrast",
        "equation": "O_i = phi[target(i, phase)] - phi[i]",
        "classification": "scalar-smoothing / local contrast candidate",
        "charge_packet_safe": False,
    },
    "completed_rank3_balance": {
        "channel": "raw_scalar_completed_rank3_balance",
        "equation": "O_i = mean(phi[assoc[i,0]], phi[assoc[i,1]], phi[assoc[i,2]]) - phi[i]",
        "classification": "scalar-smoothing / completed association balance candidate",
        "charge_packet_safe": False,
    },
    "tensor_completion_pressure": {
        "channel": "derived_tensor_scalar_pressure",
        "equation": "O_i = weighted_mean_{j,k}(0.5*(phi[j]+phi[k])-phi[i]) using derived tensor geometry",
        "classification": "derived tensor smoothing candidate",
        "charge_packet_safe": False,
    },
    "support_initialization_source": {
        "channel": "sealed_support_initialization_source",
        "equation": "O_i = sealed support-source[i] during initialization epoch only",
        "classification": "initialization source, not measurement SOO by itself",
        "charge_packet_safe": False,
    },
    "relation_complete_packet_contrast": {
        "channel": "relation_complete_signed_boundary_dressing_packet",
        "equation": "chi_H,r = phi[b_H,r] - phi[d_H,r]; O_path = propagated signed packet comparison from both supports",
        "classification": "signed relation-complete charge-contact candidate",
        "charge_packet_safe": True,
    },
}


@dataclass(frozen=True)
class SOOFunctionalReport:
    report_schema: str
    scalar_update_rule_name: str
    scalar_update_rule_metadata: dict[str, Any]
    recipe_id: str | None
    closure: dict[str, Any] | None
    residual_terms: tuple[dict[str, Any], ...]
    whole_field_update: bool
    signed_values_preserved: bool
    clamping_forbidden: bool
    zero_crossing_allowed: bool
    functional_equation: str
    diagnostic_point_sampling: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    primitive_soo_operator: dict[str, Any] | None = None
    cyclic_return_hash: str | None = None
    stiffness_input_hash: str | None = None
    stiffness_feedback_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return stable_json_hash(self.to_dict())


def build_soo_functional_report(
    *,
    scalar_update_rule: object,
    metadata: RuleMetadata,
) -> SOOFunctionalReport:
    recipe: SOORecipe | None = getattr(scalar_update_rule, "recipe", None)
    diagnostic_points = tuple(getattr(scalar_update_rule, "diagnostic_points", ()))

    residual_terms: list[dict[str, Any]] = []
    warnings: list[str] = []
    closure_payload: dict[str, Any] | None = None
    signed_values_preserved = False
    clamping_forbidden = False
    zero_crossing_allowed = False
    recipe_id: str | None = None

    primitive_payload: dict[str, Any] | None = None
    cyclic_return_hash: str | None = None
    stiffness_input_hash: str | None = None
    stiffness_feedback_hash: str | None = None

    primitive_operator_id = getattr(scalar_update_rule, "primitive_operator_id", None)
    if primitive_operator_id == "association_indexed_soo_v1":
        execution_report = getattr(scalar_update_rule, "get_soo_execution_report", lambda: None)()
        cyclic_report = getattr(scalar_update_rule, "get_cyclic_return_report", lambda: None)()
        stiffness_report = getattr(scalar_update_rule, "get_stiffness_input_report", lambda: None)()
        feedback_report = getattr(scalar_update_rule, "get_stiffness_feedback_report", lambda: None)()
        primitive_payload = {
            "operator_id": "association_indexed_soo_v1",
            "classification": "association-indexed second-order SOO primitive",
            "residual_recipe_used": False,
            "two_ledger_state_required": True,
            "equation": "(Phi_l - A_theta_l Phi_{l-1}) - A^*_{theta_{l+1}}(Phi_{l+1} - A_theta_{l+1} Phi_l) - epsilon^2 K_theta_l Phi_l = 0",
            "execution_report_hash": execution_report.fingerprint() if execution_report is not None else None,
        }
        cyclic_return_hash = cyclic_report.fingerprint() if cyclic_report is not None else None
        stiffness_input_hash = stable_json_hash(stiffness_report) if stiffness_report is not None else None
        stiffness_feedback_hash = feedback_report.fingerprint() if feedback_report is not None else None
        warnings.append("association_indexed_soo_v1 is candidate infrastructure; stiffness closure verdict must be read separately before admission claims.")
    elif recipe is None:
        warnings.append("Scalar update rule does not expose a declarative SOO recipe.")
    else:
        recipe_id = recipe.recipe_id
        closure_payload = asdict(recipe.closure)
        signed_values_preserved = bool(recipe.closure.preserve_signed_values)
        clamping_forbidden = bool(recipe.closure.forbid_clamping)
        zero_crossing_allowed = bool(recipe.closure.allow_zero_crossing)
        for term in recipe.residual_terms:
            notes = OPERATOR_FUNCTIONAL_NOTES.get(term.operator_id, {})
            residual_terms.append(
                {
                    "id": term.id,
                    "operator_id": term.operator_id,
                    "weight": float(term.weight),
                    "scope": term.scope,
                    "operator_functional": notes,
                }
            )
            if notes and not bool(notes.get("charge_packet_safe", False)) and term.operator_id != "support_initialization_source":
                warnings.append(
                    f"Residual term {term.id!r} uses {term.operator_id!r}, classified as "
                    f"{notes.get('classification', 'unknown')}. It is not a relation-complete signed packet operator."
                )

    if recipe is not None and not any(term.operator_id == "relation_complete_packet_contrast" for term in recipe.residual_terms):
        warnings.append(
            "Recipe contains no relation_complete_packet_contrast term; charge-orientation tests may reduce to raw scalar smoothing."
        )

    sampled = tuple(
        {
            "point_index": int(point),
            "role": str(role),
        }
        for point, role in diagnostic_points
    )

    return SOOFunctionalReport(
        report_schema="rank3_soo_functional_report_v1",
        scalar_update_rule_name=getattr(scalar_update_rule, "name", metadata.name),
        scalar_update_rule_metadata=asdict(metadata),
        recipe_id=recipe_id,
        closure=closure_payload,
        residual_terms=tuple(residual_terms),
        whole_field_update=(metadata.name == "soo_declarative_v0_1"),
        signed_values_preserved=signed_values_preserved,
        clamping_forbidden=clamping_forbidden,
        zero_crossing_allowed=zero_crossing_allowed,
        functional_equation=(
            primitive_payload["equation"] if primitive_payload is not None else
            "For each layer ell and active phase r: R_i = sum_t weight_t * O_t(phi_ell, G_ell, r)_i; "
            "Delta phi_i = Closure(R_i); phi_{ell+1,i} = phi_{ell,i} + Delta phi_i."
        ),
        diagnostic_point_sampling=sampled,
        warnings=tuple(warnings),
        primitive_soo_operator=primitive_payload,
        cyclic_return_hash=cyclic_return_hash,
        stiffness_input_hash=stiffness_input_hash,
        stiffness_feedback_hash=stiffness_feedback_hash,
    )
