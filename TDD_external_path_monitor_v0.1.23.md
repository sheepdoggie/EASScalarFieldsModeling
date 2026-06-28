# TDD: External Path Monitor API v0.1.23

## Problem

Earlier versions risked treating path shortening/lengthening as intrinsic framework rules. That is not EAS-safe.  Path length changes must be exploratory hypotheses, not ontology.

## Design

The framework exposes path records as data and accepts explicit external edit requests.  External code may monitor scalar/path records and request a path edit, but the framework only performs validation and transactional logging.

## Data objects

### `PathMonitorSnapshot`

Read-only snapshot containing:

- path record
- association hash
- scalar-value hash if supplied
- cycle/phase
- center nodes
- active ordered nodes
- path length

### `ExternalPathEditRequest`

External request containing:

- operation: `none`, `remove_node`, or `insert_existing_node`
- path id
- target node/index or new node/index
- monitor fingerprint
- evidence hash
- reason
- required flags:
  - `external_exploratory=True`
  - `ontology_rule=False`

### `ExternalPathEditResult`

Validated transaction containing:

- path before/after
- association after
- geometry transaction report
- `scalar_values_moved=False`

## Security properties

- External callbacks are disabled by default.
- `call_external_path_monitor(..., allow_external_code=True)` must be explicit.
- The request must declare itself exploratory and non-ontological.
- Scalar values are never moved by path edit transactions.
- Result packages must report external monitor use as exploratory/non-certified unless later admitted by separate protocol.

## Non-goals

This API does not certify `Delta L = +/- 1`.  It only makes exploratory path editing possible without adding path changes as framework ontology.
