# Release Guard Policy

## Purpose

The release guard prevents obsolete framework snapshots from being used for new candidate/admission evidence.

The prior failure mode was:

```text
operator bundles an older locked framework ZIP
user runs it successfully
result is a framework run, but lacks newer mandatory evidence artifacts
```

This policy closes that gap.

## Required candidate/admission behavior

Before any candidate/admission run, the runner must:

1. Load `FRAMEWORK_RELEASE_MANIFEST.json` from the canonical release source.
2. Verify `FRAMEWORK_RELEASE_MANIFEST.sig` with `FRAMEWORK_RELEASE_PUBLIC_KEY.pem`.
3. Compute the local framework package/source hash.
4. Compare it to `latest_framework_sha256`.
5. Confirm all `required_capabilities` are present.
6. Refuse to run if any check fails.

## Required refusal cases

Refuse candidate/admission execution if:

- the release manifest is missing;
- the manifest signature cannot be verified;
- the installed framework hash differs from `latest_framework_sha256`;
- required capability modules are missing;
- the job bundle contains executable files;
- the job bundle tries to provide a framework ZIP or runner script.

## Archive reproduction exception

Old framework versions may be used only for archive reproduction. Such runs must be labeled:

```text
run_kind = archive_reproduction
admitted = false
candidate_or_admission_allowed = false
```

Archive reproduction cannot certify new claims.
