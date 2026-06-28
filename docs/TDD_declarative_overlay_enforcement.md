# Technical Design Document: Declarative Overlay Enforcement Layer

## 1. Purpose

This document defines the revision that prevents certified/candidate modeling from accepting arbitrary Python overlays.

The earlier enforceable framework hardened the core runner, controls, evidence hashing, immutable outputs, and BASE gate. However, if overlays remain arbitrary executable Python, the overlay can still manipulate the model by selecting diagnostics post hoc, encoding target outcomes in update/remap/readout logic, or choosing support records after seeing outputs.

The new enforcement layer removes executable overlays from candidate/admission modeling.

## 2. Trust Boundary

The system now has three layers:

```text
Locked core:
    scalar_field_geometry engine
    immutable result wrapper
    evidence hashing
    control suite
    BASE gate
    certified runner

Locked interpreter:
    JSON overlay loader
    declarative overlay schema
    locked rule registry
    locked readout registry
    model-type registry
    overlay compiler

Untrusted overlay:
    data only
    no Python code
    no functions
    no imports
    no custom executable readouts
    no custom executable update/remap rules
```

The AI may propose overlay data. It may not define certifiable execution logic inside the overlay.

## 3. New Modules

```text
rank3_enforced/overlay_schema.py
rank3_enforced/overlay_loader.py
rank3_enforced/locked_registries.py
rank3_enforced/model_type_registry.py
rank3_enforced/overlay_compiler.py
```

## 4. Entry Points

### 4.1 Direct model package path

```python
run_model_package(package)
```

This remains available for direct control packages and exploratory infrastructure use.

Candidate/admission direct packages are blocked unless they contain a `compiled_overlay_hash` produced by the overlay compiler.

### 4.2 Declarative overlay path

```python
run_declarative_overlay(path)
```

This is the enforced candidate/admission-capable path. It accepts JSON overlay files only.

## 5. Declarative Overlay Schema

A valid overlay may declare:

```text
schema_version
model_type
model_name
model_version
purpose
run_kind
external_admission_verdict
initial_geometry
initial_phi
execution
rules
supports
constraints
readouts
controls
requested_certification
expected_core_hash
notes
```

It may not contain executable keys such as:

```text
python
callable
function
lambda
source
source_code
code
exec
eval
module
import
class
```

Files must be JSON. `.py` overlays are rejected.

## 6. Locked Rule Registry

All executable rule behavior is selected from `locked_registries.py`.

Registry categories:

```text
SCALAR_UPDATE_RULES
ASSOCIATION_REMAP_RULES
PHASE_RULES
PAIR_WEIGHT_RULES
TRIPLET_LIFT_RULES
READOUT_RULES
```

An overlay can select a rule by name. It cannot define a new rule.

## 7. Model-Type Compiler

The overlay declares a `model_type`. The locked model-type registry expands that into required controls, readouts, phases, graph modes, path scopes, and forbidden interpretations.

Implemented model types:

```text
minimal_control
two_support_path_adjustment
```

### 7.1 `minimal_control`

Requires the base readouts and base controls.

### 7.2 `two_support_path_adjustment`

Requires:

```text
exactly two supports
non_overlap_required=true
three-phase active maps when require_three_phase_coherence=true
path_length_summary readout
completed_path_scope control
active_phase_path_scope control
directed_graph_mode control
undirected_graph_mode control
```

This prevents the AI from forgetting the controls or diagnostics associated with a support-to-support path-adjustment model type.

## 8. Candidate/Admission Blocker

`run_model_package` now rejects candidate/admission packages that were not produced by the declarative overlay compiler.

Blocking condition:

```text
manifest.run_kind in {candidate, admission}
and package.compiled_overlay_hash is None
```

This prevents arbitrary Python `ModelPackage` overlays from being used as candidate/admission modeling packages.

## 9. Evidence Package Revision

The evidence package now includes:

```text
compiled_overlay_hash
```

For declarative overlays this is the overlay file/payload hash. For direct control packages it is recorded as:

```text
direct_model_package
```

Candidate/admission runs must not use `direct_model_package`.

## 10. Included Overlay Examples

```text
overlays/minimal_control_overlay.json
overlays/minimal_candidate_overlay.json
overlays/two_support_candidate_overlay.json
```

## 11. Tests

The test suite verifies:

```text
control overlay runs with compiled overlay hash
candidate overlay runs but is not admitted
two-support candidate overlay expands mandatory controls
.py overlay files are rejected
executable overlay keys are rejected
direct candidate ModelPackage is blocked
```

Current test status:

```text
9 passed
```

## 12. Residual Limitation

This enforcement protects candidate/admission modeling from arbitrary overlay logic in normal use. It does not protect against malicious editing of the locked core package or monkeypatching of the runtime. For operational hardening, install the package as a non-editable, hash-pinned dependency and set `expected_core_hash` in the overlay.
