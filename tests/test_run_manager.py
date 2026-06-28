from __future__ import annotations

from pathlib import Path

from rank3_enforced.run_manager import list_builtin_suites, overlay_files_from_source, write_workspace


def test_builtin_charge_suite_is_packaged():
    suites = {row["suite_id"]: row for row in list_builtin_suites()}
    assert "charge_same_opposite_association_indexed" in suites
    assert suites["charge_same_opposite_association_indexed"]["overlay_count"] == 34
    files = overlay_files_from_source(suite_id="charge_same_opposite_association_indexed")
    assert len(files) == 34
    assert all(path.name.endswith("_association_indexed_soo.json") for path in files)


def test_write_code_free_workspace(tmp_path: Path):
    workspace = write_workspace(tmp_path / "rank3_workspace")
    assert (workspace / "README.md").is_file()
    assert (workspace / "SUITES.json").is_file()
    assert (workspace / "runs").is_dir()
    assert (workspace / "logs").is_dir()
    assert not (workspace / "rank3_enforced").exists()
