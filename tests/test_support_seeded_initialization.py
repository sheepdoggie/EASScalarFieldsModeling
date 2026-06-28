from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from rank3_enforced.certified_runner import run_declarative_overlay
from rank3_enforced.exceptions import ManifestError

ROOT = Path(__file__).resolve().parents[1]


def _load_two_support() -> dict:
    return json.loads((ROOT / "overlays" / "two_support_candidate_overlay.json").read_text())


def test_two_support_overlay_has_support_seeded_initialization():
    result = run_declarative_overlay(ROOT / "overlays" / "two_support_candidate_overlay.json")
    assert result.initialization_report is not None
    assert result.initialization_report.mode == "support_seeded"
    assert result.initialization_report.passed
    assert result.initialization_report.source_trace.support_nonzero_count > 0
    assert result.initialization_report.source_trace.vacuum_nonzero_count == 0
    assert len(result.initialization_soo_traces) == result.initialization_report.initialization_cycles
    assert all(trace.epoch == "initialization" for trace in result.initialization_soo_traces)
    assert result.evidence.initialization_hash == result.initialization_report.fingerprint()


def test_two_support_without_support_seeded_initialization_is_rejected(tmp_path: Path):
    payload = _load_two_support()
    payload["initialization"] = {"mode": "vacuum_zero", "source_rule": "zero_vacuum"}
    bad = tmp_path / "bad_two_support.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ManifestError, match="support_seeded"):
        run_declarative_overlay(bad)


def test_support_initialization_source_without_support_seeded_mode_is_rejected(tmp_path: Path):
    payload = _load_two_support()
    payload["model_type"] = "minimal_control"
    payload["supports"] = []
    payload["constraints"] = {}
    payload["initialization"] = {"mode": "vacuum_zero", "source_rule": "zero_vacuum"}
    # Keep the recipe containing support_initialization_source; it must be rejected.
    bad = tmp_path / "bad_source_operator.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ManifestError, match="support_initialization_source"):
        run_declarative_overlay(bad)
