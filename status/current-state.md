# R Current State

Last updated: 2026-05-06

## Repository

- Path: `/root/hermes-workspace/R`
- Remote: `git@github.com-r:CesarPetrescu/R.git`
- Branch: `main`
- Product direction: repository-readiness toolkit for autonomous software maintenance.
- Current implementation: tested Python scaffold with `r_project` analyzer and installable `r-project`/`r-project-lint` CLIs, including per-priority backlog summaries, README example drift tests and on-demand drift checks, vector memory-layout padding helpers with explicit invalid-alignment and overflow-limit errors, C-like struct memory layout helpers with explicit invalid-alignment and overflow-limit errors, release/versioning notes, and MIT licensing.
- Test environment: Dockerized verification via `Dockerfile` and `docker-compose.yml` service `test`.
- Example fixture: `tests/fixtures/readiness-repo/` documents expected report behavior and backs CLI tests.

## Implemented behavior

- `r_project.report.analyze_project(root)` reads a checkout and returns backlog counts, per-priority backlog groups, the next unchecked item, and active blocker status.
- `ProjectReport.to_markdown()` formats readiness data as GitHub-flavored Markdown for human status pages.
- `python3 -m r_project --root <path> --json` emits the report as stable JSON for cron/agent consumption.
- `python3 -m r_project --root <path> --markdown` emits the report as Markdown for PR comments, issue updates, and status pages.
- `python3 -m pip install -e .` installs an editable `r-project` console script for local development.
- `python3 -m r_project --root <path> --json --fail-on-blockers` emits the selected report and exits with status 2 when active blockers exist.
- `python3 -m r_project --root <path> --check-readme-examples` compares README JSON/Markdown examples against current generated output and exits with status 1 plus drift diagnostics when they differ.
- `python3 -m r_project.lint --root <path>` and installed `r-project-lint --root <path>` run a lightweight Python syntax lint over `src/` and `tests/`.
- `r_project.vector_layout(...)` calculates aligned vector payload offsets, stride, and total size so header and trailing padding are represented consistently; invalid negative values, zero element sizes/alignments, non-power-of-two element alignments, and optional `max_total_size` overflows raise `ValueError`.
- `r_project.memory.struct_layout(fields)` computes C-like structure offsets with per-field alignment and tail padding so arrays of structures remain aligned; invalid field sizes/alignments, non-power-of-two field alignments, and optional `max_total_size` overflows raise `ValueError`.
- Tests compare README JSON and Markdown report examples with the current CLI output so documented examples do not drift when report fields or counts change.
- `README.md` documents the current `0.1.0` semantic-versioning release policy and `CHANGELOG.md` records unreleased user-visible changes.
- `LICENSE` declares the project MIT license for Project R contributors.

## Verified commands

```bash
git diff --check
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
PYTHONPATH=src python3 -m r_project --root . --check-readme-examples
PYTHONPATH=src python3 -m r_project.lint --root .
docker compose run --build --rm test
```

## Operating rule

The autonomous agent must turn this into a real, tested project by finishing concrete backlog items each run. It should not stop at vague improvements when code can be created safely.

Scheduled R runs are PR-first and reviewer-gated: changes must be made on `ai/r/*` branches, pushed with `/usr/local/bin/r-bot-git-push`, opened/updated as PRs to `main`, reviewed by the AI reviewer, and merged to `main` by r-coder only when `AI_REVIEW:CLEAR`, clean/mergeable state, and local Docker verification are all present.
