# R Autonomous Agent Plan

> **For Hermes:** Operating specification for recurring autonomous development on `/root/hermes-workspace/R`.

**Goal:** Build project R aggressively and safely by finishing concrete backlog items each run. The agent must create and verify real code, tests, docs, and releases as the project takes shape; it must not stop at vague "improvements" when implementation work is possible.

**Architecture:** A Hermes cron job runs in `/root/hermes-workspace/R`. Each run pulls first, reads `status/`, ideates concrete product/backlog-completion tasks, evaluates impact/safety/testability, chooses the highest-impact finishable work package, researches with official docs/web/man pages as needed, implements with tests first when behavior changes, verifies locally, updates status/backlog, commits, pushes, and reports.

## Operating Principles

1. **Finish things:** Treat unchecked backlog as a queue to complete, not suggestions.
2. **Concrete implementation over polish:** Prefer shipping working features, tests, and tooling over generic cleanup or status-only edits.
3. **TDD for behavior:** Write failing tests first for behavior changes, then implement, then verify.
4. **Autonomous ideation:** If the repo is empty or underspecified, create a concrete product direction in `status/current-state.md` and `status/missing-features.md`, implement the first useful scaffold, and keep moving. Do not ask questions during cron runs.
5. **Research when unsure:** Prefer official docs; use `man` pages for local commands, C/POSIX/libc/system details, or when web docs are unavailable. Record findings in `status/research.md`.
6. **No secrets:** Never commit private keys, tokens, `.env`, or host-specific credentials.
7. **Always version controlled:** Start with `git checkout main && git pull --ff-only`; commit and push every verified change.

## Per-run Algorithm

1. Sync: `git checkout main && git pull --ff-only`; inspect `git status --short`.
2. Read `README.md`, `docs/plans/autonomous-agent.md`, and every file under `status/`.
3. Ideate several candidate work packages that would move R toward a complete, useful project.
4. Think/evaluate: impact, safety, dependencies, testability, verification cost.
5. Choose the highest-impact work package that can be completed and verified now.
6. If behavior changes, use TDD: add failing tests, confirm RED, implement, confirm GREEN.
7. Run project verification. If no language/tooling exists yet, create it and add a verification command in status.
8. Update status/backlog, including overflow ideas with concrete acceptance tests.
9. Commit and push verified changes.
10. Report compactly: ideation, selected work package, backlog items completed, tests, verification, commit/push, blockers, next item.

## Verification

Use the best available project verification. Initially, before code exists:

```bash
git diff --check
```

As soon as a language/toolchain exists, replace/extend this with real build, lint, and test commands in `status/current-state.md` and the cron prompt.

## Stop Conditions

Stop without pushing broken work if tests fail and the fix is not safe, push auth is missing, the tree has unexpected user changes, or implementation requires unsafe host actions. Record blockers in `status/stuck.md`.
