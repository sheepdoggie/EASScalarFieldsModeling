# TDD current framework state v0.1.18

## Change from v0.1.17

The candidate direction-preserving external remap rule has been renamed from the ambiguous slot-0 phrasing to:

```text
path_target_derived_external_remap_v1
```

The rule remains configurable. The path-facing slot is specified by `path_slot`; it is not assumed to be slot 0.

## Rule semantics

For an eligible point `x`:

```text
y = a_path_slot(x)
a'_path_slot(x) = a_path_slot(x)
a'_s(x) = a_s(y) for each configured external remap slot s
```

Configured fixed points are not remapped. Configured fixed slots are not changed. No scalar values are moved, copied, overwritten, reset, or rotated.

The rule is still marked candidate and not allowed for certified runs.

## Why the rename matters

Some EAS geometries use slot 0 as a boundary-facing fixed slot, while another slot is path-facing. The old name implied that slot 0 was always path-facing. The new name records the correct invariant: remap follows the configured path-facing target, whatever slot carries that role in the tested geometry.
