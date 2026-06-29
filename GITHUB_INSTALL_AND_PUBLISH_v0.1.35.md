# GitHub Install and Publish: v0.1.35

Use the existing version-general publisher:

```bash
YES=1 ./publish_eas_framework_release.sh 0.1.35
```

Expected package name:

```text
EASScalarFieldsModeling_v0.1.35_github_package.zip
```

Expected internal release archives:

```text
releases/current/enforceable_rank3_modeling_v0.1.35_gradient_vacuum_split_planning.zip
releases/current/enforceable_rank3_modeling_v0.1.35_gradient_vacuum_split_planning.tar.gz
```

The publish script should install editable package metadata as `enforceable-rank3-modeling==0.1.35`, run tests, check release identity, sign the manifest locally, verify the signature, check for private keys, commit, push, tag, and push the tag.

Re-sign locally with your trusted private key before treating a GitHub release as authoritative.
