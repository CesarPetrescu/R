# Release Automation Index

This page is the release-only automation entry point for checklist, fixture, and release-section consumers. It keeps release docs discoverable without requiring dashboard automation links.

## Release surfaces

- [release readiness index](release-index.md)
- [release checklist fixture docs](release-checklist.md)
- [release checklist JSON fixture](release/checklist.json)
- [release checklist examples](release-examples.md)
- [release example fixture registry](release-example-fixtures.md)
- [release example section registry](release-example-sections.md)
- [release section writer matrix](release-section-writer-matrix.md)

## Verification commands

Run these commands from an editable install before publishing release automation output:

```bash
r-project --root . --check-changelog-version
r-project --root . --check-release-tag v0.1.0 --docker-verified
r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
r-project --root . --check-release-examples --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.3.0 --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.3.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md
r-project --root . --check-release-example-fixtures
r-project --root . --check-release-example-sections
r-project --root . --check-release-section-writer-matrix
r-project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.3.0
r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.3.0
r-project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0
r-project --root . --write-release-section-writer-matrix --dry-run-release-section-writer-matrix --release-section-writer-matrix-version 0.3.0
r-project --root . --check-release-examples-path-safety
r-project --root . --generate-release-automation-index
r-project --root . --generate-release-automation-index --release-automation-index-version 0.3.0
r-project --root . --write-release-automation-index --dry-run-release-automation-index
r-project --root . --write-release-automation-index --dry-run-release-automation-index --release-automation-index-version 0.3.0
r-project --root . --check-release-automation-index
r-project --root . --check-release-automation-index --release-automation-index-version 0.3.0
```
