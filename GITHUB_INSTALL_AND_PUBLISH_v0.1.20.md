# GitHub install and publish instructions for v0.1.20

Repository: https://github.com/sheepdoggie/EASScalarFieldsModeling

## Publish from a clean directory

```bash
unzip EASScalarFieldsModeling_v0.1.20_github_package.zip
cd EASScalarFieldsModeling_v0.1.20_github_package

python -m pip install -e .
pytest -q

git init
git branch -M main
git remote add origin https://github.com/sheepdoggie/EASScalarFieldsModeling.git
git add .
git commit -m "Package GitHub-installable framework v0.1.20"
git tag -a v0.1.20 -m "v0.1.20 GitHub-installable publication-certified framework"
git push -u origin main
git push origin v0.1.20
```

## Update an existing clone

```bash
git clone https://github.com/sheepdoggie/EASScalarFieldsModeling.git
cd EASScalarFieldsModeling
rsync -a --delete /path/to/EASScalarFieldsModeling_v0.1.20_github_package/ ./
python -m pip install -e .
pytest -q
git add .
git commit -m "Package GitHub-installable framework v0.1.20"
git tag -a v0.1.20 -m "v0.1.20 GitHub-installable publication-certified framework"
git push origin main
git push origin v0.1.20
```

## Install after publishing

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.20#egg=enforceable-rank3-modeling"
```

## Release archive install

```bash
python -m pip install --force-reinstall releases/current/enforceable_rank3_modeling_v0.1.20_publication_certified_run.zip
```

## Sign the release manifest

```bash
python tools/generate_release_key.py releases/current/FRAMEWORK_RELEASE_PRIVATE_KEY.pem releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem
python tools/sign_release_manifest.py releases/current/FRAMEWORK_RELEASE_MANIFEST.json releases/current/FRAMEWORK_RELEASE_PRIVATE_KEY.pem releases/current/FRAMEWORK_RELEASE_MANIFEST.sig
python tools/verify_release_manifest.py releases/current/FRAMEWORK_RELEASE_MANIFEST.json releases/current/FRAMEWORK_RELEASE_MANIFEST.sig releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem releases/current/enforceable_rank3_modeling_v0.1.20_publication_certified_run.zip
```

Do not commit the private key. Move it out of the repository before commit.
