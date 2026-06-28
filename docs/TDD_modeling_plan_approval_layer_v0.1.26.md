# Technical Design Document: Modeling Plan Approval Layer v0.1.26

## Purpose

v0.1.26 adds a pre-execution planning and approval layer above the existing
`modeling_intent` contract layer. The contract remains the controlling scientific
authority. The modeling plan is the concrete, executable run plan proposed under
that contract.

No certification-mode model execution may begin unless all of the following are
present and valid:

1. a predeclared `modeling_intent` contract;
2. a draft modeling plan generated from that contract and selected overlays;
3. an explicit approved-plan record;
4. a pre-run modeling-plan validation report;
5. matching contract, plan, and overlay hashes.

## Non-ontology status

The modeling plan is not EAS ontology. It does not define SOO, path behavior,
scalar-value behavior, remap behavior, or admission truth. It only records and
binds the proposed executable configuration before execution.

## New CLI commands

```bash
rank3-plan-from-modeling-intent
rank3-approve-modeling-plan
rank3-validate-modeling-plan
```

## Certification execution rule

`rank3-run-suite --mode certification` now requires:

```bash
--modeling-intent-contract <contract.json>
--approved-plan <approved_plan.json>
```

The run manager validates the approved plan before release-guard checking and
before any SOO/model execution. If validation fails, execution stops.

## Generated artifacts

Suite-level artifacts:

```text
MODELING_INTENT_CONTRACT.json
MODELING_INTENT_CONTRACT.sha256
MODELING_PLAN.json
MODELING_PLAN.sha256
MODELING_PLAN_VALIDATION_REPORT.json
SUITE_RUN_REPORT.json
```

Per-case artifacts for pre-run blocked cases:

```text
MODELING_INTENT_CONTRACT.json
MODELING_INTENT_COMPLIANCE_REPORT.json
MODELING_PLAN.json
MODELING_PLAN.sha256
MODELING_PLAN_VALIDATION_REPORT.json
CONTRACT_PROPAGATION_REPORT.json
RUN_CLASSIFICATION.json
RUN_ERROR.txt
```

Per-case artifacts for executed cases additionally include the normal signed
certificate/evidence envelope, and the modeling plan payload is included before
package signing so hashes cover it.

## Security/evidential rules

Certification execution cannot add run-time debug, settling, or execution
overrides outside the approved plan. Such changes require regenerating and
reapproving the plan.

Candidate overlays remain non-certifying unless they satisfy the supplied
contract. The plan may list blocked cases, but those cases must not execute SOO
under certification mode.

## Expected use

```bash
rank3-plan-from-modeling-intent \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --output-plan plans/charge_path_draft_plan.json \
  --output-overlays overlays/planned_charge_path_v001

rank3-approve-modeling-plan \
  --plan plans/charge_path_draft_plan.json \
  --output plans/charge_path_approved_plan.json \
  --approved-by Michael

rank3-validate-modeling-plan \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --plan plans/charge_path_approved_plan.json \
  --require-approved

rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract.json \
  --approved-plan plans/charge_path_approved_plan.json \
  --output-root results/charge_path_certification_v0126
```
