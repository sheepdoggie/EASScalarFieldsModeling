# TDD Current Framework State v0.1.42

Release label: `0.1.42-vacuum-admissibility-variation`.

v0.1.42 adds an exploratory vacuum-admissibility variation runner. It supersedes the next modeling step after v0.1.41 by treating v0.1.41 as a separation diagnostic rather than an emergence model.

## Modeling correction

v0.1.41 compared endpoint classes with different provenance:

- triangles: generated from split-vacuum machinery;
- photon-like records: locally constructed and then SOO-processed;
- bounded supports: calibration/control endpoint records.

v0.1.42 removes the endpoint-class comparison path from the new runner. Every candidate now begins from the same chain:

```text
undefined vacuum -> split/lift -> SOO -> association selection -> motif discovery -> post-run classification
```

## New runner

Module: `rank3_enforced.vacuum_admissibility_variation`

Console commands:

```bash
rank3-run-vacuum-admissibility-variation
rank3-write-vacuum-admissibility-packet
```

The runner varies five admissibility regimes:

1. A: pure scalar-gradient admissibility.
2. B: split-conjugacy preserving admissibility.
3. C: relation-complete burden admissibility.
4. D: successor-covariant cyclic admissibility.
5. E: bounded-support closure admissibility.

## Required reports

- `VACUUM_ADMISSIBILITY_VARIANT_LEDGER.json`
- `VACUUM_SPLIT_AND_LIFT_LEDGER.json`
- `SOO_FULL_FIELD_TRACE.json`
- `ASSOCIATION_BURDEN_DECOMPOSITION_REPORT.json`
- `POSTRUN_PHOTON_LIKE_CERTIFIER_REPORT.json`
- `POSTRUN_TRIANGLE_SCAFFOLD_REPORT.json`
- `BOUNDED_SUPPORT_CLOSURE_REPORT.json`
- `PATH_FACING_RESIDUAL_DISCOVERY_REPORT.json`
- `PATH_ACCOMMODATION_BY_PROVENANCE_REPORT.json`
- `STANDARD_MODEL_INTERFACE_QUARANTINE_REPORT.json`

## Controls

The release explicitly includes:

- `PHOTON_PATH_FACING_ZERO_LAYER_CONTROL`
- `CONSTRUCTED_PHOTON_ENDPOINT_CONTROL`

These block the v0.1.41 failure mode in which photon-like `Delta L=0` could be overconstrained by a locally constructed `[0,q,-q]` record and an independently sealed path-facing zero layer.

## Certification status

Exploratory only. No photon, charge, bounded-support, Standard Model, or path-accommodation theorem certification is claimed.
