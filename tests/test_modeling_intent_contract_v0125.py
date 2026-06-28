from __future__ import annotations

import json
import os
from pathlib import Path

from rank3_enforced.modeling_intent import charge_path_adjustment_certification_template
from rank3_enforced.run_manager import run_overlay_suite, stage_overlay_with_run_overrides


def test_stage_overlay_propagates_supplied_contract(tmp_path: Path) -> None:
    source = Path("overlays/minimal_control_overlay.json")
    contract = charge_path_adjustment_certification_template()
    staged = stage_overlay_with_run_overrides(
        overlay_path=source,
        staging_dir=tmp_path,
        modeling_intent_payload=contract.to_dict(),
    )
    payload = json.loads(staged.read_text(encoding="utf-8"))
    assert payload["modeling_intent"]["mode"] == "certification"
    assert payload["modeling_intent"]["modeling_intent"] == "charge_path_adjustment_theorem"


def test_certification_suite_blocks_before_modeling_and_preserves_contract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RANK3_RELEASE_GUARD", "off")
    contract = charge_path_adjustment_certification_template()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    report = run_overlay_suite(
        suite_id="charge_role_path_remap_dynamic_path_v0_1",
        output_root=tmp_path / "suite",
        private_key_path=Path.home() / ".rank3" / "private_key.pem",
        fail_fast=True,
        progress=False,
        case_ids=("L7_same_no_remap",),
        modeling_mode="certification",
        modeling_intent_contract_path=contract_path,
    )
    assert report.failed_count == 1
    case_dir = tmp_path / "suite" / "runs" / "L7_same_no_remap"
    assert (case_dir / "MODELING_INTENT_CONTRACT.json").is_file()
    assert not (case_dir / "CERTIFICATE.json").exists()
    emitted = json.loads((case_dir / "MODELING_INTENT_CONTRACT.json").read_text(encoding="utf-8"))
    assert emitted["mode"] == "certification"
    assert emitted["modeling_intent"] == "charge_path_adjustment_theorem"
    propagation = json.loads((case_dir / "CONTRACT_PROPAGATION_REPORT.json").read_text(encoding="utf-8"))
    assert propagation["supplied_contract_used"] is True
    assert propagation["exploratory_default_substituted"] is False
    assert propagation["model_executed"] is False


def test_suite_accepts_local_release_guard_sources_args(tmp_path: Path) -> None:
    # Presence of the keyword path is enough for regression coverage at the
    # run-manager boundary; deeper cryptographic behavior is covered by
    # test_release_version_guard.py.
    import inspect
    from rank3_enforced.run_manager import run_overlay_suite

    sig = inspect.signature(run_overlay_suite)
    assert "release_manifest_url" in sig.parameters
    assert "release_signature_url" in sig.parameters
    assert "release_public_key_url" in sig.parameters
    assert "framework_zip_path" in sig.parameters
