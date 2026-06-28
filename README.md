# EASScalarFieldsModeling

Current framework release: `0.1.20` / `0.1.20-github-installable-publication-certified-run`.

This repository is GitHub-installable and also carries a versioned release ZIP under `releases/current/`.

## Install from source checkout

```bash
python -m pip install --upgrade pip
python -m pip install -e .
pytest -q
```

## Install from GitHub after publish

```bash
python -m pip install "git+https://github.com/sheepdoggie/EASScalarFieldsModeling.git@v0.1.20#egg=enforceable-rank3-modeling"
```

## Install from the versioned release archive

```bash
python -m pip install --force-reinstall releases/current/enforceable_rank3_modeling_v0.1.20_publication_certified_run.zip
rank3-check-release-guard --force-refresh
```

## Publication-certified run mode

Generate keys:

```bash
rank3-generate-signing-key --private-key ~/.rank3/private_key.pem --public-key ~/.rank3/public_key.pem
rank3-generate-encryption-key --private-key ~/.rank3/recipient_private_key.pem --public-key ~/.rank3/recipient_public_key.pem
```

Run a publication-certified overlay:

```bash
rank3-run-publication-certified overlays/minimal_candidate_overlay.json runs/example_pubcert \
  --signing-key ~/.rank3/private_key.pem \
  --recipient-public-key ~/.rank3/recipient_public_key.pem
```

Verify:

```bash
rank3-verify-publication-certified runs/example_pubcert
rank3-verify-publication-certified runs/example_pubcert --recipient-private-key ~/.rank3/recipient_private_key.pem
```

## Release manifest

The current release manifest is:

```text
releases/current/FRAMEWORK_RELEASE_MANIFEST.json
```

This package is unsigned until a maintainer signs `FRAMEWORK_RELEASE_MANIFEST.json` and adds:

```text
releases/current/FRAMEWORK_RELEASE_MANIFEST.sig
releases/current/FRAMEWORK_RELEASE_PUBLIC_KEY.pem
```

Unsigned packages are suitable for source review and local testing, not publication-grade external admission.
