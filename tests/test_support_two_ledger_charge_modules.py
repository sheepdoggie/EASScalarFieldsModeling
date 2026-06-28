from pathlib import Path

from rank3_enforced.overlay_loader import load_declarative_overlay
from rank3_enforced.overlay_compiler import compile_overlay_to_model_package
from rank3_enforced.certified_runner import run_model_package
from rank3_enforced.path_construction import build_explicit_path_association_state
from rank3_enforced.overlay_schema import PathConstructionSpec, SupportSpec
from rank3_enforced.active_association import build_A_theta, is_orthogonal


def test_linear_support_path_v0_2_produces_orthogonal_slots():
    supports = (
        SupportSpec(
            name="support_A", support_points=(0,1,2,3,4,5), boundary_points=(0,1,2), dressing_points=(3,4,5), handedness="right", active_phase_map={0:3,1:4,2:5}
        ),
        SupportSpec(
            name="support_B", support_points=(6,7,8,9,10,11), boundary_points=(6,7,8), dressing_points=(9,10,11), handedness="left", active_phase_map={0:9,1:10,2:11}
        ),
    )
    state, report = build_explicit_path_association_state(
        n_points=48,
        path_spec=PathConstructionSpec(rule="linear_support_path_v0_2", path_length=16, orientation="opposite", left_support="support_A", right_support="support_B"),
        supports=supports,
    )
    assert report.rule == "linear_support_path_v0_2"
    for theta in (0,1,2):
        assert is_orthogonal(build_A_theta(state, theta))


def test_charge_overlay_runs_with_two_ledger_reports_and_packet_readouts():
    path = Path("overlays/charge_same_opposite_association_indexed/L16_same_association_indexed_soo.json")
    overlay, overlay_hash = load_declarative_overlay(path)
    package = compile_overlay_to_model_package(overlay, overlay_hash=overlay_hash)
    assert package.config.initial_phi_previous is not None
    assert package.initial_two_ledger_report is not None
    result = run_model_package(package)
    readout_names = {readout.name for readout in result.readouts}
    assert "relation_complete_packet_readout" in readout_names
    assert "common_mode_zero_sum_report" in readout_names
    assert result.initial_two_ledger_report is not None
    assert result.soo_execution_report is not None
    assert result.cyclic_return_report is not None
    assert result.response_burden_report.burden_rule_id == "path_support_packet_burden_v0_1"
    assert result.path_facing_association_report is not None
    assert result.path_facing_association_report.status == "association_role_report_only"
    assert result.run_debugging_report is None
    assert result.controls.passed


def test_all_rebuilt_charge_overlays_compile():
    paths = sorted(Path("overlays/charge_same_opposite_association_indexed").glob("*.json"))
    assert len(paths) == 34
    for path in paths:
        overlay, overlay_hash = load_declarative_overlay(path)
        package = compile_overlay_to_model_package(overlay, overlay_hash=overlay_hash)
        assert package.manifest.model_name.startswith("charge_")
        assert package.config.initial_phi_previous is not None
        assert package.initial_two_ledger_report is not None
        assert package.run_debugging_spec is None


def test_run_debugging_is_explicit_opt_in(tmp_path):
    from rank3_enforced.run_manager import stage_overlay_with_debug

    source = Path("overlays/charge_same_opposite_association_indexed/L16_same_association_indexed_soo.json")
    staged = stage_overlay_with_debug(overlay_path=source, staging_dir=tmp_path, depth=1, max_points=256)
    overlay, overlay_hash = load_declarative_overlay(staged)
    package = compile_overlay_to_model_package(overlay, overlay_hash=overlay_hash)
    assert package.run_debugging_spec is not None
    result = run_model_package(package)
    assert result.run_debugging_report is not None
    assert result.run_debugging_report.instrumentation_module == "run_debugging"
    assert result.run_debugging_report.debug_point_count >= 18
