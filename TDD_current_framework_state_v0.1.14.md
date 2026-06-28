# Current Framework State v0.1.14 — Direct Recurrent Initialization Solver

Version `0.1.14` adds a SOO-only direct recurrent initialization solver for testing interpolated initialization profiles without treating forward SOO as a relaxation procedure.

## Added command

```bash
rank3-run-direct-recurrent-initialization \
  --output-dir runs/direct_recurrent_L31_same \
  --path-length 31 \
  --orientation same \
  --epsilon 0.1 \
  --stiffness-lambda 1.0 \
  --period-max 128
```

## Ontological guardrails

The interpolated profile is an initialization-profile hypothesis only. It does not alter SOO, does not preserve path points, and does not give path-facing points special update rules.

The solver tests finite-cycle recurrence by solving

```text
(F_cyc^P - I) v = 0
```

for the two-ledger state vector `v = (Phi_curr, Phi_prev)` subject to declared profile constraints.

## Profile hypothesis

The default profile follows the user's proposed test:

- support boundary values have absolute value 1;
- dressing values have absolute value 0.5 and opposite boundary sign;
- path values interpolate to zero at the center between two supports;
- beside-path exterior points are assigned one-half the adjacent path value.

## Solve policies

The command reports:

- `current_profile_only`: constrain only `Phi_curr` to the interpolated profile while solving for `Phi_prev`;
- `both_ledgers_profile`: constrain both ledgers to the interpolated profile;
- full-state residuals;
- witness-only residuals for diagnostics only.

Witness-only recurrence is not admission-grade by itself.

## Additional phase-consistent ledger test

The command also tests

```text
Phi_prev = cos(omega) * Phi_curr
```

where `cos(omega) = (2 - epsilon^2 lambda) / 2`. This suppresses artificial tenfold oscillator-amplitude inflation from `Phi_prev=0`, but it remains conservative/oscillatory.

## Emitted artifacts

- `DIRECT_RECURRENT_INITIALIZATION_REPORT.json`
- `interpolated_profile_rows.csv`
- `direct_recurrent_solve_rows.csv`
- `phase_consistent_layer_rows.csv`
- `phase_consistent_point_rows.csv`
