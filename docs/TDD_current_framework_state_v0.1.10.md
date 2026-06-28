# Technical Design Document: Current Framework State v0.1.10

## Release identity

- Framework version: `0.1.10`
- Release label: `0.1.10-soo-debug-pair-analysis`
- Primary purpose of this revision: provide a targeted SOO-debug workflow for one same-orientation and one opposite-orientation charge run, with explicit initialization/measurement accounting.

## Design correction

The framework must not treat path-facing points as a special SOO update domain. Path-facing means only that a rank-3 association slot lies on the declared diagnostic path. The debug system therefore instruments a path neighborhood but does not seed path-carrier scalar values, preserve path points, alter stiffness, or alter the SOO equation.

## New operational need

Full 34-case charge suites are too large for first-line SOO diagnostics. The framework now supports a focused run:

```bash
rank3-run-soo-debug-pair \
  --path-length 31 \
  --output-root runs/soo_debug_L31 \
  --signing-key ~/.rank3/private_key.pem \
  --debug-depth 1 \
  --debug-max-points 256
```

This runs only:

- `L31_same_association_indexed_soo`
- `L31_opposite_association_indexed_soo`

and then analyzes the resulting path-neighborhood SOO debug records.

## New modules

### `rank3_enforced/soo_debug_analysis.py`

Reads two signed debug run directories and emits:

- `SOO_DEBUG_PAIR_ANALYSIS.json`
- `soo_path_transition_rows.csv`
- `soo_path_layer_summaries.csv`

The report explicitly distinguishes:

- initialization mode,
- initialization cycles,
- initialization SOO steps,
- measurement layer count,
- measurement SOO step count,
- full rank-3 cycles counted after initialization.

### `rank3_enforced/soo_debug_analysis_cli.py`

Console entry point:

```bash
rank3-analyze-soo-debug-pair \
  --same-run-dir <same_run> \
  --opposite-run-dir <opposite_run> \
  --output-dir <analysis_output>
```

### `rank3_enforced/soo_debug_pair_cli.py`

Console entry point:

```bash
rank3-run-soo-debug-pair --path-length L --output-root <out> --signing-key <key>
```

It runs the same/opposite pair with debug instrumentation enabled and immediately invokes the analyzer.

## Run-manager additions

`rank3-run-suite` now accepts exact and glob case filtering:

```bash
--case L31_same_association_indexed_soo
--case L31_opposite_association_indexed_soo
--case-glob 'L31_*'
```

This avoids copying overlays or constructing ad hoc run loops.

## Initialization accounting

The support-seeded two-ledger initializer remains the current charge initializer:

```text
Phi_prev = declared_initial_phi
Phi_curr = declared_initial_phi + sealed support source
Pi_A_curr = Phi_curr - A_theta_curr Phi_prev
```

For the current built-in charge overlays:

```text
initialization.mode = support_seeded_two_ledger
initialization_cycles = 0
measurement_starts_after_initialization = true
```

Therefore, when a 100-layer measurement run reports:

```text
SOO execution steps = 99
full rank-3 cycles = 33
```

those are measurement-run counts after the initialization epoch. They do not include initialization SOO cycles, because the current two-ledger initializer uses zero initialization cycles.

## Debug-data interpretation

The SOO debug pair analysis is instrumentation only. It is not a charge theorem certification and not an admission verdict. Its forbidden interpretations are:

- debug neighborhood as special SOO update domain,
- nonzero scalar value as required for path participation,
- debug output as path-adjustment certification.

## Current limitations

- The SOO stiffness feedback module remains a placeholder/diagnostic handle.
- The charge attraction/repulsion theorem remains uncertified.
- A Delta-L claim still requires relational path-record accommodation; scalar center-zero alone is insufficient.
- The current association remap rule is still identity in the built-in charge overlays, so no declared path-length change should be expected from the current candidate suite.

## Validation target

A correct targeted SOO debug run should produce, for both same and opposite cases:

- signed evidence package,
- `INITIAL_TWO_LEDGER_REPORT.json`,
- `initialization_report.json`,
- `SOO_EXECUTION_REPORT.json`,
- `RUN_DEBUG_REPORT.json`,
- `PATH_FACING_ASSOCIATION_REPORT.json`,
- `PATH_CONSTRUCTION_REPORT.json`,
- pair-level `SOO_DEBUG_PAIR_ANALYSIS.json`.
