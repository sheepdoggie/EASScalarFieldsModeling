# TDD: Separated Workspace Layout v0.1.23

## Problem

Framework update/publish files and modeling run outputs were mixed under the same subtree. That makes provenance and cleanup harder.

## Design

The recommended project tree separates install/update material from run material:

```text
Projects/
├── EASScalarFieldsModeling_github_files/
│   ├── EASScalarFieldsModeling_publish/
│   └── packages/
└── EAS_runs/
    ├── overlays/
    ├── results/
    ├── logs/
    └── workspaces/
```

## CLI

```bash
rank3-init-workspace --separate-subtrees --project-root ~/Projects
```

This writes:

- `EAS_WORKSPACE_LAYOUT.json`
- `EAS_WORKSPACE_LAYOUT.md`

## Rule

Do not put framework source trees under `EAS_runs/`. Do not put routine run outputs under the publish repository unless intentionally committing examples.
