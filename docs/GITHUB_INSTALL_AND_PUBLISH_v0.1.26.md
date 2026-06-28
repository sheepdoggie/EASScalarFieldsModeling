# GitHub Install and Publish: v0.1.26

## Publish

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files
unzip EASScalarFieldsModeling_v0.1.26_github_package.zip

cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main

rsync -a --delete --exclude='.git' \
  ../EASScalarFieldsModeling_v0.1.26_github_package/ \
  ./

python -m pip install -e .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q $(find tests -maxdepth 1 -type f | grep -v test_support_two_ledger_charge_modules.py)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_support_two_ledger_charge_modules.py

git add .
git commit -m "Package GitHub-installable framework v0.1.26"
git push origin main

git tag -a v0.1.26 -m "v0.1.26 modeling plan approval layer"
git push origin v0.1.26
```

## Sign

```bash
openssl pkey \
  -in ~/.rank3/signing_private.pem \
  -pubout \
  -out releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem

python tools/sign_release_manifest.py \
  releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  ~/.rank3/signing_private.pem \
  releases/current/FRAMEWORK_RELEASE_MANIFEST.sig

python tools/verify_release_manifest.py \
  releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  releases/current/FRAMEWORK_RELEASE_MANIFEST.sig \
  releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem \
  releases/current/enforceable_rank3_modeling_v0.1.26_modeling_plan_approval.zip
```

## Run from EAS_runs

```bash
cd ~/Projects/EAS_runs

rank3-plan-from-modeling-intent \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --output-plan plans/charge_path_draft_plan_v0126.json \
  --output-overlays overlays/planned_charge_path_v0126

rank3-approve-modeling-plan \
  --plan plans/charge_path_draft_plan_v0126.json \
  --output plans/charge_path_approved_plan_v0126.json \
  --approved-by Michael

rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract.json \
  --approved-plan plans/charge_path_approved_plan_v0126.json \
  --release-manifest ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  --release-signature ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/FRAMEWORK_RELEASE_MANIFEST.sig \
  --release-public-key ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem \
  --framework-zip ~/Projects/EASScalarFieldsModeling_github_files/EASScalarFieldsModeling_publish/releases/current/enforceable_rank3_modeling_v0.1.26_modeling_plan_approval.zip \
  --output-root results/charge_path_certification_v0126 \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```
