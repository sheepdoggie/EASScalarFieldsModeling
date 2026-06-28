from __future__ import annotations

import json
from pathlib import Path

import pytest

from rank3_enforced import ManifestError, run_declarative_overlay

ROOT = Path(__file__).resolve().parents[1]


def test_association_indexed_soo_feedback_overlay_emits_modular_reports():
    result = run_declarative_overlay(ROOT / "overlays" / "minimal_association_indexed_soo_feedback_overlay.json")
    assert result.soo_execution_report is not None
    assert result.soo_execution_report.primitive_operator_id == "association_indexed_soo_v1"
    assert result.soo_execution_report.step_count == result.primary_result.phi.shape[0] - 1
    assert result.cyclic_return_report is not None
    assert result.cyclic_return_report.passed is True
    assert result.stiffness_input_report is not None
    assert result.response_burden_report is not None
    assert result.induced_stiffness_report is not None
    assert result.stiffness_closure_report is not None
    assert result.stiffness_feedback_report is not None
    assert result.soo_functional_report is not None
    assert result.soo_functional_report.primitive_soo_operator["operator_id"] == "association_indexed_soo_v1"
    assert result.soo_functional_report.cyclic_return_hash == result.cyclic_return_report.fingerprint()


def test_residual_recipe_rejected_for_association_indexed_model_type(tmp_path: Path):
    payload = json.loads((ROOT / "overlays" / "minimal_association_indexed_soo_feedback_overlay.json").read_text())
    payload["rules"]["scalar_update_rule"] = "soo_declarative_v0_1"
    payload["rules"]["scalar_update_params"] = {
        "recipe": {
            "recipe_id": "bad_residual_recipe",
            "residual_terms": [{"id": "active", "operator_id": "active_association_contrast", "weight": 1.0}],
            "closure": {"id": "linear_response", "response_scale": 0.1}
        }
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ManifestError):
        run_declarative_overlay(path)
