from __future__ import annotations

import argparse
import json
from pathlib import Path

from .soo_debug_analysis import analyze_soo_debug_pair


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze two debug-enabled same/opposite SOO runs around a declared path neighborhood.")
    parser.add_argument("--same-run-dir", required=True, help="Signed evidence directory for same-orientation debug run")
    parser.add_argument("--opposite-run-dir", required=True, help="Signed evidence directory for opposite-orientation debug run")
    parser.add_argument("--output-dir", required=True, help="Directory for SOO debug pair analysis outputs")
    args = parser.parse_args(argv)
    report = analyze_soo_debug_pair(
        same_run_dir=Path(args.same_run_dir),
        opposite_run_dir=Path(args.opposite_run_dir),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
