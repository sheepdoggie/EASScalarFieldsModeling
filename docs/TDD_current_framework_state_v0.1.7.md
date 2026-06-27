# Technical Design Document: Current Framework State v0.1.7

## 1. Release identity

- Framework version: `0.1.7`
- Release label: `0.1.7-installed-run-manager`
- Package name: `enforceable-rank3-modeling`

This revision reorganizes run execution so candidate/admission work uses installed console commands and code-free run workspaces. It preserves the locked association-indexed SOO core introduced in v0.1.5 and the support-seeded two-ledger charge modules introduced in v0.1.6.

## 2. Design problem addressed

Earlier revisions required users to copy top-level scripts and overlays from an extracted framework source tree. That created a repeated failure mode:

1. The release guard passed for the installed package.
2. A run script was executed inside an extracted source tree.
3. Python imported `./rank3_enforced/` from the source tree instead of the installed signed package.
4. The release guard correctly failed because the executed code hash did not match the signed manifest.

This revision separates:

```text
installed framework package  -> executable code and built-in overlay suites
run workspace                -> code-free results/logs/manifests only
external overlays             -> optional JSON-only overlay directories
```

The user no longer needs to run `python run_signed_declarative_overlay.py ...` from an extracted framework directory.

## 3. Architectural principles

1. **No source-tree execution for candidate/admission runs.** Candidate/admission runs should use installed console commands.
2. **Code-free run workspaces.** Run directories must not contain `rank3_enforced/`.
3. **Built-in suites are package data.** Standard overlay suites are installed with the package and loaded by name.
4. **External overlays remain JSON-only.** Experimental overlays may be supplied by directory, but they are still data-only overlays.
5. **Release guard remains mandatory.** Suite and overlay commands call the release guard before execution.
6. **Signed evidence packaging remains unchanged.** Each overlay run still emits signed packages with certificates and evidence envelopes.

## 4. New modules

### 4.1 `rank3_enforced.run_manager`

Purpose: central run orchestration for installed-package execution.

Primary responsibilities:

- define built-in overlay suites;
- list suite metadata;
- locate packaged overlay resources;
- initialize code-free workspaces;
- run one signed overlay case;
- run a complete overlay suite;
- write `SUITE_RUN_REPORT.json`;
- write package-level `SHA256SUMS.csv`.

Important objects:

```text
BuiltinSuite
OverlayRunRecord
SuiteRunReport
```

Important functions:

```text
list_builtin_suites()
overlay_files_from_source(...)
write_workspace(path)
run_signed_overlay_case(...)
run_overlay_suite(...)
```

### 4.2 Console-entry modules

```text
rank3_enforced.run_overlay_cli
rank3_enforced.run_suite_cli
rank3_enforced.list_suites_cli
rank3_enforced.init_workspace_cli
```

These are thin CLI wrappers around `run_manager`.

## 5. New console commands

### 5.1 `rank3-init-workspace`

Creates a code-free run workspace:

```bash
rank3-init-workspace charge_assoc_workspace
```

Creates:

```text
README.md
SUITES.json
runs/
logs/
```

It intentionally does not copy `rank3_enforced/`.

### 5.2 `rank3-list-suites`

Lists installed built-in overlay suites:

```bash
rank3-list-suites
rank3-list-suites --json
```

### 5.3 `rank3-run-suite`

Runs a built-in or external suite:

```bash
rank3-run-suite charge_same_opposite_association_indexed \
  --output-root runs/charge_same_opposite_assoc_soo \
  --signing-key ~/.rank3/private_key.pem
```

External JSON-only overlays:

```bash
rank3-run-suite --overlays-dir path/to/overlays \
  --output-root runs/custom_suite \
  --signing-key ~/.rank3/private_key.pem
```

Default behavior is fail-fast. Use `--continue-on-failure` to run remaining overlays after a failed case.

### 5.4 `rank3-run-overlay`

Runs one overlay:

```bash
rank3-run-overlay path/to/overlay.json runs/case_id \
  --signing-key ~/.rank3/private_key.pem
```

## 6. Built-in overlay suite package data

The framework now packages:

```text
rank3_enforced/overlay_suites/charge_same_opposite_association_indexed/*.json
```

The suite ID is:

