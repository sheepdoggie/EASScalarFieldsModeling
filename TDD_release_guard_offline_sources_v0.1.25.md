# TDD: Offline Release Guard Sources v0.1.25

## Problem

Certification-mode runs may be executed from a run subtree or an offline environment where GitHub raw URLs are unavailable. The release guard still must verify the signed manifest and local framework identity without weakening the evidential boundary.

## Solution

v0.1.25 adds explicit local/offline release guard sources:

```text
rank3-run-suite ... \
  --release-manifest /path/FRAMEWORK_RELEASE_MANIFEST.json \
  --release-signature /path/FRAMEWORK_RELEASE_MANIFEST.sig \
  --release-public-key /path/FRAMEWORK_RELEASE_PUBLIC_KEY.pem \
  --framework-zip /path/enforceable_rank3_modeling_vX.Y.Z.zip
```

or:

```text
RANK3_RELEASE_DIR=/path/to/releases/current
```

The signature and manifest are still verified. This is not warning mode and not a bypass.

## Required behavior

If the local manifest signature is invalid, the framework refuses to run in required mode. If the local code hash or framework ZIP hash does not match the signed manifest, the framework refuses to run in required mode.
