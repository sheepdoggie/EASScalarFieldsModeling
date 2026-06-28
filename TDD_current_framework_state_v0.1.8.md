# Technical Design Document: Current Framework State v0.1.8

## Version

- Framework version: `0.1.8`
- Release label: `0.1.8-run-debugging-path-neighborhood`

## Purpose of this revision

This revision adds optional run-debugging instrumentation for path-sector investigations while preserving the core EAS constraint that SOO is whole-field and must not treat path points as a privileged scalar-update domain.

The debug module is an overlay-selected instrumentation module. It records scalar changes and association-indexed ordered differences on a declared path and on points connected to that path to a specified association-depth. It does not seed path values, preserve path carriers, alter stiffness, alter association records, or feed back into SOO.

## Ontology guardrail

The framework distinguishes:

```text
path-facing association role:
    which rank-3 association slot lies on the declared diagnostic path

scalar-value carrier status:
    forbidden as a path requirement
```

No framework component may require `Phi(x) != 0` or `Pi_A(x) != 0` merely because `x` belongs to a declared diagnostic path.

## New modules

### `rank3_enforced/path_debugging.py`

Provides:

- `RunDebuggingSpec`
- `PathFacingAssociationReport`
- `RunDebuggingReport`
- `spec_from_optional_modules`
- `build_path_facing_association_report`
- `build_run_debugging_report`

### Optional module ID

```json
{
  "module_id": "run_debugging",
  "status": "experimental_instrumentation",
  "params": {
    "enabled": true,
    "path_neighborhood_depth": 1,
    "include_phi_history": true,
    "include_ordered_differences": true,
    "include_association_rows": true,
    "include_soo_step_report_links": true,
    "max_points": 256
  }
}
```

## New artifacts

### `PATH_FACING_ASSOCIATION_REPORT.json`

Records the declared path-facing association slots and their targets. This report is association-role metadata only.

It explicitly forbids the interpretations:

```text
path_facing_as_scalar_carrier_status
path_points_as_special_SOO_update_domain
nonzero_phi_required_for_path_participation
```

### `RUN_DEBUG_REPORT.json`

Records debug instrumentation over a path neighborhood:

- declared path and anchor points;
- connected points to the requested association-depth;
- layer-by-layer scalar values for debug points;
- transition-level `delta_phi_next_minus_curr`;
- transition-level `Pi_A_curr = Phi_l(x) - Phi_{l-1}(a_theta(x))` when the previous ledger is available;
- association rows for debug points;
- hashes linking to SOO step reports.

This report is not an admission verdict.

## Integration points

### Overlay compiler

The compiler extracts a `RunDebuggingSpec` from optional modules and stores it in the `ModelPackage`.

### Certified runner

After the primary whole-field run completes, the runner builds:

1. `PATH_FACING_ASSOCIATION_REPORT.json`
2. `RUN_DEBUG_REPORT.json` when requested

Both are post-run reports. Neither affects SOO execution.

### Packaging

The signed evidence package now writes both artifacts. Built-in charge suite runs require both artifacts because the built-in overlays request the `run_debugging` optional module.

## Built-in charge suite update

All 34 charge same/opposite overlays now declare the `run_debugging` module with `path_neighborhood_depth=1`. This makes the latest suite retain the data needed to inspect SOO behavior on the path and on the immediately associated neighborhood.

## Status

Implemented:

- optional run-debugging module;
- path-facing association report;
- path-neighborhood scalar and SOO-difference traces;
- installed suite integration;
- updated tests.

Not implemented:

- no path-special SOO;
- no active scalar carrier seeding;
- no path-adjustment/remap certification rule;
- no completed stiffness feedback closure gate.

## Correct interpretation

The debug module enables diagnosis of failures such as broad zeroing, nonlocalized cancellation, and unchanged declared path records. It does not make those failures admissible or inadmissible by itself. Any future `Delta L` claim still requires a relational/path-record accommodation certificate, not scalar-zero evidence alone.
