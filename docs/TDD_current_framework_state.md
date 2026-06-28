# Current framework state v0.1.22

## Summary

Version 0.1.22 corrects the v0.1.21 framework gap revealed by the charge modeling redo audit.

The v0.1.21 package contained role/path-remap and dynamic-path infrastructure, but the built-in `charge_same_opposite_association_indexed` suite still used `candidate_identity_remap_v0_1` and could not test path-continuation remap or path-length mutation. Therefore `delta_declared_path_length = 0` in that legacy suite is expected and must not be treated as a theorem-capable rejection or confirmation.

Version 0.1.22 adds a separate theorem-capable candidate suite:

```text
charge_role_path_remap_dynamic_path_v0_1
```

This suite is diagnostic/candidate only. It does not certify the paper theorem and it does not force `L -> L +/- 1`.

## Legacy suite status

```text
charge_same_opposite_association_indexed:
    legacy diagnostic suite
    association_remap_rule = candidate_identity_remap_v0_1
    dynamic path mutation = not active
    not theorem-capable for Delta L = +/- 1
```

This suite remains available as a negative/legacy control.

## New v0.1.22 suite

```text
charge_role_path_remap_dynamic_path_v0_1:
    role/path-remap candidate suite
    path construction = role_path_two_support_v0_1
    remap rule = path_continuation_role_remap_v1 or identity control
    scalar update = bounded_context_soo_v1
    midpoint readout = role_path_midpoint_arrival_readout
    path mutation = disabled unless a scalar-record admission gate is declared
```

## New capabilities

- `role_path_two_support_path_construction_v0_1`
- `charge_role_path_remap_dynamic_path_suite_v0_1`
- `role_path_midpoint_arrival_readout`
- `role_path_remap_report_artifact`
- `legacy_charge_identity_remap_suite_marked_not_theorem_capable`
- `path_change_admission_gate_policy_v0_1`
- `initialization_steady_state_gate_policy_v0_1`

## Certification status

The framework can now run theorem-capable candidate overlays, but publication-grade evidence still requires:

1. signed release manifest,
2. release guard pass,
3. initialization/steady-state gate pass when required,
4. BASE gate pass,
5. negative controls,
6. scalar-record-only path-change admission gates,
7. no label-triggered `Delta L` mutation.

## Important non-claim

v0.1.22 does not prove the theorem:

```text
same orientation     -> Delta L = +1
opposite orientation -> Delta L = -1
```

It only corrects the framework so that the theorem can be tested through registered role/path machinery rather than ad hoc runner logic or legacy identity-remap suites.
