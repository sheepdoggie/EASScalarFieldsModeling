# Current Framework State v0.1.23

## Purpose

v0.1.23 corrects the treatment of path-length changes.  Path length changes are **not** EAS ontology and are **not** intrinsic framework dynamics.  The framework now exposes an exploratory external path-monitor API that can inspect a registered path and request an add/remove transaction.  The framework validates and logs the transaction; it does not infer or impose `L -> L +/- 1`.

## Main changes

- Added `rank3_enforced/external_path_monitor.py`.
- Added `PathMonitorSnapshot`.
- Added `ExternalPathEditRequest`.
- Added `ExternalPathEditResult`.
- Added `make_path_monitor_snapshot(...)`.
- Added `apply_external_path_edit_request(...)`.
- Added `call_external_path_monitor(...)`, disabled unless `allow_external_code=True`.
- Added separated install/run workspace layout helpers.
- Added `latest_framework_code_sha256` and `accepted_framework_code_sha256` to the release-manifest schema for strict release-guard operation without requiring `RANK3_FRAMEWORK_ZIP`.

## Path-length policy

Path changes are now classified as external exploratory edits:

```text
external monitor observes path -> external request -> framework validates/logs transaction
```

The framework must not treat add/remove as admitted EAS rules, theorem conclusions, or automatic consequences of same/opposite labels.

## Workspace policy

Framework source/package installation and modeling runs should be separated:

```text
EASScalarFieldsModeling_github_files/   install/update/publish/package area
EAS_runs/                               modeling runs/results/logs/workspaces
```

The helper command is:

```bash
rank3-init-workspace --separate-subtrees --project-root ~/Projects
```

## Status

v0.1.23 is an infrastructure/security correction.  It does not certify the charge path-adjustment theorem.
