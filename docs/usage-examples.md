# R Usage Examples

Dashboard and automation consumers can use this standalone README-style document when they need report examples outside the main `README.md`. The fenced examples below are generated from the current repository state and guarded by:

```bash
r-project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md
```

## JSON readiness report

```json
{"active_blockers": ["2026-07-06: `/usr/local/bin/r-bot-git-push ai/r/rustic-balance-crag` failed after local commit `97de2ea` with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). The branch is locally verified but not pushed; PR/reviewer/merge are blocked until bot push permission or credentials are restored."], "completed_backlog_items": 335, "has_active_blockers": true, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 254, "next_item": null, "open": 0}, "P2": {"completed": 77, "next_item": null, "open": 0}}, "project_name": "R"}
```

## Markdown readiness report

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 335 |
| Open backlog items | 0 |
| Active blockers | 1 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 254 | 0 | None |
| P2 | 77 | 0 | None |

## Next backlog item

None

## Active blockers

- 2026-07-06: `/usr/local/bin/r-bot-git-push ai/r/rustic-balance-crag` failed after local commit `97de2ea` with GitHub 403 (`Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`). The branch is locally verified but not pushed; PR/reviewer/merge are blocked until bot push permission or credentials are restored.
```
