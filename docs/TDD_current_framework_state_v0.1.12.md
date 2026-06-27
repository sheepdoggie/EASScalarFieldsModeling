# TDD: Enforceable Rank-3 Modeling Framework v0.1.12

## Release label

`0.1.12-long-initialization-debug-controls`

## Purpose

Version 0.1.12 makes SOO initialization-settling diagnostics the first-class workflow for charge/path runs. The framework now supports long initialization scans, early stop when a witness recurrent/fixed condition is reached, explicit command-line overrides for settling parameters, and progress reporting during initialization cycles.

## Corrected initialization model

A support-seeded two-ledger state is not treated as a settled physical state. For charge/path candidate diagnostics, the framework applies whole-field association-indexed SOO during an initialization epoch and monitors a support-influenced exterior witness set. Measurement is valid only after the witness set reaches a fixed or recurrent condition under the declared criterion.

SOO remains whole-field. The witness set is only a convergence/readout domain. It never alters updates, stiffness, associations, scalar values, or remapping.

## Witness selection

For two or more supports, the default witness scope is the relational path exterior between supports, excluding support-owned points. For one support, the witness scope is the dressing/exterior record. A no-support whole-field fallback is retained only for control-style runs.

## Settling metrics

For each completed rank-3 cycle and each tested recurrence period, the initializer compares same-phase returns over the witness set for both `Phi` and `Pi_A`:

- RMS delta
- q95 absolute delta
- maximum absolute delta
- sign-change fraction
- comparable point count

The initializer accepts either fixed steady state (`period=1`) or recurrent steady state (`period>1`) once the configured number of consecutive stable cycles is reached.

## New behavior in v0.1.12

### Early stop

The initialization scan no longer always runs to `max_cycles`. It runs cycle-by-cycle and stops at the first accepted fixed/recurrent witness state. The report preserves both requested and actual scan lengths.

### Progress reporting

When enabled, initialization prints progress after the first cycle, at configured intervals, at acceptance, and at the final cycle. Progress lines include cycle count, accepted status, recurrence period, best available max deltas, sign-change fraction, and elapsed time.

### CLI overrides

The suite and SOO-debug commands can override initialization settling settings without editing built-in overlays. Overrides are staged into temporary data-only overlays under the run output directory.

Supported override flags include:

- `--init-min-cycles`
- `--init-max-cycles`
- `--init-recurrence-period-min`
- `--init-recurrence-period-max`
- `--init-consecutive-stable-cycles`
- `--init-tol-rms`
- `--init-tol-q95`
- `--init-tol-max`
- `--init-tol-sign`
- `--init-progress`
- `--init-progress-interval`

## New command

`rank3-run-initialization-debug-pair` runs exactly one same-orientation and one opposite-orientation overlay for a chosen path length as an initialization-settling diagnostic. Measurement transitions are reduced to one layer so the target artifacts are initialization reports, not charge theorem readouts.

Example:

```bash
rank3-run-initialization-debug-pair \
  --path-length 31 \
  --output-root runs/init_debug_L31_100cycles \
  --signing-key ~/.rank3/private_key.pem \
  --init-max-cycles 100 \
  --init-min-cycles 10 \
  --init-recurrence-period-max 12 \
  --init-consecutive-stable-cycles 3 \
  --init-progress-interval 10
```

## Main emitted artifact

`INITIALIZATION_SETTLING_REPORT.json` now includes:

- requested scan layers
- actual scan layers
- actual scan cycles
- accepted initialization steps/cycles
- accepted recurrence period
- steady state type
- whether initialization stopped early on steady state
- progress-enabled status
- per-cycle witness statistics
- hashes for the accepted measurement two-ledger state when reached

## Admission rule

If initialization settling is enabled and no steady/recurrent witness state is reached, the run remains a signed diagnostic package but fails the BASE gate. Measurement/theorem interpretation is not admitted.

## Scope limitation

This release does not certify charge attraction/repulsion and does not add a path-remap/accommodation rule. It is specifically for finding SOO conditions that produce a valid settled initialization state and for auditing whether association-indexed SOO behaves according to theory before any charge-path interpretation is attempted.
