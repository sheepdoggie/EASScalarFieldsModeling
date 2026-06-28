# TDD: Release Manifest Code Hash Fields v0.1.23

## Problem

v0.1.22 strict release guard could validate the signed release ZIP, but installed GitHub packages could fail when no local framework ZIP was supplied.  The manifest lacked code-hash fields.

## Added fields

```json
"latest_framework_code_sha256": "...",
"accepted_framework_code_sha256": ["..."]
```

## Behavior

The release guard can now compare the installed framework code fingerprint to accepted signed code hashes.  This avoids requiring `RANK3_FRAMEWORK_ZIP` for ordinary installed runs.

## Security note

The code hash is not a substitute for the release ZIP hash. It is an installed-code identity check used by the release guard. The release ZIP hash remains in `latest_framework_sha256`.
