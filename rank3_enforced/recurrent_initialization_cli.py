from __future__ import annotations

import argparse
import json
from pathlib import Path

from .recurrent_initialization_solver import run_direct_recurrent_initialization


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve/test interpolated profile as a direct recurrent SOO two-ledger initialization.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--path-length", type=int, default=31)
    parser.add_argument("--orientation", choices=("same", "opposite"), default="same")
    parser.add_argument("--epsilon", type=float, default=0.1)
    parser.add_argument("--stiffness-lambda", type=float, default=1.0)
    parser.add_argument("--period-max", type=int, default=128)
    parser.add_argument("--exact-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--phase-consistent-steps", type=int, default=600)
    args = parser.parse_args()

    report = run_direct_recurrent_initialization(
        output_dir=Path(args.output_dir),
        path_length=args.path_length,
        orientation=args.orientation,
        epsilon=args.epsilon,
        stiffness_lambda=args.stiffness_lambda,
        period_max=args.period_max,
        exact_tolerance=args.exact_tolerance,
        phase_consistent_steps=args.phase_consistent_steps,
    )
    print(json.dumps({
        "output_dir": str(Path(args.output_dir).resolve()),
        "report_hash": report.fingerprint(),
        "exact_full_recurrent_profile_found": report.exact_full_recurrent_profile_found,
        "exact_witness_recurrent_profile_found": report.exact_witness_recurrent_profile_found,
        "best_full_current_period": report.best_full_current_only.period_cycles,
        "best_full_current_max_abs_residual": report.best_full_current_only.full_max_abs_residual,
        "best_witness_current_period": report.best_witness_current_only.period_cycles,
        "best_witness_current_max_abs_residual": report.best_witness_current_only.witness_max_abs_residual,
        "phase_consistent_growth_factor": report.phase_consistent_ledger.growth_factor_over_initial,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
