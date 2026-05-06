# R Current State

Last updated: 2026-05-05

## Repository

- Path: `/root/hermes-workspace/R`
- Remote: `git@github.com-r:CesarPetrescu/R.git`
- Branch: `main`
- Product direction: repository-readiness toolkit for autonomous software maintenance.
- Current implementation: tested Python scaffold with `r_project` analyzer and installable `r-project` CLI, including per-priority backlog summaries and vector memory-layout padding helpers.
- Test environment: Dockerized verification via `Dockerfile` and `docker-compose.yml` service `test`.
- Example fixture: `tests/fixtures/readiness-repo/` documents expected report behavior and backs CLI tests.

## Implemented behavior

- `r_project.report.analyze_project(root)` reads a checkout and returns backlog counts, per-priority backlog groups, the next unchecked item, and active blocker status.
- `ProjectReport.to_markdown()` formats readiness data as GitHub-flavored Markdown for human status pages.
- `python3 -m r_project --root <path> --json` emits the report as stable JSON for cron/agent consumption.
- `python3 -m r_project --root <path> --markdown` emits the report as Markdown for PR comments, issue updates, and status pages.
- `python3 -m pip install -e .` installs an editable `r-project` console script for local development.
- `--fail-on-blockers` makes the CLI exit with status 2 when active blockers exist, after emitting the selected report format.
- `r_project.vector_layout(...)` calculates aligned vector payload offsets, stride, and total size so header and trailing padding are represented consistently.

## Verified commands

```bash
git diff --check
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
docker compose run --build --rm test
```

## Operating rule

The autonomous agent must turn this into a real, tested project by finishing concrete backlog items each run. It should not stop at vague improvements when code can be created safely.

Scheduled R runs are PR-first and reviewer-gated: changes must be made on `ai/r/*` branches, pushed with `/usr/local/bin/r-bot-git-push`, opened/updated as PRs to `main`, reviewed by the AI reviewer, and merged to `main` by r-coder only when `AI_REVIEW:CLEAR`, clean/mergeable state, and local Docker verification are all present.
