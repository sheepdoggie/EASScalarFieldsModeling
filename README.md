# EASScalarFieldsModeling

Current framework release: `0.1.29` / `0.1.29-contract-driven-overlay-synthesis`.

v0.1.29 adds contract-driven overlay synthesis and operator-required-items reporting. Certification mode still requires a predeclared modeling_intent contract, an approved modeling plan, signed release identity, and contract-compliant executable overlays.

## Install

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.29#egg=enforceable-rank3-modeling"
```

## Synthesize or request overlays from a contract

```bash
rank3-synthesize-overlays-from-contract \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --output-overlays overlays/synthesized_charge_path_v0129
```

This command does not run SOO. If the selected overlays cannot satisfy the contract, it writes `OPERATOR_REQUIRED_ITEMS.json` explaining what the operator must provide.

## Generate a reviewable plan

```bash
rank3-plan-from-modeling-intent \
  --suite-id charge_role_path_remap_dynamic_path_v0_1 \
  --contract overlays/charge_path_adjustment_contract.json \
  --synthesize-overlays \
  --output-plan plans/charge_path_draft_plan_v0129.json \
  --output-overlays overlays/synthesized_charge_path_v0129
```

## Certification execution

Certification execution requires:

```text
--modeling-intent-contract
--approved-plan
signed release manifest/signature/public key/framework zip
```

If required items are absent, the run writes `OPERATOR_REQUIRED_ITEMS.json` and stops before model execution.
