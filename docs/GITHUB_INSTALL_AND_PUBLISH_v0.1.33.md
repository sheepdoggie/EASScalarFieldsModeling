# GitHub install and publish notes for v0.1.33

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files
unzip EASScalarFieldsModeling_v0.1.33_github_package.zip
cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main
rsync -a --delete --exclude='.git' ../EASScalarFieldsModeling_v0.1.33_github_package/ ./
python -m pip install -e .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q $(find tests -maxdepth 1 -type f | grep -v test_support_two_ledger_charge_modules.py)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_support_two_ledger_charge_modules.py
rank3-check-release-identity --repo-root . --manifest releases/current/FRAMEWORK_RELEASE_MANIFEST.json --framework-zip releases/current/enforceable_rank3_modeling_v0.1.33_admission_control_materials.zip --framework-tar-gz releases/current/enforceable_rank3_modeling_v0.1.33_admission_control_materials.tar.gz
git add .
git commit -m "Package GitHub-installable framework v0.1.33"
git push origin main
git tag -a v0.1.33 -m "v0.1.33 admission/control materials"
git push origin v0.1.33
```

The package includes a generated release public key and signature for self-consistency. For a trusted repository release, re-sign with your own private key before publication.
