# Release Readiness Index

Use this page as the release automation entry point when a dashboard or maintainer needs one compact map from human release guidance to the checked machine-readable fixture.

## Release readiness surfaces

- Read the [release checklist fixture workflow](release-checklist.md) for the external fixture-path workflow, preview command, writer command, and Docker verification expectations.
- Consume the [checked release checklist JSON](release/checklist.json) from release dashboards that need a stable docs-path fixture.
- Embed the [checked release checklist examples](release-examples.md) when consumers need a README-style fenced JSON snippet near release automation docs.
- Keep package-version notes synchronized with the README and changelog before tagging.

## Guard commands

Run these commands from an editable install before publishing release automation output:

```bash
r-project --root . --check-changelog-version
r-project --root . --check-release-tag v0.1.0 --docker-verified
r-project --root . --check-release-tag-fixture --release-tag-fixture-path docs/release/checklist.json
r-project --root . --check-release-examples --release-examples-path docs/release-examples.md
```

Run the full clean-container verification before trusting the release dashboard bundle:

```bash
docker compose run --build --rm test
```

The Docker harness runs the docs-path fixture drift check, while the host release guard commands confirm the current package version, release tag, Docker evidence, and checked fixture stay aligned.
