# Dashboard Automation Index

This page is the dashboard-only automation entry point for readiness report and memory-overlap schema consumers. It keeps dashboard docs discoverable without requiring release automation links.

## Dashboard surfaces

- [dashboard readiness/schema index](../docs/dashboard-index.md) links checked readiness report examples with compact memory-overlap schema examples.
- [readiness report examples](../docs/usage-examples.md) stores the checked JSON and Markdown readiness report fences.
- [memory-overlap schema examples](../docs/dashboard-schema.md) stores the checked compact JSON Schema fence for memory-overlap demo payloads.
- [dashboard example fixture registry](../docs/dashboard-example-fixtures.md) maps split dashboard example docs to Docker-covered guard commands.
- [dashboard section writer matrix](../docs/dashboard-section-writer-matrix.md) maps dashboard readiness/schema sections to Docker-covered writer dry-runs.

## Verification commands

Run these Docker-covered commands before publishing dashboard docs changes:

```bash
r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md
r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md
r-project --root . --generate-dashboard-example-fixtures
r-project --root . --write-dashboard-example-fixtures --dry-run-dashboard-example-fixtures
r-project --root . --check-dashboard-example-fixtures
r-project --root . --check-dashboard-section-writer-matrix
r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact
r-project --root . --generate-dashboard-automation-index
r-project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index
r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
r-project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
r-project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant expanded
r-project --root . --generate-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --write-dashboard-automation-index --dry-run-dashboard-automation-index --dashboard-automation-index-variant expanded
r-project --root . --check-dashboard-automation-index --dashboard-automation-index-variant expanded
```

Run the dashboard automation index guard itself after changing links or commands:

```bash
r-project --root . --check-dashboard-automation-index
```
