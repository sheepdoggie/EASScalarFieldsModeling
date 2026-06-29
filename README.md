# EASScalarFieldsModeling

Current framework release: `0.1.30` / `0.1.30-operator-review-packet-workflow`.

v0.1.30 adds the operator-review packet workflow. A certification-mode run that lacks required operator materials writes `OPERATOR_REQUIRED_ITEMS.json` with a recommended `rank3-generate-operator-review-packet` command. The modeling chat should generate/customize that packet and return it for user approval before execution.

Install after publishing:

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.30#egg=enforceable-rank3-modeling"
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
