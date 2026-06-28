# GitHub install and publish instructions for v0.1.25

## Publish/update repository

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files

unzip EASScalarFieldsModeling_v0.1.25_github_package.zip

cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main

rsync -a --delete --exclude='.git' \
  ../EASScalarFieldsModeling_v0.1.25_github_package/ \
  ./

python -m pip install -e .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q $(find tests -maxdepth 1 -type f | grep -v test_support_two_ledger_charge_modules.py)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_support_two_ledger_charge_modules.py

git status --short
git add .
git commit -m "Package GitHub-installable framework v0.1.25"
git push origin main

git tag -a v0.1.25 -m "v0.1.25 contract propagation and offline guard"
git push origin v0.1.25
```

## Sign release manifest

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
  releases/current/enforceable_rank3_modeling_v0.1.25_contract_propagation_offline_guard.zip
```

Then:

```bash
git add releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem
git add releases/current/FRAMEWORK_RELEASE_MANIFEST.sig
git add releases/current/FRAMEWORK_RELEASE_MANIFEST.json
git add releases/current/SHA256SUMS.txt
git add releases/current/enforceable_rank3_modeling_v0.1.25_contract_propagation_offline_guard.zip
git add releases/current/enforceable_rank3_modeling_v0.1.25_contract_propagation_offline_guard.tar.gz

git commit -m "Sign v0.1.25 release manifest"
git push origin main
```

## Install after publishing

```bash
python -m pip install --force-reinstall \
  "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.25#egg=enforceable-rank3-modeling"
```

## Run with local/offline release guard

```bash
cd ~/Projects/EAS_runs

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
