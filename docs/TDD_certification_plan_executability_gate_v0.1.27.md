# TDD: Certification Plan Executability Gate v0.1.27

## Purpose

v0.1.27 separates two statuses that v0.1.26 allowed to collapse:

1. **Structural validity**: the plan JSON is well-formed, approved, contract-bound, and hash-consistent.
2. **Certification executability**: the approved plan contains at least one case that is eligible to execute under the certification contract.

A plan with zero certification-eligible cases may be useful as an audit artifact, but it is not an executable certification plan.

## Required behavior

For `--mode certification`, `rank3-run-suite` must refuse before release-guard access and before per-case staging when the approved plan is not certification-executable.

A certification plan is non-executable if:

- it selects zero cases;
- it has zero certification-eligible cases;
- all selected cases are blocked by contract compliance before SOO/model execution.

## Artifacts

`MODELING_PLAN_VALIDATION_REPORT.json` now includes:

- `structurally_valid`
- `plan_certification_executable`
- `execution_blocking_violations`
- `passed`

For certification execution, `passed` is true only when both structural validity and certification executability are true.

## Evidential rule

A structurally valid but non-executable plan is not a certification run. It is an audit/planning result only.

