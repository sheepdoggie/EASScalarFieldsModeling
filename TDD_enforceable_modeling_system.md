# Technical Design Document: Enforceable Rank-3 Scalar Field Modeling System

## 1. Purpose

This enforcement layer converts the rank-3 scalar field geometry scaffold into a controlled modeling system. The raw geometry engine remains responsible for immutable association states, derived geometry reports, externally supplied scalar update rules, and externally supplied association remap rules. The enforcement layer adds the machinery needed to prevent common AI mishandling during model execution.

The enforced system does not make Python absolutely secure against an actor that can edit or monkeypatch the core package. It does make ordinary model execution pass through a locked-style API with manifests, rule metadata, mandatory controls, pre-registered readouts, source-pattern audits, evidence hashes, frozen results, and an executable BASE gate.

## 2. Design Principle

The raw geometry runner executes supplied rules. The enforced runner decides whether a model package is complete enough to execute, whether required controls are present, whether result evidence is frozen and fingerprinted, and whether downstream certification/admission language is allowed.

The central enforced rule is:

```text
No downstream certified/admitted result exists unless run_model_package() constructs a passing BaseGateReport.
```

## 3. Security Boundary

### Locked core

The following modules should be treated as locked core:

```text
scalar_field_geometry.py
rank3_enforced/certified_runner.py
rank3_enforced/base_gate.py
rank3_enforced/control_suite.py
rank3_enforced/evidence.py
rank3_enforced/fingerprints.py
rank3_enforced/immutable_result.py
rank3_enforced/manifest.py
rank3_enforced/rule_metadata.py
rank3_enforced/source_audit.py
```

### Untrusted model layer

The model layer may supply:

```text
candidate scalar update rules
candidate association remap rules
model manifests
support records
readout rules
model-specific diagnostics
```

The model layer must not bypass the certified runner if the result is to be used downstream.

## 4. Core Objects

### ModelManifest

Declares the model name, version, purpose, run kind, requested certification status, external admission verdict, required controls, required readouts, and forbidden interpretations.

### DiagnosticManifest

Pre-registers required readouts and controls. This prevents post-hoc diagnostic selection.

### RuleMetadata

Every supplied model-bearing rule must declare:

```text
name
version
status
source_hash
allowed_for_certified_runs
notes
```

Rule status is one of:

```text
admitted
candidate
control
demonstration
rejected
```

### ModelPackage

Bundles the manifest, raw geometry configuration, rule metadata, and readout rules.

### EnforcedRunResult

Contains the immutable primary result, readout reports, control reports, source audit reports, evidence package, BASE gate, and core hash.

## 5. Execution Pipeline

The enforced runner performs:

```text
1. Verify core integrity hash if manifest.expected_core_hash is supplied.
2. Audit the manifest.
3. Audit scalar update and remap rule statuses.
4. Audit scalar update and remap rule source patterns.
5. Run all required controls.
6. Run the primary geometry model.
7. Convert the primary result to an immutable result view.
8. Run pre-registered readouts.
9. Build evidence package hashes.
10. Build executable BASE gate report.
11. Block requested certification if the gate does not pass.
```

## 6. Mandatory Controls

Default required controls are:

```text
identity_remap_zero_update
identity_remap_candidate_update
candidate_remap_zero_update
```

Additional supported controls include:

```text
completed_path_scope
active_phase_path_scope
directed_graph_mode
undirected_graph_mode
```

## 7. Readouts

Default required readouts are:

```text
result_shape
state_verification
phi_history_hash
geometry_snapshot_count
```

Additional included readout:

```text
path_length_summary
```

Readouts are evidence reports only. They do not mutate the result and do not certify physical interpretation by themselves.

## 8. Result Immutability

The immutable result wrapper freezes:

```text
phi history
adjacency arrays
path length arrays
pair weight arrays
tensor geometry arrays
```

Association states are already frozen by the raw geometry engine.

## 9. Evidence Package

The evidence package hashes:

```text
manifest
initial association state
initial phi
scalar update rule source
association remap rule source
primary result
readouts
controls
combined package
```

## 10. BASE Gate

The executable BASE gate records:

```text
source_provenance_passed
verdict_independence_passed
blind_generation_projection_separation_passed
negative_controls_passed
leakage_manipulation_checks_passed
external_admission_verdict
```

The gate passes only if all checks pass and the external admission verdict is `Admitted`.

Control and candidate runs may execute, but they do not produce admitted certification.

## 11. Blocking Conditions

Certification is blocked when:

```text
manifest is incomplete
requested certification is inconsistent with run kind
required readouts are missing
required controls fail or are missing
rule status is incompatible with run kind
rule is not allowed for certified runs
forbidden source patterns are found
result arrays are mutable
association state verification fails
external verdict is not Admitted
core integrity hash mismatch occurs
```

## 12. Known Limits

The system is not absolute security against a process that can edit the core source, alter imports, monkeypatch functions, or run with an editable install. Operational hardening requires:

```text
hash-pinned package install
read-only core files
no editable install for the core
CI tests
expected_core_hash in the manifest
separate untrusted model plugin directory
```

## 13. Acceptance Tests

The included tests verify:

```text
minimal enforced control execution
result freezing
mandatory control completion
non-admission of control run
certification blocking behavior
```

Run:

```bash
pytest -q
```
