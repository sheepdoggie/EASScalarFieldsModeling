# TDD: Theorem Failure Diagnostics v0.1.34

v0.1.34 adds a diagnostic-only causal trace layer for charge path-adjustment certification attempts.

The added artifacts are:

- `EFFECTIVE_ORIENTATION_RECORD.json`
- `PATH_MONITOR_DECISION_REPORT.json`
- `PATH_EDIT_ADMISSION_REPORT.json`
- `GEOMETRY_TRANSACTION_REPORT.json`
- `ACTIVE_PATH_RECORD_REPORT.json`
- `THEOREM_FAILURE_TRACE.json`

These artifacts explain the causal chain from support packet readout through center scalar condition, monitor decision, path-edit request/admission, geometry transaction, active/declared path records, and final Delta-L readout.

The layer is explicitly diagnostic-only. It does not add path points, remove path points, alter scalar values, or convert same/opposite labels into theorem outcomes.

Additional certification blockers:

- `admitted_nonlabel_path_monitor_v1` rejects all forbidden decision inputs: `orientation`, `same_label`, `opposite_label`, and `target_delta_l`.
- `candidate_not_admitted=true` in a primitive execution report blocks certification.
- If a certification contract requires steady/recurrent initialization, absent or disabled initialization-settling evidence blocks certification.
- Failed certification attempts remain packageable so the signed artifact can explain why they did not certify.

Scientific status: v0.1.34 does not certify the charge path-adjustment theorem.
