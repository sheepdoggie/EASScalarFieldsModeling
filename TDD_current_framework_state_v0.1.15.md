# Current Framework State v0.1.15 -- Feedback-SOO Stiffness Search

Version `0.1.15` adds a SOO-only constrained feedback stiffness-search command.  This is not a charge run and not a path-length theorem test.

## Added command

```bash
rank3-run-feedback-soo-search \
  --output-dir runs/feedback_soo_L31_same \
  --path-length 31 \
  --orientation same \
  --epsilon 0.1 \
  --period-max 512 \
  --grid-mode tied \
  --k-grid 0.01,0.03,0.1,0.3,1,3,10,30,100,300
```

The same command can be run for `--orientation opposite` to evaluate the other declarative overlay under the same SOO-only search policy.

## Search level

The implemented search is Level 1:

```text
K_theta = k_theta I, theta = 0,1,2
```

The default `--grid-mode tied` tests candidates of the form:

```text
(k0,k1,k2) = (k,k,k)
```

The optional `--grid-mode cartesian` tests the full Cartesian product of the supplied grid, subject to `--max-cartesian-candidates`.

## Guardrails

The optimizer/ranking objective uses only:

- cyclic-return spectrum;
- current-profile full recurrence residual;
- current-profile witness recurrence residual;
- both-ledgers full recurrence residual;
- both-ledgers witness recurrence residual.

Forbidden optimizer terms are explicitly reported as false:

- charge verdict target;
- path-length target;
- center-zero target;
- same/opposite theorem label;
- attraction/repulsion label.

The `orientation` argument is used only to select the declarative overlay to load. It is not used as a scoring term.

## Emitted artifacts

- `FEEDBACK_SOO_CONFIG.json`
- `FEEDBACK_SOO_SEARCH_REPORT.json`
- `K_SEARCH_GRID_REPORT.json`
- `K_CANDIDATE_SPECTRUM_REPORT.json`
- `K_RECURRENCE_RESIDUAL_REPORT.json`
- `FEEDBACK_CLOSURE_REPORT.json`
- `INITIALIZATION_SETTLING_REPORT.json`
- `k_candidate_rows.csv`
- `spectrum_rows.csv`
- `recurrence_residual_rows.csv`
- `interpolated_profile_rows.csv`

`FEEDBACK_CLOSURE_REPORT.json` is intentionally marked `not_run` in v0.1.15 because Level 1 does not implement the induced closure loop

```text
K -> SOO response -> response burden -> K' -> compare K' to K.
```

`INITIALIZATION_SETTLING_REPORT.json` is intentionally marked `not_certified`; forward settling is a separate post-selection test.

## Admission status

This revision is a candidate-search tool.  A low residual does not certify charge attraction/repulsion, does not certify path shortening/lengthening, and does not certify recurrent initialization until the appropriate downstream gates are run.
