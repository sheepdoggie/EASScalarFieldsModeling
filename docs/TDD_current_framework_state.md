# Current Framework State

Current release: v0.1.23 / `0.1.23-external-path-monitor-workspace-layout`.

v0.1.23 changes path-length treatment: path add/remove is not intrinsic EAS ontology and is not an automatic framework rule.  The framework exposes an exploratory external path-monitor API that can request path edits; the framework validates/logs the transaction without moving scalar values.

The release manifest now includes:

- `latest_framework_code_sha256`
- `accepted_framework_code_sha256`

The workspace helper now supports separated install/run subtrees.
