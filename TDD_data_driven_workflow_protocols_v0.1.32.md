# TDD: Data-Driven Workflow Protocols v0.1.32

## Purpose

v0.1.32 modularizes the operator-agent / contract / release workflow layer so small workflow-instruction changes can be patched through protocol data rather than scalar-field kernel code.

The approval-loop procedure is now represented by:

```text
rank3_enforced/protocols/certification_operator_agent_approval_loop_v1.json
```

The Python layer loads, validates, fingerprints, and renders this protocol. It should not be the primary source of approval-loop wording or sequencing.

## Security rules preserved

The protocol explicitly enforces:

```text
no model execution before explicit approval
no silent approval
revision requires revise -> revalidate -> return -> wait again
approval must bind packet hash and plan hash
candidate-to-admission label promotion is forbidden
path add/remove is not intrinsic EAS ontology
```

## New protocol identity

The release manifest includes:

```text
latest_workflow_protocol_sha256
accepted_workflow_protocol_sha256
```

This allows future workflow protocol updates to be identified separately from core framework source-code identity.

## CLI

```bash
rank3-validate-workflow-protocol \
  --protocol-id certification_operator_agent_approval_loop_v1
```

## Expected effect

A future approval-loop wording change should generally affect:

```text
rank3_enforced/protocols/*.json
rank3_enforced/workflow_protocols.py only if validation rules change
tests/test_workflow_protocols_*.py
docs/operator protocol notes
```

It should not require changes to SOO kernels, path construction, remap rules, or scalar-field readouts.
