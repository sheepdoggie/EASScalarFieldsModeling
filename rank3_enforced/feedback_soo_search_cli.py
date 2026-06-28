from __future__ import annotations

import argparse
import json
from pathlib import Path

from .feedback_soo_search import run_feedback_soo_search


def _parse_k_grid(text: str) -> tuple[float, ...]:
    vals = []
    for part in str(text).replace(";", ",").split(","):
        stripped = part.strip()
        if stripped:
            vals.append(float(stripped))
    if not vals:
        raise argparse.ArgumentTypeError("k grid must contain at least one number")
    return tuple(vals)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SOO-only constrained feedback stiffness search with K_theta = k_theta I."
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--path-length", type=int, default=31)
    parser.add_argument("--orientation", choices=("same", "opposite"), default="same")
    parser.add_argument("--epsilon", type=float, default=0.1)
    parser.add_argument("--period-max", type=int, default=512)
    parser.add_argument("--exact-tolerance", type=float, default=1.0e-9)
    parser.add_argument(
        "--k-grid",
        type=_parse_k_grid,
        default=(0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0),
        help="Comma-separated candidate k values. Default: 0.01,0.03,0.1,0.3,1,3,10,30,100,300",
    )
    parser.add_argument("--grid-mode", choices=("tied", "cartesian"), default="tied")
    parser.add_argument("--max-cartesian-candidates", type=int, default=1000)
    parser.add_argument("--no-spectrum-rows", action="store_true")
    parser.add_argument("--no-recurrence-rows", action="store_true")
    args = parser.parse_args()

    report = run_feedback_soo_search(
        output_dir=Path(args.output_dir),
        path_length=args.path_length,
        orientation=args.orientation,
        epsilon=args.epsilon,
        period_max=args.period_max,
        exact_tolerance=args.exact_tolerance,
        k_grid=args.k_grid,
        grid_mode=args.grid_mode,
        max_cartesian_candidates=args.max_cartesian_candidates,
        emit_spectrum_rows=not args.no_spectrum_rows,
        emit_recurrence_rows=not args.no_recurrence_rows,
    )
    print(json.dumps({
        "output_dir": str(Path(args.output_dir).resolve()),
        "report_hash": report.fingerprint(),
        "candidates_tested": report.candidates_tested,
        "candidates_spectral_radius_lt_one": report.candidates_spectral_radius_lt_one,
        "candidates_spectral_radius_near_one": report.candidates_spectral_radius_near_one,
        "candidates_spectral_radius_gt_one": report.candidates_spectral_radius_gt_one,
        "best_full_current_k": [
            report.best_by_full_current_residual["k0"],
            report.best_by_full_current_residual["k1"],
            report.best_by_full_current_residual["k2"],
        ],
        "best_full_current_period": report.best_by_full_current_residual["best_full_current_period"],
        "best_full_current_max_abs_residual": report.best_by_full_current_residual["best_full_current_max_abs_residual"],
        "best_witness_current_k": [
            report.best_by_witness_current_residual["k0"],
            report.best_by_witness_current_residual["k1"],
            report.best_by_witness_current_residual["k2"],
        ],
        "best_witness_current_period": report.best_by_witness_current_residual["best_witness_current_period"],
        "best_witness_current_max_abs_residual": report.best_by_witness_current_residual["best_witness_current_max_abs_residual"],
        "leakage_flags": report.leakage_flags,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
