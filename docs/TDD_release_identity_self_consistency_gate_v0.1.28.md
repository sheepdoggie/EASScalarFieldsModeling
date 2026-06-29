# TDD: Release Identity Self-Consistency Gate v0.1.28

## Purpose

v0.1.28 fixes the release-identity defect exposed by the v0.1.27 audit: the release manifest's `latest_framework_code_sha256` could be stale relative to the actual source tree used by the installed framework.

The release manifest is not allowed to be merely plausible. It must identify the exact source tree and exact release archive being published.

## New rule

Packaging is invalid unless all of the following agree:

```text
manifest latest_framework_version == package FRAMEWORK_VERSION
manifest latest_framework_release_label == package FRAMEWORK_RELEASE_LABEL
manifest latest_framework_sha256 == actual internal framework ZIP SHA-256
manifest latest_framework_size_bytes == actual internal framework ZIP size
manifest latest_framework_code_sha256 == installed/source-tree code SHA-256
manifest latest_framework_code_sha256 == code SHA-256 recomputed from the internal framework ZIP
manifest latest_framework_code_sha256 in accepted_framework_code_sha256
manifest latest_framework_tar_gz_sha256 == actual internal TAR.GZ SHA-256
required_files_in_zip all present in the internal framework ZIP
```

## Code identity definition

The code identity hash is computed with `rank3_enforced.version_guard.compute_framework_code_sha256` over the package root. It includes:

```text
rank3_enforced/**/*.py
scalar_field_geometry.py
run_declarative_overlay.py
run_signed_declarative_overlay.py
run_dual_declarative_overlay.py
pyproject.toml
```

The internal release ZIP checker strips the archive root and computes the same identity hash from the archived files.

## New CLI

```bash
rank3-check-release-identity \
  --repo-root . \
  --manifest releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  --framework-zip releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.zip \
  --framework-tar-gz releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.tar.gz
```

Exit status is non-zero if any release identity check fails.

## Scientific status

This release does not certify any EAS theorem. It only strengthens the release identity gate required before future certification/admission runs.
