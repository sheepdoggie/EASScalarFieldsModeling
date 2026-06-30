# GitHub install and publish notes for v0.1.36

v0.1.36 is an exploratory framework release for split-vacuum triangle emergence and downstream relational path-accommodation diagnostics. It is not a certification release.

After placing `EASScalarFieldsModeling_v0.1.36_github_package.zip` in `~/Projects/EASScalarFieldsModeling_github_files/`, publish with:

```bash
cd ~/Projects
YES=1 ./publish_eas_framework_release.sh 0.1.36
```

Do not use `SKIP_TESTS=1` for an authoritative publish.
