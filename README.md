# EASScalarFieldsModeling

Current framework release: `0.1.26` / `0.1.26-modeling-plan-approval`.

v0.1.26 adds a mandatory pre-run modeling-plan approval layer for certification mode. The modeling_intent contract remains the controlling scientific authority; the modeling plan is the concrete executable run plan proposed under that contract and approved before model execution.

## Install

```bash
python -m pip install --force-reinstall \
  "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.26#egg=enforceable-rank3-modeling"
```

## Framework-use modes

Exploratory mode is the default. It may run candidate mechanisms and diagnostics but is non-certifying.

Certification mode requires:

```text
--modeling-intent-contract <contract.json>
--approved-plan <approved_plan.json>
```

No certification-mode SOO/model execution begins without a valid approved modeling plan whose contract and overlay hashes match.

## Pre-run planning workflow

```bash
cd ~/Projects/EAS_runs

rank3-write-modeling-intent-template \
  --output overlays/charge_path_adjustment_contract.json

rank3-plan-from-modeling-intent \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --output-plan plans/charge_path_draft_plan_v0126.json \
  --output-overlays overlays/planned_charge_path_v0126

rank3-approve-modeling-plan \
  --plan plans/charge_path_draft_plan_v0126.json \
  --output plans/charge_path_approved_plan_v0126.json \
  --approved-by Michael

rank3-validate-modeling-plan \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --plan plans/charge_path_approved_plan_v0126.json \
  --require-approved
```

Only after approval:

```bash
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract.json \
  --approved-plan plans/charge_path_approved_plan_v0126.json \
  --output-root results/charge_path_certification_v0126 \
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
