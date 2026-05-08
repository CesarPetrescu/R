# Automation Index Smoke Fixture

## Embedded readiness report example

```json
{"active_blockers": [], "completed_backlog_items": 71, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 33, "next_item": null, "open": 0}, "P2": {"completed": 34, "next_item": null, "open": 0}}, "project_name": "R"}
```

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 71 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 33 | 0 | None |
| P2 | 34 | 0 | None |

## Next backlog item

None

## Active blockers

None
```

## Memory overlap demo JSON Schemas

## Embedded memory-overlap schema example

```json
{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"memoryOverlapTotalsDemo": {"required": ["by", "totals"], "totals_item": {"required": ["group", "overlap_count", "total_overlap_size"]}}, "memoryThresholdDemo": {"required": ["by", "max_overlap_count", "max_total_overlap_size", "violations"], "violations_item": {"required": ["group", "overlap_count", "total_overlap_size", "max_overlap_count", "max_total_overlap_size", "exceeded"]}}}}
```

## Release automation

This fixture intentionally includes a stale release checklist fence below so the scoped dry-run writer can prove it updates only the release section while preserving the readiness and schema examples above.

## Embedded release checklist example

```json
{"checks": {"docker_verified": false, "git_clean": "skipped", "tag_matches_version": false}, "expected_tag": "v9.9.9", "ready": false, "tag": "v9.9.9", "version": "9.9.9"}
```

## Full clean verification

```bash
docker compose run --build --rm test
```
