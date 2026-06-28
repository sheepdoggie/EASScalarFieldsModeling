from __future__ import annotations

import argparse
import json
from pathlib import Path

from .run_manager import build_settling_overrides, default_signing_key, run_overlay_suite

SUITE_ID = "charge_same_opposite_association_indexed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly one same-orientation and one opposite-orientation charge overlay "
            "as an initialization-settling diagnostic. Measurement is reduced to one layer; "
            "the target artifact is INITIALIZATION_SETTLING_REPORT.json."
        )
    )
    parser.add_argument("--path-length", type=int, required=True, help="Declared path length L to debug, e.g. 31")
    parser.add_argument("--output-root", required=True, help="Output root for the two signed initialization-debug runs")
    parser.add_argument("--signing-key", default=str(default_signing_key()), help="Private signing key path. Default: ~/.rank3/private_key.pem")
    parser.add_argument("--init-min-cycles", type=int, default=10, help="Initialization settling min_cycles. Default: 10")
    parser.add_argument("--init-max-cycles", type=int, default=100, help="Initialization settling max_cycles. Default: 100")
    parser.add_argument("--init-recurrence-period-min", type=int, default=1, help="Initialization settling recurrence_period_min. Default: 1")
    parser.add_argument("--init-recurrence-period-max", type=int, default=12, help="Initialization settling recurrence_period_max. Default: 12")
    parser.add_argument("--init-consecutive-stable-cycles", type=int, default=3, help="Consecutive stable cycles required. Default: 3")
    parser.add_argument("--init-tol-rms", type=float, default=None, help="Override initialization settling RMS tolerance")
    parser.add_argument("--init-tol-q95", type=float, default=None, help="Override initialization settling q95 tolerance")
    parser.add_argument("--init-tol-max", type=float, default=None, help="Override initialization settling max tolerance")
    parser.add_argument("--init-tol-sign", type=float, default=None, help="Override initialization settling sign-change tolerance")
    parser.add_argument("--init-progress-interval", type=int, default=10, help="Progress interval in completed rank-3 cycles. Default: 10")
    parser.add_argument("--continue-on-failure", action="store_true", default=True, help="Continue so both same/opposite reports are produced")
    args = parser.parse_args(argv)

    L = int(args.path_length)
    cases = (
        f"L{L}_same_association_indexed_soo",
        f"L{L}_opposite_association_indexed_soo",
    )
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
        output_root=Path(args.output_root),
        private_key_path=Path(args.signing_key),
        fail_fast=False,
        progress=True,
        debug=False,
        case_ids=cases,
        settling_overrides=settling_overrides,
        # Reduce measurement to no measurement transitions. The initialization
        # epoch still runs whole-field SOO through the configured settling scan.
        execution_overrides={"n_layers": 1},
        initialization_progress=True,
        required_artifacts=(
            "CERTIFICATE.json",
            "EVIDENCE_ENVELOPE.json",
            "INITIAL_TWO_LEDGER_REPORT.json",
            "INITIALIZATION_SETTLING_REPORT.json",
        ),
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.overlay_count == 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
