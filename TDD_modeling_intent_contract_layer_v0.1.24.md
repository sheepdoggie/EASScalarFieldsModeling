# TDD: modeling intent contract layer v0.1.24

## Purpose

v0.1.24 adds a framework-use contract layer above the existing runners. The framework now distinguishes two evidential modes:

1. exploratory modeling mode
2. certification/admission modeling mode

The scalar-field update rules, remap rules, and path-monitor transaction boundary are not changed by this document. This layer controls how a run is framed, whether it is certification-eligible, and what compliance artifacts must be emitted.

## Default rule

Any run without a `modeling_intent` contract is exploratory by default. Exploratory runs may investigate candidate mechanisms, monitors, diagnostics, and failed/ambiguous cases, but they are not allowed to carry certification language or downstream evidential status.

## Certification rule

Certification/admission runs require a predeclared `modeling_intent` contract before execution. The contract must declare:

- modeling intent
- mode
- claim
- required mechanisms
- forbidden shortcuts
- admissible inputs
- required initialization
- required SOO properties
- required monitors
- negative controls
- leakage checks
- admission verdict rules
- abort conditions

If the contract is missing or fails compliance, the run is blocked or marked non-certifying.

## Contract artifacts

Every declarative run now emits:

- `MODELING_INTENT_CONTRACT.json`
- `MODELING_INTENT_COMPLIANCE_REPORT.json`

These artifacts are included in the signed result package.

## Charge theorem guardrails

For `charge_path_adjustment_theorem`, the contract layer checks that path edits are not encoded as intrinsic ontology or intrinsic framework rules. Path add/remove remains external-monitor-requested and transactionally validated by the framework.

## External audit workflow

A separate audit can inspect the contract, compliance report, run manifest, source hashes, controls, readouts, and BASE gate without trusting the chat that ran the model.
