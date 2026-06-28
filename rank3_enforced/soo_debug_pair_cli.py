from __future__ import annotations

import argparse
import json
from pathlib import Path

from .run_manager import build_settling_overrides, default_signing_key, run_overlay_suite
from .soo_debug_analysis import analyze_soo_debug_pair

SUITE_ID = "charge_same_opposite_association_indexed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly one same-orientation and one opposite-orientation charge overlay "
            "with SOO path-neighborhood debugging enabled, then analyze the SOO transitions."
        )
    )
    parser.add_argument("--path-length", type=int, required=True, help="Declared path length L to debug, e.g. 16 or 31")
    parser.add_argument("--output-root", required=True, help="Output root for the two signed debug runs and analysis")
    parser.add_argument("--signing-key", default=str(default_signing_key()), help="Private signing key path. Default: ~/.rank3/private_key.pem")
    parser.add_argument("--debug-depth", type=int, default=1, help="Rank-3 association neighborhood depth. Default: 1")
    parser.add_argument("--debug-max-points", type=int, default=256, help="Maximum debug points. Default: 256")
    parser.add_argument("--continue-on-failure", action="store_true", help="Continue if one case fails; analysis still requires both debug reports")
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

    L = int(args.path_length)
    cases = (
        f"L{L}_same_association_indexed_soo",
        f"L{L}_opposite_association_indexed_soo",
    )
    output_root = Path(args.output_root).resolve()
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
        suite_id=SUITE_ID,
        output_root=output_root,
        private_key_path=Path(args.signing_key),
        fail_fast=not args.continue_on_failure,
        progress=True,
        debug=True,
        debug_depth=args.debug_depth,
        debug_max_points=args.debug_max_points,
        case_ids=cases,
        settling_overrides=settling_overrides or None,
        initialization_progress=args.init_progress,
    )
    same_dir = output_root / "runs" / cases[0]
    opposite_dir = output_root / "runs" / cases[1]
    if report.failed_count == 0 and same_dir.is_dir() and opposite_dir.is_dir():
        analysis = analyze_soo_debug_pair(
            same_run_dir=same_dir,
            opposite_run_dir=opposite_dir,
            output_dir=output_root / "SOO_DEBUG_PAIR_ANALYSIS",
        )
        print(json.dumps({"suite_report": report.to_dict(), "analysis_report": analysis.to_dict()}, indent=2, sort_keys=True))
        return 0
    print(json.dumps({"suite_report": report.to_dict(), "analysis_status": "not_run_because_suite_failed"}, indent=2, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
