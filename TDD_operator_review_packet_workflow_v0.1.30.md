# TDD: Operator Review Packet Workflow v0.1.30

## Purpose

v0.1.30 implements the workflow in which a modeling chat is expected to prepare the certification materials for operator/user approval before any model execution.

The framework now supports this sequence:

```text
modeling request
-> modeling_intent contract
-> synthesis/preflight reports missing operator-required items
-> framework directs the modeling chat to a review-packet generator
-> modeling chat generates and customizes templates
-> operator/user reviews and approves the exact plan
-> certification execution may proceed only after approval and validation
```

## Non-goals

This release does not certify the charge path-adjustment theorem. It does not create admitted mechanisms by relabeling candidate mechanisms. It does not make path add/remove intrinsic EAS ontology.

## New command

```bash
rank3-generate-operator-review-packet \
  --contract overlays/charge_path_adjustment_contract.json \
  --operator-required-items results/attempt/OPERATOR_REQUIRED_ITEMS.json \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --output-dir review_packets/charge_path_v0130
```

This command writes reviewable templates but does not run SOO/model execution.

## New artifacts

```text
OPERATOR_REVIEW_PACKET_MANIFEST.json
OPERATOR_REVIEW_PACKET_MANIFEST.sha256
CHAT_MODELING_INSTRUCTIONS.md
ADMISSION_OVERLAY_TEMPLATE.json
MECHANISM_STATUS_DECLARATION_TEMPLATE.json
INITIALIZATION_SETTLING_REQUIREMENTS_TEMPLATE.json
NEGATIVE_CONTROL_SUITE_TEMPLATE/README.md
NEGATIVE_CONTROL_SUITE_TEMPLATE/negative_control_overlay_template.json
PATH_MONITOR_POLICY_TEMPLATE.json
MODELING_PLAN_APPROVAL_REQUEST_TEMPLATE.json
RELEASE_SIGNING_CHECKLIST.md
USER_APPROVAL_CHECKLIST.md
```

## Enforcement

`OPERATOR_REQUIRED_ITEMS.json` now includes:

```text
recommended_generator_command
recommended_generator_outputs
per-item generator fields
per-item review_artifacts fields
```

Thus a blocked certification preflight tells the modeling chat what to generate next, instead of merely saying that inputs are missing.

## Security boundary

The packet is a review scaffold. Any placeholder-bearing template is non-executable. The modeling chat must customize the templates, generate a draft plan, and return the customized packet for approval. Certification execution still requires an approved plan hash.
