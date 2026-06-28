from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .exceptions import ManifestError
from .fingerprints import stable_json_hash


SUPPORTED_OPTIONAL_MODULES = {
    "soo_stiffness_feedback": {
        "status": "placeholder",
        "purpose": "SOO stiffness feedback closure diagnostics; default K_theta=I when no feedback test is declared.",
    },
    "charge_attraction_repulsion": {
        "status": "experimental",
        "purpose": "Initializes two charged supports and explicit paths for same/opposite orientation analysis.",
    },
    "gravitation": {
        "status": "experimental_placeholder",
        "purpose": "Initializes two neutral supports and explicit paths for gravitational/path-sector analysis.",
    },
    "run_debugging": {
        "status": "experimental_instrumentation",
        "purpose": "Optional run instrumentation retaining path-neighborhood SOO changes without altering SOO execution.",
    },
}


@dataclass(frozen=True)
class OptionalModuleReport:
    report_schema: str
    modules: tuple[dict[str, Any], ...]
    module_hash: str
    passed: bool
    details: dict[str, Any]

    def fingerprint(self) -> str:
        return stable_json_hash(asdict(self))


def validate_optional_modules(modules: tuple[object, ...]) -> OptionalModuleReport:
    records: list[dict[str, Any]] = []
    passed = True
    errors: list[str] = []
    for module in modules:
        module_id = str(getattr(module, "module_id", ""))
        if module_id not in SUPPORTED_OPTIONAL_MODULES:
            passed = False
            errors.append(f"Unsupported optional module: {module_id}")
            metadata = {"status": "unsupported", "purpose": "not recognized"}
        else:
            metadata = SUPPORTED_OPTIONAL_MODULES[module_id]
        records.append(
            {
                "module_id": module_id,
                "declared_status": str(getattr(module, "status", "experimental")),
                "params_hash": stable_json_hash(getattr(module, "params", {})),
                "framework_status": metadata["status"],
                "purpose": metadata["purpose"],
            }
        )
    if not passed:
        raise ManifestError("Optional module validation failed: " + "; ".join(errors))
    return OptionalModuleReport(
        report_schema="rank3_optional_module_report_v1",
        modules=tuple(records),
        module_hash=stable_json_hash(records),
        passed=True,
        details={
            "optional_modules_are_configuration_overlays_not_executable_plugins": True,
            "supported_module_ids": sorted(SUPPORTED_OPTIONAL_MODULES),
        },
    )
