# TDD: Operator-Agent Approval Loop (v0.1.31)

## Purpose

v0.1.31 repairs the v0.1.30 ambiguity in which `OPERATOR_REQUIRED_ITEMS.json` could be read as user/operator homework. The framework now treats the modeling chat as an operator-agent that must draft draftable certification materials, mark non-inventable materials honestly, validate the customized packet, and return the packet to the user/operator for explicit approval before any certification-mode model execution.

## Required workflow

1. A certification preflight or synthesis step writes `OPERATOR_REQUIRED_ITEMS.json`.
2. The modeling chat runs `rank3-generate-operator-review-packet`.
3. The modeling chat runs `rank3-customize-operator-review-packet` or performs equivalent customization.
4. The modeling chat drafts every draftable item.
5. Non-inventable items are marked absent/non-certification-usable; they are not fabricated.
6. The modeling chat validates the customized packet with `rank3-validate-operator-review-packet`.
7. The modeling chat returns the customized packet and validation report to the user/operator.
8. The modeling chat waits for explicit `approve`, `revise`, or `reject`.
9. If `revise`, the packet must be revised, revalidated, returned, and approval awaited again.
10. If `reject`, certification stops.
11. If `approve`, a `USER_APPROVAL_DECISION.json` must bind the approved packet hash and approved modeling plan hash.
12. Certification modeling may begin only after approval validation reports `approved_for_modeling=true`.

## Forbidden behavior

- Model execution before explicit approval.
- Treating silence, template generation, or partial assent as approval.
- Running after a revision request without revision, validation, return, and renewed approval.
- Label promotion from candidate to admission evidence.
- Intrinsic framework path-length change rules.

## New commands

```bash
rank3-customize-operator-review-packet \
  --review-packet-dir OPERATOR_REVIEW_PACKET \
  --output-dir CUSTOMIZED_REVIEW_PACKET

rank3-validate-operator-review-packet \
  --packet-dir CUSTOMIZED_REVIEW_PACKET \
  --output CUSTOMIZED_REVIEW_PACKET/CUSTOMIZED_PACKET_VALIDATION_REPORT.json
```

With approval:

```bash
rank3-validate-operator-review-packet \
  --packet-dir CUSTOMIZED_REVIEW_PACKET \
  --approval-decision USER_APPROVAL_DECISION.json
```

## New artifacts

- `CHAT_APPROVAL_LOOP_PROTOCOL.md`
- `CHAT_TASKS.json`
- `GENERATE_CUSTOMIZED_REVIEW_PACKET.sh`
- `CUSTOMIZED_REVIEW_PACKET_MANIFEST.json`
- `CUSTOMIZATION_DECISION_TABLE.json`
- `APPROVAL_LOOP_PROTOCOL.json`
- `USER_APPROVAL_DECISION_TEMPLATE.json`
- `CUSTOMIZED_PACKET_VALIDATION_REPORT.json`

## Evidential status

This release does not certify the charge path-adjustment theorem. It strengthens the certification workflow so a modeling chat cannot reasonably skip the approval loop.
