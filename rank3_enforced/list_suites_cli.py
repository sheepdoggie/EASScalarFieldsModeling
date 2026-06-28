from __future__ import annotations

import argparse
import json

from .run_manager import list_builtin_suites


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List built-in Rank-3 overlay suites packaged with the installed framework.")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)
    suites = list_builtin_suites()
    if args.json:
        print(json.dumps(suites, indent=2, sort_keys=True))
    else:
        for s in suites:
            print(f"{s['suite_id']}  overlays={s['overlay_count']}")
            print(f"  {s['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
