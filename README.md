# EASScalarFieldsModeling

Current framework release: `0.1.27` / `0.1.27-certification-plan-executability`.

v0.1.27 adds a certification-plan executability gate above the v0.1.27 pre-run modeling-plan approval layer. The modeling_intent contract remains the controlling scientific authority; the modeling plan is the concrete executable run plan proposed under that contract and approved before model execution.

## Install

```bash
python -m pip install --force-reinstall \
  "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.27#egg=enforceable-rank3-modeling"
```

## Framework-use modes

Exploratory mode is the default. It may run candidate mechanisms and diagnostics but is non-certifying.

Certification mode requires:

```text
--modeling-intent-contract <contract.json>
--approved-plan <approved_plan.json>
```

No certification-mode SOO/model execution begins without a valid approved modeling plan whose contract and overlay hashes match and that contains at least one certification-eligible executable case.

## Pre-run planning workflow

```bash
cd ~/Projects/EAS_runs

rank3-write-modeling-intent-template \
  --output overlays/charge_path_adjustment_contract.json

rank3-plan-from-modeling-intent \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --output-plan plans/charge_path_draft_plan_v0127.json \
  --output-overlays overlays/planned_charge_path_v0127

rank3-approve-modeling-plan \
  --plan plans/charge_path_draft_plan_v0127.json \
  --output plans/charge_path_approved_plan_v0127.json \
  --approved-by Michael

rank3-validate-modeling-plan \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --plan plans/charge_path_approved_plan_v0127.json \
  --require-approved
```

Only after approval and validation as certification-executable:

```bash
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract.json \
  --approved-plan plans/charge_path_approved_plan_v0127.json \
  --output-root results/charge_path_certification_v0127 \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

## Run workspace

Use separate subtrees:

```text
~/Projects/EASScalarFieldsModeling_github_files/
    EASScalarFieldsModeling_publish/
    packages/

~/Projects/EAS_runs/
    overlays/
    plans/
    results/
    logs/
    workspaces/
```

Initialize with:

```bash
rank3-init-workspace --separate-subtrees --project-root ~/Projects
```

## External path monitor boundary

Path add/remove is not EAS ontology and not an intrinsic framework rule. Path edits can only enter through an external exploratory monitor request that the framework validates, applies transactionally, and logs.

## Certification status of current charge role/path suite

`charge_role_path_remap_dynamic_path_v0_1` remains a candidate suite unless a supplied modeling_intent contract and approved plan make a selected overlay set certification eligible. Candidate overlays must not be used as certified support for the charge path-adjustment theorem.
