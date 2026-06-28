from pathlib import Path

import json

from rank3_enforced.certified_runner import run_declarative_overlay
from rank3_enforced.overlay_schema import parse_declarative_overlay
from rank3_enforced.overlay_compiler import compile_overlay_to_model_package
from rank3_enforced.run_manager import BUILTIN_SUITES, suite_resource_files


def suite_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "rank3_enforced" / "overlay_suites" / "charge_role_path_remap_dynamic_path_v0_1"


def test_v0122_builtin_suite_is_registered_and_has_expected_cases():
    assert "charge_role_path_remap_dynamic_path_v0_1" in BUILTIN_SUITES
    files = suite_resource_files("charge_role_path_remap_dynamic_path_v0_1")
    assert len(files) == 18
    assert any(p.name == "L17_same_role_remap_same_slot.json" for p in files)


def test_v0122_role_path_overlay_compiles_to_role_path_constructor():
    payload = json.loads((suite_dir() / "L7_same_no_remap.json").read_text())
    overlay = parse_declarative_overlay(payload)
    package = compile_overlay_to_model_package(overlay, overlay_hash="test_overlay_hash")
    report = package.path_construction_report
    assert report is not None
    assert report.rule == "role_path_two_support_v0_1"
    state = package.config.initial_state
    # left dressing endpoint 3: slot0 boundary fixed, slot1 path-facing
    assert int(state.assoc[3, 0]) == 0
    assert int(state.assoc[3, 1]) == 12
    # right dressing endpoint 9: slot0 boundary fixed, slot1 path-facing to last path node
    assert int(state.assoc[9, 0]) == 6
    assert int(state.assoc[9, 1]) == 18


def test_v0122_no_remap_case_runs_and_keeps_declared_path_length_zero_delta():
    result = run_declarative_overlay(suite_dir() / "L7_same_no_remap.json")
    readouts = {r.name: r.payload for r in result.readouts}
    assert "role_path_midpoint_arrival_readout" in readouts
    assert readouts["delta_l_classification"]["delta_declared_path_length"] == 0
    assert readouts["delta_l_classification"]["classification"] == "no_declared_path_length_change_observed"
    assert result.role_path_remap_report is None or len(result.role_path_remap_report) == 0


def test_v0122_role_remap_case_runs_and_emits_role_remap_report():
    result = run_declarative_overlay(suite_dir() / "L7_same_role_remap_same_slot.json")
    assert result.role_path_remap_report is not None
    assert len(result.role_path_remap_report) > 0
    applied = [r for r in result.role_path_remap_report if r.applied]
    assert applied
    assert all(r.details["scalar_values_moved"] is False for r in applied)
    assert all(r.details["boundary_slots_fixed"] is True for r in applied)
