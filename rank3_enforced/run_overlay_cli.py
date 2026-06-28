from __future__ import annotations

import argparse
import json
from pathlib import Path

from .run_manager import default_signing_key, run_signed_overlay_case, stage_overlay_with_debug


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and sign one declarative Rank-3 overlay using the installed framework package.")
    parser.add_argument("overlay", help="Path to overlay JSON")
    parser.add_argument("output_dir", help="Directory where the signed evidence package will be written")
    parser.add_argument("--signing-key", default=str(default_signing_key()), help="Private signing key path. Default: ~/.rank3/private_key.pem")
    parser.add_argument("--required-artifact", action="append", default=[], help="Artifact that must exist after the run; may be repeated")
    parser.add_argument("--debug", action="store_true", help="Explicitly enable run-debugging instrumentation for this overlay")
    parser.add_argument("--debug-depth", type=int, default=1, help="Rank-3 association neighborhood depth for --debug. Default: 1")
    parser.add_argument("--debug-max-points", type=int, default=256, help="Maximum debug neighborhood points for --debug. Default: 256")
    args = parser.parse_args(argv)
    overlay_path = Path(args.overlay)
    required = tuple(args.required_artifact)
    if args.debug:
        overlay_path = stage_overlay_with_debug(
            overlay_path=overlay_path,
            staging_dir=Path(args.output_dir) / ".rank3_staged_overlay",
            depth=args.debug_depth,
            max_points=args.debug_max_points,
        )
        if "RUN_DEBUG_REPORT.json" not in required:
            required = required + ("RUN_DEBUG_REPORT.json",)
    record = run_signed_overlay_case(
        overlay_path=overlay_path,
        output_dir=Path(args.output_dir),
        private_key_path=Path(args.signing_key),
        required_artifacts=required,
        command="rank3-run-overlay" + (" --debug" if args.debug else ""),
    )
    print(json.dumps(record.__dict__, indent=2, sort_keys=True))
    return 0 if record.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
