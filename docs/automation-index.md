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
