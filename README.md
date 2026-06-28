# EASScalarFieldsModeling

Current framework release: `0.1.23` / `0.1.23-external-path-monitor-workspace-layout`.

This package is a GitHub-installable rank-3 scalar-field modeling framework with locked registries, publication-certified run infrastructure, role/path remap support, and separated install/run workspace helpers.

## v0.1.23 highlights

- Path-length changes are **external exploratory monitor requests**, not intrinsic EAS ontology.
- Added `external_path_monitor.py` with validated add/remove path-edit transactions.
- External Python callbacks are disabled unless explicitly allowed for exploratory non-certified work.
- Added separated workspace layout helper:

```bash
rank3-init-workspace --separate-subtrees --project-root ~/Projects
```

- Release manifest now includes:
  - `latest_framework_code_sha256`
  - `accepted_framework_code_sha256`

## Install from GitHub tag

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.23#egg=enforceable-rank3-modeling"
```

## Run a suite

```bash
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --output-root ~/Projects/EAS_runs/results/charge_role_path_v0123 \
  --signing-key ~/.rank3/private_key.pem \
  --continue-on-failure
```

## Important theorem status

The framework does not certify `same -> Delta L = +1` or `opposite -> Delta L = -1`.  v0.1.23 specifically prevents path add/remove from being treated as an intrinsic framework rule.
