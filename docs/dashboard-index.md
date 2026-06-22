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
{"active_blockers": ["2026-06-22: `/usr/local/bin/r-bot-git-push ai/r/rustic-band-span-gap-ratio` failed after local commit `d200d54` with GitHub 403: `Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`. Local verification, including Docker, passed before the push attempt; PR/reviewer/merge steps are blocked until app push permissions recover."], "completed_backlog_items": 187, "has_active_blockers": true, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 123, "next_item": null, "open": 0}, "P2": {"completed": 60, "next_item": null, "open": 0}}, "project_name": "R"}
```

## Markdown readiness report

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 187 |
| Open backlog items | 0 |
| Active blockers | 1 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 123 | 0 | None |
| P2 | 60 | 0 | None |

## Next backlog item

None

## Active blockers

- 2026-06-22: `/usr/local/bin/r-bot-git-push ai/r/rustic-band-span-gap-ratio` failed after local commit `d200d54` with GitHub 403: `Permission to CesarPetrescu/R.git denied to r-hermes-bot[bot]`. Local verification, including Docker, passed before the push attempt; PR/reviewer/merge steps are blocked until app push permissions recover.
```

## Memory overlap demo JSON Schemas

```json
{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"memoryOverlapTotalsDemo": {"required": ["by", "totals"], "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]}}, "memoryThresholdDemo": {"required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"], "violations_item": {"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]}}}}
```
