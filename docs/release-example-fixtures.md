# Release Example Fixture Index

This page indexes the executable Markdown smoke fixtures that protect release-example writer behavior. Use it when adding or auditing release docs fixtures so every fixture is discoverable and exercised by the clean Docker harness.

## Fixtures

| Fixture | Purpose | Docker verification command |
| --- | --- | --- |
| `tests/fixtures/automation-index-release-smoke.md` | Proves the scoped `docs/automation-index.md` release-example writer refreshes only the embedded release checklist section while preserving surrounding readiness and memory-overlap schema examples. | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path tests/fixtures/automation-index-release-smoke.md --release-examples-section 'Embedded release checklist example'` |
| `tests/fixtures/release-examples-future-version-smoke.md` | Proves future-version preview output can target a compact current-version release checklist fixture without mutating checked current-version docs. | `r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path tests/fixtures/release-examples-future-version-smoke.md` |

## Acceptance checklist for new fixtures

- Add the fixture under `tests/fixtures/` with the smallest Markdown surface that proves the intended release-example behavior.
- Add or update a host test that uses the fixture directly and confirms dry-run writer output plus non-mutation behavior.
- Add the matching command to `docker-compose.yml` so `docker compose run --build --rm test` exercises the fixture in a clean container.
- Add the fixture and command to this index so release automation consumers can audit fixture coverage from one page.

## Full clean verification

Run the index guard directly after adding or editing fixture rows so it proves every listed Docker command has equivalent clean-container coverage:

```bash
r-project --root . --check-release-example-fixtures
```

Run the full clean-container harness before publishing release-example fixture changes:

```bash
docker compose run --build --rm test
```
