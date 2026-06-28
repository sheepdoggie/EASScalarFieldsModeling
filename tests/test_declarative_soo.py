from __future__ import annotations

import json
from pathlib import Path

import pytest

from rank3_enforced import ManifestError, run_declarative_overlay


def test_declarative_soo_overlay_emits_primary_traces():
    result = run_declarative_overlay("overlays/minimal_candidate_soo_overlay.json")
    assert not result.certified
    assert len(result.soo_traces) == result.primary_result.phi.shape[0] - 1
    assert result.evidence.soo_trace_hash != "not_applicable"
    assert result.gate.details["soo_trace_audit"]["invariant_passed"] is True
    assert all(trace.invariants.passed for trace in result.soo_traces)


def test_soo_recipe_rejects_target_verdict_keys(tmp_path: Path):
    base = json.loads(Path("overlays/minimal_candidate_soo_overlay.json").read_text())
    base["rules"]["scalar_update_params"]["recipe"]["expected_result"] = "shorten"
    path = tmp_path / "bad_soo_overlay.json"
    path.write_text(json.dumps(base))

    with pytest.raises(ManifestError):
        run_declarative_overlay(path)
