# Role/path remap and dynamic path-length infrastructure v0.1.21

## Purpose

Version 0.1.21 adds framework-level infrastructure required to express EAS-conformant path remapping and gated path-length changes without ad hoc runner code.

The immediate correction is that path remap is no longer interpreted as a fixed numeric-slot operation such as "follow slot 1 everywhere." Dressing remap is role based:

- one dressing slot is boundary-facing and fixed;
- one non-boundary slot carries the path-facing role;
- one non-boundary slot carries the vacuum-facing role;
- path/vacuum roles may exchange only when explicitly configured;
- scalar values are not moved by remap.

## New registered remap rule

`path_continuation_role_remap_v1`

This candidate rule accepts only data parameters:

```json
{
  "path_records": [
    {
      "path_id": "lane0",
      "left_endpoint": 0,
      "right_endpoint": 4,
      "ordered_nodes": [1, 2, 3],
      "lane_id": "0"
    }
  ],
  "dressing_roles": [
    {
      "point": 0,
      "boundary_slot": 0,
      "path_slot": 1,
      "vacuum_slot": 2,
      "path_id": "lane0",
      "endpoint_side": "left",
      "allow_path_vacuum_exchange": false
    },
    {
      "point": 4,
      "boundary_slot": 0,
      "path_slot": 1,
      "vacuum_slot": 2,
      "path_id": "lane0",
      "endpoint_side": "right",
      "allow_path_vacuum_exchange": false
    }
  ],
  "cadence": 10
}
```

The continuation is orientation aware:

- left endpoint advances toward the right endpoint;
- right endpoint advances toward the left endpoint.

This prevents the previous invalid configuration in which the same numeric slot was followed on both sides of a two-ended path.

## Dynamic path records

The new `dynamic_paths.py` module provides:

- `RelationalPathRecord`
- `DressingRoleMap`
- `PathChangeAdmission`
- `GeometryTransactionReport`
- `shorten_path_record`
- `lengthen_path_record`

These are framework data structures and transaction helpers. They do not certify a physical path change by themselves.

## Gated path-length mutation

Path length changes are available only through explicit gate records.

Rejected operation:

```text
orientation == opposite -> shorten path
```

Allowed framework form:

```text
SOO/readout/admission gate produces PathChangeAdmission(admitted=True, ...)
then a registered transaction may produce L -> L - 1 or L -> L + 1.
```

`shorten_path_record` currently handles odd single-center paths. Even center-pair collapse remains intentionally rejected pending a separate center-pair rule.

`lengthen_path_record` inserts an existing spare/vacuum point into the active ordered path record. It does not create a new scalar point and does not move scalar values.

## Audit constraints

All geometry transactions report:

- association hash before;
- association hash after;
- affected points;
- path hash before;
- path hash after;
- delta L;
- admission hash;
- scalar_values_moved = false.

## Certification status

These rules are candidate infrastructure. They are not admitted EAS laws. Publication-certified scientific runs must still include blind generation/projection separation, controls, label-independence checks, and signed evidence packages.
