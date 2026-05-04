# R

Project **R** is a repository-readiness toolkit for autonomous software maintenance. It turns the repo's status files into machine-readable reports so scheduled builder agents can choose concrete, safe, tested work instead of drifting into vague cleanup.

The repository is maintained by a Hermes autonomous agent. The agent is expected to implement concrete, tested features and finish backlog items, not merely perform vague improvements.

## Current product scaffold

The first scaffold is a Python package, `r_project`, with a CLI that analyzes an R checkout and reports:

- project name from `README.md`
- completed/open backlog item counts from `status/missing-features.md`
- the next unchecked backlog item
- per-priority backlog summaries (P0/P1/P2 completed/open counts and next item)
- active blockers from `status/stuck.md`
- JSON for automation or Markdown for human-readable status pages
- optional nonzero exit status when active blockers are present

Run from a checkout:

```bash
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
```

Or install the CLI in editable mode for local development:

```bash
python3 -m pip install -e .
r-project --root . --json
r-project --root . --markdown
r-project --root . --json --fail-on-blockers
```

Example output:

```json
{"active_blockers": [], "completed_backlog_items": 13, "has_active_blockers": false, "next_backlog_item": "Add release/versioning notes.", "open_backlog_items": 3, "priority_backlog_groups": {"P0": {"completed": 4, "next_item": null, "open": 0}, "P1": {"completed": 7, "next_item": null, "open": 0}, "P2": {"completed": 2, "next_item": "Add release/versioning notes.", "open": 3}}, "project_name": "R"}
```

The `--fail-on-blockers` flag still emits the requested report, then exits with status `2` when `status/stuck.md` contains active blockers. This lets cron jobs and CI gates fail fast while preserving machine-readable diagnostics on stdout.

Markdown output starts with a compact report suitable for PR comments, issue updates, or status pages:

```markdown
# R Readiness Report

| Metric | Value |
| --- | ---: |
| Completed backlog items | 13 |
| Open backlog items | 3 |
| Active blockers | 0 |

## Backlog by priority

| Priority | Completed | Open | Next item |
| --- | ---: | ---: | --- |
| P0 | 4 | 0 | None |
| P1 | 7 | 0 | None |
| P2 | 2 | 3 | Add release/versioning notes. |
```

A documented test fixture lives at `tests/fixtures/readiness-repo/` and is used by the CLI tests as an executable example of expected report behavior.

## Development

Run the host checks directly when iterating:

```bash
git diff --check
python3 -m pytest -q
PYTHONPATH=src python3 -m r_project --root . --json
PYTHONPATH=src python3 -m r_project --root . --markdown
PYTHONPATH=src python3 -m r_project --root . --json --fail-on-blockers
```

Before committing, run the same verification in Docker so tests execute in a clean, reproducible container:

```bash
docker compose run --build --rm test
```

## Autonomous maintenance

- Plan: [`docs/plans/autonomous-agent.md`](docs/plans/autonomous-agent.md)
- Cron prompt: [`docs/autonomous-agent-prompt.md`](docs/autonomous-agent-prompt.md)
- Status/backlog: [`status/`](status/)
