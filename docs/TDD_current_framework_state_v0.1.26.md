# Current Framework State v0.1.26

v0.1.26 adds a required pre-run modeling-plan approval layer for certification
mode.

## Certification boundary

The framework-use modes remain:

1. exploratory modeling mode;
2. certification/admission modeling mode.

Any run without a `modeling_intent` contract is exploratory by default. Any
certification run now also requires an approved modeling plan generated from the
contract and selected overlays.

## What v0.1.26 fixes

- A modeling chat can generate the concrete overlay/run plan for user approval
  before model execution.
- The approved plan is hash-bound to the contract and overlay files.
- Certification execution refuses to start without `--approved-plan`.
- Certification execution refuses run-time overrides not represented in the
  approved plan.
- Result packages include the plan and plan-validation report.

## What v0.1.26 does not certify

This release does not certify the charge path-adjustment theorem. It only adds
the planning/approval enforcement needed before a future certification attempt.

Current built-in charge role/path overlays remain candidate overlays unless a
contract-compliant plan and overlays make them certification eligible.
