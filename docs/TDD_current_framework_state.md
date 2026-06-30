# TDD Current Framework State v0.1.44

## Release label

`0.1.44-field0-locked-admissibility-simulation`

## Purpose

v0.1.44 repairs the operational boundary of the modeling framework. The framework is now designed around a strict simulation discipline:

```text
field 0 may be imposed;
admissibility variants may be selected before the run;
all later fields are generated only by SOO plus the frozen admissibility specification;
post-run labels/readouts never feed the generator.
```

The release does not certify photons, charge, bounded supports, Standard Model particles, or a path-accommodation theorem. It certifies only that the new runner obeys the operational constraint surface needed for future exploratory modeling.

## New runner

`rank3_enforced/field0_locked_simulation.py`

Console commands:

```text
rank3-run-field0-locked-simulation
rank3-write-field0-locked-simulation-packet
```

## Operational rule

A test may provide scalar point values and rank-3 associations only on field 0. A test may also select one locked admissibility specification before the run begins. No later-field scalar values, later-field associations, structure labels, endpoint classes, target tuples, or slot-specific sign policies are accepted as generator inputs.

## Pre-run admissibility variation

Admissibility exploration remains allowed, but only as a pre-run locked specification. v0.1.44 includes these registered specs:

```text
LOCKED_PURE_GRADIENT_STATIC_ASSOCIATIONS
LOCKED_LEAST_GRADIENT_REASSOCIATION
LOCKED_CONJUGATE_SPLIT_ON_FIRST_ASSOCIATION
```

Each spec is hashed before execution. Every later field state records the same admissibility hash. Any unregistered or mutated spec is rejected before the run begins.

## Generated later fields

For every field `ell > 0`, the runner applies:

```text
previous field state
+ locked topology/admissibility transition, if the pre-run spec permits one
+ single burden functional for all association slots
+ SOO scalar update
= next field state
```

A topology change such as conjugate splitting is therefore allowed only when it is part of the frozen admissibility spec selected before the run. It is not a runner-local special construction.

## Observer-only readouts

Post-run readouts may compute quantities such as:

```text
lambda(P)=Phi(P)-Phi(first_generated_association(P))
```

and may scan motifs such as three-cycles. These are observer outputs only and are not allowed to determine later associations, scalar values, path transactions, or candidate promotion.

## Legacy quarantine

The following exploratory runners remain in the package only as historical diagnostics:

```text
rank3_enforced.endpoint_class_path_response_separation
rank3_enforced.vacuum_admissibility_variation
rank3_enforced.whole_field_conjugate_vacuum
```

They are not v0.1.44-compliant certification surfaces because they use endpoint classes, runner-local admissibility variants, motif labels, or slot policies that violate the field-0-only operational constraint.

## Required reports

```text
FIELD0_INPUT_CONFIGURATION_REPORT.json
FROZEN_ADMISSIBILITY_SPEC_REPORT.json
FIELD_EVOLUTION_TRACE.json
ASSOCIATION_TRANSITION_LEDGER.json
ADMISSIBILITY_BURDEN_LEDGER.json
SOO_TRANSITION_LEDGER.json
OPERATIONAL_CONSTRAINT_COMPLIANCE_REPORT.json
POSTRUN_OBSERVER_READOUT_REPORT.json
LEGACY_RUNNER_QUARANTINE_REPORT.json
EXPLORATORY_VERDICT_REPORT.json
```

## Status

v0.1.44 is exploratory and framework-operational. It is the required base for the next whole-field tests because it prevents the two prior failure modes:

1. constructed endpoint/provenance mismatch;
2. slot-role admissibility contradiction.
