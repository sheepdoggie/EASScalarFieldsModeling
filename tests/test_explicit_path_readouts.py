from pathlib import Path

from rank3_enforced import run_declarative_overlay
from rank3_enforced.overlay_loader import load_declarative_overlay
from rank3_enforced.overlay_compiler import compile_overlay_to_model_package


def test_explicit_path_overlay_requires_locked_path_readouts():
    overlay_path = Path(__file__).resolve().parents[1] / "overlays" / "two_support_explicit_path_candidate_overlay.json"
    overlay, overlay_hash = load_declarative_overlay(overlay_path)
    package = compile_overlay_to_model_package(overlay, overlay_hash=overlay_hash)
    names = {rule.name for rule in package.readout_rules}
    assert "center_locus_readout" in names
    assert "structural_silence_readout" in names
    assert "delta_l_classification" in names


def test_explicit_path_run_produces_declared_path_diagnostics():
    overlay_path = Path(__file__).resolve().parents[1] / "overlays" / "two_support_explicit_path_candidate_overlay.json"
    result = run_declarative_overlay(overlay_path)
    reports = {report.name: report for report in result.readouts}
    center = reports["center_locus_readout"].payload
    silence = reports["structural_silence_readout"].payload
    delta = reports["delta_l_classification"].payload
    assert center["declared_path_length"] == 16
    assert center["center_kind"] == "center_pair"
    assert len(center["center_points"]) == 2
    assert silence["declared_path_length"] == 16
    assert delta["declared_path_length"] == 16
    assert delta["classification"] == "no_declared_path_length_change_observed"
    assert delta["edge_audits_by_state"][0]["declared_path_intact"] is True