```text
charge_same_opposite_association_indexed
```

It contains 34 overlays:

```text
L16-L32 same
L16-L32 opposite
```

The suite runner requires these artifacts for the built-in charge suite:

```text
CERTIFICATE.json
EVIDENCE_ENVELOPE.json
INITIAL_TWO_LEDGER_REPORT.json
OPTIONAL_MODULE_REPORT.json
SOO_EXECUTION_REPORT.json
CYCLIC_RETURN_REPORT.json
STIFFNESS_INPUT_REPORT.json
RESPONSE_BURDEN_REPORT.json
INDUCED_STIFFNESS_REPORT.json
STIFFNESS_CLOSURE_REPORT.json
STIFFNESS_FEEDBACK_REPORT.json
SOO_FUNCTIONAL_REPORT.json
```

Missing required artifacts make the case fail.

## 7. Preserved SOO architecture

The primitive SOO operator remains:

```text
association_indexed_soo_v1
```

It executes the association-indexed second-order relation:

```text
(Phi_l - A_theta_l Phi_{l-1})
-
A^*_{theta_{l+1}}(Phi_{l+1} - A_theta_{l+1} Phi_l)
-
epsilon^2 K_theta_l Phi_l
= 0
```

For the current charge modules, default stiffness is phase-specific identity:

```text
K0 = K1 = K2 = I
```

The SOO-stiffness feedback closure remains a placeholder diagnostic handle, not an admission-solving gate.

## 8. Preserved optional module architecture

Supported optional/experimental module IDs remain:

```text
soo_stiffness_feedback
charge_attraction_repulsion
gravitation
```

The framework emits:

```text
OPTIONAL_MODULE_REPORT.json
```

for module-enabled runs.

## 9. Run output layout

For a suite command with:

```bash
--output-root runs/charge_same_opposite_assoc_soo
```

the runner writes:

```text
runs/charge_same_opposite_assoc_soo/
    release_guard.json
    SUITE_RUN_REPORT.json
    SHA256SUMS.csv
    runs/
        L16_same_association_indexed_soo/
            CERTIFICATE.json
            EVIDENCE_ENVELOPE.json
            ...
        L16_opposite_association_indexed_soo/
            CERTIFICATE.json
            EVIDENCE_ENVELOPE.json
            ...
```

Failed cases write:

```text
RUN_ERROR.txt
```

inside that case output directory.

## 10. BASE/release guard behavior

The run manager calls:

```text
enforce_latest_release_guard(run_kind="candidate")
```

at suite start and again per case through the cached run environment. The cache is written under the output root so looped runs do not repeatedly fetch the remote manifest.

The release guard still checks:

- signed release manifest;
- manifest signature;
- framework code hash;
- required capabilities;
- local installed package identity.

## 11. Capabilities added in v0.1.7

```text
installed_console_run_manager
builtin_overlay_suites_package_data
code_free_run_workspaces
```

## 12. User workflow after v0.1.7

Normal workflow:

```bash
python -m pip install --force-reinstall releases/current/enforceable_rank3_modeling.zip
rank3-check-release-guard --force-refresh

cd ~/Projects/EAS_runs
rank3-init-workspace charge_assoc_workspace
cd charge_assoc_workspace
rank3-list-suites
rank3-run-suite charge_same_opposite_association_indexed \
  --output-root runs/charge_same_opposite_assoc_soo \
  --signing-key ~/.rank3/private_key.pem
```

No script copying is required. No extracted framework source tree is required.

## 13. Current limitations

1. The SOO-stiffness closure BASE gate remains postponed.
2. Charge path/support burden rules are placeholders.
3. Gravitation module exists as an optional module ID but does not yet include a full built-in suite.
4. Built-in suite resources are packaged for the charge same/opposite association-indexed tests only.
5. The top-level legacy scripts remain in the framework ZIP for backward compatibility, but candidate/admission runs should use the installed console commands.

## 14. Next recommended improvements

1. Add a built-in gravitation neutral-support path suite.
2. Add suite-level summary analysis scripts for same/opposite comparison.
3. Add `rank3-export-suite` to zip a completed suite output with checksums.
4. Promote selected controls into separate built-in control suites.
5. Replace placeholder burden rules with fully specified scalar-field-native burden definitions.
