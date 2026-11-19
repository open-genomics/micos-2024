# micos-2024 - Project Context

## Identity

- **Canonical repository**: `holtwood-genomics/micos-2024`
- **Lifecycle**: competition project; experimental
- **Language**: Python (production orchestrator), WDL (experimental references)

## Core contracts

| Capability | Path | Description |
|---|---|---|
| `workflow-orchestration` | `openspec/specs/workflow-orchestration/` | Production orchestrator, WDL status, resume support |

## External boundaries

- **Decision `MICOS-ORCH-001`**: Python CLI (`micos full-run`) is the sole production
  orchestrator. Shell script is a thin wrapper. WDL files are experimental single-step
  references. Resume/skip-from-checkpoint is unsupported.

## Validation commands

```bash
black --check --diff micos scripts
flake8 micos scripts
mypy micos --ignore-missing-imports
pytest tests/ -v
```

## Archived changes

Completed, merged, and moved under `openspec/changes/archive/`:

| Date | Change | Capability |
|---|---|---|
| 2026-08-19 | `declare-python-production-orchestrator` | `workflow-orchestration` |

## Authority rules

- `micos/` Python source is the implementation source of truth.
- Models must not commit, push, create PRs, or publish without explicit authorization.
- High-risk changes (orchestration, config, provenance) use lightweight OpenSpec changes.
