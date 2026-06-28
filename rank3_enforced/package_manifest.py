from __future__ import annotations

import platform
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .certificates import write_enforced_run_package
from .fingerprints import directory_hash, stable_json_hash
from .locked_registries import (
    ASSOCIATION_REMAP_RULES,
    PAIR_WEIGHT_RULES,
    PHASE_RULES,
    READOUT_RULES,
    PATH_READOUT_NAMES,
    SUPPORT_READOUT_NAMES,
    SCALAR_UPDATE_RULES,
    TRIPLET_LIFT_RULES,
)
from .signing import sign_enforced_run_package
from .soo_operator_registry import SOO_RESIDUAL_OPERATORS
from .soo_functional import OPERATOR_FUNCTIONAL_NOTES


def default_environment_record() -> dict[str, Any]:
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
    }


def registry_hashes() -> dict[str, str]:
    rule_registry_payload = {
        "scalar_update_rules": {
            k: asdict(v.metadata) if v.metadata is not None else None
            for k, v in sorted(SCALAR_UPDATE_RULES.items())
        },
        "association_remap_rules": {
            k: asdict(v.metadata) if v.metadata is not None else None
            for k, v in sorted(ASSOCIATION_REMAP_RULES.items())
        },
        "phase_rules": sorted(PHASE_RULES.keys()),
        "pair_weight_rules": sorted(PAIR_WEIGHT_RULES.keys()),
        "triplet_lift_rules": sorted(TRIPLET_LIFT_RULES.keys()),
        "soo_residual_operators": sorted(SOO_RESIDUAL_OPERATORS.keys()),
        "soo_operator_functional_notes": OPERATOR_FUNCTIONAL_NOTES,
    }
    return {
        "rule_registry_hash": stable_json_hash(rule_registry_payload),
        "readout_registry_hash": stable_json_hash(sorted(set(READOUT_RULES.keys()) | PATH_READOUT_NAMES | SUPPORT_READOUT_NAMES)),
        "model_type_registry_hash": stable_json_hash(["minimal_control", "two_support_path_adjustment", "two_support_explicit_path_adjustment", "association_indexed_soo_feedback_candidate", "charge_attraction_repulsion_candidate", "gravitation_path_candidate", "charge_role_path_remap_dynamic_path_candidate"]),
    }


def package_and_sign_enforced_result(
    *,
    result,
    output_dir: str | Path,
    private_key_path: str | Path,
    overlay_path: str | Path | None = None,
    command: str = "not_recorded",
    environment: dict[str, Any] | None = None,
) -> None:
    output_dir = Path(output_dir)
    environment = environment or default_environment_record()
    write_enforced_run_package(
        result=result,
        output_dir=output_dir,
        overlay_path=overlay_path,
        command=command,
        environment=environment,
    )
    hashes = registry_hashes()
    sign_enforced_run_package(
        package_dir=output_dir,
        result=result,
        private_key_path=private_key_path,
        command_hash=stable_json_hash(command),
        environment_hash=stable_json_hash(environment),
        rule_registry_hash=hashes["rule_registry_hash"],
        readout_registry_hash=hashes["readout_registry_hash"],
        model_type_registry_hash=hashes["model_type_registry_hash"],
    )
