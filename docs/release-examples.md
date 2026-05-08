# Release Checklist Examples

This document gives dashboard and release automation consumers a README-style Markdown surface for the release checklist JSON payload. It mirrors the checked release checklist fixture while keeping a copy-pasteable fenced block close to the release readiness index.

Generate or verify this example from current CLI output with:

```bash
r-project --root . --check-release-examples --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-path docs/release-examples.md
r-project --root . --write-release-examples --dry-run-release-examples --release-examples-version 0.2.0 --release-examples-path docs/release-examples.md
```

Use `--release-examples-version X.Y.Z` with the checker or writer to preview a
future release checklist tag in this README-style Markdown snippet before the
package version changes in `pyproject.toml`.

Current checked release checklist example:

```json
{"checks": {"docker_verified": true, "git_clean": "skipped", "tag_matches_version": true}, "expected_tag": "v0.1.0", "ready": true, "tag": "v0.1.0", "version": "0.1.0"}
```

Run the full clean-container harness before publishing release automation docs:

```bash
docker compose run --build --rm test
```
