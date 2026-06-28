from __future__ import annotations

import argparse
import json
from pathlib import Path

from .soo_validation import run_soo_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Run association-indexed SOO validation controls.")
    parser.add_argument("--output-dir", required=True, help="Directory for SOO validation artifacts.")
    parser.add_argument("--path-length", type=int, default=31, help="Built-in charge-suite path length for cyclic spectrum/recurrent solve.")
    parser.add_argument("--orientation", choices=("same", "opposite"), default="same")
    parser.add_argument("--epsilon", type=float, default=0.1)
    parser.add_argument("--stiffness-lambda", type=float, default=1.0)
    parser.add_argument("--period-max", type=int, default=12)
    parser.add_argument("--comparison-steps", type=int, default=200)
    args = parser.parse_args()

    report = run_soo_validation(
        output_dir=Path(args.output_dir),
        path_length=args.path_length,
        orientation=args.orientation,
        epsilon=args.epsilon,
        stiffness_lambda=args.stiffness_lambda,
        period_max=args.period_max,
        comparison_steps=args.comparison_steps,
    )
    print(json.dumps({
        "passed_identity_recurrence": report.identity_recurrence.passed,
        "identity_max_abs_error": report.identity_recurrence.max_abs_error,
        "analytic_amplitude": report.identity_recurrence.analytic_amplitude,
        "observed_peak_abs": report.identity_recurrence.observed_peak_abs,
        "cyclic_spectral_radius": report.cyclic_return_spectrum.spectral_radius,
        "cyclic_unit_modulus_count": report.cyclic_return_spectrum.count_modulus_near_one_1e_10,
        "cyclic_dimension": report.cyclic_return_spectrum.state_dimension,
        "support_constrained_exact_full_state_found": report.recurrent_solve.support_constrained_exact_full_state_found,
        "support_constrained_exact_witness_found": report.recurrent_solve.support_constrained_exact_witness_found,
        "output_dir": str(Path(args.output_dir).resolve()),
        "report_hash": report.fingerprint(),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
