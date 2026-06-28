# Charge role/path-remap suite v0.1.22

## Purpose

The `charge_role_path_remap_dynamic_path_v0_1` suite converts the corrected exploratory case-7 semantics into framework-declarative overlays.

The suite separates three cases:

```text
identity/no remap:
    path mutation disabled
    declared path length should remain unchanged

role/path remap, same slot:
    boundary-facing slot fixed
    path role remains in its numeric slot
    vacuum role remains in its numeric slot

role/path remap, role exchange:
    boundary-facing slot fixed
    path/vacuum roles may exchange numeric slots
    relational path role is preserved by role state, not hard-coded slot identity
```

## Built-in coverage

The suite includes odd path lengths:

```text
L = 7, 17, 41
```

and both orientations:

```text
same
opposite
```

with three remap policies:

```text
no_remap
role_remap_same_slot
role_remap_exchange
```

Total overlays:

```text
3 path lengths x 2 orientations x 3 remap policies = 18 overlays
```

## Path construction

The suite uses:

```text
role_path_two_support_v0_1
```

This constructor exists because the older permutation path constructor cannot represent the dressing-role rule cleanly.

Endpoint convention:

```text
left dressing endpoint:
    slot 0 = boundary-facing fixed
    slot 1 = path-facing
    slot 2 = vacuum-facing

right dressing endpoint:
    slot 0 = boundary-facing fixed
    slot 1 = path-facing
    slot 2 = vacuum-facing

path nodes:
    slot 0 = toward left endpoint
    slot 1 = toward right endpoint
    slot 2 = vacuum-facing completion
```

## Remap rule

The suite uses:

```text
path_continuation_role_remap_v1
```

The rule is orientation-aware:

```text
left endpoint:
    continuation moves toward right endpoint

right endpoint:
    continuation moves toward left endpoint
```

The rule records `ROLE_PATH_REMAP_REPORT.json` and states explicitly:

```text
scalar_values_moved = false
boundary_slots_fixed = true
role_based_not_slot_index_based = true
orientation_aware_continuation = true
```

## Readout

The suite adds:

```text
role_path_midpoint_arrival_readout
```

The readout reports:

```text
left_arrival
right_arrival
left + right
left - right
reinforcement ratio
cancellation/contrast ratio
center values
late-window means
```

The readout is diagnostic only. It cannot mutate path length.

## Path length status

Path mutation is disabled in these overlays. Therefore a correct no-remap run reports:

```text
delta_declared_path_length = 0
```

If remap changes endpoint path-facing associations, the legacy declared-edge classifier may classify the fixed original path as disrupted. That is not a theorem verdict. It means the dynamic path record/readout must be used before making path-length claims.
