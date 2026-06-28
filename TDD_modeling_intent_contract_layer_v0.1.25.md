# TDD: Modeling Intent Contract Layer v0.1.25

## Background

v0.1.24 introduced two framework-use modes:

1. exploratory modeling mode;
2. certification/admission modeling mode.

The architecture was correct, but the suite runner had a propagation defect: a supplied certification contract could be accepted at the CLI and still not appear in the emitted per-case artifacts.

## Required invariant

For every suite run:

```text
suite-level contract hash == per-case contract hash == compliance report contract hash
```

If this invariant cannot be satisfied, the case is non-certifying.

## Enforcement behavior

### Exploratory mode

If no contract is supplied, the framework writes the exploratory default contract and marks the run as exploratory.

Exploratory records must not be described as admitted, certified, confirmed, proved, or usable downstream.

### Certification mode

Certification mode requires:

```text
--mode certification
--modeling-intent-contract <path>
```

Before model execution, each overlay is validated against the supplied contract.

If validation fails, the framework writes:

```text
MODELING_INTENT_CONTRACT.json
MODELING_INTENT_COMPLIANCE_REPORT.json
CONTRACT_PROPAGATION_REPORT.json
RUN_CLASSIFICATION.json
RUN_ERROR.txt
```

and does not run SOO.

## Warning/off release guard mode

If release-guard warning/off mode is used, emitted records are explicitly marked non-certifying. This prevents diagnostic records from being mistaken for certification/admission evidence.

## Offline/local release guard

v0.1.25 adds CLI options for local signed release sources:

```text
--release-manifest
--release-signature
--release-public-key
--framework-zip
```

It also supports:

```text
RANK3_RELEASE_DIR=/path/to/releases/current
```

which resolves the three release files from that directory.
