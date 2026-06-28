# GitHub install and publish instructions for v0.1.22

## Update existing repository safely

```bash
cd ~/Projects/EASScalarFieldsModeling_github_files

unzip EASScalarFieldsModeling_v0.1.22_github_package.zip

if [ ! -d EASScalarFieldsModeling_publish/.git ]; then
  git clone https://github.com/sheepdoggie/EASScalarFieldsModeling.git EASScalarFieldsModeling_publish
fi

cd EASScalarFieldsModeling_publish
git fetch origin main
git checkout -B main origin/main

rsync -a --delete --exclude='.git' \
  ../EASScalarFieldsModeling_v0.1.22_github_package/ \
  ./

python -m pip install -e .
pytest -q

git status --short
git add .
git commit -m "Package GitHub-installable framework v0.1.22"
git push origin main

git tag -a v0.1.22 -m "v0.1.22 charge role/path remap candidate suite"
git push origin v0.1.22
```

## Install after publishing

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.22#egg=enforceable-rank3-modeling"
```

## Run the corrected candidate suite

```bash
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --output-root runs/charge_role_path_v0122 \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

## Legacy suite warning

```bash
rank3-run-suite charge_same_opposite_association_indexed --output-root runs/legacy_charge_assoc
```

The legacy suite uses identity remap and is not theorem-capable for `Delta L = +/- 1`.
