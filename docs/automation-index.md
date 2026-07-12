# Automation Index

This page is the single navigation entry point for dashboard and release automation consumers that need stable checked docs without scanning the whole README.

## Dashboard automation

- [dashboard automation index](dashboard-automation-index.md) is the dashboard-only navigation page with link and command coverage guards.
- [dashboard readiness/schema index](dashboard-index.md) links the checked readiness report examples with compact memory-overlap schema examples.
- [readiness report examples](usage-examples.md) stores the checked JSON and Markdown readiness report fences.
- [memory overlap schema examples](dashboard-schema.md) stores the checked compact JSON Schema fence for memory-overlap demo payloads.
- [dashboard example fixture registry](dashboard-example-fixtures.md) maps split dashboard example docs to Docker-covered guard commands.
- [dashboard section writer matrix](dashboard-section-writer-matrix.md) maps dashboard readiness/schema sections to Docker-covered writer dry-runs.

Verify dashboard docs with:

```bash
r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
r-project --root . --check-readme-examples --readme-examples-path docs/automation-index.md
r-project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md
r-project --root . --generate-dashboard-automation-index
r-project --root . --generate-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index
r-project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --check-dashboard-automation-index
r-project --root . --check-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --generate-dashboard-example-fixtures
r-project --root . --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures
r-project --root . --check-dashboard-example-fixtures
r-project --root . --check-dashboard-section-writer-matrix
r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
```

## Embedded readiness report example

The combined index also embeds the checked readiness report examples directly so dashboard consumers can discover current automation metrics without following another link.

```json
{"active_blockers": [], "completed_backlog_items": 390, "has_active_blockers": false, "next_backlog_item": null, "open_backlog_items": 0, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 254, "next_item": null, "open": 0}, "P2": {"completed": 132, "next_item": null, "open": 0}}, "project_name": "R"}
```

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 390 |
| Open backlog items | 0 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 254 | 0 | None |
| P2 | 132 | 0 | None |

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

- [release automation index](release-automation-index.md) is the release-only navigation page with link and command coverage guards.
- [release readiness index](release-index.md) links release checklist fixture docs with version/tag guard commands.
- [release checklist fixture workflow](release-checklist.md) documents the external release checklist path.
- [checked release checklist JSON](release/checklist.json) is the docs-path fixture for release automation consumers.
- [checked release checklist examples](release-examples.md) provides a README-style fenced JSON snippet for dashboard docs.
- [release example fixture index](release-example-fixtures.md) lists every release-example smoke fixture and the Docker command that exercises it.
- [release example section registry](release-example-sections.md) lists independently checked Markdown release checklist sections and the Docker command that exercises each section.
- [release section writer matrix](release-section-writer-matrix.md) lists current-version and future-version writer dry-runs for every registered release checklist section.
- [automation command fixture index](automation-command-fixtures.md) maps the combined automation index commands to Docker harness coverage so future split command docs remain auditable.

Verify release docs and guards with:

```bash
r-project --root . --check-changelog-version
r-project --root . --check-release-tag v0.1.0 --docker-verified
r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
r-project --root . --check-release-examples --release-examples-path docs/release-examples.md
r-project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md
r-project --root . --check-release-example-fixtures
r-project --root . --check-release-example-sections
r-project --root . --check-release-section-writer-matrix
r-project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --check-release-examples-path-safety
r-project --root . --generate-release-automation-index
r-project --root . --write-release-automation-index --dry-run-release-automation-index
r-project --root . --check-release-automation-index
r-project --root . --check-automation-index-links
r-project --root . --check-automation-index-commands
r-project --root . --check-automation-command-fixtures
```

## Embedded release checklist example

The combined index embeds the current release checklist JSON snippet in a scoped section so release dashboards can validate one navigation page without conflicting with the readiness report JSON fence above.

```json
{"checks": {"docker_verified": true, "git_clean": "skipped", "tag_matches_version": true}, "expected_tag": "v0.1.0", "ready": true, "tag": "v0.1.0", "version": "0.1.0"}
```

## Full clean verification

Before publishing docs or release automation changes, run the complete clean-container harness:

```bash
docker compose run --build --rm test
```
