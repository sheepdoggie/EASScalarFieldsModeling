# EASScalarFieldsModeling

Current framework release: `0.1.24` / `0.1.24-modeling-intent-contract-layer`.

v0.1.24 adds a modeling-intent contract layer. Runs now have two distinct evidential modes:

1. exploratory modeling mode
2. certification/admission modeling mode

Absent a contract, a run is exploratory by default. Certification/admission requires a pre-run `modeling_intent` contract and emits a `MODELING_INTENT_COMPLIANCE_REPORT.json` in every result package.

Install after publishing:

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.24#egg=enforceable-rank3-modeling"
```

Create a contract template:

```bash
rank3-write-modeling-intent-template --output ~/Projects/EAS_runs/overlays/charge_path_adjustment_contract_v0124.json
```

Run exploratory mode:

```bash
cd ~/Projects/EAS_runs
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 --mode exploratory --output-root results/charge_role_path_v0124_exploratory --signing-key ~/.rank3/private_key.pem --continue-on-failure
```

Run certification mode:

```bash
cd ~/Projects/EAS_runs
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 --mode certification --modeling-intent-contract overlays/charge_path_adjustment_contract_v0124.json --output-root results/charge_path_certification_v0124 --signing-key ~/.rank3/private_key.pem --continue-on-failure
```

Path add/remove remains external-monitor-requested and is not an EAS ontology rule or intrinsic framework rule.
