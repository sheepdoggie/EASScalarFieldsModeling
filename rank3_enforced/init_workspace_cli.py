from __future__ import annotations

import argparse

from .run_manager import write_workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a code-free Rank-3 run workspace.")
    parser.add_argument("path", help="Workspace directory to create")
    args = parser.parse_args(argv)
    root = write_workspace(args.path)
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
