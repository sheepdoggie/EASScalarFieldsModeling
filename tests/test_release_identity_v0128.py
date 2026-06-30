from pathlib import Path

from rank3_enforced.release_identity import (
    check_release_identity,
    compute_framework_zip_code_sha256,
)
from rank3_enforced.version_guard import compute_framework_code_sha256


def test_release_identity_report_passes_for_current_tree():
    root = Path(__file__).resolve().parents[1]
    report = check_release_identity(
        repo_root=root,
        manifest_path=root / "releases/current/FRAMEWORK_RELEASE_MANIFEST.json",
        framework_zip_path=root / "releases/current/enforceable_rank3_modeling_v0.1.40_endpoint_class_photon_field_processing.zip",
        framework_tar_gz_path=root / "releases/current/enforceable_rank3_modeling_v0.1.40_endpoint_class_photon_field_processing.tar.gz",
    )
    assert report.passed, report.errors
    assert report.manifest_code_sha256 == report.actual_source_tree_code_sha256
    assert report.manifest_code_sha256 == report.actual_framework_zip_code_sha256
    assert report.manifest_framework_sha256 == report.actual_framework_sha256


def test_framework_zip_code_hash_matches_installed_source_hash():
    root = Path(__file__).resolve().parents[1]
    zip_hash = compute_framework_zip_code_sha256(
        root / "releases/current/enforceable_rank3_modeling_v0.1.40_endpoint_class_photon_field_processing.zip"
    )
    tree_hash = compute_framework_code_sha256(root)
    assert zip_hash == tree_hash
