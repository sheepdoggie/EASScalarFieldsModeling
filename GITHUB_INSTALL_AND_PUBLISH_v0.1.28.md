# GitHub install and publish: v0.1.28

## Publish source tree

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files
unzip EASScalarFieldsModeling_v0.1.28_github_package.zip
cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main
rsync -a --delete --exclude='.git' \
  ../EASScalarFieldsModeling_v0.1.28_github_package/ \
  ./
python -m pip install -e .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q $(find tests -maxdepth 1 -type f | grep -v test_support_two_ledger_charge_modules.py)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_support_two_ledger_charge_modules.py
rank3-check-release-identity \
  --repo-root . \
  --manifest releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  --framework-zip releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.zip \
  --framework-tar-gz releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.tar.gz
git status --short
git add .
git commit -m "Package GitHub-installable framework v0.1.28"
git push origin main
git tag -a v0.1.28 -m "v0.1.28 release identity self-consistency gate"
git push origin v0.1.28
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
  releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.zip
rank3-check-release-identity \
  --repo-root . \
  --manifest releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  --framework-zip releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.zip \
  --framework-tar-gz releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.tar.gz
```

Never commit the private key.
