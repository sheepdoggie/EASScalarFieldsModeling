# GitHub install and publish instructions for v0.1.24

## Publish

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files
unzip EASScalarFieldsModeling_v0.1.24_github_package.zip
cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main
rsync -a --delete --exclude='.git' ../EASScalarFieldsModeling_v0.1.24_github_package/ ./
python -m pip install -e .
pytest -q
git add .
git commit -m "Package GitHub-installable framework v0.1.24"
git push origin main
git tag -a v0.1.24 -m "v0.1.24 modeling intent contract layer"
git push origin v0.1.24
```

## Install

```bash
python -m pip install --force-reinstall "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.24#egg=enforceable-rank3-modeling"
```

## Write a certification contract template

```bash
rank3-write-modeling-intent-template --output ~/Projects/EAS_runs/overlays/charge_path_adjustment_contract_v0124.json
```

## Exploratory run

```bash
cd ~/Projects/EAS_runs
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode exploratory \
  --output-root results/charge_role_path_v0124_exploratory \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

## Certification-mode run

```bash
cd ~/Projects/EAS_runs
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract_v0124.json \
  --output-root results/charge_path_certification_v0124 \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

Certification mode will fail or mark cases non-certifying if the contract requirements are not met.
