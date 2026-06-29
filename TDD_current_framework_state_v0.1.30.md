# Current Framework State v0.1.30

v0.1.30 adds the operator-review packet workflow.

Certification mode now has these layers:

```text
modeling_intent contract
approved modeling plan
plan executability gate
release identity/signature gate
operator-required-items report
operator-review packet generator
```

If certification preflight lacks required materials, the framework writes `OPERATOR_REQUIRED_ITEMS.json` with a recommended `rank3-generate-operator-review-packet` command. The modeling chat should run that generator, customize the resulting templates for the model, and return them to the operator/user for approval before modeling.

The current charge role/path suite remains candidate/exploratory. This release does not certify the charge path-adjustment theorem.
