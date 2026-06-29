# GitHub Install and Publish v0.1.34

Use the version-general publish script from a clean working tree:

```bash
./publish_eas_framework_release.sh 0.1.34
```

Before treating the release as authoritative, re-sign the release manifest locally with the trusted private key. Do not rely on package-embedded demonstration signing material as the user's authoritative release signature.

After installation, verify:

```bash
rank3-check-release-identity
pytest -q
```

v0.1.34 adds theorem-failure diagnostic artifacts and stricter certification blockers. It does not certify the charge path-adjustment theorem.
