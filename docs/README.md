# EAS Scalar Fields Modeling Framework

Current framework release: `0.1.25` / `0.1.25-contract-propagation-offline-guard`.

## Status

v0.1.25 repairs the modeling-intent contract propagation defect found in v0.1.24.

Key guarantees:

- no contract means exploratory mode by default;
- certification mode requires `--modeling-intent-contract`;
- the supplied contract is injected into each staged overlay;
- certification compliance is checked before model execution;
- rejected certification overlays emit non-modeling rejection artifacts;
- local/offline signed release guard sources are supported.

Path add/remove remains external-monitor-only and is not EAS ontology or an intrinsic framework rule.

## Install from GitHub after publishing

```bash
python -m pip install --force-reinstall \
  "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.25#egg=enforceable-rank3-modeling"
```

## Run from separated run subtree

```bash
cd ~/Projects/EAS_runs

rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode exploratory \
  --output-root results/charge_role_path_v0125_exploratory \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

## Certification mode

```bash
cd ~/Projects/EAS_runs

rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract.json \
  --output-root results/charge_path_certification_v0125 \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

For offline/local release-guard verification:

```bash
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract.json \
  --release-manifest ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  --release-signature ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/FRAMEWORK_RELEASE_MANIFEST.sig \
  --release-public-key ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem \
  --framework-zip ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/enforceable_rank3_modeling_v0.1.25_contract_propagation_offline_guard.zip \
  --output-root results/charge_path_certification_v0125 \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

## Important

This framework package does not certify the charge path-adjustment theorem. It enforces the architecture needed for certification attempts to be auditable and fail-closed.
