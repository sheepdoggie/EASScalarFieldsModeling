# Role/path remap and dynamic path-length infrastructure v0.1.22

Version 0.1.22 refines the v0.1.21 role/path-remap infrastructure by adding a theorem-capable charge suite and a role/path-specific path constructor.

## New constructor

```text
role_path_two_support_v0_1
```

This constructor preserves the EAS dressing-role structure:

```text
boundary-facing dressing slot fixed
path-facing role remappable
vacuum-facing role remappable
```

## Updated remap validation

`path_continuation_role_remap_v1` no longer assumes that the path-facing target is always the path node immediately adjacent to the endpoint. After remap, the path-facing target may be an interior node farther along the registered path or the opposite endpoint saturation point.

This avoids the v0.1.21 error mode in which repeated remap would fail validation after the first endpoint advance.

## Dynamic path mutation

Path mutation remains gated infrastructure. No built-in charge suite forces `Delta L`.

## Required next step

Use v0.1.22 to run the role/path suite, audit the scalar midpoint readouts, and then design scalar-record-only admission gates for path shortening/lengthening.
