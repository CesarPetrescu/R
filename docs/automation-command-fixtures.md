# Automation Command Fixture Index

This page is the standalone fixture index for automation-facing `r-project` commands that are documented in [`docs/automation-index.md`](automation-index.md). It lets future docs split command lists across Markdown files while preserving one auditable table that maps every command to clean-container Docker coverage.

Before publishing automation docs changes, run:

```bash
r-project --root . --check-automation-command-fixtures
docker compose run --build --rm test
```

| Source docs | Purpose | Docker-covered command |
| --- | --- | --- |
| [Automation index](automation-index.md) | Dashboard index readiness examples | `r-project --root . --check-readme-examples --readme-examples-path docs/dashboard-index.md` |
| [Automation index](automation-index.md) | Dashboard index schema examples | `r-project --root . --check-readme-schema-examples --readme-schema-path docs/dashboard-index.md` |
| [Automation index](automation-index.md) | Dashboard readiness examples in the combined automation index | `r-project --root . --check-readme-examples --readme-examples-path docs/automation-index.md` |
| [Automation index](automation-index.md) | Dashboard schema examples in the combined automation index | `r-project --root . --check-readme-schema-examples --readme-schema-path docs/automation-index.md` |
| [Automation index](automation-index.md) | Dashboard example fixture registry guard | `r-project --root . --check-dashboard-example-fixtures` |
| [Automation index](automation-index.md) | Dashboard section writer matrix guard | `r-project --root . --check-dashboard-section-writer-matrix` |
| [Automation index](automation-index.md) | Dashboard section writer matrix variant preview guard | `r-project --root . --check-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact` |
| [Automation index](automation-index.md) | Dashboard section writer matrix variant row generator | `r-project --root . --generate-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact` |
| [Automation index](automation-index.md) | Dashboard section writer matrix variant row writer dry-run | `r-project --root . --write-dashboard-section-writer-matrix --dry-run-dashboard-section-writer-matrix --dashboard-section-writer-matrix-variant compact` |
| [Automation index](automation-index.md) | Release version documentation guard | `r-project --root . --check-changelog-version` |
| [Automation index](automation-index.md) | Release tag readiness guard | `r-project --root . --check-release-tag v0.1.0 --docker-verified` |
| [Automation index](automation-index.md) | Docs-path release checklist fixture guard | `r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json` |
| [Automation index](automation-index.md) | Standalone release checklist example guard | `r-project --root . --check-release-examples --release-examples-path docs/release-examples.md` |
| [Automation index](automation-index.md) | Embedded automation-index release checklist guard | `r-project --root . --check-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'` |
| [Automation index](automation-index.md) | Embedded automation-index release checklist writer smoke | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'` |
| [Automation index](automation-index.md) | Embedded automation-index future-version release checklist writer preview | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/automation-index.md --release-examples-section 'Embedded release checklist example'` |
| [Automation index](automation-index.md) | Fixture-backed embedded release checklist writer smoke | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'` |
| [Automation index](automation-index.md) | Future-version release example docs preview | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md` |
| [Automation index](automation-index.md) | Fixture-backed future-version release example preview | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md` |
| [Automation index](automation-index.md) | Release example fixture index guard | `r-project --root . --check-release-example-fixtures` |
| [Automation index](automation-index.md) | Release example section registry guard | `r-project --root . --check-release-example-sections` |
| [Automation index](automation-index.md) | Release section writer matrix guard | `r-project --root . --check-release-section-writer-matrix` |
| [Automation index](automation-index.md) | Configurable release section writer matrix guard | `r-project --root . --check-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0` |
| [Automation index](automation-index.md) | Release section writer matrix row generator | `r-project --root . --generate-release-section-writer-matrix --release-section-writer-matrix-version 0.2.0` |
| [Automation index](automation-index.md) | Release examples path safety audit | `r-project --root . --check-release-examples-path-safety` |
| [Automation index](automation-index.md) | Automation index standalone-link guard | `r-project --root . --check-automation-index-links` |
| [Automation index](automation-index.md) | Automation index command coverage guard | `r-project --root . --check-automation-index-commands` |
| [Automation command fixture index](automation-command-fixtures.md) | Automation command fixture coverage guard | `r-project --root . --check-automation-command-fixtures` |
