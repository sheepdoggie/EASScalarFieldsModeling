# Current Framework State v0.1.13 — SOO Validation Controls

Version `0.1.13` adds a SOO-only validation workflow. It does not attempt to certify charge attraction/repulsion. Its purpose is to answer whether the association-indexed SOO operator behaves like the expected second-order recurrence, whether the observed scalar growth is the predicted conservative oscillator amplitude, whether the rank-3 cyclic return map is neutral or settling, and whether a recurrent two-ledger state can be solved directly under support constraints.

## Added module

```text
rank3_enforced/soo_validation.py
rank3_enforced/soo_validation_cli.py
```

## Added command

```text
rank3-run-soo-validation
```

Example:

```bash
rank3-run-soo-validation \
  --output-dir runs/soo_validation_L31 \
  --path-length 31 \
  --orientation same \
  --epsilon 0.1 \
  --stiffness-lambda 1.0 \
  --period-max 12 \
  --comparison-steps 200
```

## Emitted artifacts

```text
SOO_VALIDATION_REPORT.json
identity_recurrence_sequence.csv
cyclic_return_eigenvalues.csv
recurrent_solve_rows.csv
README.md
```

## Validation questions answered

1. Identity-association recurrence check:
   
   \[
   x_{\ell+1}=(2-\epsilon^2K)x_\ell-x_{\ell-1}.
   \]

2. Analytic oscillator amplitude check for `epsilon=0.1`, `K=1`, `x_prev=0`, `x_curr=1`.

3. Rank-3 cyclic return spectrum for the selected built-in path association state.

4. Direct recurrent two-ledger solve over periods 1..P:

   \[
   F_{\mathrm{cyc},A}^{P}(\Phi_\ell,\Phi_{\ell-1})=(\Phi_\ell,\Phi_{\ell-1})
   \]

   under multiple support-constraint profiles.

## Guardrails

The workflow is diagnostic only. It does not alter SOO, association geometry, initialization, support records, or charge readouts. Witness-only recurrent solves are reported separately from full-state recurrent solves and are not sufficient to certify a measurement initial state.

## New capabilities

```text
soo_validation_controls
identity_recurrence_validation
analytic_oscillator_amplitude_validation
cyclic_return_spectrum_validation
recurrent_two_ledger_solve_validation
```
