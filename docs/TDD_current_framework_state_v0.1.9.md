# Technical Design Document: Current Framework State v0.1.9

## Release identity

- Framework version: `0.1.9`
- Release label: `0.1.9-debug-opt-in-progress`
- Primary purpose of this revision: make run-debugging instrumentation opt-in, keep built-in suites debug-free by default, and add visible progress reporting to installed run-manager commands.

## Design correction in this revision

Version `0.1.8` made the run-debugging module available but also enabled it in the built-in charge overlays. That was incorrect. Debug instrumentation is not part of SOO, not part of ordinary candidate execution, and not part of the default charge suite.

Version `0.1.9` corrects that by enforcing the following rules:

1. Debugging is off by default.
2. Built-in suites do not contain an enabled `run_debugging` module.
3. Debugging is added only when explicitly requested through a run-manager command, for example `rank3-run-suite --debug`.
4. Debugging produces `RUN_DEBUG_REPORT.json`; non-debug runs are not required to produce it.
5. Debugging remains instrumentation only. It cannot seed scalar values, alter SOO, alter stiffness, alter associations, or affect admission verdicts.

## Installed run-manager workflow

Normal non-debug run:

```bash
rank3-run-suite charge_same_opposite_association_indexed \
  --output-root runs/charge_same_opposite_assoc_soo \
  --signing-key ~/.rank3/private_key.pem
```

Debug run, explicitly requested:

```bash
rank3-run-suite charge_same_opposite_association_indexed \
  --output-root runs/charge_same_opposite_assoc_soo_debug \
  --signing-key ~/.rank3/private_key.pem \
  --debug \
  --debug-depth 1 \
  --debug-max-points 256
```

The installed run manager now prints progress messages:

```text
[suite] charge_same_opposite_association_indexed
[suite] overlays=34 output=...
[release-guard] checking latest signed framework manifest
[release-guard] passed=True cache=...
[debug] off
[1/34] START L16_opposite_association_indexed_soo
[1/34] PASS  L16_opposite_association_indexed_soo elapsed=...
...
[suite] finished passed=34 failed=0 total=34
```

## Module inventory added or revised

### `rank3_enforced.run_manager`

Revised behavior:

- Adds progress output during suite execution.
- Adds explicit debug staging through `stage_overlay_with_debug`.
- Removes `RUN_DEBUG_REPORT.json` from required artifacts for ordinary charge-suite runs.
- Adds `RUN_DEBUG_REPORT.json` to required artifacts only when `debug=True`.
- Stages debug overlays under `.rank3_staged_overlays/` so the built-in overlays remain clean and debug-free.

### `rank3_enforced.run_suite_cli`

New arguments:

```text
--debug
--debug-depth N
--debug-max-points N
--quiet
```

### `rank3_enforced.run_overlay_cli`

New arguments:

```text
--debug
--debug-depth N
--debug-max-points N
```

### `rank3_enforced.path_debugging`

Revised behavior:

- `run_debugging` is not enabled merely by the module schema existing.
- `spec_from_optional_modules` returns a debug spec only when `params.enabled` is explicitly `true`.
- The debug report remains path-neighborhood SOO instrumentation only.

## Built-in suite changes

The built-in suite remains:

```text
charge_same_opposite_association_indexed
```

The 34 overlays remain installed as package data:

```text
rank3_enforced/overlay_suites/charge_same_opposite_association_indexed/*.json
```

But their `optional_modules` now include only:

```text
soo_stiffness_feedback
charge_attraction_repulsion
```

They do not include enabled `run_debugging` by default.

## Required artifacts for ordinary charge-suite runs

Ordinary non-debug charge-suite runs require:

```text
CERTIFICATE.json
EVIDENCE_ENVELOPE.json
INITIAL_TWO_LEDGER_REPORT.json
OPTIONAL_MODULE_REPORT.json
SOO_EXECUTION_REPORT.json
CYCLIC_RETURN_REPORT.json
STIFFNESS_INPUT_REPORT.json
RESPONSE_BURDEN_REPORT.json
INDUCED_STIFFNESS_REPORT.json
STIFFNESS_CLOSURE_REPORT.json
STIFFNESS_FEEDBACK_REPORT.json
SOO_FUNCTIONAL_REPORT.json
PATH_FACING_ASSOCIATION_REPORT.json
```

`RUN_DEBUG_REPORT.json` is required only when debug is explicitly enabled.

## EAS guardrail preserved

Path-facing remains association-role metadata only. It is not scalar-carrier status. The debugging module may inspect a path neighborhood, but it must not make path points special for SOO.

The debugging module is therefore forbidden to:

```text
seed path-carrier scalar values
preserve path points
alter SOO updates
alter K_theta
alter associations
feed into readout verdicts
make path points a special update domain
```

## Validation status

- Test suite: `30 passed`
- New tests verify:
  - built-in charge overlays compile without debug enabled;
  - ordinary runs produce no debug report object;
  - explicit debug staging does produce a debug report;
  - all previous association-indexed SOO, two-ledger, path-facing, and installed-suite behavior still passes.

## Known limitations

1. Stiffness feedback remains a placeholder/diagnostic handle. Default `K_theta = I` is used when feedback is not under test.
2. The charge same/opposite overlays remain candidate/exploratory, not admitted evidence.
3. Delta-L/path accommodation still requires relational/path-record certification beyond scalar center-zero observations.
4. The framework still needs a relational path-adjustment gate that rejects scalar-only Delta-L interpretations.
