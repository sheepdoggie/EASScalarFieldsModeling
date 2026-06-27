# Enforceable Rank-3 Scalar Field Modeling Framework

Current release: `0.1.7-installed-run-manager`.

This package is designed to be installed and then run from code-free workspaces. Do not execute candidate/admission runs from inside an extracted framework source tree containing `./rank3_enforced/`, because Python will import that local tree instead of the signed installed package.

## Install and verify

```bash
python -m pip install --force-reinstall releases/current/enforceable_rank3_modeling.zip
rank3-check-release-guard --force-refresh
```

The release guard must report `"passed": true` before candidate/admission work.

## Normal run workflow

Create a workspace:

```bash
cd ~/Projects/EAS_runs
rank3-init-workspace charge_assoc_workspace
cd charge_assoc_workspace
```

List built-in suites:

```bash
rank3-list-suites
```

Run the rebuilt charge same/opposite suite:

```bash
rank3-run-suite charge_same_opposite_association_indexed \
  --output-root runs/charge_same_opposite_assoc_soo \
  --signing-key ~/.rank3/private_key.pem
```

The suite runner loads overlays from the installed package, performs the release guard once, writes signed evidence packages under `runs/`, and writes:

```text
SUITE_RUN_REPORT.json
SHA256SUMS.csv
release_guard.json
```

## Run one overlay

```bash
rank3-run-overlay path/to/overlay.json runs/case_id --signing-key ~/.rank3/private_key.pem
```

## Built-in overlay suites

The framework currently packages this built-in suite as package data:

```text
charge_same_opposite_association_indexed
```

It contains the 34 rebuilt charge overlays for L16-L32 same/opposite tests using:

```text
support_seeded_two_ledger initialization
association_indexed_soo_v1
linear_support_path_v0_2
charge path/support burden placeholders
relation-complete packet readout
common-mode / zero-sum readout
```

## Key architectural rule

Framework source, overlays, and run workspaces are now separated:

```text
installed package:     rank3_enforced code and built-in overlay suites
run workspace:         code-free results/logs/manifests only
external overlays:     optional JSON-only overlays supplied with --overlays-dir
```

This prevents source-tree import shadowing and removes the need to copy scripts manually for each run.
