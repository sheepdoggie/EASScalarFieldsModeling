from __future__ import annotations

import argparse
import json
from pathlib import Path

from .modeling_intent import (
    charge_path_adjustment_certification_template,
    contract_from_file,
    validate_contract_for_overlay,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main_template(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a modeling_intent contract template.")
    parser.add_argument("--intent", default="charge_path_adjustment_theorem", choices=["charge_path_adjustment_theorem"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    contract = charge_path_adjustment_certification_template()
    _write_json(Path(args.output), contract.to_dict())
    print(f"Wrote modeling_intent contract template: {args.output}")
    return 0


def main_validate(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a modeling_intent contract against an overlay JSON.")
    parser.add_argument("contract")
    parser.add_argument("overlay")
    args = parser.parse_args(argv)
    contract = contract_from_file(args.contract)
    overlay_payload = json.loads(Path(args.overlay).read_text(encoding="utf-8"))
    report = validate_contract_for_overlay(contract=contract, overlay_payload=overlay_payload, overlay_hash=None)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1
