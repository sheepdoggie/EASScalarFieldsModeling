from pathlib import Path

from rank3_enforced.workspace_layout import create_separated_workspace_layout
from rank3_enforced.capabilities import FRAMEWORK_VERSION, FRAMEWORK_CAPABILITIES


def test_v0123_capabilities_mark_path_change_external_only():
    assert FRAMEWORK_VERSION == "0.1.42"
    assert "external_path_monitor_api_v0_1" in FRAMEWORK_CAPABILITIES
    assert "path_length_change_external_monitor_only" in FRAMEWORK_CAPABILITIES
    assert "path_edit_not_intrinsic_framework_rule" in FRAMEWORK_CAPABILITIES
    assert "latest_framework_code_sha256_manifest_field" in FRAMEWORK_CAPABILITIES
    assert "accepted_framework_code_sha256_manifest_field" in FRAMEWORK_CAPABILITIES
    assert "gated_path_shortening_v1" not in FRAMEWORK_CAPABILITIES
    assert "gated_path_lengthening_v1" not in FRAMEWORK_CAPABILITIES


def test_separated_workspace_layout(tmp_path: Path):
    layout = create_separated_workspace_layout(tmp_path)
    assert Path(layout.install_root).name == "EASScalarFieldsModeling_github_files"
    assert Path(layout.run_root).name == "EAS_runs"
    assert Path(layout.publish_repo).is_dir()
    assert Path(layout.run_results).is_dir()
    assert (tmp_path / "EAS_WORKSPACE_LAYOUT.json").is_file()
    assert (tmp_path / "EAS_WORKSPACE_LAYOUT.md").is_file()
