# TDD current framework state v0.1.17

## Added candidate remap rule

`slot0_target_derived_external_remap_v1` implements a direction-preserving, association-level remap rule.

Rules:

1. Slot 0 is the path-facing anchor.
2. The path-facing slot is not globally rotated or arbitrarily changed by this rule.
3. Eligible external slots inherit their targets from the current slot-0 associate: for eligible point `x`, let `y = a_0(x)`; then selected external slots satisfy `a'_s(x) = a_s(y)`.
4. Bounded/support-owned points are excluded unless explicitly listed, and framework overlays must declare eligible points explicitly.
5. Boundary-facing dressing associations remain fixed; only declared external slots may update.
6. No scalar value is moved, copied, reset, overwritten, or relabeled.
7. The rule is candidate infrastructure, not an admitted EAS remap law.

This replaces arbitrary external-slot cycling as an admissible framework test remap.
