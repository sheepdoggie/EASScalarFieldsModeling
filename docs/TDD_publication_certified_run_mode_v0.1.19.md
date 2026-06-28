# TDD: Publication-Certified Run Mode v0.1.19

## Purpose

Version 0.1.19 adds a publication-certified run boundary around the locked Rank-3/EAS modeling framework. The purpose is to prevent evidential packages from depending on unregistered Python code, notebook logic, external scripts, post-hoc diagnostics, or manually assembled outputs.

This version implements the first enforceable harness layer. It does not make any scientific result admitted. It makes publication-grade execution fail closed unless the operator uses framework entry points, data-only declarative overlays, signed plaintext evidence, and an encrypted duplicate evidence payload.

## Console commands

```bash
rank3-run-publication-certified <overlay.json> <output_dir> \
  --signing-key ~/.rank3/private_key.pem \
  --recipient-public-key ~/.rank3/recipient_public_key.pem

rank3-verify-publication-certified <output_dir> \
  --recipient-private-key ~/.rank3/recipient_private_key.pem
```

## Enforced input boundary

The publication-certified runner accepts a declarative JSON overlay as input. The runner audits that:

1. The overlay is a JSON file.
2. The overlay does not contain forbidden code-bearing key names.
3. The overlay does not contain forbidden code-bearing string fragments.
4. The overlay directory is code-free by default.
5. The run is executed through the installed `rank3_enforced` package.
6. The framework latest-release guard is checked.
7. The result is packaged using the locked evidence-package path.

Blocked key fragments include `python`, `callable`, `function`, `script`, `source_code`, `code`, `lambda`, `eval`, `exec`, `subprocess`, `importlib`, `pickle`, `cloudpickle`, and `dill`.

Blocked nearby file suffixes include `.py`, `.pyc`, `.ipynb`, shell scripts, batch scripts, and binary extension modules.

## Evidence output

The publication-certified runner creates:

1. A canonical signed evidence package.
2. A deterministic plaintext ZIP of that package.
3. An encrypted duplicate payload of the exact same ZIP bytes.
4. A transfer manifest binding plaintext and encrypted hashes.
5. Ed25519 signatures for integrity verification.
6. A publication-certified run report.

The encrypted payload uses the existing X25519 + HKDF-SHA256 + ChaCha20Poly1305 framework encryption path.

## Security model

This is not a sandbox. It is a provenance and execution-boundary mechanism. It blocks publication-certified evidential status for results that depend on external code, unregistered runners, or notebook-only logic. Exploratory code can still be written outside the framework, but it cannot be represented as framework-certified evidence.

## Current limitations

1. The runner does not yet provide OS-level sandboxing.
2. The publication-certified run report is written beside the transfer package rather than inside the canonical evidence package.
3. Exact external admission must still be performed by a separate external review process.
4. Scientific correctness is not certified by cryptography. The cryptographic package certifies provenance and integrity only.

## Status

Framework version: 0.1.19

Implementation status: enforceable publication-certified harness layer added.

Scientific admission status: none.
