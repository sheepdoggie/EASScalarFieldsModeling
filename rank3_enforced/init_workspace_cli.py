from __future__ import annotations

import argparse

from .run_manager import write_workspace
from .workspace_layout import create_separated_workspace_layout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Rank-3/EAS run workspace directories.")
    parser.add_argument("path", nargs="?", help="Workspace directory to create, or project root when --separate-subtrees is used")
    parser.add_argument("--separate-subtrees", action="store_true", help="Create separate framework-install and modeling-run subtrees")
    parser.add_argument("--project-root", help="Project root for --separate-subtrees; overrides positional path")
    parser.add_argument("--install-subtree", default="EASScalarFieldsModeling_github_files")
    parser.add_argument("--run-subtree", default="EAS_runs")
    args = parser.parse_args(argv)
    root_arg = args.project_root or args.path
    if not root_arg:
        parser.error("path or --project-root is required")
    if args.separate_subtrees:
        layout = create_separated_workspace_layout(
            root_arg,
            install_subtree=args.install_subtree,
            run_subtree=args.run_subtree,
        )
        print(layout.project_root)
        return 0
    root = write_workspace(root_arg)
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
