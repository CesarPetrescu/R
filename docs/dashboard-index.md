# Dashboard Readiness Index

Dashboard and automation consumers can use this standalone landing page when they need one README-style document that links the checked readiness examples and checked memory-overlap schema examples.

- [Readiness report examples](usage-examples.md) provide stable JSON and Markdown output for repository-readiness dashboards.
- [Memory overlap schema examples](dashboard-schema.md) provide compact JSON Schema contracts for memory-overlap demo payload validation.

The report fences below are guarded by:

```bash
r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
```

The schema fence in the `Memory overlap demo JSON Schemas` section is guarded by:

```bash
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
```

## JSON readiness report

```json
{"active_blockers": [], "completed_backlog_items": 282, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 218, "next_item": null, "open": 0}, "P2": {"completed": 60, "next_item": null, "open": 0}}, "project_name": "R"}
```

## Markdown readiness report

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 282 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 218 | 0 | None |
| P2 | 60 | 0 | None |

## Next backlog item

None

## Active blockers

None
```

## Memory overlap demo JSON Schemas

```json
{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"memoryOverlapTotalsDemo": {"required": ["by", "totals"], "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]}}, "memoryThresholdDemo": {"required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"], "violations_item": {"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]}}}}
```
