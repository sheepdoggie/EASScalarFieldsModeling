from __future__ import annotations

import json
from pathlib import Path

from rank3_enforced.publication_certified_run import (
    audit_publication_overlay_input,
    verify_publication_certified_package,
)


def test_publication_input_audit_accepts_data_only_overlay(tmp_path: Path):
    overlay = tmp_path / "case.json"
    overlay.write_text(json.dumps({"model_name": "demo", "scalar_update_rule": "bounded_context_soo_v1"}), encoding="utf-8")
    report = audit_publication_overlay_input(overlay)
    assert report.passed
    assert report.overlay_is_json
    assert report.overlay_is_data_only
    assert report.overlay_parent_code_free


def test_publication_input_audit_blocks_forbidden_code_key(tmp_path: Path):
    overlay = tmp_path / "case.json"
    overlay.write_text(json.dumps({"python_callable": "evil"}), encoding="utf-8")
    report = audit_publication_overlay_input(overlay)
    assert not report.passed
    assert report.forbidden_key_hits


def test_publication_input_audit_blocks_code_file_near_overlay(tmp_path: Path):
    overlay = tmp_path / "case.json"
    overlay.write_text(json.dumps({"model_name": "demo"}), encoding="utf-8")
    (tmp_path / "helper.py").write_text("print('not allowed')\n", encoding="utf-8")
    report = audit_publication_overlay_input(overlay)
    assert not report.passed
    assert report.forbidden_external_code_files == ("helper.py",)


def test_publication_input_audit_allows_explicit_code_near_overlay_override(tmp_path: Path):
    overlay = tmp_path / "case.json"
    overlay.write_text(json.dumps({"model_name": "demo"}), encoding="utf-8")
    (tmp_path / "helper.py").write_text("print('exploratory only')\n", encoding="utf-8")
    report = audit_publication_overlay_input(overlay, strict_overlay_parent_code_free=False)
    assert report.passed


def test_verify_publication_package_reports_missing(tmp_path: Path):
    report = verify_publication_certified_package(tmp_path)
    assert not report["valid"]
    assert not report["publication_report_present"]
