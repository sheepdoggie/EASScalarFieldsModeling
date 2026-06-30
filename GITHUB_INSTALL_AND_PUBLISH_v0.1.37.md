# GitHub install and publish notes for v0.1.37

v0.1.37 is an exploratory runner-repair release. It is not a certification release.

After placing `EASScalarFieldsModeling_v0.1.37_github_package.zip` in `~/Projects/EASScalarFieldsModeling_github_files/`, publish with:

```bash
cd ~/Projects
YES=1 ./publish_eas_framework_release.sh 0.1.37
```

Do not use `SKIP_TESTS=1` for the authoritative publish.
