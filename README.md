# Enforceable Rank-3 Scalar Field Modeling Framework

Current release: `0.1.6-support-seeded-two-ledger-charge-modules`

This framework is a locked, declarative modeling harness for EAS rank-3 scalar-field diagnostics. It is designed to prevent model-specific Python overlays, post-hoc readout selection, and residual-update recipes from being treated as admitted SOO dynamics.

## Current core capabilities

- Declarative overlays only.
- Signed evidence packages.
- GitHub signed-release guard with run-environment cache.
- Association-indexed second-order SOO primitive: `association_indexed_soo_v1`.
- Phase-indexed stiffness reports with default `K0=K1=K2=I` when feedback is not under test.
- Stiffness-feedback diagnostic placeholder reports.
- Support-seeded two-ledger initialization.
- Optional/experimental module declarations.
- Charge attraction/repulsion candidate module.
- Gravitation path candidate module placeholder.
- Explicit permutation-safe path construction `linear_support_path_v0_2`.
- Relation-complete charge packet readouts.
- Common-mode/zero-sum packet readouts.
- Rebuilt charge same/opposite overlays for L16-L32.

## Important status warning

The framework is infrastructure. It does not certify charge attraction/repulsion, gravitation, or stiffness feedback. The current SOO-stiffness feedback module is a placeholder diagnostic handle. Final closure rules and admission gates remain future work.

## Main overlay directories

```text
overlays/minimal_association_indexed_soo_feedback_overlay.json
overlays/charge_same_opposite_association_indexed/*.json
```

## Running one overlay

```bash
python run_signed_declarative_overlay.py \
  overlays/charge_same_opposite_association_indexed/L16_same_association_indexed_soo.json \
  runs/L16_same \
  ~/.rank3/signing_private.pem
```

If your signing key uses the older filename, use:

```bash
~/.rank3/private_key.pem
```

## Expected artifacts for association-indexed SOO runs

```text
SOO_EXECUTION_REPORT.json
CYCLIC_RETURN_REPORT.json
STIFFNESS_INPUT_REPORT.json
RESPONSE_BURDEN_REPORT.json
INDUCED_STIFFNESS_REPORT.json
STIFFNESS_CLOSURE_REPORT.json
STIFFNESS_FEEDBACK_REPORT.json
INITIAL_TWO_LEDGER_REPORT.json
OPTIONAL_MODULE_REPORT.json
SOO_FUNCTIONAL_REPORT.json
BASE_GATE_REPORT.json
CERTIFICATE.json
EVIDENCE_ENVELOPE.json
```

## Current tests

```bash
pytest -q
```

Expected:

```text
27 passed
```

## Technical Design Documents

```text
TDD_current_framework_state_v0.1.6.md
TDD_association_indexed_SOO_feedback_core.md
TDD_support_seeded_initialization.md
TDD_locked_explicit_path_readouts.md
TDD_signed_release_guard.md
```
