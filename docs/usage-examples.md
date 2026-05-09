# R Usage Examples

Dashboard and automation consumers can use this standalone README-style document when they need report examples outside the main `README.md`. The fenced examples below are generated from the current repository state and guarded by:

```bash
r-project --root . --check-readme-examples --readme-examples-path docs/usage-examples.md
r-project --root . --write-readme-examples --dry-run-readme-examples --readme-examples-path docs/usage-examples.md
```

## JSON readiness report

```json
{"active_blockers": [], "completed_backlog_items": 92, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 33, "next_item": null, "open": 0}, "P2": {"completed": 55, "next_item": null, "open": 0}}, "project_name": "R"}
```

## Markdown readiness report

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 92 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 33 | 0 | None |
| P2 | 55 | 0 | None |

## Next backlog item

None

## Active blockers

None
```
