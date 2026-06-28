# GitHub install and publish instructions for v0.1.21

Repository: https://github.com/sheepdoggie/EASScalarFieldsModeling

## Update an existing clone

Use this workflow to avoid the non-fast-forward problem. It starts from GitHub's current `main`, then copies the package contents over it.

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files

# Clone or refresh a publish clone.
if [ ! -d EASScalarFieldsModeling_publish/.git ]; then
  git clone https://github.com/sheepdoggie/EASScalarFieldsModeling.git EASScalarFieldsModeling_publish
fi

cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main

# Copy v0.1.21 package contents over the remote-based main.
rsync -a --delete --exclude='.git' \
  ../EASScalarFieldsModeling_v0.1.21_github_package/ \
  ./

python -m pip install -e .
pytest -q

git status --short
git add .
git commit -m "Package GitHub-installable framework v0.1.21"
git push origin main

git tag -a v0.1.21 -m "v0.1.21 role-path remap and dynamic path infrastructure"
git push origin v0.1.21
```

If `git commit` reports `nothing to commit`, check whether the tag already exists:

```bash
git ls-remote --tags origin v0.1.21
```

## Install after publishing

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.21#egg=enforceable-rank3-modeling"
```

## Release archive install

```bash
python -m pip install --force-reinstall releases/current/enforceable_rank3_modeling_v0.1.21_role_path_remap_dynamic_path.zip
```

## Sign the release manifest

```bash
python tools/generate_release_key.py releases/current/FRAMEWORK_RELEASE_PRIVATE_KEY.pem releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem
python tools/sign_release_manifest.py releases/current/FRAMEWORK_RELEASE_MANIFEST.json releases/current/FRAMEWORK_RELEASE_PRIVATE_KEY.pem releases/current/FRAMEWORK_RELEASE_MANIFEST.sig
python tools/verify_release_manifest.py releases/current/FRAMEWORK_RELEASE_MANIFEST.json releases/current/FRAMEWORK_RELEASE_MANIFEST.sig releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem releases/current/enforceable_rank3_modeling_v0.1.21_role_path_remap_dynamic_path.zip
```

Do not commit the private key. Move it out of the repository before commit.
