from __future__ import annotations

"""Workspace helpers for separating framework installs from modeling runs."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class SeparatedWorkspaceLayout:
    schema: str
    project_root: str
    install_root: str
    publish_repo: str
    package_archive_root: str
    run_root: str
    run_overlays: str
    run_results: str
    run_logs: str
    run_workspaces: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_separated_workspace_layout(
    project_root: str | Path,
    *,
    install_subtree: str = "EASScalarFieldsModeling_github_files",
    run_subtree: str = "EAS_runs",
) -> SeparatedWorkspaceLayout:
    root = Path(project_root).expanduser().resolve()
    install_root = root / install_subtree
    run_root = root / run_subtree
    publish_repo = install_root / "EASScalarFieldsModeling_publish"
    package_archive_root = install_root / "packages"
    run_overlays = run_root / "overlays"
    run_results = run_root / "results"
    run_logs = run_root / "logs"
    run_workspaces = run_root / "workspaces"
    for path in (install_root, publish_repo, package_archive_root, run_root, run_overlays, run_results, run_logs, run_workspaces):
        path.mkdir(parents=True, exist_ok=True)
    layout = SeparatedWorkspaceLayout(
        schema="rank3_separated_workspace_layout_v0_1",
        project_root=str(root),
        install_root=str(install_root),
        publish_repo=str(publish_repo),
        package_archive_root=str(package_archive_root),
        run_root=str(run_root),
        run_overlays=str(run_overlays),
        run_results=str(run_results),
        run_logs=str(run_logs),
        run_workspaces=str(run_workspaces),
    )
    (root / "EAS_WORKSPACE_LAYOUT.json").write_text(json.dumps(layout.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "EAS_WORKSPACE_LAYOUT.md").write_text(
        "# EAS Scalar Fields separated workspace layout\n\n"
        "This layout keeps install/update material separate from modeling run outputs.\n\n"
        f"- Framework install/update subtree: `{install_root}`\n"
        f"- Publish repository: `{publish_repo}`\n"
        f"- Package archive root: `{package_archive_root}`\n"
        f"- Modeling run subtree: `{run_root}`\n"
        f"- Run overlays: `{run_overlays}`\n"
        f"- Run results: `{run_results}`\n"
        f"- Run logs: `{run_logs}`\n"
        f"- Run workspaces: `{run_workspaces}`\n\n"
        "Do not write framework source trees into the run subtree. Do not write run outputs into the publish repository except when intentionally committing examples.\n",
        encoding="utf-8",
    )
    return layout
