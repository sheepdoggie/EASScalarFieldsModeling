# Path-change admission gates v0.1.22

## Purpose

The framework must never trigger `L -> L + 1` or `L -> L - 1` from labels such as `same` or `opposite`.

Path mutation requires a scalar-record admission gate.

## Disabled by default

In v0.1.22 built-in charge role/path overlays:

```text
path_length_mutation_enabled = false
```

This is intentional. The suite first tests role/path-remap and midpoint scalar diagnostics without allowing path length mutation.

## Required future gates

Future path mutation must be guarded by separate gates:

```text
path_lengthening_candidate_gate_v1
path_shortening_candidate_gate_v1
```

### Lengthening candidate

May only admit if generated scalar records show:

- center reinforcement,
- phase-complete/coherent record,
- negative controls do not produce the same event,
- label independence is checked,
- no diagnostic feeds back into update rules.

### Shortening candidate

May only admit if generated scalar records show:

- center cancellation or vacuum-equivalent center condition,
- phase-complete/coherent record,
- negative controls do not produce the same event,
- label independence is checked,
- no diagnostic feeds back into update rules.

## Existing infrastructure

v0.1.21/v0.1.22 already contains transaction-level primitives:

```text
shorten_path_record(...)
lengthen_path_record(...)
PathChangeAdmission(...)
GeometryTransactionReport(...)
```

These are infrastructure. They are not automatic physics laws.
