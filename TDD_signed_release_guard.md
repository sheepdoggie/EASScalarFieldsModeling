# TDD: Signed Release Guard and Run-Environment Cache

## Purpose

The framework must prevent candidate/admission runs from being executed with an obsolete framework snapshot. Operators may prepare declarative configurations, but framework executables should not be passed around as part of job bundles. A runner must verify the installed framework against the canonical signed release manifest before execution.

## Release source

The canonical release source is the GitHub repository:

```text
https://github.com/sheepdoggie/EASScalarFieldsModeling.git
```

The guard reads:

```text
releases/current/FRAMEWORK_RELEASE_MANIFEST.json
releases/current/FRAMEWORK_RELEASE_MANIFEST.sig
releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem
```

The manifest is not trusted merely because it is hosted on GitHub. It is trusted only after the Ed25519 signature verifies against the release public key.

## Local framework identity

The guard computes a deterministic local code fingerprint over the framework code surface:

```text
rank3_enforced/*.py
scalar_field_geometry.py
run_declarative_overlay.py
run_signed_declarative_overlay.py
run_dual_declarative_overlay.py
pyproject.toml
```

The signed release manifest should contain:

```json
"latest_framework_code_sha256": "..."
```

The runner refuses to execute if the local code fingerprint differs.

## Required capabilities

The manifest also declares required framework capabilities. The installed framework must expose all required capabilities through `rank3_enforced.capabilities.FRAMEWORK_CAPABILITIES`.

For current charge/SOO work, the required capability set includes SOO functional reporting, diagnostic-point residual samples, relation-complete packet contrast, explicit path construction, and dual plaintext/encrypted output.

## Cache behavior

The first successful check writes a run-environment cache file:

```text
.rank3_release_guard_passed.json
```

Cache location precedence:

1. `RANK3_VERSION_GUARD_CACHE`
2. `RANK3_RUN_ENV_DIR/.rank3_release_guard_passed.json`
3. `./.rank3_release_guard_passed.json`

The cache is accepted only if the local framework code fingerprint still matches and the TTL has not expired. This allows a loop over many overlays to avoid fetching GitHub for every separate process execution.

## Fail-closed policy

Candidate/admission runners call the guard before running. If the manifest is missing, unsigned, has an invalid signature, declares a different framework hash, or requires a missing capability, the runner stops before producing evidence.

Archive reproduction runs may use warning mode, but they cannot be admitted as current candidate/admission evidence.
