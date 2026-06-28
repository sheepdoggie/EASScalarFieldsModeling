# GitHub install and publish instructions for v0.1.23

## Publish update safely

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files
unzip EASScalarFieldsModeling_v0.1.23_github_package.zip

if [ ! -d EASScalarFieldsModeling_publish/.git ]; then
  git clone https://github.com/sheepdoggie/EASScalarFieldsModeling.git EASScalarFieldsModeling_publish
fi

cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main

rsync -a --delete --exclude='.git' \
  ../EASScalarFieldsModeling_v0.1.23_github_package/ \
  ./

python -m pip install -e .
pytest -q

git status --short
git add .
git commit -m "Package GitHub-installable framework v0.1.23"
git push origin main

git tag -a v0.1.23 -m "v0.1.23 external path monitor and workspace layout"
git push origin v0.1.23
```

## Install after publishing

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.23#egg=enforceable-rank3-modeling"
```

## Recommended separated directories

```bash
rank3-init-workspace --separate-subtrees --project-root ~/Projects
```

This creates install/update directories under `~/Projects/EASScalarFieldsModeling_github_files/` and run directories under `~/Projects/EAS_runs/`.

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
  releases/current/enforceable_rank3_modeling_v0.1.23_external_path_monitor.zip
```

Do not commit `~/.rank3/signing_private.pem`.
