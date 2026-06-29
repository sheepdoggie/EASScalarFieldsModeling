# TDD: Contract-Driven Overlay Synthesis and Operator Requirements v0.1.29

## Purpose

v0.1.29 adds a planning layer that attempts to turn a `modeling_intent` contract into a concrete, reviewable overlay plan before any certification/admission model execution.

The layer is intentionally conservative. It does not certify a theorem, it does not make path add/remove intrinsic EAS ontology, and it does not silently promote candidate overlays into admission evidence.

## Required workflow

```text
modeling_intent contract
-> contract-driven synthesis attempt
-> operator-required-items report if anything is missing
-> draft modeling plan
-> operator approval
-> plan validation
-> certification execution only if the plan is executable
```

## New artifacts

```text
OVERLAY_SYNTHESIS_REPORT.json
OPERATOR_REQUIRED_ITEMS.json
```

`OPERATOR_REQUIRED_ITEMS.json` is also written by certification preflight when a certification run lacks a required contract, approved plan, executable plan, or signed release material.

## Anti-leakage rule

Candidate overlays are not converted into admission overlays by default. Automatic candidate-to-admission conversion would be label leakage, because it would let the framework create certification status from a candidate test artifact.

## Operator supplied items

For certification-mode modeling, the operator must provide or approve all necessary items, including:

```text
modeling_intent contract
approved modeling plan
admission overlays or admissible synthesized overlays
non-candidate mechanisms, unless the contract explicitly allows candidate status
initialization/settling requirements
negative controls
path monitor policy
signed release identity material
```

## Expected behavior for current charge-path candidate suite

The current `charge_role_path_remap_dynamic_path_v0_1` suite remains candidate/exploratory. v0.1.29 synthesis should produce an operator-required-items report rather than silently making it certifying.
