# EASScalarFieldsModeling

Current framework release: `0.1.31` / `0.1.31-operator-agent-approval-loop`.

v0.1.31 adds the operator-review packet workflow. A certification-mode run that lacks required operator materials writes `OPERATOR_REQUIRED_ITEMS.json` with a recommended `rank3-generate-operator-review-packet` command. The modeling chat should generate/customize that packet and return it for user approval before execution.

Install after publishing:

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.31#egg=enforceable-rank3-modeling"
```

Generate a review packet from a blocked certification preflight:

```bash
rank3-generate-operator-review-packet \
  --contract overlays/charge_path_adjustment_contract.json \
  --operator-required-items results/charge_path_attempt/OPERATOR_REQUIRED_ITEMS.json \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --output-dir review_packets/charge_path_v0130
```

This does not run the model. It creates reviewable templates for admission overlays, mechanism declarations, initialization/settling, negative controls, path monitor policy, plan approval, and release signing.

The current built-in charge role/path suite remains candidate/exploratory and does not certify the charge path-adjustment theorem.

## v0.1.31 operator-agent approval loop

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
