# Current Framework State v0.1.27

Release label: `0.1.27-certification-plan-executability`

v0.1.27 adds a certification-plan executability gate above release-guard access and above model execution.

## Main correction

v0.1.26 could validate an approved plan as structurally valid even when every planned case was contract-blocked and zero cases were certification-eligible. v0.1.27 preserves that structural status but refuses to treat such a plan as certification-executable.

## New fields

`MODELING_PLAN.json` includes:

- `plan_certification_executable`
- `execution_blocking_reasons`

`MODELING_PLAN_VALIDATION_REPORT.json` includes:

- `structurally_valid`
- `plan_certification_executable`
- `execution_blocking_violations`

## Certification-mode execution

Certification execution requires:

- supplied modeling intent contract;
- approved modeling plan;
- plan hash and overlay hashes consistent;
- `plan_certification_executable = true`;
- at least one certification-eligible case.

If these checks fail, the runner writes the plan and validation report, then stops before release-guard/network access and before SOO/model execution.

## Status of charge path-adjustment theorem

This framework release does not certify the theorem. Candidate overlays remain non-certifying unless they satisfy the approved modeling-intent contract.

