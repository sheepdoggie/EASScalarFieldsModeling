from __future__ import annotations

import argparse
import json
from pathlib import Path

from .run_manager import BUILTIN_SUITES, build_settling_overrides, default_signing_key, run_overlay_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a built-in or external overlay suite using the installed framework package.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("suite_id", nargs="?", choices=sorted(BUILTIN_SUITES.keys()), help="Built-in suite ID")
    source.add_argument("--overlays-dir", help="Directory containing external overlay JSON files")
    parser.add_argument("--output-root", required=True, help="Output root for suite results")
    parser.add_argument("--signing-key", default=str(default_signing_key()), help="Private signing key path. Default: ~/.rank3/private_key.pem")
    parser.add_argument("--continue-on-failure", action="store_true", help="Continue running later overlays after a failure")
    parser.add_argument("--debug", action="store_true", help="Explicitly enable run-debugging instrumentation for each overlay in the suite")
    parser.add_argument("--debug-depth", type=int, default=1, help="Rank-3 association neighborhood depth for --debug. Default: 1")
    parser.add_argument("--debug-max-points", type=int, default=256, help="Maximum debug neighborhood points for --debug. Default: 256")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress messages; final JSON report is still printed")
    parser.add_argument("--case", action="append", default=[], help="Exact overlay case stem to run; may be repeated")
    parser.add_argument("--case-glob", action="append", default=[], help="fnmatch-style overlay stem pattern to run; may be repeated")
    parser.add_argument("--init-min-cycles", type=int, default=None, help="Override initialization settling min_cycles")
    parser.add_argument("--init-max-cycles", type=int, default=None, help="Override initialization settling max_cycles")
    parser.add_argument("--init-recurrence-period-min", type=int, default=None, help="Override initialization settling recurrence_period_min")
    parser.add_argument("--init-recurrence-period-max", type=int, default=None, help="Override initialization settling recurrence_period_max")
    parser.add_argument("--init-consecutive-stable-cycles", type=int, default=None, help="Override initialization settling consecutive stable cycles")
    parser.add_argument("--init-tol-rms", type=float, default=None, help="Override initialization settling RMS tolerance")
    parser.add_argument("--init-tol-q95", type=float, default=None, help="Override initialization settling q95 tolerance")
    parser.add_argument("--init-tol-max", type=float, default=None, help="Override initialization settling max tolerance")
    parser.add_argument("--init-tol-sign", type=float, default=None, help="Override initialization settling sign-change tolerance")
    parser.add_argument("--init-progress", action="store_true", help="Print progress from initialization-settling cycles")
    parser.add_argument("--init-progress-interval", type=int, default=None, help="Initialization progress interval in completed rank-3 cycles")
    args = parser.parse_args(argv)
    settling_overrides = build_settling_overrides(
        init_min_cycles=args.init_min_cycles,
        init_max_cycles=args.init_max_cycles,
        init_recurrence_period_min=args.init_recurrence_period_min,
        init_recurrence_period_max=args.init_recurrence_period_max,
        init_consecutive_stable_cycles=args.init_consecutive_stable_cycles,
        init_tol_rms=args.init_tol_rms,
        init_tol_q95=args.init_tol_q95,
        init_tol_max=args.init_tol_max,
        init_tol_sign=args.init_tol_sign,
        init_progress_interval=args.init_progress_interval,
    )
    report = run_overlay_suite(
        suite_id=args.suite_id,
        overlays_dir=Path(args.overlays_dir) if args.overlays_dir else None,
        output_root=Path(args.output_root),
        private_key_path=Path(args.signing_key),
        fail_fast=not args.continue_on_failure,
        progress=not args.quiet,
        debug=args.debug,
        debug_depth=args.debug_depth,
        debug_max_points=args.debug_max_points,
        case_ids=tuple(args.case),
        case_globs=tuple(args.case_glob),
        settling_overrides=settling_overrides or None,
        initialization_progress=args.init_progress,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.failed_count == 0 and report.passed_count == report.overlay_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
