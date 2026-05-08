# Release Checklist Fixtures

External release automation can keep a frozen release checklist JSON fixture outside `tests/fixtures/` when another dashboard or release system needs to validate the same payload from a stable docs path.

The checked fixture in this repository lives at `docs/release/checklist.json` and is generated from the current `pyproject.toml` version with Docker evidence enabled and git cleanliness skipped for copied/container contexts. Validate it before publishing release dashboards with:

```bash
r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
```

Preview a refreshed fixture without mutating files with:

```bash
r-project --root . --write-release-tag-fixture --dry-run-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
```

If the preview is expected, update the checked fixture with:

```bash
r-project --root . --write-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
```

Run the full clean-container verification before relying on a refreshed release checklist fixture:

```bash
docker compose run --build --rm test
```

The Docker harness also runs the docs-path check so `docs/release/checklist.json` cannot drift silently from the CLI-generated release checklist summary.
