# Technical Design Document: Locked Explicit Path Construction and Closure Readouts

## 1. Purpose

This document specifies the framework extension that adds locked registry support for:

1. explicit support-to-support path construction;
2. center-locus readout;
3. structural-silence readout; and
4. Delta-L classification.

The purpose is to prevent path construction and closure diagnostics from being supplied as ad hoc Python scripts. All four functions are now part of the declarative overlay and locked registry pathway.

## 2. Scope

Included:

- `path_construction` section in declarative overlays;
- locked `linear_support_path_v0_1` construction rule;
- path-construction provenance report;
- mandatory path readouts for `two_support_explicit_path_adjustment`;
- locked center-locus diagnostic;
- locked structural-silence diagnostic;
- locked Delta-L diagnostic;
- signed evidence inclusion through readout fingerprints and compiled manifest notes.

Excluded:

- theorem admission;
- arbitrary Python path constructors;
- arbitrary Python center audits;
- arbitrary Python Delta-L classifiers;
- post-run selection of center points;
- graph-layout or visualization evidence.

## 3. Overlay Schema

The new declarative section is:

```json
"path_construction": {
  "rule": "linear_support_path_v0_1",
  "path_length": 16,
  "orientation": "opposite",
  "left_support": "support_A",
  "right_support": "support_B",
  "path_slot": 0,
  "reverse_slot": 1,
  "allow_support_overlap": false
}
```

`path_length` is interpreted as the number of declared path positions in `path_points`. If `path_points` is omitted, the compiler chooses the first available non-support points. The completed graph support-anchor edge distance is separately recorded as `path_length + 1`.

The schema remains data-only. Executable keys are still rejected.

## 4. Locked Path Constructor

The locked constructor is implemented in:

```text
rank3_enforced/path_construction.py
```

The constructor:

1. validates two declared supports;
2. selects support anchors from active phase 0, falling back to dressing, boundary, then support points;
3. selects or validates path points;
4. constructs a complete rank-3 association table;
5. freezes and fingerprints the resulting `FrozenAssociationState`;
6. emits an `ExplicitPathConstructionReport`.

The constructor is registry/core code, not overlay code.

## 5. Mandatory Model Type

The model type:

```text
two_support_explicit_path_adjustment
```

requires:

- exactly two supports;
- support-seeded initialization;
- non-overlap;
- complete active phase maps for phases 0, 1, and 2;
- `path_construction.rule = linear_support_path_v0_1`.

It automatically requires these readouts:

```text
center_locus_readout
structural_silence_readout
delta_l_classification
```

## 6. Center-Locus Readout

Implemented by:

```text
CenterLocusReadout
```

For odd declared path length:

```text
center_points = (path_points[L // 2],)
```

For even declared path length:

```text
center_points = (path_points[L // 2 - 1], path_points[L // 2])
```

The readout reports exact-zero and tolerance-zero status for single centers, and exact/tolerance balanced-edge status for center pairs.

This is diagnostic-only.

## 7. Structural-Silence Readout

Implemented by:

```text
StructuralSilenceReadout
```

It excludes center points and reports, per layer:

- non-center path point count;
- exact non-center zero count;
- tolerance-level non-center near-zero count;
- exact zero point list;
- tolerance-level near-zero point list.

This separates exact zeros from tolerance-level near zeros and prevents ambiguous report wording.

## 8. Delta-L Classification

Implemented by:

```text
DeltaLClassificationReadout
```

The classifier is deliberately conservative. It audits the declared path record and reports whether the declared path edges remain intact across association states.

It does not infer path shortening or lengthening from center values alone.

Current classifications include:

```text
no_declared_path_length_change_observed
unclassified_declared_path_disrupted
unclassified_initial_path_not_intact
```

A graph-shortest-path summary is included as a cautionary derived report, not as the classifier, because completed rank-3 filler associations can create shortcut paths that are unrelated to the declared path record.

## 9. Certification Boundary

A valid package must include these readouts through the locked registry. A package that supplies center-locus, structural-silence, or Delta-L logic in custom Python remains exploratory only.

The evidence envelope signs the compiled manifest, readout results, and framework hashes. The path construction is included through the overlay hash, manifest notes, initial association fingerprint, and readout payload fingerprints.

## 10. Admission Status

This extension provides locked diagnostics only.

It does not admit the charge closure theorem or any Delta-L theorem. It ensures that the relevant diagnostics are generated by the framework instead of by ad hoc scripts.
