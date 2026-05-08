# Automation Index

This page is the single navigation entry point for dashboard and release automation consumers that need stable checked docs without scanning the whole README.

## Dashboard automation

- [dashboard readiness/schema index](dashboard-index.md) links the checked readiness report examples with compact memory-overlap schema examples.
- [readiness report examples](usage-examples.md) stores the checked JSON and Markdown readiness report fences.
- [memory overlap schema examples](dashboard-schema.md) stores the checked compact JSON Schema fence for memory-overlap demo payloads.

Verify dashboard docs with:

```bash
r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
r-project --root . --check-readme-examples --readme-examples-path docs/automation-index.md
r-project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md
```

## Embedded readiness report example

The combined index also embeds the checked readiness report examples directly so dashboard consumers can discover current automation metrics without following another link.

```json
{"active_blockers": [], "completed_backlog_items": 69, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 33, "next_item": null, "open": 0}, "P2": {"completed": 32, "next_item": null, "open": 0}}, "project_name": "R"}
```

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 69 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 33 | 0 | None |
| P2 | 32 | 0 | None |

## Next backlog item

None

## Active blockers

None
```

## Memory overlap demo JSON Schemas

## Embedded memory-overlap schema example

The compact schema fence below is checked with the same alternate README-style path guard used by standalone dashboard docs.

```json
{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"memoryOverlapTotalsDemo": {"required": ["by", "totals"], "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]}}, "memoryThresholdDemo": {"required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"], "violations_item": {"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]}}}}
```

## Release automation

- [release readiness index](release-index.md) links release checklist fixture docs with version/tag guard commands.
- [release checklist fixture workflow](release-checklist.md) documents the external release checklist path.
- [checked release checklist JSON](release/checklist.json) is the docs-path fixture for release automation consumers.
- [checked release checklist examples](release-examples.md) provides a README-style fenced JSON snippet for dashboard docs.

Verify release docs and guards with:

```bash
r-project --root . --check-changelog-version
r-project --root . --check-release-tag v0.1.0 --docker-verified
r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
r-project --root . --check-release-examples --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
```

## Full clean verification

Before publishing docs or release automation changes, run the complete clean-container harness:

```bash
docker compose run --build --rm test
```
