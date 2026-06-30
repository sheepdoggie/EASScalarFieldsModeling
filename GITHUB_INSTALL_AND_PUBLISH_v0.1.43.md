# GitHub Install and Publish Notes v0.1.43

## Release

`0.1.43-whole-field-conjugate-vacuum-derived-longitudinal`

## Install locally

```bash
python -m pip install -e .
```

## Run the new exploratory whole-field runner

```bash
rank3-run-whole-field-conjugate-vacuum \
  --output-root runs/v0_1_43_whole_field_conjugate_vacuum \
  --width 4 \
  --height 4 \
  --cycles 9
```

Optional single variant:

```bash
rank3-run-whole-field-conjugate-vacuum \
  --output-root runs/v0_1_43_transverse_slot_only \
  --variant C_CONJUGATE_LINK_TRANSVERSE_SLOT
```

## Write approval packet

```bash
rank3-write-whole-field-conjugate-vacuum-packet \
  --output approval_packets/v0_1_43_whole_field_conjugate_vacuum.zip
```

## Test

```bash
python -m pytest tests/test_whole_field_conjugate_vacuum_v0143.py -q
```

## Status

Exploratory only. Do not use this release to certify photons, charge, bounded supports, Standard Model particle identity, or a path-accommodation theorem.
