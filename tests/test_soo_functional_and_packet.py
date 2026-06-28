from __future__ import annotations

from pathlib import Path

from rank3_enforced import run_declarative_overlay


ROOT = Path(__file__).resolve().parents[1]


def test_soo_functional_report_flags_smoothing_recipe():
    result = run_declarative_overlay(ROOT / "overlays" / "two_support_explicit_path_candidate_overlay.json")
    report = result.soo_functional_report
    assert report is not None
    assert report.recipe_id == "support_seeded_explicit_path_soo_v0_1"
    assert any("scalar smoothing" in warning or "raw scalar smoothing" in warning for warning in report.warnings)
    assert any("no relation_complete_packet_contrast" in warning for warning in report.warnings)
    assert result.soo_traces
    first_trace = result.soo_traces[0]
    assert first_trace.closure_trace.point_samples
    assert any(sample.role.startswith("declared_center") for sample in first_trace.closure_trace.point_samples)
    assert all(term.point_samples for term in first_trace.residual_terms)


def test_relation_complete_packet_operator_is_locked_and_traced():
    result = run_declarative_overlay(
        ROOT / "overlays" / "two_support_explicit_path_signed_packet_candidate_overlay.json"
    )
    report = result.soo_functional_report
    assert report is not None
    assert report.recipe_id == "support_seeded_explicit_path_signed_packet_soo_v0_1"
    assert len(report.residual_terms) == 1
    assert report.residual_terms[0]["operator_id"] == "relation_complete_packet_contrast"
    assert report.residual_terms[0]["operator_functional"]["charge_packet_safe"] is True

    trace = result.soo_traces[0]
    term = trace.residual_terms[0]
    assert term.operator_id == "relation_complete_packet_contrast"
    center_samples = [sample for sample in term.point_samples if sample.role.startswith("declared_center")]
    assert center_samples
    # L16 opposite case should show a balanced signed center-pair packet, not identical common-mode smoothing.
    assert len(center_samples) == 2
    assert center_samples[0].raw_residual_value == -center_samples[1].raw_residual_value
    closure_samples = [sample for sample in trace.closure_trace.point_samples if sample.role.startswith("declared_center")]
    assert closure_samples[0].delta_phi_value == -closure_samples[1].delta_phi_value
