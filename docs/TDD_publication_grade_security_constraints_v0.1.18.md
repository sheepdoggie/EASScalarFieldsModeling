# Publication-grade security and provenance constraints v0.1.18

This document defines the intended security boundary for publication-grade EAS diagnostic runs.

## Run classes

### Exploratory run

An exploratory run may use external scripts, notebooks, or temporary code. Its output cannot be admitted as framework-certified evidence. It must be labeled exploratory or diagnostic.

### Framework-certified run

A framework-certified run must be executed only through locked framework entry points and registry-selected rules. It must not import or execute user-supplied Python, notebook code, shell snippets, or ad hoc test logic unless that code has first been promoted into the framework, hashed, reviewed, and registered.

## Required constraints for framework-certified runs

1. Locked rule registry only.
2. No external code injection.
3. No unregistered scalar update, remap, initialization, geometry, stiffness, projection, or readout functions.
4. Source hashes for framework, runner, rule registry, geometry, initialization, stiffness, remap, update, and readout code.
5. Exact command and parameters recorded.
6. Blind generation separated from projection/readout.
7. BASE gate report included.
8. Negative controls and label-swap/sign-randomization controls included when target labels exist.
9. Immutable output package with plaintext results and duplicate encrypted results.
10. Manifest signature over all source hashes, configuration hashes, plaintext result hashes, and encrypted result hashes.
11. Verification command must recompute hashes and signature before any admission verdict.

## Duplicate encrypted results

The encrypted copy is not a substitute for hashing or signing. Its purpose is tamper-evidence and independent preservation of the exact result bundle. Publication-grade packages must include both:

```text
plaintext result bundle
encrypted duplicate bundle
signed manifest covering both
```

## Admission rule

A result is not publication-grade merely because it uses framework code. It is publication-grade only if the certified-run harness verifies that no unregistered code participated and that the signed manifest covers the full generation path.
