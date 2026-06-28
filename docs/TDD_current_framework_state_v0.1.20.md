# Current framework state v0.1.20

Version 0.1.20 packages the v0.1.19 publication-certified run mode in a GitHub-installable repository layout.

## Packaging repair

The repository root is now directly installable with:

```bash
python -m pip install -e .
pytest -q
```

The release bundle also includes a versioned framework archive under:

```text
releases/current/enforceable_rank3_modeling_v0.1.20_publication_certified_run.zip
```

## Security status

Publication-certified run mode remains the required path for evidential runs. The GitHub package format does not by itself admit scientific claims; it provides reproducible source installation, release-manifest checking, and versioned packaging.
