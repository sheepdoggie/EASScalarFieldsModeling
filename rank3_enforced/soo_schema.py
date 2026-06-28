from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .exceptions import ManifestError

ResidualOperatorId = Literal[
    "active_association_contrast",
    "completed_rank3_balance",
    "tensor_completion_pressure",
    "support_initialization_source",
    "relation_complete_packet_contrast",
]
ClosureId = Literal["linear_response", "fixed_point_damped"]

ALLOWED_RESIDUAL_OPERATORS = {
    "active_association_contrast",
    "completed_rank3_balance",
    "tensor_completion_pressure",
    "support_initialization_source",
    "relation_complete_packet_contrast",
}
ALLOWED_CLOSURES = {"linear_response", "fixed_point_damped"}


@dataclass(frozen=True)
class SOOResidualTermSpec:
    id: str
    operator_id: ResidualOperatorId
    weight: float = 1.0
    scope: str = "all_points"


@dataclass(frozen=True)
class SOOClosureSpec:
    id: ClosureId
    response_scale: float = 0.0
    max_iterations: int = 1
    tolerance: float = 1e-12
    preserve_signed_values: bool = True
    allow_zero_crossing: bool = True
    forbid_clamping: bool = True


@dataclass(frozen=True)
class SOORecipe:
    recipe_id: str
    residual_terms: tuple[SOOResidualTermSpec, ...]
    closure: SOOClosureSpec
    invariant_profile: str = "strict_candidate"


FORBIDDEN_SOO_KEYS = {
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
    "expected_result",
    "desired_result",
    "attraction",
    "repulsion",
    "force_path_shortening",
    "force_path_lengthening",
    "midpoint_collapse",
    "target_verdict",
}


def reject_executable_or_target_keys(value: Any, *, path: str = "soo_recipe") -> None:
    if isinstance(value, dict):
        for key, subvalue in value.items():
            lower = str(key).lower()
            if lower in FORBIDDEN_SOO_KEYS or lower.endswith("_code") or lower.endswith("_source"):
                raise ManifestError(
                    f"Forbidden SOO recipe key rejected at {path}.{key!s}. "
                    "SOO recipes are declarative and target-blind."
                )
            reject_executable_or_target_keys(subvalue, path=f"{path}.{key!s}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_executable_or_target_keys(item, path=f"{path}[{index}]")


def parse_soo_recipe(payload: dict[str, Any]) -> SOORecipe:
    reject_executable_or_target_keys(payload)

    residual_terms_raw = payload.get("residual_terms")
    if not isinstance(residual_terms_raw, list) or not residual_terms_raw:
        raise ManifestError("SOO recipe requires a non-empty residual_terms list.")

    residual_terms: list[SOOResidualTermSpec] = []
    seen_ids: set[str] = set()
    for raw in residual_terms_raw:
        if not isinstance(raw, dict):
            raise ManifestError("Each SOO residual term must be an object.")
        term_id = str(raw.get("id", "")).strip()
        operator_id = str(raw.get("operator_id", raw.get("operator", ""))).strip()
        if not term_id:
            raise ManifestError("SOO residual term requires id.")
        if term_id in seen_ids:
            raise ManifestError(f"Duplicate SOO residual term id: {term_id}")
        seen_ids.add(term_id)
        if operator_id not in ALLOWED_RESIDUAL_OPERATORS:
            raise ManifestError(f"Unknown locked SOO residual operator: {operator_id}")
        scope = str(raw.get("scope", "all_points"))
        if scope not in ("all_points", "declared_support_sites"):
            raise ManifestError("SOO residual term scope must be 'all_points' or 'declared_support_sites'.")
        if operator_id != "support_initialization_source" and scope != "all_points":
            raise ManifestError("Only support_initialization_source may use scope='declared_support_sites'.")
        residual_terms.append(
            SOOResidualTermSpec(
                id=term_id,
                operator_id=operator_id,  # type: ignore[arg-type]
                weight=float(raw.get("weight", 1.0)),
                scope=scope,
            )
        )

    closure_raw = payload.get("closure")
    if not isinstance(closure_raw, dict):
        raise ManifestError("SOO recipe requires closure object.")
    closure_id = str(closure_raw.get("id", "")).strip()
    if closure_id not in ALLOWED_CLOSURES:
        raise ManifestError(f"Unknown locked SOO closure: {closure_id}")

    closure = SOOClosureSpec(
        id=closure_id,  # type: ignore[arg-type]
        response_scale=float(closure_raw.get("response_scale", 0.0)),
        max_iterations=int(closure_raw.get("max_iterations", 1)),
        tolerance=float(closure_raw.get("tolerance", 1e-12)),
        preserve_signed_values=bool(closure_raw.get("preserve_signed_values", True)),
        allow_zero_crossing=bool(closure_raw.get("allow_zero_crossing", True)),
        forbid_clamping=bool(closure_raw.get("forbid_clamping", True)),
    )

    if closure.max_iterations < 1:
        raise ManifestError("SOO closure max_iterations must be at least 1.")
    if closure.tolerance <= 0:
        raise ManifestError("SOO closure tolerance must be positive.")
    if not closure.preserve_signed_values:
        raise ManifestError("SOO recipe must preserve signed values in enforced mode.")
    if not closure.allow_zero_crossing:
        raise ManifestError("SOO recipe must allow zero crossing in enforced mode.")
    if not closure.forbid_clamping:
        raise ManifestError("SOO recipe must forbid clamping in enforced mode.")

    return SOORecipe(
        recipe_id=str(payload.get("recipe_id", "soo_recipe")).strip() or "soo_recipe",
        residual_terms=tuple(residual_terms),
        closure=closure,
        invariant_profile=str(payload.get("invariant_profile", "strict_candidate")),
    )
