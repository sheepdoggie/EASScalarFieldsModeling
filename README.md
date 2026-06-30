# EASScalarFieldsModeling

Current framework release: `0.1.42` / `0.1.42-vacuum-admissibility-variation`.


## v0.1.42 vacuum-admissibility variation

v0.1.42 adds `rank3-run-vacuum-admissibility-variation` and `rank3-write-vacuum-admissibility-packet`. This release treats v0.1.41 as a useful endpoint-class separation diagnostic, not an emergence model, because its triangle, photon-like, and bounded-support records did not share the same provenance.

The v0.1.42 runner starts every candidate from the same chain:

```text
undefined vacuum -> split/lift -> SOO -> association selection -> motif discovery -> post-run classification
```

It varies five admissibility regimes: pure scalar-gradient, split-conjugacy preserving, relation-complete burden, successor-covariant cyclic, and bounded-support closure. Photon-like records, [0,q,-q] transverse forms, path-facing zero layers, bounded-support calibration endpoints, predeclared triangles, predeclared paths, Standard Model labels, and expected Delta L are forbidden generator inputs.

Required reports include the vacuum admissibility variant ledger, split/lift ledger, full-field SOO trace, association burden decomposition, post-run photon-like certifier, triangle scaffold report, bounded-support closure report, path-facing residual discovery, path accommodation by provenance, and Standard Model interface quarantine.

Commands:

```bash
rank3-write-vacuum-admissibility-packet --output vacuum_admissibility_variation_approval_items_v0142.zip --print-summary
rank3-run-vacuum-admissibility-variation --output-root vacuum_admissibility_variation_results_v0142 --zip vacuum_admissibility_variation_results_v0142.zip
```

This release is exploratory only. It does not certify photons, charge, bounded supports, Standard Model particles, or a path-accommodation theorem.

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


## v0.1.38 endpoint-class path-response separation

v0.1.38 adds an exploratory endpoint-class separation runner. It compares emergent sign-coherent triangle endpoints, locally certified photon-like records, and bounded/support-like sign-coherent endpoint candidates. Center conditions are classified from generated path scalar profiles only, not from endpoint class, charge labels, Standard Model labels, or target Delta L. This release is exploratory only and does not certify charge, photons, lepton supports, or path accommodation.

Commands:

```bash
rank3-write-endpoint-class-separation-packet --output endpoint_class_path_response_separation_approval_items_v0138.zip --print-summary
rank3-run-endpoint-class-separation --output-root endpoint_class_path_response_separation_results_v0138 --zip endpoint_class_path_response_separation_results_v0138.zip
```
