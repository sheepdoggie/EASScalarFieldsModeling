# EASScalarFieldsModeling

Current framework release: `0.1.28` / `0.1.28-release-identity-self-consistency`.

v0.1.28 adds a release identity self-consistency gate. The release manifest must now identify the exact source tree and exact internal release archives before a package should be published or used for future certification/admission work.

## Install

```bash
python -m pip install --force-reinstall \
  "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.28#egg=enforceable-rank3-modeling"
```

## Release identity check

Run this before signing/publishing:

```bash
rank3-check-release-identity \
  --repo-root . \
  --manifest releases/current/FRAMEWORK_RELEASE_MANIFEST.json \
  --framework-zip releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.zip \
  --framework-tar-gz releases/current/enforceable_rank3_modeling_v0.1.28_release_identity_self_consistency.tar.gz
```

The check fails if the manifest code hash, release archive hash, version, release label, TAR.GZ hash, or required ZIP contents are stale or inconsistent.

## Modeling modes

Any run without a `modeling_intent` contract is exploratory by default. Certification/admission mode requires a predeclared contract and an approved modeling plan.

```bash
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode exploratory \
  --output-root results/charge_role_path_exploratory \
  --continue-on-failure
```

Certification mode requires both a contract and an approved plan:

```bash
rank3-run-suite charge_role_path_remap_dynamic_path_v0_1 \
  --mode certification \
  --modeling-intent-contract overlays/charge_path_adjustment_contract.json \
  --approved-plan plans/charge_path_approved_plan.json \
  --output-root results/charge_path_certification \
  --continue-on-failure
```

The current built-in charge role/path suite remains candidate/exploratory. It is expected to be blocked by a certification contract unless the overlays become contract-compliant and certification-executable.

## Scientific status

This release does not certify the charge path-adjustment theorem. It strengthens release identity controls required before future certification/admission work.
