# Technical Design Document: Locked Framework Certificate System

## 1. Purpose

This document defines the locked certificate system for the enforceable rank-3 scalar field modeling framework.

The purpose of the certificate system is to distinguish:

```text
framework-certified evidence packages
framework-assisted exploratory outputs
external/manual outputs
```

A result is not considered framework-certified because an operator says the framework was used. A result is framework-certified only when a signed evidence envelope verifies.

## 2. Trust Boundary

The certificate system separates three roles:

```text
Untrusted overlay author:
    may write declarative overlays
    may request runs
    may inspect outputs
    may not sign arbitrary evidence packages

Locked framework:
    compiles overlays
    runs initialization/model/control/readout pipeline
    builds evidence package
    computes hashes
    builds evidence envelope

Signing authority:
    owns Ed25519 private key
    signs evidence envelope
    must remain outside AI-editable workspace
```

The private signing key must not be included in output packages, repositories, notebooks, or AI-accessible workspaces.

## 3. Certificate Artifacts

Every signed output package must contain:

```text
EVIDENCE_ENVELOPE.json
EVIDENCE_ENVELOPE.sig
CERTIFICATE.json
SHA256SUMS.csv
FRAMEWORK_PUBLIC_KEY.pem
```

The private key is never packaged.

## 4. Evidence Envelope

`EVIDENCE_ENVELOPE.json` is a canonical JSON object with schema:

```text
rank3_evidence_envelope_v1
```

It records hashes of the evidential package:

```text
framework_name
framework_version
framework_core_hash
rule_registry_hash
readout_registry_hash
model_type_registry_hash
overlay_hash
compiled_manifest_hash
initialization_trace_hash
soo_trace_hash
control_suite_hash
raw_result_hash
readout_result_hash
base_gate_report_hash
evidence_package_hash
environment_hash
command_hash
package_hash
file_hashes
run_id
run_kind
external_verdict
base_gate_passed
admitted
timestamp_utc
```

The envelope is signed, not merely written.

## 5. Signing Algorithm

The system uses Ed25519 public-key signatures.

```text
EVIDENCE_ENVELOPE.json + private key -> EVIDENCE_ENVELOPE.sig
```

Verification uses only the public key.

```text
EVIDENCE_ENVELOPE.json + EVIDENCE_ENVELOPE.sig + public key -> valid/invalid
```

## 6. Package Hashing

The framework hashes all non-generated package files. Certificate-generated files are excluded from the package hash to avoid recursion:

```text
EVIDENCE_ENVELOPE.json
EVIDENCE_ENVELOPE.sig
CERTIFICATE.json
SHA256SUMS.csv
FRAMEWORK_PUBLIC_KEY.pem
```

All other files are listed in `file_hashes` and `SHA256SUMS.csv`.

## 7. Verification

The verifier performs these checks:

```text
1. Required certificate files exist.
2. Signature verifies against EVIDENCE_ENVELOPE.json.
3. Every declared file hash matches the package file.
4. No unexpected non-certificate files are present.
5. No declared files are missing.
6. Recomputed package_hash matches the envelope package_hash.
```

If any check fails, the package is not framework-certified.

## 8. Certification Meaning

A valid certificate certifies:

```text
provenance and framework execution integrity
```

It does not certify:

```text
scientific truth
physical admission
correctness of candidate SOO
correctness of candidate remapping
```

A candidate package may have:

```text
certificate_status = valid_framework_certificate
run_kind = candidate
external_verdict = Ambiguous
admitted = false
base_gate_passed = false
```

That is valid provenance, not scientific admission.

## 9. Partial Framework Use

A package that contains reports or CSVs from framework functions but lacks a valid evidence-envelope signature is classified as:

```text
framework-assisted exploratory output
```

It is not certification-grade. If external software is used, it must either be included, hashed, and signed inside the evidence envelope, or the output is not framework-certified.

## 10. Operational Commands

Generate signing keypair:

```bash
python -m rank3_enforced.generate_signing_key ~/.rank3/private_key.pem ~/.rank3/public_key.pem
```

Run and sign overlay:

```bash
python run_signed_declarative_overlay.py overlays/minimal_control_overlay.json signed_run ~/.rank3/private_key.pem
```

Verify package:

```bash
python -m rank3_enforced.verify_certificate signed_run
```

## 11. Failure Modes

The verifier rejects:

```text
missing signature
missing envelope
missing public key
signature mismatch
modified report/CSV/readout after signing
missing declared file
unexpected added file
package hash mismatch
```

## 12. Acceptance Criteria

The certificate system is accepted when:

```text
signed package verifies
post-signature file modification invalidates verification
all previous framework tests pass
private key is never included in package
```
