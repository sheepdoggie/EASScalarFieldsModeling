# Current framework state v0.1.21

Version 0.1.21 adds role/path-preserving remap and gated dynamic path-length infrastructure.

## Added

- `rank3_enforced.dynamic_paths`
- `rank3_enforced.role_path_remap`
- registered remap rule `path_continuation_role_remap_v1`
- `RelationalPathRecord`
- `DressingRoleMap`
- `PathChangeAdmission`
- `GeometryTransactionReport`
- gated `shorten_path_record`
- gated `lengthen_path_record`
- tests for orientation-aware remap, role exchange, registry construction, and admission-gated path mutation

## Corrected design point

The framework no longer requires path remap to follow the same numeric slot everywhere. For a two-ended path:

- left endpoint continuation follows the registered path toward the right endpoint;
- right endpoint continuation follows the registered path toward the left endpoint;
- the boundary-facing slot is fixed;
- path/vacuum roles may exchange if explicitly enabled.

## What remains candidate

- `path_continuation_role_remap_v1` is candidate infrastructure, not an admitted EAS remap law.
- `shorten_path_record` and `lengthen_path_record` require explicit admission gates.
- even-path center-pair shortening is intentionally not implemented as a default rule.

## Validation

The package was validated with:

```text
python -m compileall: pass
pytest: 45 passed
```
