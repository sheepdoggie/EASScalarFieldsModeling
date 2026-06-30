# EASScalarFieldsModeling

Current framework release: `0.1.33` / `0.1.33-admission-control-materials`.

v0.1.33 adds executable admission/control materials requested by the operator-agent workflow: a non-candidate whole-field SOO mechanism declaration, a non-label path-monitor policy declaration, a charge-path admission/control overlay suite, required negative controls, and package-embedded release signature/public-key files for self-consistency. It still does not certify the charge path-adjustment theorem.

Install after publishing:

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.33#egg=enforceable-rank3-modeling"
```

Run the admission/control planning surface from the run directory:

```bash
rank3-plan-from-modeling-intent \
  --suite-id charge_path_admission_controls_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --synthesize-overlays \
  --output-plan plans/charge_path_admission_plan_v0133.json \
  --output-overlays overlays/charge_path_admission_controls_v0133
```

This does not certify the theorem. It creates a reviewable plan using the executable admission/control materials. The older `charge_role_path_remap_dynamic_path_v0_1` suite remains candidate/exploratory.

## v0.1.33 operator-agent approval loop

Certification preparation now follows a strict approval loop. When a certification run is blocked by missing materials, the modeling chat should generate an operator review packet, customize all draftable materials, validate the customized packet, return it to the user/operator, and wait for explicit approval. If revisions are requested, the packet must be revised, revalidated, returned, and approval awaited again. Modeling may begin only after approval validation binds the approved packet hash and approved plan hash.

Commands:

```bash
rank3-generate-operator-review-packet --contract overlays/contract.json --operator-required-items results/attempt/OPERATOR_REQUIRED_ITEMS.json --output-dir review_packets/packet
rank3-customize-operator-review-packet --review-packet-dir review_packets/packet --output-dir review_packets/customized
rank3-validate-operator-review-packet --packet-dir review_packets/customized --output review_packets/customized/CUSTOMIZED_PACKET_VALIDATION_REPORT.json
```

With approval:

```bash
rank3-validate-operator-review-packet --packet-dir review_packets/customized --approval-decision review_packets/customized/USER_APPROVAL_DECISION.json
```

## v0.1.33 admission/control materials

New suite:

```text
charge_path_admission_controls_v0_1
```

Required controls included as executable overlays:

```text
no_remap_control
wrong_continuation_slot_control
broken_path_control
label_swap_control
sign_randomized_control
```

List mechanism declarations:

```bash
rank3-list-admission-mechanisms
```

The non-label path monitor policy may inspect signed scalar/path records only. It may not read same/opposite labels or trigger path edits from orientation labels. Path add/remove remains an external transaction, not EAS ontology.

## v0.1.35 planning release

v0.1.35 adds a gradient-governed vacuum-split path-accommodation planning layer. It freezes A1-A7 admissibility candidates, separates H1-H5 as theorem-facing proof obligations rather than primitive rules, adds generator/readout separation constraints, and packages mandatory controls/audit gates for operator approval. It is not a theorem-certifying release.

To generate the approval-items ZIP:

```bash
rank3-write-gradient-path-accommodation-packet --output gradient_path_accommodation_approval_items_v0135.zip --print-summary
```


## v0.1.37 exploratory split-vacuum triangle emergence

v0.1.37 adds `rank3-run-split-vacuum-triangle-emergence` and `rank3-write-split-vacuum-triangle-packet`. This is an exploratory mechanism-discovery release only. Triangle membership and path endpoints are readouts, not generator inputs, and the release does not certify a theorem or charge.
