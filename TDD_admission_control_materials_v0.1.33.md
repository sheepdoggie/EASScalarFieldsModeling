# TDD: Admission/Control Materials v0.1.33

v0.1.33 supplies concrete framework materials requested by the operator-agent approval loop for the charge path-adjustment certification workflow.

## Scope

This release adds executable admission/control overlays and mechanism declarations. It does not admit the theorem. A completed run may still produce Ambiguous or Rejected verdicts.

## Added materials

- `charge_path_admission_controls_v0_1` built-in overlay suite.
- `charge_path_admission_mechanisms_v0_1` mechanism declaration.
- `admitted_nonlabel_path_monitor_v1` optional module policy.
- Required negative controls: `no_remap_control`, `wrong_continuation_slot_control`, `broken_path_control`, `label_swap_control`, `sign_randomized_control`.
- Package-embedded release public key/signature materials for self-consistency; operators should re-sign trusted releases locally.

## Non-leakage rule

The non-label path monitor policy may inspect signed scalar records and active path records. It may not read same/opposite labels, target Delta L labels, or trigger path edits by orientation label. Path add/remove remains an external transaction, not EAS ontology.
