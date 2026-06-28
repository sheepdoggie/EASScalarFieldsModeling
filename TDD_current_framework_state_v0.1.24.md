# Current framework state v0.1.24

v0.1.24 adds the modeling-intent contract layer.

## New capabilities

- `modeling_intent_contract_layer_v0_1`
- `exploratory_modeling_mode`
- `certification_admission_modeling_mode`
- `modeling_intent_compliance_report`
- `modeling_intent_contract_cli`
- `certification_requires_predeclared_contract`
- `exploratory_default_without_contract`
- `contract_bound_run_manager_staging`

## Operational rule

Runs without a contract are exploratory by default. Certification/admission requires a pre-run contract and a passing compliance report.

## Important non-change

Path add/remove remains external-monitor-requested and is not an EAS ontology rule or intrinsic framework mechanism.

## Status

v0.1.24 improves evidential hygiene. It does not certify the charge path-adjustment theorem.
